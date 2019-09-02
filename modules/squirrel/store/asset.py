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

from squirrel.shared import envvars, libSquirrel
from squirrel.shared.squirrelerror import SquirrelError

import meta
import pin


# ==============================================================================
class Asset(object):
    """
    Class responsible for copying source files into a versioned destination.

    In the division of labor of the asset management, "store" handles
    everything from the asset name down to the individual version directories.
    This includes all metadata and thumbnails stored within the asset. Once
    within a version directory, no squirrel related files will be stored (only
    the actual files provided to "store" by the end user).

    So, the structure looks like this:

    /some/dirs/that/may/be/manged/elsewhere

    Within this location (which can be anywhere as far as "store" is concerned)
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
    - CURRENT (symlink to one of the v#### directories)
    - .CURRENT (symlink to the associated .v#### directory)
    - LATEST (symlink to the HIGHEST v#### directory)
    - .LATEST (symlink to the associated .v#### directory)

    There may be additional, ALL_CAPS symlinks to various version directories.
    For each of these there will also be a .ALL_CAPS hidden symlink to the
    metadata .v#### directory.

    With the exception of actually copying the data to live inside the version
    directories (actually as symlinks to the asset .data dir), "store" only
    handles versioning and storing metadata, and never alters the structure
    inside a version dir.
    """

    # --------------------------------------------------------------------------
    def __init__(self,
                 language):
        """
        :param language: The language used for communication with the end user.
               Defaults to "english".

        :return: Nothing.
        """

        assert type(language) is str

        module_d = os.path.split(inspect.stack()[0][1])[0]
        resources_d = os.path.join(module_d, "..", "..", "..", "resources")
        config_d = os.path.join(module_d, "..", "..", "..", "config")
        self.resc = resources.Resources(resources_d, "lib_store", language)

        self.language = language

        self.config_p = os.path.join(config_d, "store.config")
        self.config_p = os.path.abspath(self.config_p)
        self.config_obj = config.Config(self.config_p,
                                        envvars.SQUIRREL_NAME_CONFIG_PATH)

        self.validate_config()

        self.src_p = None
        self.name = None
        self.asset_parent_d = None
        self.asset_d = None
        self.data_d = None
        self.data_sizes = None
        self.thumbnail_data_d = None
        self.prev_ver_n = None
        self.prev_ver_d = None
        self.curr_ver_n = None
        self.curr_ver_d = None
        self.metadata_d = None
        self.metadata = None
        self.keywords = None
        self.notes = None
        self.thumbnails = None
        self.poster_frame = None
        self.merge = None
        self.pins = None
        self.verify_copy = None
        self.skip_list_regex = None

    # --------------------------------------------------------------------------
    def validate_config(self):
        """
        Makes sure the config file is valid. Raises a squirrel error if not.

        :return: Nothing.
        """

        sections = dict()
        sections["skip list regex"] = [None]

        failures = self.config_obj.validation_failures(sections)
        if failures:
            if failures[1] is None:
                err = self.resc.error(501)
                err.msg = err.msg.format(config_p=self.config_p,
                                         section=failures[0])
                raise SquirrelError(err.msg, err.code)
            else:
                err = self.resc.error(502)
                err.msg = err.msg.format(config_p=self.config_p,
                                         setting=failures[0],
                                         section=failures[1])
                raise SquirrelError(err.msg, err.code)

    # --------------------------------------------------------------------------
    def set_attributes(self,
                       name,
                       asset_parent_d,
                       src_p=None,
                       metadata=None,
                       keywords=None,
                       notes=None,
                       thumbnails=None,
                       poster_frame=None,
                       merge=True,
                       pins=None,
                       verify_copy=False):
        """
        Sets the attributes for the current asset.

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
               2 as though they had been explicitly published a second time). If
               False, then only the files provided will be a part of the asset
               (essentially creating a "fresh" version of the asset). Defaults
               to True.
        :param pins: A list of pins to set to point to the newly created
               version. These are in addition to the automatic "LATEST" and
               "CURRENT". If None, no pins beyond the automatic pins will be
               created. Defaults to None.
        :param verify_copy: If True, then an md5 checksum will be done on each
               source and each copy to ensure that the file was copied
               correctly. Defaults to False.
        """

        assert name and type(name) is str
        assert os.path.exists(asset_parent_d)
        assert os.path.isdir(asset_parent_d)
        assert src_p is None or os.path.exists(src_p)
        assert metadata is None or type(metadata) is dict
        assert keywords is None or type(keywords) is list
        if thumbnails:
            assert type(thumbnails) is list
            for thumbnail in thumbnails:
                assert os.path.exists(thumbnail)
                assert os.path.isfile(thumbnail)
            if poster_frame:
                assert type(poster_frame) is int
        assert type(merge) is bool
        assert pins is None or type(pins) is list
        assert type(verify_copy) is bool

        self.src_p = src_p
        self.name = name

        self.asset_parent_d = asset_parent_d
        self.asset_d = os.path.join(asset_parent_d, self.name)

        self.data_d = os.path.join(self.asset_d, ".data")
        if os.path.exists(self.data_d):
            self.data_sizes = filesystem.dir_files_keyed_by_size(self.data_d)
        else:
            self.data_sizes = dict()

        self.thumbnail_data_d = os.path.join(self.asset_d, ".thumbnaildata")

        self.prev_ver_n = self.get_highest_ver()
        self.prev_ver_d = os.path.join(self.asset_d, self.prev_ver_n)

        if not metadata:
            self.metadata = dict()
        else:
            self.metadata = metadata

        if not keywords:
            self.keywords = list()
        else:
            self.keywords = keywords

        if not notes:
            self.notes = ""
        else:
            self.notes = notes

        if not thumbnails:
            self.thumbnails = list()
        else:
            self.thumbnails = thumbnails

        if not poster_frame:
            self.poster_frame = 1
        else:
            self.poster_frame = poster_frame

        self.merge = merge
        self.pins = pins
        self.verify_copy = verify_copy

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
        pattern = r"^(v)([0-9]*[0-9]*[0-9]*[0-9]+)$"
        
        items = os.listdir(self.asset_d)
        for item in items:
            if os.path.isdir(os.path.join(self.asset_d, item)):
                result = re.match(pattern, item)
                if result is not None:
                    highest = max(highest, int(result.groups()[1]))
        
        if highest > 9999:
            err = self.resc.error(103)
            raise SquirrelError(err.msg, err.code)
        
        return "v" + str(highest).rjust(4, "0")

    # --------------------------------------------------------------------------
    def get_next_available_ver(self):
        """
        Increments the current highest version (actually stored under
        prev_ver_d) and returns a formatted string with that value (v####)..

        :return: The next available version number, formatted as v####.
        """

        highest = int(os.path.split(self.prev_ver_d)[1].split("v")[1])
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
        raise SquirrelError(err.msg, err.code)

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
    def copy_files(self):
        """
        Actually copy the files from self.src_p to self.asset_d. (Actually files
        will be copied to self.data_d and symlinks will be made in self.asset_d)

        :return: True if the copy is successful, False otherwise.
        """

        # If self.src_p is a file, handle it differently than if it is a dir.
        if not os.path.isdir(self.src_p):
            file_n = os.path.split(self.src_p)[1]
            if file_n not in self.skip_list_regex:
                filesystem.copy_file_deduplicated(
                    source_p=self.src_p,
                    dest_d=self.curr_ver_d,
                    dest_n=file_n,
                    data_d=self.data_d,
                    data_sizes=self.data_sizes,
                    ver_prefix="sqv",
                    num_digits=4,
                    do_verified_copy=self.verify_copy)

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
                        filesystem.copy_file_deduplicated(
                            source_p=source_p,
                            dest_d=dest_d,
                            dest_n=file_n,
                            data_d=self.data_d,
                            data_sizes=self.data_sizes,
                            ver_prefix="sqv",
                            num_digits=4,
                            do_verified_copy=self.verify_copy)

        return True

    # --------------------------------------------------------------------------
    def store(self):
        """
        Stores the self.src_p to a version subdir of self.asset_d.

        :return: True if the store was successful, False otherwise.
        """

        # Reserve a version number (this will also create the asset directory on
        # disk if needed).
        self.reserve_version()

        # store the dir or file in this version
        self.copy_files()

        # Store the metadata.
        metadata_obj = meta.Metadata(self.language)
        metadata_obj.set_attributes(asset_d=self.asset_d,
                                    version=self.curr_ver_n,
                                    metadata=self.metadata,
                                    keywords=self.keywords,
                                    notes=self.notes,
                                    thumbnails=self.thumbnails,
                                    merge=self.merge,
                                    poster_frame=self.poster_frame)
        metadata_obj.save_metadata()
        metadata_obj.save_keywords()
        metadata_obj.save_notes()
        metadata_obj.save_thumbnails()

        # Carry forward any old files if needed.
        if self.merge:
            self.merge_dir()

        # Create the "CURRENT" and "LATEST" pins
        self.set_pin("CURRENT", self.curr_ver_n)
        self.set_pin("LATEST", self.curr_ver_n)

        # Create any additional pins
        if self.pins:
            for pin_name in self.pins:
                if pin_name.upper() not in ["CURRENT", "LATEST"]:
                    self.set_pin(pin_name.upper(), self.curr_ver_n)

    # --------------------------------------------------------------------------
    def add_keywords(self,
                     version,
                     keywords):
        """
        Sets the keywords for a specified version.

        :param version: The version on which to set the metadata.
        :param keywords: A list of keywords to ad.

        :return:
        """

        meta_obj = meta.Metadata(self.language)
        meta_obj.set_attributes(self.asset_d, version)
        meta_obj.add_keywords(version, keywords)

    # --------------------------------------------------------------------------
    def delete_keywords(self,
                        version,
                        keywords):
        """
        Deletes keywords for a specified version.

        :param version: The version on which to set the metadata.
        :param keywords: The list of keywords to delete.

        :return:
        """

        assert libSquirrel.validate_version(version, "v", 4)
        assert type(keywords) is list

        meta_obj = meta.Metadata(self.language)
        meta_obj.set_attributes(self.asset_d, version)
        meta_obj.delete_keywords(version, keywords)

    # --------------------------------------------------------------------------
    def add_metadata(self,
                     version,
                     metadata):
        """
        Sets the keywords for a specified version.

        :param version: The version on which to set the metadata.
        :param metadata: A dictionary of key=value pairs to add.

        :return:
        """

        assert libSquirrel.validate_version(version, "v", 4)
        assert type(metadata) is dict

        meta_obj = meta.Metadata(self.language)
        meta_obj.set_attributes(self.asset_d, version)
        meta_obj.add_metadata(version, metadata)

    # --------------------------------------------------------------------------
    def delete_metadata(self,
                        version,
                        metadata):
        """
        Deletes keywords for a specified version.

        :param version: The version on which to set the metadata.
        :param metadata: A dictionary of keys to delete.

        :return:
        """

        assert libSquirrel.validate_version(version, "v", 4)
        assert type(metadata) is dict

        meta_obj = meta.Metadata(self.language)
        meta_obj.set_attributes(self.asset_d, version)
        meta_obj.delete_metadata(version, metadata)

    # --------------------------------------------------------------------------
    def add_notes(self,
                  version,
                  notes,
                  append):
        """
        Sets the notes for a specified version.

        :param version: The version on which to set the metadata.
        :param notes: A string of notes to add.
        :param append: If True, then the notes will be appended to the current
               set of notes.

        :return:
        """

        assert libSquirrel.validate_version(version, "v", 4)
        assert type(notes) is str
        assert type(append) is bool

        meta_obj = meta.Metadata(self.language)
        meta_obj.set_attributes(self.asset_d, version)
        meta_obj.add_notes(version, notes, append)

    # --------------------------------------------------------------------------
    def add_thumbnails(self,
                       version,
                       thumbnails,
                       poster_frame=None):
        """
        Sets the thumbnails for a specified version.

        :param version: The version on which to set the metadata.
        :param thumbnails: The list of thumbnail files to add.
        :param poster_frame: The frame number (as an integer or string that
               evaluates to an integer) that indicates which frame of the
               thumbnails to make the poster frame. If None, and thumbnails are
               provided, then the first frame will be made into the poster.
               Defaults to None.

        :return:
        """

        assert libSquirrel.validate_version(version, "v", 4)
        assert type(thumbnails) is list
        for thumbnail in thumbnails:
            assert os.path.exists(thumbnail)
        assert poster_frame is None or type(poster_frame) is bool

        meta_obj = meta.Metadata(self.language)
        meta_obj.set_attributes(self.asset_d, version)
        meta_obj.add_thumbnails(version, thumbnails, poster_frame)

    # --------------------------------------------------------------------------
    def delete_thumbnails(self,
                          version):
        """
        Deletes the thumbnails from a specific version.

        :param version: The version on which to set the metadata.

        :return:
        """

        assert libSquirrel.validate_version(version, "v", 4)

        meta_obj = meta.Metadata(self.language)
        meta_obj.set_attributes(self.asset_d, version)
        meta_obj.delete_thumbnails(version)

    # --------------------------------------------------------------------------
    def set_poster_frame(self,
                         version,
                         poster_frame=None):
        """
        Sets the notes for a specified version.

        :param version: The version on which to set the metadata.
        :param poster_frame: The frame number (as an integer or string that
               evaluates to an integer) that indicates which frame of the
               thumbnails to make the poster frame. If None, and thumbnails are
               provided, then the first frame will be made into the poster.
               Defaults to None.

        :return:
        """

        assert libSquirrel.validate_version(version, "v", 4)
        assert poster_frame is None or type(poster_frame) is bool

        meta_obj = meta.Metadata(self.language)
        meta_obj.set_attributes(self.asset_d, version)
        meta_obj.set_poster(version, poster_frame)

    # --------------------------------------------------------------------------
    def set_pin(self,
                pin_name,
                version):
        """
        Sets a pin for the current asset with the name "name" to the version
        given by "version".

        :param pin_name: The name of the pin to be set.
        :param version: The version to set the pin to.

        :return: Nothing.
        """

        assert libSquirrel.validate_version(version, "v", 4)
        assert type(pin_name) is str

        pin_obj = pin.Pin(self.language)
        pin_obj.set_attributes(self.asset_d,
                               version,
                               pin_name)
        pin_obj.set_pin()

    # --------------------------------------------------------------------------
    def remove_pin(self,
                   pin_name):
        """
        Removes a pin fro the current asset with the name "name".

        :param pin_name: The name of the pin to remove.

        :return: Nothing.
        """

        assert type(pin_name) is str

        pin_obj = pin.Pin(self.language)
        pin_obj.set_attributes(self.asset_d,
                               None,
                               pin_name)
        pin_obj.remove_pin()

    # --------------------------------------------------------------------------
    def pin_exists(self,
                   pin_name):
        """
        Returns True if a pin exists.

        :param pin_name: The name of the pin who's version to retrieve.

        :return: True if the pin exists. False otherwise.
        """

        assert type(pin_name) is str

        if self.get_pin_version(pin_name):
            return True
        return False

    # --------------------------------------------------------------------------
    def get_pin_version(self,
                        pin_name):
        """
        Returns the version number associated with the pin: pin_name.

        :param pin_name: The name of the pin who's version to retrieve.

        :return: A version number.
        """

        assert type(pin_name) is str

        items = os.listdir(self.asset_d)
        for item in items:
            test_p = os.path.join(self.asset_d, item)
            if (item == pin_name
                    and os.path.islink(test_p)
                    and os.path.split(os.path.realpath(test_p))[1][0] == "v"):
                return os.path.split(os.path.realpath(test_p))[1]
        return None

    # --------------------------------------------------------------------------
    def get_pins(self):
        """
        Returns a list of all user defined pins.

        :return: A list of all the (user-defined) pins in the asset.
        """

        output = list()
        items = os.listdir(self.asset_d)
        for item in items:
            test_p = os.path.join(self.asset_d, item)
            if (os.path.islink(test_p)
                    and item != "LATEST"
                    and item != "CURRENT"
                    and item != ".LATEST"
                    and item != ".CURRENT"):
                output.append(item)
        return output

    # --------------------------------------------------------------------------
    def version_exists(self,
                       version):
        """
        Returns True if the version exists. False otherwise.

        :param version: The version we are testing.

        :return: True if the version exists. False otherwise.
        """

        assert libSquirrel.validate_version(version, "v", 4)

        if not libSquirrel.validate_version(version, "v", 4):
            err = self.resc.error(111)
            raise SquirrelError(err.msg, err.code)

        items = os.listdir(self.asset_d)
        for item in items:
            test_p = os.path.join(self.asset_d, item)
            if item == version and not os.path.islink(test_p):
                return True
        return False

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

        assert type(versions) is list
        for version in versions:
            assert libSquirrel.validate_version(version, "v", 4)

        pattern = r"^v[0-9][0-9][0-9][0-9]$"
        if type(versions) != list:
            versions = [versions]
        return filesystem.invert_dir_list(self.asset_d, versions, pattern)

    # --------------------------------------------------------------------------
    def invert_metadata_list(self, meta_vers):
        """
        Given a list of metadata versions, returns any metadata versions in the
        asset that is NOT in this list.

        :param meta_vers: A list of metadata versions (.v#### format) to
               "invert" (i.e. list all metadata versions in the asset minus
               these).

        :return: A list of all metadata versions in an asset minus those passed
                 in the parameter versions.
        """

        assert type(meta_vers) is list

        for meta_ver in meta_vers:
            assert libSquirrel.validate_version(meta_ver, ".v", 4)

        pattern = r"^\.v[0-9][0-9][0-9][0-9]$"
        if type(meta_vers) != list:
            meta_vers = [meta_vers]
        return filesystem.invert_dir_list(self.asset_d, meta_vers, pattern)

    # --------------------------------------------------------------------------
    def version_pins(self, version):
        """
        Returns a list of pins that point to the given version. If no pins point
        to this version, an empty list is returned.

        :param version: The name of the version (in v#### format).

        :return: A list of pins that point to this version. The list will be
                 empty if no pins point to the given version.
        """

        assert libSquirrel.validate_version(version, "v", 4)

        output = list()

        ver_d = os.path.join(self.asset_d, version)

        psbl_pins_n = os.listdir(self.asset_d)
        for psbl_pin_n in psbl_pins_n:
            psbl_pin_p = os.path.join(self.asset_d, psbl_pin_n)
            if os.path.islink(psbl_pin_p):
                if os.path.realpath(psbl_pin_p) == ver_d:
                    output.append(psbl_pin_n)

        return output

    # --------------------------------------------------------------------------
    def delete_version(self, version):
        """
        Deletes a single version and any files it references (as long as these
        files are not being referenced by any other version).

        :param version: The version to delete (in the format v####).

        :return: Nothing.
        """

        # TODO: Split the repetitive bits into a separate function

        assert libSquirrel.validate_version(version, "v", 4)

        ver_d = os.path.join(self.asset_d, version)
        meta_d = os.path.join(self.asset_d, "." + version)

        # The version path and metadata path must exist
        if not os.path.exists(ver_d):
            err = self.resc.error(100)
            err.msg = err.msg.format(version=version)
            raise OSError(err.msg)

        if not os.path.exists(meta_d):
            err = self.resc.error(101)
            err.msg = err.msg.format(metadata="." + version)
            raise OSError(err.msg)

        # Cannot delete a version if it has any pins pointing to it.
        ver_pins_n = self.version_pins(version)
        if ver_pins_n:
            err = self.resc.error(102)
            err.msg = err.msg.format(version=version,
                                     pin=",".join(ver_pins_n))
            raise OSError(err.msg)

        # Get a list of all the files referenced by the other versions
        keep_vers_n = self.invert_version_list([version])
        keep_vers_d = [os.path.join(self.asset_d, n) for n in keep_vers_n]
        keep_lnks_p = filesystem.recursively_list_files_in_dirs(keep_vers_d)
        keep_files_p = filesystem.symlinks_to_real_paths(keep_lnks_p)

        # Get a list of symlinks in the current version to delete
        psbl_del_lnks_p = filesystem.recursively_list_files_in_dirs([ver_d])
        psbl_del_files_p = filesystem.symlinks_to_real_paths(psbl_del_lnks_p)

        # Delete any that are not in the "keep" list.
        for psbl_del_file_p in psbl_del_files_p:
            if psbl_del_file_p not in keep_files_p:
                if os.path.exists(psbl_del_file_p):
                    os.remove(psbl_del_file_p)

        # Get a list of all the files referenced by the other metadata
        keep_vers_n = self.invert_metadata_list(["." + version])
        keep_vers_d = [os.path.join(self.asset_d, n) for n in keep_vers_n]
        keep_lnks_p = filesystem.recursively_list_files_in_dirs(keep_vers_d)
        keep_files_p = filesystem.symlinks_to_real_paths(keep_lnks_p)

        # Get a list of symlinks in the current version to delete
        psbl_del_lnks_p = filesystem.recursively_list_files_in_dirs([meta_d])
        psbl_del_files_p = filesystem.symlinks_to_real_paths(psbl_del_lnks_p)

        # Delete any that are not in the "keep" list.
        for psbl_del_file_p in psbl_del_files_p:
            if psbl_del_file_p not in keep_files_p:
                if os.path.exists(psbl_del_file_p):
                    os.remove(psbl_del_file_p)

        shutil.rmtree(ver_d, ignore_errors=True)
        shutil.rmtree(meta_d, ignore_errors=True)

    # --------------------------------------------------------------------------
    def collapse(self, del_orphaned_pins=False):
        """
        Deletes all versions in an asset except the "LATEST".

        This is a DANGEROUS function and should be wrapped in a metric ton of
        warnings before the user is allowed to execute it. There is no backup
        and there is no undo.

        :param del_orphaned_pins: If True, then any pins that point to versions
               that will be deleted will also be deleted. The one exception is
               the "CURRENT" pin, which will be reset to point to the "LATEST"
               version. If False, then if any pins are pointing to a version
               that would be deleted, an error is raised. Defaults to False.

        :return: Nothing.
        """

        assert type(del_orphaned_pins) is bool
        
        keep_ver_n = self.get_highest_ver()
        del_vers_n = self.invert_version_list([keep_ver_n])

        if del_orphaned_pins:

            # Move the "CURRENT" pin to point to the latest version
            pin_obj = pin.Pin(self.language)
            pin_obj.set_attributes(self.asset_d,
                                   keep_ver_n,
                                   "CURRENT")
            pin_obj.set_pin()

            # Delete any other pins that may point to the deleted versions
            for del_ver_n in del_vers_n:
                linked_pins = self.version_pins(del_ver_n)
                if linked_pins:
                    for linked_pin in linked_pins:
                        pin_obj = pin.Pin(self.language)
                        pin_obj.set_attributes(self.asset_d,
                                               keep_ver_n,
                                               linked_pin)
                        pin_obj.remove_pin()

        for del_ver_n in del_vers_n:
            self.delete_version(del_ver_n)
