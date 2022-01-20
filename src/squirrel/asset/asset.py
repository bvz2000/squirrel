import errno
import os
from pathlib import Path
import re
import shutil

from squirrel.shared import libtext
from squirrel.shared.squirrelerror import SquirrelError
from squirrel.asset.version import Version
from squirrel.asset.pin import Pin
from squirrel.asset.keywords import Keywords
from squirrel.asset.keyvaluepairs import KeyValuePairs
import bvzversionedfiles.bvzversionedfiles as bvzversionedfiles
from bvzversionedfiles.copydescriptor import Copydescriptor
from bvzframespec import Framespec

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

        self.version_strings = self._get_all_version_strings()
        self.version_ints = self._get_all_version_numbers()

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
    def _get_all_pins(self) -> dict:
        """
        Returns a dictionary of all the pins in the asset where the key is the pin name and the value is the version
        string the pin references.

        :return:
                A dictionary of all the pins in the asset. key=pin name, value=referenced version (as a string).
        """

        output = dict()

        if not os.path.exists(self.asset_d):
            return output

        items = os.listdir(self.asset_d)
        for potential_pin in items:
            potential_pin_p = os.path.join(self.asset_d, potential_pin)
            if os.path.islink(potential_pin_p):
                target = os.path.split(str(Path(potential_pin_p).resolve()))[1]
                result = re.match(pattern=VERSION_PATTERN, string=target)
                if result:
                    output[potential_pin] = target

        return output

    # ------------------------------------------------------------------------------------------------------------------
    def _get_all_version_strings(self) -> list:
        """
        Returns a list of all the version strings that exist on disk.

        :return:
                A list of strings that represent all of the version numbers.
        """

        output = list()

        if not os.path.exists(self.asset_d):
            return []

        items = os.listdir(self.asset_d)
        for item in items:
            if os.path.isdir(os.path.join(self.asset_d, item)):
                result = re.match(pattern=VERSION_PATTERN, string=str(item))
                if result is not None:
                    output.append(item)

        return output

    # ------------------------------------------------------------------------------------------------------------------
    def _get_all_version_numbers(self) -> list:
        """
        Returns a list of all the version numbers that exist on disk.

        :return:
                A list of integers that represent all of the version numbers.
        """

        output = list()

        for version_str in self.version_strings:
            output.append(self._version_int_from_str(version_str=version_str))

        return output

    # ------------------------------------------------------------------------------------------------------------------
    def _get_highest_ver_num(self) -> int:
        """
        Finds the highest version dir in the asset dir and returns that value.

        :return:
               The highest version dir in the asset as an int. If the asset does not have any versions yet, returns 0.
        """

        if not self.version_ints:
            return 0

        return max(self.version_ints)

    # ------------------------------------------------------------------------------------------------------------------
    def _get_next_available_ver_num(self) -> int:
        """
        Increments the current highest version and returns it as an integer.

        :return:
               The next available version number as an integer.
        """

        highest = self._get_highest_ver_num()

        return highest + 1

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
    def _version_int_from_str(self,
                              version_str) -> int:
        """
        Given a version as a string, return an integer.

        :param version_str:
                The version number as a string.
        """

        result = re.match(pattern=VERSION_PATTERN, string=str(version_str))
        if result is not None:
            return int(result.groups()[1])

        err_msg = self.localized_resource_obj.get_error_msg(11009)
        err_msg = err_msg.format(version=version_str)
        raise SquirrelError(err_msg, 11009)

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
            version = self._version_int_from_str(version)

        return version in self.version_ints

    # ------------------------------------------------------------------------------------------------------------------
    def _version_str_from_pin(self,
                              pin_n):
        """
        Given a pin, return the string of the version that this pin references. Assumes that the pin_n is a valid pin.

        :param pin_n:
                The name of the pin from which we want to extract the version string.
        """

        pin_p = os.path.join(self.asset_d, pin_n)

        return os.path.split(str(Path(pin_p).resolve()))[1]

    # ------------------------------------------------------------------------------------------------------------------
    def _pins_from_version_str(self,
                               version_str):
        """
        Given a version string, return a list of pins that reference this version.

        :param version_str:
                The version string.

        :return:
                A list of pins that reference the version. If no pins reference the version, an empty list is returned.
        """

        output = list()

        pins_n = self._get_all_pins()
        for pin_n in pins_n:
            pin_version_str = self._version_str_from_pin(pin_n)
            if pin_version_str == version_str:
                output.append(pin_n)

        return output

    # ------------------------------------------------------------------------------------------------------------------
    def _pin_exists(self,
                    pin_n) -> bool:
        """
        Given a pin, return whether this pin actually exists or not.

        :param pin_n:
                The pin.

        :return:
                True if the pin exists. False otherwise.
        """

        return pin_n in self._get_all_pins()

    # ------------------------------------------------------------------------------------------------------------------
    def _new_version_obj(self,
                         version_str=None,
                         version_must_exist=True) -> Version:
        """
        Given a version string, returns a version object. If the version_str is None, then the highest existing version
        number will be used.

        :param version_str:
                A string version or None. If None, then the highest available version number will be used. Defaults to 
                None.
        :param version_must_exist:
                If True, an error is raised if the version does not exist on disk. Defaults to True.

        :return:
                A version object.
        """

        assert version_str is None or type(version_str) is str

        if version_str is None:
            version_int = self._get_highest_ver_num()
            version_str = self._version_str_from_int(version_int=version_int)

        if not self._version_exists(version_str) and version_must_exist:
            err_msg = self.localized_resource_obj.get_error_msg(11000)
            err_msg = err_msg.format(version=str(version_str))
            raise SquirrelError(err_msg, 11000)

        return Version(version_str=version_str,
                       asset_n=self.asset_n,
                       asset_d=self.asset_d,
                       config_obj=self.config_obj,
                       localized_resource_obj=self.localized_resource_obj)

    # ------------------------------------------------------------------------------------------------------------------
    def _new_pin_obj(self,
                     pin_n,
                     pin_must_exist,
                     version_str=None):
        """
        Given a pin name, create a pin object.

        :param pin_n:
                The name of the pin.
        :param pin_must_exist:
                If True, then the pin must exist on disk or an error will be raised.
        :param version_str:
                The version string this pin will reference. Only needed when creating a new pin that does not already
                exist on disk. Ignored otherwise (set to None by default for convenience).

        :return:
                A pin object.
        """

        if not self._pin_exists(pin_n) and pin_must_exist:
            err_msg = self.localized_resource_obj.get_error_msg(11002)
            err_msg = err_msg.format(pin=pin_n)
            raise SquirrelError(err_msg, 11002)

        return Pin(pin_n=pin_n,
                   asset_d=self.asset_d,
                   version_str=version_str,
                   localized_resource_obj=self.localized_resource_obj)

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
        current_version_obj = self._new_version_obj(version_str=current_version_str,
                                                    version_must_exist=True)  # self.versions[current_version_str]

        new_version_num = self._get_next_available_ver_num()
        new_version_str = self._version_str_from_int(new_version_num)
        new_version_obj = self._new_version_obj(version_str=new_version_str,
                                                version_must_exist=False)

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
            new_version_str = self._version_str_from_int(new_version_num)
            version_obj = self._new_version_obj(version_str=new_version_str,
                                                version_must_exist=False)
            version_obj.create_dirs()

        return version_obj

    # ------------------------------------------------------------------------------------------------------------------
    def store(self,
              copydescriptors,
              merge,
              verify_copy=False,
              log_str=None):
        """
        Stores the files given by sources_obj to a new version.

        :param copydescriptors:
               A list of objects of type Copydescriptor that describe the files to be stored.
        :param merge:
               If True, then these files will be merged with the files brought forward from the previous version.
        :param verify_copy:
               If True, then each file will be checksummed before and after copying to make sure the copy worked as
               expected. Defaults to False.
        :param log_str:
                A string to use for logging. If None, nothing will be appended to the log. Defaults to None.

        :return:
               The version object where the data was stored.
        """

        assert type(copydescriptors) is list
        for copydescriptor in copydescriptors:
            assert type(copydescriptor) is Copydescriptor
        assert type(merge) is bool
        assert type(verify_copy) == bool

        version_obj = self._create_version(merge)
        bvzversionedfiles.copy_files_deduplicated(copydescriptors=copydescriptors,
                                                  dest_d=version_obj.version_d,
                                                  data_d=self.data_d,
                                                  ver_prefix="sqv",
                                                  num_digits=4,
                                                  do_verified_copy=verify_copy)

        # Create the default pin (if the config is set up to do that)
        if self.config_obj.get_boolean("asset_settings", "auto_create_default_pin"):
            pin_name = self.config_obj.get_string("asset_settings", "default_pin_name").upper()
            self.set_pin(pin_n=pin_name,
                         version_str=version_obj.version_str,
                         locked=True,
                         allow_delete_locked=True)

        if log_str is not None:
            files = [item.source_p for item in copydescriptors]
            log_msg = self.localized_resource_obj.get_msg("log_str_store")
            log_str += log_msg.format(version=version_obj.version_str, files=", ".join(files))
            self.append_to_log(log_str)

        return version_obj

    # ------------------------------------------------------------------------------------------------------------------
    def delete_version(self,
                       version_str,
                       log_str=None):
        """
        Deletes the version given by version_str.

        :param version_str:
                The string that identifies the version.
        :param log_str:
                A string to use for logging. If None, nothing will be appended to the log. Defaults to None.

        :return:
                Nothing.
        """

        pins = self._pins_from_version_str(version_str)
        if pins:
            err_msg = self.localized_resource_obj.get_error_msg(13001)
            err_msg = err_msg.format(version=version_str)
            raise SquirrelError(err_msg, 13001)

        if version_str not in self.version_strings:
            err_msg = self.localized_resource_obj.get_error_msg(11000)
            err_msg = err_msg.format(version=version_str)
            raise SquirrelError(err_msg, 11000)

        # Build a list of all the other versions so that we can build a list of their files (we will be keeping those)
        version_strings = self.version_strings.copy()  # We will be modifying this list, so make a copy
        version_strings.remove(version_str)  # Remove the version to be deleted. We don't want to keep these files.

        files_to_keep = list()
        for version_to_keep_str in version_strings:
            version_to_keep_obj = self._new_version_obj(version_str=version_to_keep_str,
                                                        version_must_exist=True)
            files_to_keep.extend(version_to_keep_obj.user_data_files())

        version_obj = self._new_version_obj(version_str=version_str,
                                            version_must_exist=True)
        version_obj.delete_version(files_to_keep=files_to_keep)

        # Update the list of versions
        self.version_strings.remove(version_str)
        self.version_ints.remove(self._version_int_from_str(version_str))

        if log_str is not None:
            log_msg = self.localized_resource_obj.get_msg("log_str_delete_version")
            log_str += log_msg.format(version=version_str)
            self.append_to_log(log_str)

    # ------------------------------------------------------------------------------------------------------------------
    def collapse(self,
                 log_str=None):
        """
        Deletes all versions in an asset except the highest version number.

        This is a DANGEROUS function and should be wrapped in a metric ton of warnings before the user is allowed to
        execute it. There is no backup and there is no undo.

        :param log_str:
                A string to use for logging. If None, nothing will be appended to the log. Defaults to None.

        :return: Nothing.
        """

        latest_version_int = self._get_highest_ver_num()
        all_version_ints = self.version_ints.copy()  # We will be modifying this list of versions
        all_version_ints.remove(latest_version_int)

        for version_int in all_version_ints:
            version_str = self._version_str_from_int(version_int)
            self.delete_version(version_str=version_str)

        if log_str is not None:
            latest_version_str = self._version_str_from_int(latest_version_int)
            log_msg = self.localized_resource_obj.get_msg("log_str_collapse")
            log_str += log_msg.format(version=latest_version_str)
            self.append_to_log(log_str)

    # ------------------------------------------------------------------------------------------------------------------
    def set_pin(self,
                pin_n,
                version_str,
                locked,
                allow_delete_locked,
                log_str=None):
        """
        Sets a pin for the current asset with the name "name" to the version given by "version".

        :param pin_n:
                The name of the pin to be set.
        :param version_str:
                The version string of the version to set the pin to.
        :param locked:
                If True, then the pin will be locked and cannot be deleted or changed by the user.
        :param allow_delete_locked:
                If True, then if there is a previous version of this pin, it will first be deleted regardless of locked
                status. If False, and if there is a previous version of this pin that is locked, then an error is
                raised.
        :param log_str:
                A string to use for logging. If None, nothing will be appended to the log. Defaults to None.

        :return:
                Nothing.
        """

        assert type(pin_n) is str
        assert type(version_str) is str

        pin_obj = self._new_pin_obj(pin_n=pin_n,
                                    pin_must_exist=False,
                                    version_str=version_str)
        pin_obj.create_link(allow_delete_locked=allow_delete_locked,
                            lock=locked)

        if log_str is not None:
            log_msg = self.localized_resource_obj.get_msg("log_str_set_pin")
            log_str += log_msg.format(version=version_str, pin=pin_n.upper())
            self.append_to_log(log_str)

    # ------------------------------------------------------------------------------------------------------------------
    def delete_pin(self,
                   pin_n,
                   allow_delete_locked=True,
                   log_str=None):
        """
        Deletes a pin from the asset.

        :param pin_n:
                The name of the pin to be removed.
        :param allow_delete_locked:
                If True, then locked pins may be deleted. If False, then locked pins may not be deleted. Defaults to
                True.
        :param log_str:
                A string to use for logging. If None, nothing will be appended to the log. Defaults to None.

        :return:
                A list of all the (user-defined) pins in the asset.
        """

        assert type(pin_n) is str

        pin_n = pin_n.upper()
        if not self._pin_exists(pin_n):
            err_msg = self.localized_resource_obj.get_error_msg(1234)
            err_msg = err_msg.format(pin_n=pin_n)
            raise SquirrelError(err_msg, 1234)

        pin_obj = self._new_pin_obj(pin_n=pin_n,
                                    pin_must_exist=True,
                                    version_str=None)
        pin_obj.delete_link(allow_delete_locked)

        if log_str is not None:
            log_msg = self.localized_resource_obj.get_msg("log_str_deleted_pin")
            log_str += log_msg.format(pin=pin_n)
            self.append_to_log(log_str)

    # ------------------------------------------------------------------------------------------------------------------
    def lock_pin(self,
                 pin_n,
                 log_str=None):
        """
        Locks a pin on the asset.

        :param pin_n:
                The name of the pin to be removed.
        :param log_str:
                A string to use for logging. If None, nothing will be appended to the log. Defaults to None.

        :return:
                A list of all the (user-defined) pins in the asset.
        """

        assert type(pin_n) is str

        pin_n = pin_n.upper()
        if not self._pin_exists(pin_n):
            err_msg = self.localized_resource_obj.get_error_msg(1234)
            err_msg = err_msg.format(pin_n=pin_n)
            raise SquirrelError(err_msg, 1234)

        pin_obj = self._new_pin_obj(pin_n=pin_n,
                                    pin_must_exist=True,
                                    version_str=None)
        pin_obj.lock()

        if log_str is not None:
            log_msg = self.localized_resource_obj.get_msg("log_str_locked_pin")
            log_str += log_msg.format(pin=pin_n)
            self.append_to_log(log_str)

    # ------------------------------------------------------------------------------------------------------------------
    def unlock_pin(self,
                   pin_n,
                   log_str=None):
        """
        unlocks a pin on the asset.

        :param pin_n:
                The name of the pin to be removed.
        :param log_str:
                A string to use for logging. If None, nothing will be appended to the log. Defaults to None.

        :return:
                A list of all the (user-defined) pins in the asset.
        """

        assert type(pin_n) is str

        pin_n = pin_n.upper()
        if not self._pin_exists(pin_n):
            err_msg = self.localized_resource_obj.get_error_msg(1234)
            err_msg = err_msg.format(pin_n=pin_n)
            raise SquirrelError(err_msg, 1234)

        pin_obj = self._new_pin_obj(pin_n=pin_n,
                                    pin_must_exist=True,
                                    version_str=None)
        pin_obj.unlock()

        if log_str is not None:
            log_msg = self.localized_resource_obj.get_msg("log_str_unlocked_pin")
            log_str += log_msg.format(pin=pin_n)
            self.append_to_log(log_str)

    # ------------------------------------------------------------------------------------------------------------------
    def list_pins(self):
        """
        Returns a list of all the pins. Just a wrapper for _get_all_pins().

        :return:
                A list of all pins.
        """

        return self._get_all_pins()

    # ------------------------------------------------------------------------------------------------------------------
    def add_thumbnails(self,
                       thumbnails_p,
                       poster_p=None,
                       version_str=None,
                       log_str=None):
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
        :param log_str:
                A string to use for logging. If None, nothing will be appended to the log. Defaults to None.

        :return:
                Nothing.
        """

        version_obj = self._new_version_obj(version_str=version_str,
                                            version_must_exist=True)
        version_obj.add_thumbnails(thumbnails_p=thumbnails_p,
                                   poster_p=poster_p)

        if log_str is not None:
            fs = Framespec()
            fs.files = thumbnails_p
            log_msg = self.localized_resource_obj.get_msg("log_str_added_thumbnails")
            log_str += log_msg.format(version=version_str, thumbnails=fs.framespec_str)
            self.append_to_log(log_str)

    # ------------------------------------------------------------------------------------------------------------------
    def delete_thumbnails(self,
                          version_str,
                          log_str=None):
        """
        Deletes the thumbnails from a specific version.

        :param version_str:
                The version to delete the thumbnails from. If None, then the latest version will be used. Defaults to
                None.
        :param log_str:
                A string to use for logging. If None, nothing will be appended to the log. Defaults to None.

        :return:
                Nothing.
        """

        # Build a list of all the other versions so that we can build a list of their files (we will be keeping those)
        version_strings = self.version_strings.copy()  # We will be modifying this list, so make a copy
        version_strings.remove(version_str)  # Remove the version to be deleted. We don't want to keep these files.

        files_to_keep = list()
        for version_to_keep_str in version_strings:
            version_to_keep_obj = self._new_version_obj(version_str=version_to_keep_str,
                                                        version_must_exist=True)
            files_to_keep.extend(version_to_keep_obj.thumbnail_data_files())

        version_obj = self._new_version_obj(version_str=version_str,
                                            version_must_exist=True)
        version_obj.delete_thumbnails(files_to_keep=files_to_keep)

        if log_str is not None:
            log_msg = self.localized_resource_obj.get_msg("log_str_deleted_thumbnails")
            log_str += log_msg.format(version=version_str)
            self.append_to_log(log_str)

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

        version_obj = self._new_version_obj(version_str=version_str,
                                            version_must_exist=True)
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

        version_obj = self._new_version_obj(version_str=version_str,
                                            version_must_exist=True)
        return version_obj.thumbnail_poster_file()

    # ------------------------------------------------------------------------------------------------------------------
    def add_keywords(self,
                     keywords,
                     log_str=None):
        """
        Adds keywords.

        :param keywords:
                A single keyword string or a list of keywords.
       :param log_str:
                A string to use for logging. If None, nothing will be appended to the log. Defaults to None.

        :return:
                Nothing.
        """

        self._create_metadata_dir()  # On the off chance the metadata dir does not already exist (old asset for example)
        self.keywords_obj.add_keywords(keywords)

        if log_str is not None:
            log_msg = self.localized_resource_obj.get_msg("log_str_add_keywords")
            log_str += log_msg.format(keywords=", ".join(keywords))
            self.append_to_log(log_str)

    # ------------------------------------------------------------------------------------------------------------------
    def delete_keywords(self,
                        keywords,
                        log_str=None):
        """
        Removes keywords given by the list keywords.

        :param keywords:
                A single keyword string or a list of keywords.
       :param log_str:
                A string to use for logging. If None, nothing will be appended to the log. Defaults to None.

        :return:
                Nothing.
        """

        assert type(keywords) is list

        self.keywords_obj.remove_keywords(keywords)

        if log_str is not None:
            log_msg = self.localized_resource_obj.get_msg("log_str_delete_keywords")
            log_str += log_msg.format(keywords=", ".join(keywords))
            self.append_to_log(log_str)

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
                            key_value_pairs,
                            log_str=None):
        """
        Adds keywords.

        :param key_value_pairs:
                A dictionary of key value pairs.
       :param log_str:
                A string to use for logging. If None, nothing will be appended to the log. Defaults to None.

        :return:
                Nothing.
        """

        assert type(key_value_pairs) is dict

        self._create_metadata_dir()  # On the off chance the metadata dir does not already exist (old asset for example)
        self.key_values_obj.add_key_value_pairs(key_value_pairs)

        if log_str is not None:
            log_msg = self.localized_resource_obj.get_msg("log_str_add_key_value_pairs")
            log_str += log_msg.format(metadata=", ".join([f"{key}={value}" for key, value in key_value_pairs.items()]))
            self.append_to_log(log_str)

    # ------------------------------------------------------------------------------------------------------------------
    def delete_key_value_pairs(self,
                               keys,
                               log_str=None):
        """
        Removes key value pairs given by the list keys.

        :param keys:
                A single key string or a list of keys.
       :param log_str:
                A string to use for logging. If None, nothing will be appended to the log. Defaults to None.

        :return:
                Nothing.
        """

        assert type(keys) is list

        self.key_values_obj.remove_key_value_pairs(keys)

        if log_str is not None:
            log_msg = self.localized_resource_obj.get_msg("log_str_delete_key_value_pairs")
            log_str += log_msg.format(keys=",".join(keys))
            self.append_to_log(log_str)

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
                          version=None,
                          log_str=None):
        """
        Sets the notes for a specified version. This is different than notes set at the asset level.

        :param notes:
                A string of notes to add.
        :param overwrite:
                If True, then the notes will overwrite the current set of notes, otherwise they will be appended.
        :param version:
                The version OR pin on which to set the notes. If the version is None, then the latest version will be
                used. Defaults to None.
        :param log_str:
                A string to use for logging. If None, nothing will be appended to the log. Defaults to None.

        :return:
                Nothing.
        """

        assert type(notes) is str
        assert type(overwrite) is bool
        assert version is None or type(version) is str or type(version) is int

        version_obj = self._new_version_obj(version)
        version_obj.add_notes(notes=notes,
                              overwrite=overwrite)

        if log_str is not None:
            log_msg = self.localized_resource_obj.get_msg("log_str_add_version_notes")
            log_str += log_msg.format(version=version, notes=notes)
            self.append_to_log(log_str)

    # ------------------------------------------------------------------------------------------------------------------
    def delete_version_notes(self,
                             version=None,
                             log_str=None):
        """
        Removes all the notes for a specified version. This is different than notes set at the asset level.

        :param version:
                The version string, version integer, OR pin from which to delete the notes. If None, then the latest
                version will be used. Defaults to None.
        :param log_str:
                A string to use for logging. If None, nothing will be appended to the log. Defaults to None.

        :return:
                Nothing.
        """

        assert version is None or type(version) is str or type(version) is int

        version_obj = self._new_version_obj(version)
        version_obj.delete_notes()

        if log_str is not None:
            log_msg = self.localized_resource_obj.get_msg("log_str_deleted_version_notes")
            log_str += log_msg.format(version=version)
            self.append_to_log(log_str)

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

        version_obj = self._new_version_obj(version)
        return version_obj.list_notes()

    # ------------------------------------------------------------------------------------------------------------------
    def add_asset_notes(self,
                        notes,
                        overwrite,
                        log_str=None):
        """
        Sets the notes for an asset as a whole. This is different than the notes set on individual versions.

        :param notes:
                A string of notes to add.
        :param overwrite:
                If True, then the notes will overwrite the current set of notes, otherwise they will be appended.
        :param log_str:
                A string to use for logging. If None, nothing will be appended to the log. Defaults to None.

        :return:
                Nothing.
        """

        assert type(notes) is str
        assert type(overwrite) is bool

        notes_p = os.path.join(self.metadata_d, "notes")
        libtext.write_to_text_file(notes_p, notes, overwrite)

        if log_str is not None:
            log_msg = self.localized_resource_obj.get_msg("log_str_added_notes")
            log_str += log_msg.format(notes=notes)
            self.append_to_log(log_str)

    # ------------------------------------------------------------------------------------------------------------------
    def delete_asset_notes(self,
                           log_str=None):
        """
        Removes all the notes for an asset as a whole. This is different than the notes set on individual versions.

        :param log_str:
                A string to use for logging. If None, nothing will be appended to the log. Defaults to None.

        :return:
                Nothing.
        """

        notes_p = os.path.join(self.metadata_d, "notes")
        if os.path.exists(notes_p):
            os.remove(notes_p)

        if log_str is not None:
            log_msg = self.localized_resource_obj.get_msg("log_str_delete_all_asset_notes")
            log_str += log_msg
            self.append_to_log(log_str)

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
