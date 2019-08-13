"""
License
--------------------------------------------------------------------------------
Squirrel is released under version 3 of the GNU General Public License.

squirrel
Copyright (C) 2019  Bernhard VonZastrow

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import errno
import inspect
import os
import re
import shutil

from bvzlib import resources
from bvzlib import filesystem
from bvzlib import config

from shared import envvars

import meta
import pin


class Asset(object):
    """
    Class responsible for copying source files into a versioned destination.

    In the division of labor of the asset management, squirrel handles
    everything from the asset name down to the individual version directories.
    This includes all metadata and thumbnails stored within the asset. Once
    within a version directory, no squirrel related files will be stored (only
    the actual files provided to squirrel by the end user).

    So, the structure looks like this:

    /some/dirs/that/may/be/manged/elsewhere

    Within this location (which can be anywhere as far as squirrel is concerned)
    you will get something like this structure:

    asset_name
    - v0001/ (directory)
    --- <user files> (symlinked to actual user files in .data)
    - v0002/ (directory)
    --- <user files> (symlinked to actual user files in .data)
    - vNNNN/ (directory)
    --- <user files> (symlinked to actual user files in .data)
    - .v0001/ (directory)
    --- metadata
    --- keywords
    --- thumbnails/ (directory)
    ------asset_name.1.jpg  (symlinked to actual user files in .thumbnaildata)
    ------asset_name.2.jpg  (symlinked to actual user files in .thumbnaildata)
    ------asset_name.N.jpg  (symlinked to actual user files in .thumbnaildata)
    - .v0002/ (directory)
    --- metadata
    --- keywords
    --- thumbnails/ (directory)
    ------asset_name.1.jpg  (symlinked to actual thumbnails in .thumbnaildata)
    ------asset_name.2.jpg  (symlinked to actual thumbnails in .thumbnaildata)
    ------asset_name.N.jpg  (symlinked to actual thumbnails in .thumbnaildata)
    - .vNNNN/ (directory)
    --- metadata
    --- keywords
    --- thumbnails/ (directory)
    ------asset_name.1.jpg  (symlinked to actual thumbnails in .thumbnaildata)
    ------asset_name.2.jpg  (symlinked to actual thumbnails in .thumbnaildata)
    ------asset_name.N.jpg  (symlinked to actual thumbnails in .thumbnaildata)
    - .data/ (directory)
    --- <actual user files>
    - .thumbnaildata/ (directory)
    --- <actual thumbnails>

    With the exception of actually copying the data to live inside the version
    directories (actually as symlinks to the asset .data dir), squirrel only
    handles versioning and storing metadata, and never alters the structure
    inside a version dir.
    """

    # --------------------------------------------------------------------------
    def __init__(self, name, asset_parent_d, src_p=None, metadata=None,
                 keywords=None, notes=None, thumbnails=None, poster_frame=None,
                 merge=True, pins=None, verify_copy=False, language="english"):
        """
        An object responsible for copying a directory (or file) from one
        location to another (versioned) location.

        :param name: The name of the thing we are storing. Note that this is not
               necessarily the file name of the thing we are storing (though you
               could use the file name if desired).
        :param asset_parent_d: Either:

               The full path to where the source directory will be copied to.

               OR

               the full path to the parent directory of an existing asset we
               will be modifying.

               ------ Copying Files ------
               All of the actual files are stored in version directories inside
               of a sub-directory named <name>.

               For example, if we are copying the source dir:

               /the/source/dir/some_files_dir

               Then the destination should be something like this (note that it
               does not contain the actual name of the source file or dir):

               /some/destination/dir/

               The files will then be stored in version sub-directories inside a
               subdir that is named <name>. In our example it would look
               something like shown below. Note that <name> does not have to
               match "some_files_dir" of the source dir, though it may match if
               desired:

               /some/destination/dir/<name>/v0001/file1
               /some/destination/dir/<name>/v0001/file2
               etc...

               ------ Modifying An Existing Asset ------
               If we are modifying an asset (named <name>) then we would use
               asset_parent_d to indicate the parent directory of that asset.

               For example, if the asset <name> had a path of:

               /some/asset/location/<name>

               Then asset_parent_d should be:

               /some/asset/location/
        :param src_p: A full path to the directory OR file being copied. May be
               set to None for cases where we are modifying an existing asset.
               Defaults to None.
        :param metadata: A dictionary of key, value pairs that defines arbitrary
               metadata for this asset. If None, no metadata will be stored.
               Defaults to None.
        :param keywords: An optional list of keywords. If None, no keywords will
               be stored. Defaults to None.
        :param notes: An optional string containing free-form text. If None, no
               notes will be stored. Defaults to None.
        :param thumbnails: An optional list of full paths to thumbnail images.
               There may be as many thumbnails as desired (for example: a full
               turntable). The files MUST be named in the following format:

               asset_name.####.ext

               Where the asset_name is identical to the name of the asset_d dir,
               the #### digits are frame numbers (required even if there is only
               a single file), and ext is the file extension. If None, then no
               thumbnails will be stored (but any previously stored will be
               carried forward from the previous version as symlinks). Defaults
               to None.
        :param poster_frame: The frame number (as an integer or string that
               evaluates to an integer) that indicates which frame of the
               thumbnails to make the poster frame. If None, and thumbnails are
               provided, then the first frame will be made into the poster.
               Defaults to None.
        :param merge: If True, then carry forward an files from the previous
               version that were not explicitly added in this operation. This
               allows for multiple publishes to layer together (i.e. publish
               a model asset as version 1, and publish a material definition as
               version 2 -> The model file(s) will be carried forward to version
               2 as though they had been explicitly published a second time).
               Defaults to True.
        :param pins: A list of pins to set to point to the newly created
               version. These are in addition to the automatic "LATEST" and
               "CURRENT".
        :param verify_copy: If True, then an md5 checksum will be done on each
               source and each copy to ensure that the file was copied
               correctly. Defaults to False.
        :param language: The language used for communication with the end user.
               Defaults to "english".
        """

        assert name != ""

        module_d = os.path.split(inspect.stack()[0][1])[0]
        resources_d = os.path.join(module_d, "..", "..", "resources")
        config_d = os.path.join(module_d, "..", "..", "config")
        self.resc = resources.Resources(resources_d, "lib_store", language)

        self.src_p = src_p
        self.name = name

        self.asset_parent_d = asset_parent_d
        self.asset_d = os.path.join(asset_parent_d, self.name)

        self.data_d = os.path.join(self.asset_d, ".data")
        self.data_sizes = filesystem.files_keyed_by_size(self.data_d)

        self.thumbnail_data_d = os.path.join(self.asset_d, ".thumbnaildata")

        self.prev_ver_n = self.get_highest_ver()
        self.prev_ver_d = os.path.join(self.asset_d, self.prev_ver_n)

        self.curr_ver_n = None
        self.curr_ver_d = None
        self.metadata_d = None

        self.metadata = metadata
        self.keywords = keywords
        self.notes = notes
        self.thumbnails = thumbnails
        self.poster_frame = poster_frame

        self.merge = merge
        self.pins = pins
        self.verify_copy = verify_copy
        self.language = language

        # Read the squirrel config file (if the user sets the env variable
        # then that value will be used. Otherwise, read it from the app
        # resources directory)
        config_p = os.path.join(config_d, "store.config")
        self.config_obj = config.Config(config_p,
                                        envvars.SQUIRREL_STORE_CONFIG_PATH)

        # Get the list of regex patterns that we will use to skip files
        skip_list_regex = self.config_obj.items("skip list regex")
        self.skip_list_regex = [item[0] for item in skip_list_regex]

    # --------------------------------------------------------------------------
    def get_highest_ver(self):
        """
        Finds the highest version dir in the destination dir and returns that
        value. This is technically the current highest version, but we refer to
        it as the previous version as it is about to be superseded with a newer
        version.

        :return: THe highest version dir in the destination dir. If the dest
                 dir does not exist, or there are no current version dirs,
                 returns v0000.
        """

        if not os.path.exists(self.asset_d):
            return "v0000"
        
        highest = 0
        pattern = r"(v)([0-9]*[0-9]*[0-9]*[0-9]+)"
        
        items = os.listdir(self.asset_d)
        for item in items:
            if os.path.isdir(os.path.join(self.asset_d, item)):
                result = re.match(pattern, item)
                if result is not None:
                    highest = max(highest, int(result.groups()[1]))
        
        if highest > 9999:
            err = self.resc.error(103)
            raise ValueError(err.msg)
        
        return "v" + str(highest).rjust(4, "0")

    # --------------------------------------------------------------------------
    def get_next_available_ver(self):
        """
        Increments the current highest version (actually stored under
        prev_ver_d) and returns a formatted string with that value (v####)..

        :return: The next available version number, formatted as v####.
        """

        highest = int(self.prev_ver_d.split("v")[1])
        return "v" + str(highest + 1).rjust(4, "0")

    # --------------------------------------------------------------------------
    def create_asset(self):
        """
        Create an asset on disk. Will not do anything if the asset already
        exists. Note: This should probably not be called from outside this
        module. Use the reserve_version method to create a new asset.

        :return: Nothing.
        """

        try:
            os.mkdir(self.asset_d)
        except OSError as e:
            if e.errno == errno.EEXIST and os.path.isdir(self.asset_d):
                # Someone else has already created this asset, That is ok, but
                # don't continue. Let them finish creating the .asset file.
                # This could be problematic if the directory exists for some
                # other reason, but isn't actually an asset dir. But that is an
                # issue that is outside the scope of squirrel, and there is no
                # programmatic way of dealing with that.
                return
            else:
                raise  # Some other error happened, so bail.
        else:
            open(os.path.join(self.asset_d, ".asset"), 'w').close()
            os.mkdir(self.data_d)
            os.mkdir(self.thumbnail_data_d)

    # --------------------------------------------------------------------------
    def create_version_metadata_dir(self):
        """
        Creates the metadata dir for the current version (named .v#### in the
        self.asset_d directory).

        :return: Nothing.
        """

        # Create the metadata dir
        metadata_d = os.path.join(self.asset_d, "." + self.curr_ver_n)
        try:
            os.mkdir(metadata_d)
        except IOError as e:
            if e.errno == errno.EEXIST and os.path.isdir(metadata_d):
                pass
            else:
                raise

        # Create the thumbnails dir
        thumbnails_d = os.path.join(metadata_d, "thumbnails")
        try:
            os.mkdir(thumbnails_d)
        except IOError as e:
            if e.errno == errno.EEXIST and os.path.isdir(thumbnails_d):
                pass
            else:
                raise

        # symlink the .metadata dir to this version's metadata dir.
        top_metadata_d = os.path.join(self.asset_d, ".metadata")
        if os.path.exists(top_metadata_d):
            if os.path.islink(top_metadata_d):
                os.unlink(top_metadata_d)
            else:
                err = self.resc.error(104)
                raise ValueError(err.msg)
        os.symlink("./." + self.curr_ver_n, top_metadata_d)

    # --------------------------------------------------------------------------
    def reserve_version(self):
        """
        Reserves a version number for the asset. If the asset is new (i.e. the
        self.asset_d does not exist on disk), then the asset dir will be created
        first. In other words, the act of reserving a version is how you create
        an asset directory on disk. Should be race condition safe.

        :return: A full path to the version that was reserved.
        """

        # Try to create the dir on disk
        self.create_asset()

        # Try to actually reserve the version
        attempt_count = 0
        num_attempts = 100
        while attempt_count < num_attempts:

            attempt_count += 1

            # Get the next version number in this asset
            res_version = self.get_next_available_ver()

            # Try to create the version dir
            asset_version_d = os.path.join(self.asset_d, res_version)
            try:
                os.mkdir(asset_version_d)
            except IOError as e:
                if e.errno == errno.EEXIST:
                    pass  # Someone goi in first, so do nothing and try again
                else:
                    raise  # Some other error occurred, so bail.
            else:  # We succeeded

                # Record this location and name
                self.curr_ver_d = asset_version_d
                self.curr_ver_n = res_version

                # Create the version metadata dir
                self.create_version_metadata_dir()

                # And peace out
                return

        # If we get this far, then we timed out
        err = self.resc.error(105)
        err.msg = err.msg.format(asset_name=os.path.split(self.asset_d)[1],
                                 num_attempts=num_attempts)
        raise ValueError(err.msg)

    # --------------------------------------------------------------------------
    def merge_dir(self):
        """
        Carries forward any files in the previous version that are not in the
        current version.

        :return: A list of the files that were merged.
        """

        files_merged = list()

        # Walk the previous version directory
        for dir_d, sub_dirs_n, files_n in os.walk(self.prev_ver_d):

            # Create a relative directory for the current subdir of the prev
            # version
            relative_d = os.path.relpath(dir_d, self.prev_ver_d)

            # Build the parallel dir in the current version
            dest_d = os.path.join(self.curr_ver_d, relative_d)

            # Create this new parallel dir in the current version
            if relative_d != ".":
                try:
                    os.mkdir(dest_d)
                except OSError:
                    pass

            # Now process each of the files in this subdir of the previous
            # versions.
            for file_n in files_n:
                file_p = os.path.join(dir_d, file_n)

                # Just like before, build the relative path to this file in the
                # previous version
                relative_p = os.path.relpath(file_p, self.prev_ver_d)

                # And then build the parallel path in the current version.
                dest_p = os.path.join(self.curr_ver_d, relative_p)

                # If this file does not already exist, copy it from the previous
                # version, following symlinks if needed.
                if not os.path.exists(dest_p):

                    # Check to see if the file is a symlink (it most likely is)
                    # If so, just make a link in the current version to the
                    # source file. Otherwise, copy the file. Note: un Python 3.7
                    # we can do this by setting follow_symlinks=False. But none
                    # of my DCC applications are using 3.7 so here we are...
                    if os.path.islink(file_p):
                        # Note: The following is broken in Windows!!
                        real_p = os.path.realpath(file_p)
                        os.symlink(real_p, dest_p)
                    else:
                        shutil.copy(file_p, dest_p)
                    files_merged.append(dest_p)

        return files_merged

    # --------------------------------------------------------------------------
    def store(self):
        """
        Actually copy the files from self.src_p to self.asset_d. (Actually files
        will be copied to self.data_d and symlinks will be made in self.asset_d)

        :return: True if the copy is successful, False otherwise.
        """

        # If self.src_p is a file, handle it differently than if it is a dir.
        if not os.path.isdir(self.src_p):
            file_n = os.path.split(self.src_p)[1]
            if file_n not in self.skip_list_regex:
                dest_p = os.path.join(self.curr_ver_d, file_n)
                copied_p = filesystem.copy_file_deduplicated(self.src_p,
                                                             dest_p,
                                                             self.data_d,
                                                             self.data_sizes,
                                                             "sqv",
                                                             4)
                if self.verify_copy:
                    src_md5 = filesystem.md5_for_file(self.src_p)
                    copied_md5 = filesystem.md5_for_file(copied_p)
                    if src_md5 != copied_md5:
                        err = self.resc.error(110)
                        err.msg = err.msg.format(source=self.src_p,
                                                 copy=copied_p)
                        raise OSError(err.msg)

        else:

            # Walk through the entire source hierarchy
            for dir_d, sub_dirs_n, files_n in os.walk(self.src_p):

                # Build the relative path to the dir in the source dir
                relative_d = os.path.relpath(dir_d, self.src_p)

                # Build a parallel path in the destination dir
                dest_d = os.path.join(self.curr_ver_d, relative_d)
                if relative_d != ".":
                    os.mkdir(dest_d)

                # Now bring over all the files in this dir
                for file_n in files_n:

                    skip = False
                    for pattern in self.skip_list_regex:
                        result = re.match(pattern, file_n)
                        if result:
                            skip = True

                    if not skip:
                        source_p = os.path.join(self.src_p, dir_d, file_n)
                        dest_p = os.path.join(dest_d, file_n)
                        copied_p = filesystem.copy_file_deduplicated(source_p,
                                                                dest_p,
                                                                self.data_d,
                                                                self.data_sizes,
                                                                "sqv",
                                                                4)

                        if self.verify_copy:
                            src_md5 = filesystem.md5_for_file(source_p)
                            copied_md5 = filesystem.md5_for_file(copied_p)
                            if src_md5 != copied_md5:
                                err = self.resc.error(110)
                                err.msg = err.msg.format(source=self.src_p,
                                                         copy=copied_p)
                                raise OSError(err.msg)

        return True

    # --------------------------------------------------------------------------
    def publish(self):
        """
        Publishes the self.src_p to a version subdir of self.asset_d.

        :return: True if the publish was successful, False otherwise.
        """

        # Reserve a version number (this will also create the asset directory on
        # disk if needed).
        self.reserve_version()

        # store the dir or file in this version
        self.store()

        # Store the metadata.
        metadata_obj = meta.Metadata(asset_d=self.asset_d,
                                     version_name=self.curr_ver_n,
                                     metadata=self.metadata,
                                     keywords=self.keywords,
                                     notes=self.notes,
                                     thumbnails=self.thumbnails,
                                     merge=self.merge,
                                     poster_frame=self.poster_frame,
                                     language=self.language)
        metadata_obj.save_metadata()
        metadata_obj.save_keywords()
        metadata_obj.save_notes()
        metadata_obj.save_thumbnails()

        # Carry forward any old files if needed.
        if self.merge:
            self.merge_dir()

        # Create the "CURRENT" pin
        pin_obj = pin.Pin(self.asset_d,
                          self.curr_ver_n,
                          "CURRENT",
                          self.language)
        pin_obj.set_pin()

        # Create the "LATEST" link as well
        pin_obj = pin.Pin(self.asset_d,
                          self.curr_ver_n,
                          "LATEST",
                          self.language)
        pin_obj.set_pin()

        # Create any additional pins
        if self.pins:
            for pin_name in self.pins:
                if pin_name.upper() not in ["CURRENT", "LATEST"]:
                    pin_obj = pin.Pin(self.asset_d,
                                      self.curr_ver_n,
                                      pin_name.upper(),
                                      self.language)
                    pin_obj.set_pin()

    # --------------------------------------------------------------------------
    def invert_version_list(self, versions):
        """
        Given a list of versions, returns any versions in the asset that is NOT
        in this list.

        :param versions: A list of versions (v#### format) to "invert" (i.e.
               list all versions in the asset minus these).

        :return: A list of all versions in an asset minus those passed in the
                 parameter versions.
        """

        pattern = r"v[0-9][0-9][0-9][0-9]"
        if type(versions) != list:
            versions = [versions]
        return filesystem.invert_dir_list(self.asset_d, versions, pattern)

    # --------------------------------------------------------------------------
    def invert_metadata_list(self, meta_vers):
        """
        Given a list of metadata versions, returns any metadata versions in the
        asset that is NOT in this list.

        :param meta_vers: A list of metadata versions (.v#### format) to "invert"
               (i.e. list all metadata versions in the asset minus these).

        :return: A list of all metadata versions in an asset minus those passed
                 in the parameter versions.
        """

        pattern = r"\.v[0-9][0-9][0-9][0-9]"
        if type(meta_vers) != list:
            meta_vers = [meta_vers]
        return filesystem.invert_dir_list(self.asset_d, meta_vers, pattern)

    # --------------------------------------------------------------------------
    def version_pins(self, version_n):
        """
        Returns a list of pins that point to the given version. If no pins point
        to this version, an empty list is returned.

        :param version_n: The name of the version (in v#### format).

        :return: A list of pins that point to this version. The list will be
                 empty if no pins point to the given version.
        """

        output = list()

        ver_d = os.path.join(self.asset_d, version_n)

        psbl_pins_n = os.listdir(self.asset_d)
        for psbl_pin_n in psbl_pins_n:
            psbl_pin_p = os.path.join(self.asset_d, psbl_pin_n)
            if os.path.islink(psbl_pin_p):
                if os.path.realpath(psbl_pin_p) == ver_d:
                    output.append(psbl_pin_n)

        return output

    # --------------------------------------------------------------------------
    def delete_version(self, version_n):
        """
        Deletes a single version and any files it references (as long as these
        files are not being referenced by any other version).

        :param version_n: The version to delete (in the format v####).

        :return: Nothing.
        """

        # TODO: Split the repetitive bits into a separate function

        ver_d = os.path.join(self.asset_d, version_n)
        meta_d = os.path.join(self.asset_d, "." + version_n)

        # The version path and metadata path must exist
        if not os.path.exists(ver_d):
            err = self.resc.error(100)
            err.msg = err.msg.format(version=version_n)
            raise OSError(err.msg)

        if not os.path.exists(meta_d):
            err = self.resc.error(101)
            err.msg = err.msg.format(metadata="." + version_n)
            raise OSError(err.msg)

        # Cannot delete a version if it has any pins pointing to it.
        ver_pins_n = self.version_pins(version_n)
        if ver_pins_n:
            err = self.resc.error(102)
            err.msg = err.msg.format(version=version_n,
                                     pin=",".join(ver_pins_n))
            raise OSError(err.msg)

        # Get a list of all the files referenced by the other versions
        keep_vers_n = self.invert_version_list(version_n)
        keep_vers_d = [os.path.join(self.asset_d, n) for n in keep_vers_n]
        keep_lnks_p = filesystem.recursively_list_files_in_dirs(keep_vers_d)
        keep_files_p = filesystem.symlinks_to_real_paths(keep_lnks_p)

        # Get a list of symlinks in the current version to delete
        psbl_del_lnks_p = filesystem.recursively_list_files_in_dirs(ver_d)
        psbl_del_files_p = filesystem.symlinks_to_real_paths(psbl_del_lnks_p)

        # Delete any that are not in the "keep" list.
        for psbl_del_file_p in psbl_del_files_p:
            if psbl_del_file_p not in keep_files_p:
                if os.path.exists(psbl_del_file_p):
                    os.remove(psbl_del_file_p)

        # Get a list of all the files referenced by the other metadata
        keep_vers_n = self.invert_metadata_list("." + version_n)
        keep_vers_d = [os.path.join(self.asset_d, n) for n in keep_vers_n]
        keep_lnks_p = filesystem.recursively_list_files_in_dirs(keep_vers_d)
        keep_files_p = filesystem.symlinks_to_real_paths(keep_lnks_p)

        # Get a list of symlinks in the current version to delete
        psbl_del_lnks_p = filesystem.recursively_list_files_in_dirs(meta_d)
        psbl_del_files_p = filesystem.symlinks_to_real_paths(psbl_del_lnks_p)

        # Delete any that are not in the "keep" list.
        for psbl_del_file_p in psbl_del_files_p:
            if psbl_del_file_p not in keep_files_p:
                if os.path.exists(psbl_del_file_p):
                    os.remove(psbl_del_file_p)

        shutil.rmtree(ver_d, ignore_errors=True)
        shutil.rmtree(meta_d, ignore_errors=True)

    # --------------------------------------------------------------------------
    def collapse(self, relink_or_del_pins=False):
        """
        Deletes all versions in an asset except the "LATEST".

        This is a DANGEROUS function and should be wrapped in a metric ton of
        warnings before the user is allowed to execute it. There is no backup
        and there is no undo.

        :param relink_or_del_pins: If True, then any pins that point to versions
               that will be deleted will also be deleted. The one exception is
               the "CURRENT" pin, which will be reset to point to the "LATEST"
               version. If False, then if any pins are pointing to a version
               that would be deleted, an error is raised.

        :return: Nothing.
        """

        keep_ver_n = self.get_highest_ver()
        del_vers_n = self.invert_version_list([keep_ver_n])

        if relink_or_del_pins:
            # Move the "CURRENT" pin to point to the latest version
            pin_obj = pin.Pin(self.asset_d, keep_ver_n, "CURRENT",
                              self.language)
            pin_obj.set_pin()
            # Delete any other pins that may point to the deleted versions
            for del_ver_n in del_vers_n:
                linked_pins = self.version_pins(del_ver_n)
                if linked_pins:
                    for linked_pin in linked_pins:
                        pin_obj = pin.Pin(self.asset_d, keep_ver_n, linked_pin,
                                          self.language)
                        pin_obj.remove_pin()

        for del_ver_n in del_vers_n:
            self.delete_version(del_ver_n)
