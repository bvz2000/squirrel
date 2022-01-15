import errno
import os
import re
from pathlib import Path
import shutil

from squirrel.shared import libtext
from squirrel.shared.squirrelerror import SquirrelError
from squirrel.asset.version import Version
from squirrel.asset.pin import Pin
from squirrel.asset.keywords import Keywords
from squirrel.asset.keyvaluepairs import KeyValuePairs
from squirrel.asset.sourcefile import Sourcefile
import bvzversionedfiles

from squirrel.shared.constants import *


VERSION_PATTERN = r"^(v)([0-9]{" + str(VERSION_NUM_DIGITS) + "})$"


# ======================================================================================================================
class Asset(object):
    """
    Class responsible for managing files in an arbitrary location. Stores these files as versions so that data is never
    overwritten. Uses file-level de-duplication to minimize disk space usage when managing multiple versions of the same
    files. Manages metadata about the versions and stored files.

    The structure of an asset looks like this example:

    asset_name (directory)
    - .asset (semaphore file to indicate that this is an asset directory)
    - v0001/ (directory)
    --- <user files> (symlinked to actual user files in .data)
    - v0002/ (directory)
    --- <user files> (symlinked to actual user files in .data)
    - vNNNN/ (directory)
    --- <user files> (symlinked to actual user files in .data)
    - .v0001/ (directory)
    --- notes (a file containing free-form text)
    --- thumbnails/ (directory)
    ------asset_name.1.jpg  (symlinked to actual thumbnail files in .thumbnaildata)
    ------asset_name.2.jpg  (symlinked to actual thumbnail files in .thumbnaildata)
    ------asset_name.N.jpg  (symlinked to actual thumbnail files in .thumbnaildata)
    - .v0002/ (directory)
    --- notes (a file containing free-form text)
    --- thumbnails/ (directory)
    ------asset_name.1.jpg  (symlinked to actual thumbnail files in .thumbnaildata)
    ------asset_name.2.jpg  (symlinked to actual thumbnail files in .thumbnaildata)
    ------asset_name.N.jpg  (symlinked to actual thumbnail files in .thumbnaildata)
    - .vNNNN/ (directory)
    --- notes (a file containing free-form text)
    --- thumbnails/ (directory)
    ------asset_name.1.jpg  (symlinked to actual thumbnail files in .thumbnaildata)
    ------asset_name.2.jpg  (symlinked to actual thumbnail files in .thumbnaildata)
    ------asset_name.N.jpg  (symlinked to actual thumbnail files in .thumbnaildata)
    - .data/ (directory)
    --- <actual user files - with no duplicate files. Each file is guaranteed unique.>
    - .thumbnaildata/ (directory)
    --- <actual thumbnails - with no duplicate files. Each file is guaranteed unique.>
    - .metadata/ (directory)
    --- keywords (a file containing keywords, one per line)
    --- keyvalues (a file containing key/value pairs in the format key=value)
    --- log (a file containing free-form text, typically used to store arbitrary log information)
    - LATEST (symlink to the HIGHEST v#### directory - this is optional depending on the app preferences)
    - .LATEST (symlink to the associated .v#### directory - this is optional depending on the app preferences)

    There may be additional, ALL_CAPS symlinks to various version directories (similar to LATEST). For each
    of these there will also be a .ALL_CAPS hidden symlink to the metadata .v#### directory. For example, if there is
    a symlink called TRAILER that points to v0010, then there will also be a symlink called .TRAILER that points to
    .v0010.

    The asset object NEVER alters the structure of the files passed in by the user. The single exception to this rule is
    that symlinks are converted to actual files.
    """

    # ------------------------------------------------------------------------------------------------------------------
    def __init__(self,
                 asset_parent_d,
                 name,
                 config_obj,
                 localized_resource_obj):
        """
        :param asset_parent_d:
                The directory that contains the asset. Note: this is the parent directory that contains the asset, and
                NOT a full path to the asset itself. May optionally include a trailing slash.
        :param name:
                The name of the asset.
        :param config_obj:
                A config object.
        :param localized_resource_obj:
                The localized resource object.

        :return:
               Nothing.
        """

        assert os.path.exists(asset_parent_d)
        assert os.path.isdir(asset_parent_d)
        assert name
        assert type(name) == str

        self.asset_n = name
        self.asset_parent_d = asset_parent_d.rstrip(os.sep) + os.sep
        self.asset_d = os.path.join(asset_parent_d, name).rstrip(os.sep) + os.sep

        self.data_d = os.path.join(self.asset_d, ".data")
        self.thumbnail_data_d = os.path.join(self.asset_d, ".thumbnaildata")
        self.metadata_d = os.path.join(self.asset_d, ".metadata")

        self.localized_resource_obj = localized_resource_obj
        self.config_obj = config_obj

        self.keywords_obj = Keywords(self.localized_resource_obj, self.asset_d)
        self.key_values_obj = KeyValuePairs(self.localized_resource_obj, self.asset_d)

        if os.path.exists(self.asset_d):
            self.versions = self._build_versions_dict()
            self.pins = self._build_pins_dict()
        else:
            self.pins = dict()
            self.versions = dict()

        self.data_sizes = dict()

    # ------------------------------------------------------------------------------------------------------------------
    def is_asset(self) -> bool:
        """
        Returns whether the current path for the asset is actually an asset (contains a .asset semaphore file).

        :return:
            True if the Asset refers to an actual asset on disk (has a .asset semaphore file). False otherwise.
        """

        return os.path.exists(os.path.join(self.asset_d, ".asset"))

    # ------------------------------------------------------------------------------------------------------------------
    def _get_all_version_numbers(self) -> list:
        """
        Returns a list of all the version numbers that exist on disk.

        :return:
                A list of integers that represent all of the version numbers.
        """

        output = list()

        if not os.path.exists(self.asset_d):
            return []

        items = os.listdir(self.asset_d)
        for item in items:
            if os.path.isdir(os.path.join(self.asset_d, item)):
                result = re.match(pattern=VERSION_PATTERN, string=str(item))
                if result is not None:
                    output.append(int(result.groups()[1]))

        return output

    # ------------------------------------------------------------------------------------------------------------------
    def _get_highest_ver_num(self) -> int:
        """
        Finds the highest version dir in the asset dir and returns that value.

        :return:
               The highest version dir in the asset as an int. If the asset does not have any versions yet, returns 0.
        """

        versions = self._get_all_version_numbers()
        if not versions:
            return 0

        return max(versions)

    # ------------------------------------------------------------------------------------------------------------------
    def _get_next_available_ver_num(self) -> int:
        """
        Increments the current highest version and returns it as an integer.

        :return:
               The next available version number as an integer.
        """

        highest = self._get_highest_ver_num()
        next_available = highest + 1
        return next_available

    # ------------------------------------------------------------------------------------------------------------------
    @staticmethod
    def _version_str_from_int(version_int) -> str:
        """
        Given a version as an integer, return a string formatted in the correct manner.

        :param version_int:
                The version number as an integer.
        """

        return "v{version}".format(version=str(version_int).rjust(VERSION_NUM_DIGITS, "0"))

    # ------------------------------------------------------------------------------------------------------------------
    def _version_obj_from_version_str(self,
                                      version_str=None) -> Version:
        """
        Given a version string, return the associated version object. If version_str is None, then return the highest
        possible version object.

        :param version_str:
                The version string of the version to return. If None, then return the highest possible version object.
                Defaults to None.

        :return:
                A version object.
        """

        if version_str is None:
            version_str = self._get_highest_ver_num()
            version_str = self._version_str_from_int(version_str)

        if not self._version_exists(version=version_str):
            err_msg = self.localized_resource_obj.get_error_msg(11000)
            err_msg = err_msg.format(version=version_str)
            raise SquirrelError(err_msg, 11000)

        if version_str not in self.versions.keys():
            err_msg = self.localized_resource_obj.get_error_msg(11000)
            err_msg = err_msg.format(version=version_str)
            raise SquirrelError(err_msg, 11000)

        return self.versions[version_str]

    # ------------------------------------------------------------------------------------------------------------------
    def _version_exists(self,
                        version) -> bool:
        """
        Given a version (either as an integer, string) return whether this version actually exists or not.

        :param version:
                The version integer or string.

        :return:
                True if the version exists. False otherwise.
        """

        if type(version) is str:
            result = re.match(VERSION_PATTERN, version)
            if result:
                version = int(result.groups()[1])

        return version in self._get_all_version_numbers()

    # ------------------------------------------------------------------------------------------------------------------
    def _pin_exists(self,
                    pin) -> bool:
        """
        Given a pin, return whether this pin actually exists or not.

        :param pin:
                The pin.

        :return:
                True if the pin exists. False otherwise.
        """

        if not os.path.exists(self.asset_d):
            return False

        items = os.listdir(self.asset_d)
        for item in items:
            if item == pin:
                test_p = os.path.join(self.asset_d, item)
                if os.path.islink(test_p):
                    target = os.path.split(str(Path(test_p).resolve()))[1]
                    result = re.match(pattern=VERSION_PATTERN, string=target)
                    if result:
                        return True
        return False

    # ------------------------------------------------------------------------------------------------------------------
    def create_version_obj(self,
                           version_str=None) -> Version:
        """
        Given a version string, returns a version object. If the version_str is None, then the highest existing version
        number will be used.

        :param version_str:
                A string version or None. If None, then the highest available version number will be used. Defaults to 
                None.

        :return:
                A version object.
        """

        assert version_str is None or type(version_str) is str

        if version_str is None:
            version_int = self._get_highest_ver_num()
            version_str = self._version_str_from_int(version_int=version_int)

        if not self._version_exists(version_str):
            err_msg = self.localized_resource_obj.get_error_msg(11000)
            err_msg = err_msg.format(version=str(version_str))
            raise SquirrelError(err_msg, 11000)

        return Version(version_str=version_str,
                       asset_n=self.asset_n,
                       asset_d=self.asset_d,
                       config_obj=self.config_obj,
                       localized_resource_obj=self.localized_resource_obj)

    # ------------------------------------------------------------------------------------------------------------------
    def _build_versions_dict(self) -> dict:
        """
        Returns a dictionary of all of the versions where the key is the version string and the value is a version
        object.

        :return:
                A dictionary of version objects.
        """

        output = dict()

        version_ints = self._get_all_version_numbers()
        for version_int in version_ints:
            version_str = self._version_str_from_int(version_int)
            version_obj = self.create_version_obj(version_str)
            output[version_obj.version_str] = version_obj

        return output

    # ------------------------------------------------------------------------------------------------------------------
    def _build_pins_dict(self) -> dict:
        """
        Builds a dictionary of all the pins.

        :return:
                A dictionary where the key is the pin name and the value is a pin object.
        """

        output = dict()
        items = os.listdir(self.asset_d)
        for item in items:
            test_p = os.path.join(self.asset_d, item)
            if (os.path.islink(test_p)) and item[0] != ".":
                version_str = os.readlink(test_p).lstrip(".").strip("/")
                default_pin_name = self.config_obj.get_string("asset_settings", "default_pin_name").upper()
                is_default = default_pin_name == item
                output[item] = Pin(pin_n=item,
                                   asset_d=self.asset_d,
                                   version_obj=self.versions[version_str],
                                   is_locked=is_default,
                                   localized_resource_obj=self.localized_resource_obj,
                                   config_obj=self.config_obj)

        return output

    # ------------------------------------------------------------------------------------------------------------------
    def _create_asset_directory(self):
        """
        Attempts to create the actual asset directory.

        :return:
               Nothing.
        """

        try:
            os.mkdir(self.asset_d)
        except OSError as e:
            if e.errno == errno.EEXIST and os.path.isdir(self.asset_d):
                # Someone else has already created this asset directory. That is ok.
                pass
            else:
                err_msg = self.localized_resource_obj.get_error_msg(1234)
                err_msg = err_msg.format(asset_d=self.asset_d)
                raise SquirrelError(err_msg, 1234)

    # ------------------------------------------------------------------------------------------------------------------
    def _create_asset_semaphore(self):
        """
        Attempts to create the .asset semaphore file at the root of the asset directory. This will try 100 times in case
        of an error (to deal with the case of a race condition).

        :return:
               Nothing.
        """

        if os.path.exists(os.path.join(self.asset_d, ".asset")):
            return

        try:
            with open(os.path.join(self.asset_d, ".asset"), 'w') as f:
                f.write(BVZASSET_STRUCTURE_VERSION + "\n")
        except OSError:
            err_msg = self.localized_resource_obj.get_error_msg(1234)
            err_msg = err_msg.format(asset_d=self.asset_d)
            raise SquirrelError(err_msg, 1234)

        return

    # ------------------------------------------------------------------------------------------------------------------
    def _create_data_dir(self):
        """
        Creates the data directory to hold the raw asset data.

        :return:
                Nothing.
        """

        try:
            os.mkdir(self.data_d)
        except OSError as e:
            if e.errno == errno.EEXIST and os.path.isdir(self.data_d):
                pass
            else:
                raise

    # ------------------------------------------------------------------------------------------------------------------
    def _create_thumbnail_data_dir(self):
        """
        Creates the thumbnail data directory to hold the raw thumbnail data.

        :return:
                Nothing.
        """

        try:
            os.mkdir(self.thumbnail_data_d)
        except OSError as e:
            if e.errno == errno.EEXIST and os.path.isdir(self.thumbnail_data_d):
                pass
            else:
                raise

    # ------------------------------------------------------------------------------------------------------------------
    def _create_metadata_dir(self):
        """
        Creates the metadata directory to hold the metadata.

        :return:
                Nothing.
        """

        try:
            os.mkdir(self.metadata_d)
        except OSError as e:
            if e.errno == errno.EEXIST and os.path.isdir(self.metadata_d):
                pass
            else:
                raise

    # ------------------------------------------------------------------------------------------------------------------
    def _create_asset_structure(self):
        """
        Creates the basic directory structure of the asset. (.data, .metadata, and .thumbnaildata directories)

        :return:
               Nothing.
        """

        self._create_data_dir()
        self._create_thumbnail_data_dir()
        self._create_metadata_dir()

    # ------------------------------------------------------------------------------------------------------------------
    def _create_asset(self):
        """
        Create an asset on disk. Will not do anything if the asset already exists. Does not create versions within the
        asset. This is just an empty asset structure.

        :return:
               Nothing.
        """

        self._create_asset_directory()
        self._create_asset_semaphore()
        self._create_asset_structure()

    # ------------------------------------------------------------------------------------------------------------------
    def _carry_version_forward(self):
        """
        Creates a new version and copies all of the files (symlinks) in the previous version to this new version. The
        notes are not carried forward.

        :return:
               The new version object
        """

        current_version_int = self._get_highest_ver_num()
        current_version_str = self._version_str_from_int(version_int=current_version_int)
        current_version_obj = self.versions[current_version_str]

        new_version_num = self._get_next_available_ver_num()
        new_version_obj = self.create_version_obj(new_version_num)

        shutil.copytree(src=current_version_obj.version_d,
                        dst=new_version_obj.version_d,
                        symlinks=True,
                        ignore_dangling_symlinks=True)

        shutil.copytree(src=current_version_obj.version_metadata_d,
                        dst=new_version_obj.version_metadata_d,
                        symlinks=True,
                        ignore_dangling_symlinks=True)

        # Version level notes should be removed so that it is a clean slate
        notes_p = os.path.join(new_version_obj.version_metadata_d, "notes")
        if os.path.exists(notes_p):
            os.remove(notes_p)

        return new_version_obj

    # ------------------------------------------------------------------------------------------------------------------
    def _create_version(self,
                        merge):
        """
        Creates a new version for the asset using the next available version number. If the asset is new (i.e. the
        self.asset_d does not exist on disk), then the asset dir will be created first. In other words, the act of
        creating a version is how you create an asset directory on disk.

        :param merge:
               If merge is True, then the current version's symlinks will be copied over to the new version.

        :return:
               A tuple containing the version string of the new version, and the version string of the previous version.
        """

        self._create_asset()

        if merge and self._get_highest_ver_num() > 0:
            version_obj = self._carry_version_forward()
        else:
            new_version_num = self._get_next_available_ver_num()
            version_obj = self.create_version_obj(new_version_num)
            version_obj.create_dirs()

        return version_obj
    #
    # # ----------------------------------------------------------------------------------------------------------------
    # def _copy_single_file(self,
    #                       source_obj,
    #                       verify_copy):
    #     """
    #     Copies a singe file given as src_p to the destination directory given as dst_d. File will actually be copied
    #     to
    #     the data directory, and a symlink will be made in dst_d.
    #
    #     :param source_obj:
    #             A Sourcefile object.
    #     :param verify_copy:
    #             If True, then each file will be checksummed before and after copying to make sure the copy worked as
    #             expected.
    #
    #     :return:
    #            Nothing.
    #     """
    #
    #     assert type(source_obj) is Sourcefile
    #     assert type(verify_copy) is bool
    #
    #     file_n = os.path.split(source_obj)[1]
    #
    #     bvzversionedfiles.copy_files_deduplicated(
    #         sources_p=source_obj,
    #         dest_d=dst_d,
    #         dest_n=file_n,
    #         data_d=self.data_d,
    #         ver_prefix="sqv",
    #         num_digits=4,
    #         do_verified_copy=verify_copy)
    #
    # # ----------------------------------------------------------------------------------------------------------------
    # def _copy_directory(self,
    #                     src_d,
    #                     dst_d,
    #                     skip_regex,
    #                     skip_links,
    #                     skip_external_links,
    #                     verify_copy):
    #     """
    #     Copies an entire directory given as src_p to the destination directory given as dst_d. Files will actually be
    #     copied to the data directory, and symlinks to these files will be made in dst_d.
    #
    #     :param src_d:
    #             The path to the directory to be copied.
    #     :param dst_d:
    #             The path to the destination DIRECTORY where the source file will appear to be copied. In fact, the
    #             file will be copied to the data directory and symlink with the same name will be made in dst_d.
    #     :param skip_regex:
    #             A list of regex patterns to be used to skip copying specific files. If None, then all files will be
    #             copied.
    #     :param skip_links:
    #             If True, then any symbolic links will be skipped. Otherwise, symlinks will be converted to regular les
    #             and copied as though they were real files.
    #     :param skip_external_links:
    #             If True, then any symbolic links that point to files outside of the directory being copied will be
    #             skipped.
    #     :param verify_copy:
    #             If True, then each file will be checksummed before and after copying to make sure the copy worked as
    #             expected.
    #
    #     :return:
    #             Nothing.
    #     """
    #
    #     assert os.path.exists(src_d)
    #     assert os.path.isdir(src_d)
    #     assert os.path.exists(dst_d)
    #     assert os.path.isdir(dst_d)
    #     assert type(skip_regex) is list or skip_regex is None
    #     assert type(skip_links) is bool
    #     assert type(skip_external_links) is bool
    #     assert type(verify_copy) is bool
    #
    #     # Walk through the entire source hierarchy
    #     for dir_d, sub_dirs_n, files_n in os.walk(src_d):
    #
    #         # Build the relative path to the dir in the source dir
    #         relative_d = os.path.relpath(dir_d, src_d)
    #
    #         # Build a parallel path in the destination dir
    #         curr_dest_d = os.path.join(dst_d, relative_d)
    #         if relative_d != "." and not os.path.exists(curr_dest_d):
    #             os.mkdir(curr_dest_d)
    #
    #         # Now bring over all the files in this dir
    #         for file_n in files_n:
    #
    #             source_p = os.path.join(src_d, dir_d, file_n)
    #
    #             if skip_external_links and os.path.islink(source_p):
    #                 if not bvzfilesystemlib.symlink_source_is_in_dir(link_p=source_p, path_d=src_d):
    #                     continue
    #
    #             self._copy_single_file(src_p=source_p,
    #                                    dst_d=curr_dest_d,
    #                                    skip_regex=skip_regex,
    #                                    skip_links=skip_links,
    #                                    verify_copy=verify_copy)
    #
    # # ----------------------------------------------------------------------------------------------------------------
    # def _copy_items(self,
    #                 src_p,
    #                 dst_d,
    #                 skip_links,
    #                 skip_external_links,
    #                 verify_copy):
    #     """
    #     Copy the items from src_p to dst_d. (Actually files will be copied to the data directory and symlinks to these
    #     files - with the original names - will be made in dst_d)
    #
    #     :param src_p:
    #             A list of paths to the source files OR directories to be copied. Expects a list, and each file or dir
    #             in
    #             the list must actually exist on disk.
    #     :param dst_d:
    #             The path to the destination DIRECTORY where the source file or files will APPEAR to be copied. In
    #             fact,
    #             the file will be copied to the data directory and symlink with the same name will be made in dst_d.
    #     :param skip_links:
    #             If True, then any symbolic links will be skipped. Otherwise, symlinks will be converted to regular
    #             files
    #             and copied as though they were real files.
    #     :param skip_external_links:
    #             If True, then any symbolic links that point to files outside of the directory being copied will be
    #             skipped.
    #     :param verify_copy:
    #             If True, then each file will be checksummed before and after copying to make sure the copy worked as
    #             expected.
    #
    #     :return:
    #             Nothing.
    #     """
    #
    #     assert type(src_p) is list
    #     for item in src_p:
    #         assert os.path.exists(item)
    #     assert os.path.exists(dst_d)
    #     assert os.path.isdir(dst_d)
    #     assert type(skip_links) is bool
    #     assert type(skip_external_links) is bool
    #     assert type(verify_copy) is bool
    #
    #     for src in src_p:
    #         if not os.path.isdir(src):
    #             self._copy_single_file(src_p=src,
    #                                    dst_d=dst_d,
    #                                    skip_regex=skip_regex,
    #                                    skip_links=skip_links,
    #                                    verify_copy=verify_copy)
    #         else:
    #             self._copy_directory(src_d=src,
    #                                  dst_d=dst_d,
    #                                  skip_regex=skip_regex,
    #                                  skip_links=skip_links,
    #                                  skip_external_links=skip_external_links,
    #                                  verify_copy=verify_copy)
    #
    # # ----------------------------------------------------------------------------------------------------------------
    # --
    # def _check_file_count(self,
    #                       dir_d):
    #     """
    #     Checks to see if the number of files in the passed directory is within the maximum number of files allowed to
    #     be
    #     copied (as per the config object). Raises an error if the file count is greater than the limit.
    #
    #     :param dir_d:
    #             The directory we are about to store.
    #
    #     :return:
    #             Nothing.
    #     """
    #
    #     file_count = bvzfilesystemlib.count_files_recursively(dir_d)
    #     config_limit = self.config_obj.get_integer("preferences", "file_count_warning")
    #     if file_count > config_limit:
    #         err_msg = self.localized_resource_obj.get_error_msg(12000)
    #         err_msg = err_msg.format(num_files=str(file_count), config_limit=str(config_limit))
    #         raise SquirrelError(err_msg, 12000)

    # ------------------------------------------------------------------------------------------------------------------
    def store(self,
              sources_obj,
              merge,
              verify_copy=False):
        """
        Stores the files given by sources_obj to a new version.

        :param sources_obj:
               A list of objects of type Sourcefile that describe the files to be stored.
        :param merge:
               If True, then these files will be merged with the files brought forward from the previous version.
        :param verify_copy:
               If True, then each file will be checksummed before and after copying to make sure the copy worked as
               expected. Defaults to False.

        :return:
               The version object where the data was stored.
        """

        assert type(sources_obj) is list
        for source_obj in sources_obj:
            assert type(source_obj) is Sourcefile
        assert type(merge) is bool
        assert type(verify_copy) == bool

        version_obj = self._create_version(merge)
        self.versions[version_obj.version_str] = version_obj

        sources = dict()
        for source_obj in sources_obj:
            sources[source_obj.source_p] = source_obj.dest_relative_p

        bvzversionedfiles.copy_files_deduplicated(
            sources=sources,
            dest_d=version_obj.version_d,
            data_d=self.data_d,
            ver_prefix="sqv",
            num_digits=4,
            do_verified_copy=verify_copy)

        # Create the default pin (if the config is set up to do that)
        if self.config_obj.get_boolean("preferences", "auto_create_default_pin"):
            pin_name = self.config_obj.get_string("preferences", "default_pin_name").upper()
            pin_obj = self.set_pin(pin_n=pin_name,
                                   version_str=version_obj.version_str,
                                   lock=True,
                                   allow_delete_locked=True)
            self.pins[pin_obj.pin_n] = pin_obj

        return version_obj

    # ------------------------------------------------------------------------------------------------------------------
    def collapse(self):
        """
        Deletes all versions in an asset except the highest version number.

        This is a DANGEROUS function and should be wrapped in a metric ton of warnings before the user is allowed to
        execute it. There is no backup and there is no undo.

        :return: Nothing.
        """

        latest_version_obj = self.create_version_obj(None)
        # all_version_objs = self._get_all_versions()

        for version_obj in self.versions.values():
            if version_obj.version_int != latest_version_obj.version_int:
                version_obj.delete_version(all_version_objs=self.versions.values(),
                                           pins=self.pins)

    # ------------------------------------------------------------------------------------------------------------------
    def set_pin(self,
                pin_n,
                version_str,
                lock,
                allow_delete_locked):
        """
        Sets a pin for the current asset with the name "name" to the version given by "version".

        :param pin_n:
                The name of the pin to be set.
        :param version_str:
                The version string of the version to set the pin to.
        :param lock:
                If True, then the pin will be locked and cannot be deleted or changed by the user.
        :param allow_delete_locked:
                If True, then if there is a previous version of this pin, it will first be deleted regardless of locked
                status. If False, and if there is a previous version of this pin that is locked, then an error is
                raised.

        :return:
                The pin object.
        """

        assert type(pin_n) is str
        assert type(version_str) is str

        version_obj = self._version_obj_from_version_str(version_str)

        try:
            pin_obj = self.pins[pin_n]
        except KeyError:
            pin_obj = Pin(pin_n=pin_n,
                          asset_d=self.asset_d,
                          version_obj=version_obj,
                          is_locked=lock,
                          localized_resource_obj=self.localized_resource_obj,
                          config_obj=self.config_obj)

        pin_obj.create_link(allow_delete_locked)

        return pin_obj

    # ------------------------------------------------------------------------------------------------------------------
    def delete_pin(self,
                   pin_n,
                   allow_delete_locked=True):
        """
        Deletes a pin from the asset.

        :param pin_n:
                The name of the pin to be removed.

        :param allow_delete_locked:
                If True, then locked pins may be deleted. If False, then locked pins may not be deleted. Defaults to
                True.

        :return:
                A list of all the (user-defined) pins in the asset.
        """

        assert type(pin_n) is str

        pin_n = pin_n.upper()
        if pin_n not in self.pins.keys():
            err_msg = self.localized_resource_obj.get_error_msg(1234)
            err_msg = err_msg.format(pin_n=pin_n)
            raise SquirrelError(err_msg, 1234)

        self.pins[pin_n].delete_link(allow_delete_locked)
        del self.pins[pin_n]

    # ------------------------------------------------------------------------------------------------------------------
    def list_versions(self):
        """
        Returns a list of all the versions (as strings).

        :return:
                A list of all versions as strings.
        """

        output = list()

        version_objs = self.versions.values()
        for version_obj in version_objs:
            output.append(version_obj.version_str)

        return output

    # ------------------------------------------------------------------------------------------------------------------
    def list_pins(self):
        """
        Returns a list of all the pins.

        :return:
                A list of all pins.
        """

        pins = self._build_pins_dict()

        return list(pins.keys())

    # ------------------------------------------------------------------------------------------------------------------
    def add_thumbnails(self,
                       thumbnails_p,
                       poster_p=None,
                       version_str=None):
        """
        Adds thumbnail images. If version is None, then the thumbnails will be set on the latest version. If
        poster_frame is not None, then the poster_frame will be set to that frame number. If poster is None, then the
        poster frame will be set to the first frame. Thumbnails are stored using the same deduplication method as
        regular asset files.

        :param thumbnails_p:
                The list of thumbnail files to add.
        :param poster_p:
                A path to an optional poster frame. If None, then the first frame of the thumbnails is used as a poster.
                Defaults to None.
        :param version_str:
                The version to add the thumbnails to. If None, then the latest version will be used. Defaults to None.

        :return:
                Nothing.
        """

        version_obj = self._version_obj_from_version_str(version_str=version_str)
        version_obj.add_thumbnails(thumbnails_p=thumbnails_p,
                                   poster_p=poster_p)

    # ------------------------------------------------------------------------------------------------------------------
    def delete_thumbnails(self,
                          version_str):
        """
        Deletes the thumbnails from a specific version.

        :param version_str:
                The version to delete the thumbnails from. If None, then the latest version will be used. Defaults to
                None.

        :return:
                Nothing.
        """

        version_obj = self._version_obj_from_version_str(version_str=version_str)
        version_obj.delete_thumbnails(all_version_objs=list(self.versions.values()))

    # ------------------------------------------------------------------------------------------------------------------
    def list_thumbnails(self,
                        version_str):
        """
        Returns a list of all the thumbnail files (with full paths) for the version given.

        :param version_str:
                The version string from the version from which we want the list of thumbnails.

        :return:
                A list of thumbnails (including full paths).
        """

        version_obj = self._version_obj_from_version_str(version_str=version_str)

        return version_obj.thumbnail_symlink_files()

    # ------------------------------------------------------------------------------------------------------------------
    def list_poster(self,
                    version_str):
        """
        Returns a path to the thumbnail poster file for the version given.

        :param version_str:
                The version string from the version from which we want the poster frame.

        :return:
                A path to the thumbnail poster file.
        """

        version_obj = self._version_obj_from_version_str(version_str=version_str)

        return version_obj.thumbnail_poster_file()

    # ------------------------------------------------------------------------------------------------------------------
    def add_keywords(self,
                     keywords):
        """
        Adds keywords.

        :param keywords:
                A single keyword string or a list of keywords.

        :return:
                Nothing.
        """

        self._create_metadata_dir()  # On the off chance the metadata dir does not already exist (old asset for example)
        self.keywords_obj.add_keywords(keywords)

    # ------------------------------------------------------------------------------------------------------------------
    def delete_keywords(self,
                        keywords):
        """
        Removes keywords given by the list keywords.

        :param keywords:
                A single keyword string or a list of keywords.

        :return:
                Nothing.
        """

        assert type(keywords) is list

        self.keywords_obj.remove_keywords(keywords)

    # ------------------------------------------------------------------------------------------------------------------
    def list_keywords(self):
        """
        Lists all of the keywords.

        :return:
                A list of keywords.
        """

        try:
            return self.keywords_obj.list_keywords()
        except SquirrelError:  # TODO: Why am I trapping an error at this level?
            return []

    # ------------------------------------------------------------------------------------------------------------------
    def add_key_value_pairs(self,
                            key_value_pairs):
        """
        Adds keywords.

        :param key_value_pairs:
                A dictionary of key value pairs.

        :return:
                Nothing.
        """

        assert type(key_value_pairs) is dict

        self._create_metadata_dir()  # On the off chance the metadata dir does not already exist (old asset for example)
        self.key_values_obj.add_key_value_pairs(key_value_pairs)

    # ------------------------------------------------------------------------------------------------------------------
    def delete_key_value_pairs(self,
                               keys):
        """
        Removes key value pairs given by the list keys.

        :param keys:
                A single key string or a list of keys.

        :return:
                Nothing.
        """

        assert type(keys) is list

        self.key_values_obj.remove_key_value_pairs(keys)

    # ------------------------------------------------------------------------------------------------------------------
    def list_key_value_pairs(self):
        """
        Lists all of the key value pairs.

        :return:
                A dictionary of key value pairs.
        """

        try:
            return self.key_values_obj.get_key_value_pairs()
        except SquirrelError:
            return {}

    # ------------------------------------------------------------------------------------------------------------------
    def add_version_notes(self,
                          notes,
                          overwrite,
                          version=None):
        """
        Sets the notes for a specified version. This is different than notes set at the asset level.

        :param notes:
                A string of notes to add.
        :param overwrite:
                If True, then the notes will overwrite the current set of notes, otherwise they will be appended.
        :param version:
                The version OR pin on which to set the notes. If the version is None, then the latest version will be
                used. Defaults to None.

        :return:
                Nothing.
        """

        assert type(notes) is str
        assert type(overwrite) is bool
        assert version is None or type(version) is str or type(version) is int

        version_obj = self.create_version_obj(version)
        version_obj.add_notes(notes=notes,
                              overwrite=overwrite)

    # ------------------------------------------------------------------------------------------------------------------
    def delete_version_notes(self,
                             version=None):
        """
        Removes all the notes for a specified version. This is different than notes set at the asset level.

        :param version:
                The version string, version integer, OR pin from which to delete the notes. If None, then the latest
                version will be used. Defaults to None.

        :return:
                Nothing.
        """

        assert version is None or type(version) is str or type(version) is int

        version_obj = self.create_version_obj(version)
        version_obj.delete_notes()

    # ------------------------------------------------------------------------------------------------------------------
    def list_version_notes(self,
                           version=None):
        """
        Display the notes for a specified version. This is different than notes set at the asset level.

        :param version:
                The version string, version integer, OR pin from which to read the notes. If None, then the latest
                version will be used. Defaults to None.

        :return:
                Nothing.
        """

        assert version is None or type(version) is str or type(version) is int

        version_obj = self.create_version_obj(version)
        return version_obj.list_notes()

    # ------------------------------------------------------------------------------------------------------------------
    def add_asset_notes(self,
                        notes,
                        overwrite):
        """
        Sets the notes for an asset as a whole. This is different than the notes set on individual versions.

        :param notes:
                A string of notes to add.
        :param overwrite:
                If True, then the notes will overwrite the current set of notes, otherwise they will be appended.

        :return:
                Nothing.
        """

        assert type(notes) is str
        assert type(overwrite) is bool

        notes_p = os.path.join(self.metadata_d, "notes")
        libtext.write_to_text_file(notes_p, notes, overwrite)

    # ------------------------------------------------------------------------------------------------------------------
    def delete_asset_notes(self):
        """
        Removes all the notes for an asset as a whole. This is different than the notes set on individual versions.

        :return:
                Nothing.
        """

        notes_p = os.path.join(self.metadata_d, "notes")
        if os.path.exists(notes_p):
            os.remove(notes_p)

    # ------------------------------------------------------------------------------------------------------------------
    def list_asset_notes(self):
        """
        Display the notes for an asset as a whole. This is different than the notes set on individual versions.

        :return:
                Nothing.
        """

        output = ""
        notes_p = os.path.join(self.metadata_d, "notes")
        if os.path.exists(notes_p):
            with open(notes_p, "r") as f:
                lines = f.readlines()
            output = [line.rstrip() for line in lines]
            output = "\n".join(output)

        return output

    # ------------------------------------------------------------------------------------------------------------------
    def append_to_log(self,
                      text):
        """
        Appends arbitrary information to the log file. This ALWAYS appends.

        :param text:
                The string to append to the log file.

        :return:
                Nothing.
        """

        assert type(text) is str

        log_p = os.path.join(self.asset_d, ".metadata", "log")
        libtext.write_to_text_file(file_p=log_p,
                                   text=text,
                                   overwrite=False)

    # ------------------------------------------------------------------------------------------------------------------
    def display_log(self):
        """
        Display the log.

        :return:
                Nothing.
        """

        output = ""

        log_p = os.path.join(self.asset_d, ".metadata", "log")
        if os.path.exists(log_p):
            with open(log_p, "r") as f:
                lines = f.readlines()
            output = [line.rstrip() for line in lines]
            output = "\n".join(output)

        return output
