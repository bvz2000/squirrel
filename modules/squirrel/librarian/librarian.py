"""
License
--------------------------------------------------------------------------------
squirrel is released under version 3 of the GNU General Public License.

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

import inspect
import os

from bvzlib import config
from bvzlib import resources

from squirrel.interface import nameinterface
from squirrel.interface import schemainterface
from squirrel.interface import storeinterface

from squirrel.shared import envvars
from squirrel.shared.squirrelerror import SquirrelError


# ==============================================================================
class Librarian(object):
    """
    A local librarian responsible for either passing requests on to a local
    schema (tool that manages a repository of assets) or passing requests on to
    a remote librarian that, in turn, talks to its local schema.
    """

    # --------------------------------------------------------------------------
    def __init__(self,
                 language="english"):
        """
        Initialize the librarian.

        :param language: The language used for communication with the end user.
               Defaults to "english".
        """

        module_d = os.path.split(inspect.stack()[0][1])[0]
        resources_d = os.path.join(module_d, "..", "..", "..", "resources")
        config_d = os.path.join(module_d, "..", "..", "..", "config")
        self.resc = resources.Resources(resources_d, "lib_librarian", language)

        self.schema_interface = schemainterface.SchemaInterface(language)
        self.name_interface = nameinterface.NameInterface(language)
        self.store_interface = storeinterface.StoreInterface(language)

        self.config_p = os.path.join(config_d, "librarian.config")
        self.config_p = os.path.abspath(self.config_p)
        self.config_obj = config.Config(self.config_p,
                                        envvars.SQUIRREL_LIBRARIAN_CONFIG_PATH)
        self.validate_config()

        self.language = language

        self.local_mode = self.config_obj.getboolean("main", "local_mode")

    # --------------------------------------------------------------------------
    def validate_config(self):
        """
        Makes sure the config file is valid. Raises a squirrel error if not.

        :return: Nothing.
        """

        sections = dict()
        sections["main"] = ["local_mode"]
        sections["local"] = ["remote_ip"]

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
    def repo_name_is_valid(self,
                           repo_name):
        """
        Returns whether the repo name given is a valid repo.

        :param repo_name: The name of the repo.

        :return: True if it is a valid repo. False otherwise.
        """

        if self.local_mode:
            return self.schema_interface.repo_name_is_valid(repo_name)
        else:
            raise SquirrelError("Remote operation not yet implemented.", 1)

    # --------------------------------------------------------------------------
    def get_default_repo(self):
        """
        Returns the name of the default repo. If there is no default, returns
        None.

        :return: The name of the default repo. If no default, returns None.
        """
        if self.local_mode:
            return self.schema_interface.get_default_repo()
        else:
            raise SquirrelError("Remote operation not yet implemented.", 1)

    # --------------------------------------------------------------------------
    def file_is_within_repo(self,
                            file_p,
                            repo_names=None,
                            check_all_repos=True):
        """
        Returns whether or not a particular file is within a repo.

        :param file_p: The path to the file we are testing to see whether it is
               within a repo.
        :param repo_names: The name of the repo we are checking to see whether
               the file is published or not. May be set to None if
               check_all_repos is set to True. Defaults to None
        :param check_all_repos: If True, then all repos will be tested to see if
               they contain the passed file (and repo_name may be left as None).
               Defaults to True.

        :return: True if the file is within the passed repo (or within any repo
                 if check_all_repos is True. False otherwise.
        """

        if self.local_mode:
            return self.schema_interface.file_is_within_repo(file_p,
                                                             repo_names,
                                                             check_all_repos)
        else:
            raise SquirrelError("Remote operation not yet implemented.", 1)

    # --------------------------------------------------------------------------
    def file_is_within_asset(self,
                             file_p):
        """
        Returns whether or not a particular file is within an asset.

        :param file_p: The path to the file we are testing to see whether it is
               within an asset.

        :return: True if the file is within the passed repo (or within any repo
                 if check_all_repos is True. False otherwise.
        """

        if self.local_mode:
            return storeinterface.file_is_within_asset(file_p)
        else:
            raise SquirrelError("Remote operation not yet implemented.", 1)

    # --------------------------------------------------------------------------
    def token_is_valid(self,
                       token):
        """
        Returns whether or not a token is valid.

        :return: True if the token is valid, false otherwise.
        """

        if self.local_mode:
            return self.schema_interface.token_is_valid(token)
        else:
            raise SquirrelError("Remote operation not yet implemented.", 1)

    # --------------------------------------------------------------------------
    def get_gather_loc(self):
        """
        Returns where files should be gathered to.

        :return: The path where to gather the files
        """

        if self.local_mode:
            return self.schema_interface.get_gather_loc()
        else:
            raise SquirrelError("Remote operation not yet implemented.", 1)

    # --------------------------------------------------------------------------
    def get_publish_loc(self,
                        token,
                        repo):
        """
        Returns where the asset should be published to.

        :return: The path where to store (probably versioned) copies of the
                 files.
        """

        if self.local_mode:
            return self.schema_interface.get_publish_loc(token, repo)
        else:
            raise SquirrelError("Remote operation not yet implemented.", 1)

    # # ------------------------------------------------------------------------------
    # def publish(self,
    #             path_p):
    #
    #     # TODO
    #     if self.local_mode:
    #
    #         asset_obj = asset.Asset(name=opts.name,
    #                             asset_parent_d=opts.destination,
    #                             src_p=opts.source,
    #                             metadata=metadata,
    #                             keywords=opts.keywords,
    #                             notes=opts.notes,
    #                             thumbnails=opts.thumbnails,
    #                             merge=not opts.nomerge,
    #                             poster_frame=opts.poster_frame,
    #                             pins=opts.pins,
    #                             verify_copy=opts.verify,
    #                             language=opts.language,
    #                             )

    # --------------------------------------------------------------------------
    def validate_name(self,
                      item_n=None,
                      repo_n=None):
        """
        Validates the name.

        :param item_n: The name we are trying to validate.
        :param repo_n: The repo that the name will be validated against.

        :return: Nothing.
        """

        if self.local_mode:
            self.name_interface.set_attributes(item_n, repo_n)
            self.name_interface.validate_name()
        else:
            raise SquirrelError("Remote operation not yet implemented.", 1)

    # --------------------------------------------------------------------------
    def extract_metadata_from_name(self,
                                   item_n=None,
                                   repo_n=None):
        """
        Extracts the metadata from the name.

        :param item_n: The name we are trying to validate.
        :param repo_n: The repo that the name will be validated against.

        :return: Nothing.
        """

        if self.local_mode:
            return self.name_interface.extract_metadata_from_name(repo_n,
                                                                  item_n)
        else:
            raise SquirrelError("Remote operation not yet implemented.", 1)

    # --------------------------------------------------------------------------
    def store(self,
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
        Stores a versioned copy of the source data.

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

        :return: Nothing.
        """
        if self.local_mode:

            self.store_interface.set_attributes(
                name=name,
                asset_parent_d=asset_parent_d,
                src_p=src_p,
                metadata=metadata,
                keywords=keywords,
                notes=notes,
                thumbnails=thumbnails,
                merge=merge,
                poster_frame=poster_frame,
                pins=pins,
                verify_copy=verify_copy)

            self.store_interface.store()

        else:
            raise SquirrelError("Remote operation not yet implemented.", 1)

    # --------------------------------------------------------------------------
    def get_pins(self,
                 asset_p,
                 asset_name,
                 local_mode):
        """
        Returns a list of all the (user) pins in an asset.

        :param asset_p: The path to the parent directory in which the asset
               lives (not the path to the asset itself).
        :param asset_name: The name of the asset.
        :param local_mode: Whether to go through the repo system, or run
        locally.

        :return: Nothing.
        """

        if self.local_mode or local_mode:

            self.store_interface.set_attributes(
                name=asset_name,
                asset_parent_d=asset_p)

            return self.store_interface.get_pins()

        else:
            raise SquirrelError("Remote operation not yet implemented.", 1)

    # --------------------------------------------------------------------------
    def set_pin(self,
                asset_p,
                asset_name,
                pin_n,
                version,
                local_mode):
        """
        Sets a pin on an asset.

        :param asset_p: The path to the parent directory in which the asset
               lives (not the path to the asset itself).
        :param asset_name: The name of the asset.
        :param pin_n: The name of the pin.
        :param version: The version to point the pin to.
        :param local_mode: Whether to go through the repo system, or run
        locally.

        :return: Nothing.
        """

        if self.local_mode or local_mode:

            self.store_interface.set_attributes(
                name=asset_name,
                asset_parent_d=asset_p)

            self.store_interface.set_pin(pin_n, version)

        else:
            raise SquirrelError("Remote operation not yet implemented.", 1)

    # --------------------------------------------------------------------------
    def remove_pin(self,
                   asset_p,
                   asset_name,
                   pin_n,
                   local_mode):
        """
        Removes a pin from an asset.

        :param asset_p: The path to the parent directory in which the asset
               lives (not the path to the asset itself).
        :param asset_name: The name of the asset.
        :param pin_n: The name of the pin.
        :param local_mode: Whether to go through the repo system, or run
        locally.

        :return: Nothing.
        """

        if self.local_mode or local_mode:

            self.store_interface.set_attributes(
                name=asset_name,
                asset_parent_d=asset_p)

            self.store_interface.remove_pin(pin_n)

        else:
            raise SquirrelError("Remote operation not yet implemented.", 1)

    # --------------------------------------------------------------------------
    def get_pin_version(self,
                        asset_p,
                        asset_name,
                        pin_n,
                        local_mode):
        """
        Returns the version a pin points to.

        :param asset_p: The path to the parent directory in which the asset
               lives (not the path to the asset itself).
        :param asset_name: The name of the asset.
        :param pin_n: The name of the pin.
        :param local_mode: Whether to go through the repo system, or run
        locally.

        :return: The version the pin points to..
        """

        if self.local_mode or local_mode:

            self.store_interface.set_attributes(
                name=asset_name,
                asset_parent_d=asset_p)

            return self.store_interface.get_pin_version(pin_n)

        else:
            raise SquirrelError("Remote operation not yet implemented.", 1)

    # --------------------------------------------------------------------------
    def version_exists(self,
                       asset_p,
                       asset_name,
                       version,
                       local_mode):
        """
        Returns whether a version exists.

        :param asset_p: The path to the parent directory in which the asset
               lives (not the path to the asset itself).
        :param asset_name: The name of the asset.
        :param version: The version we are looking for.
        :param local_mode: Whether to go through the repo system, or run
        locally.

        :return: The version the pin points to..
        """

        if self.local_mode or local_mode:

            self.store_interface.set_attributes(
                name=asset_name,
                asset_parent_d=asset_p)

            return self.store_interface.version_exists(version)

        else:
            raise SquirrelError("Remote operation not yet implemented.", 1)

    # --------------------------------------------------------------------------
    def collapse(self,
                 asset_p,
                 asset_name,
                 del_orphaned_pins,
                 local_mode):
        """
        Collapses the asset down to only the most recent version.

        :param asset_p: The path to the parent directory in which the asset
               lives (not the path to the asset itself).
        :param asset_name: The name of the asset.
        :param del_orphaned_pins: If true, then also delete any pins that point
               to versions that are being deleted.
        :param local_mode: Whether to go through the repo system, or run
        locally.

        :return: Nothing.
        """

        if self.local_mode or local_mode:

            self.store_interface.set_attributes(
                name=asset_name,
                asset_parent_d=asset_p)

            return self.store_interface.collapse(del_orphaned_pins)

        else:
            raise SquirrelError("Remote operation not yet implemented.", 1)

    # --------------------------------------------------------------------------
    def get_highest_version(self,
                            asset_p,
                            asset_name,
                            local_mode):
        """
        Returns whether a version exists.

        :param asset_p: The path to the parent directory in which the asset
               lives (not the path to the asset itself).
        :param asset_name: The name of the asset.
        :param local_mode: Whether to go through the repo system, or run
        locally.

        :return: The version the pin points to..
        """

        if self.local_mode or local_mode:

            self.store_interface.set_attributes(
                name=asset_name,
                asset_parent_d=asset_p)

            return self.store_interface.get_highest_ver()

        else:
            raise SquirrelError("Remote operation not yet implemented.", 1)

    # --------------------------------------------------------------------------
    def add_keywords(self,
                     asset_p,
                     asset_name,
                     version,
                     keywords,
                     local_mode):
        """
        Adds keywords to the given version of the given asset..

        :param asset_p: The path to the parent directory in which the asset
               lives (not the path to the asset itself).
        :param asset_name: The name of the asset.
        :param version: The version to add keywords to.
        :param keywords: The list of keywords to add.
        :param local_mode: Whether to go through the repo system, or run
        locally.

        :return: The version the pin points to..
        """

        if self.local_mode or local_mode:

            self.store_interface.set_attributes(
                name=asset_name,
                asset_parent_d=asset_p)

            return self.store_interface.add_keywords(version, keywords)

        else:
            raise SquirrelError("Remote operation not yet implemented.", 1)

    # --------------------------------------------------------------------------
    def delete_keywords(self,
                        asset_p,
                        asset_name,
                        version,
                        keywords,
                        local_mode):
        """
        Deletes keywords from the given version of the given asset..

        :param asset_p: The path to the parent directory in which the asset
               lives (not the path to the asset itself).
        :param asset_name: The name of the asset.
        :param version: The version to add keywords to.
        :param keywords: The list of keywords to delete.
        :param local_mode: Whether to go through the repo system, or run
        locally.

        :return: The version the pin points to..
        """

        if self.local_mode or local_mode:

            self.store_interface.set_attributes(
                name=asset_name,
                asset_parent_d=asset_p)

            return self.store_interface.delete_keywords(version, keywords)

        else:
            raise SquirrelError("Remote operation not yet implemented.", 1)

    # --------------------------------------------------------------------------
    def add_metadata(self,
                     asset_p,
                     asset_name,
                     version,
                     metadata,
                     local_mode):
        """
        Adds keywords to the given version of the given asset..

        :param asset_p: The path to the parent directory in which the asset
               lives (not the path to the asset itself).
        :param asset_name: The name of the asset.
        :param version: The version to add keywords to.
        :param metadata: A dictionary of key=value pairs add.
        :param local_mode: Whether to go through the repo system, or run
        locally.

        :return: The version the pin points to..
        """

        if self.local_mode or local_mode:

            self.store_interface.set_attributes(
                name=asset_name,
                asset_parent_d=asset_p)

            return self.store_interface.add_metadata(version, metadata)

        else:
            raise SquirrelError("Remote operation not yet implemented.", 1)

    # --------------------------------------------------------------------------
    def delete_metadata(self,
                        asset_p,
                        asset_name,
                        version,
                        keys,
                        local_mode):
        """
        Deletes keywords from the given version of the given asset..

        :param asset_p: The path to the parent directory in which the asset
               lives (not the path to the asset itself).
        :param asset_name: The name of the asset.
        :param version: The version to add keywords to.
        :param keys: A list of metadata keys to delete.
        :param local_mode: Whether to go through the repo system, or run
        locally.

        :return: The version the pin points to..
        """

        if self.local_mode or local_mode:

            self.store_interface.set_attributes(
                name=asset_name,
                asset_parent_d=asset_p)

            return self.store_interface.delete_metadata(version, keys)

        else:
            raise SquirrelError("Remote operation not yet implemented.", 1)

    # --------------------------------------------------------------------------
    def add_notes(self,
                  asset_p,
                  asset_name,
                  version,
                  notes,
                  append,
                  local_mode):
        """
        Adds keywords to the given version of the given asset..

        :param asset_p: The path to the parent directory in which the asset
               lives (not the path to the asset itself).
        :param asset_name: The name of the asset.
        :param version: The version to add keywords to.
        :param notes: A string of notes to add.
        :param append: If True, then the notes will be appended to the current
               set. Otherwise they will overwrite any existing notes.
        :param local_mode: Whether to go through the repo system, or run
        locally.

        :return: The version the pin points to..
        """

        if self.local_mode or local_mode:

            self.store_interface.set_attributes(
                name=asset_name,
                asset_parent_d=asset_p)

            return self.store_interface.add_notes(version, notes, append)

        else:
            raise SquirrelError("Remote operation not yet implemented.", 1)

    # --------------------------------------------------------------------------
    def add_thumbnails(self,
                       asset_p,
                       asset_name,
                       version,
                       thumbnails,
                       poster_frame,
                       local_mode):
        """
        Adds thumbnails to the given version of the given asset.

        :param asset_p: The path to the parent directory in which the asset
               lives (not the path to the asset itself).
        :param asset_name: The name of the asset.
        :param version: The version to add keywords to.
        :param thumbnails: The list of thumbnail files to add.
        :param poster_frame: The frame number (as an integer or string that
               evaluates to an integer) that indicates which frame of the
               thumbnails to make the poster frame.
        :param local_mode: Whether to go through the repo system, or run
        locally.

        :return: The version the pin points to..
        """

        if self.local_mode or local_mode:

            self.store_interface.set_attributes(
                name=asset_name,
                asset_parent_d=asset_p)

            return self.store_interface.add_thumbnails(version,
                                                       thumbnails,
                                                       poster_frame)

        else:
            raise SquirrelError("Remote operation not yet implemented.", 1)

    # --------------------------------------------------------------------------
    def delete_thumbnails(self,
                          asset_p,
                          asset_name,
                          version,
                          local_mode):
        """
        Deletes thumbnails from the given version of the given asset.

        :param asset_p: The path to the parent directory in which the asset
               lives (not the path to the asset itself).
        :param asset_name: The name of the asset.
        :param version: The version to add keywords to.
        :param local_mode: Whether to go through the repo system, or run
        locally.

        :return: The version the pin points to..
        """

        if self.local_mode or local_mode:

            self.store_interface.set_attributes(
                name=asset_name,
                asset_parent_d=asset_p)

            return self.store_interface.delete_thumbnails(version)

        else:
            raise SquirrelError("Remote operation not yet implemented.", 1)

    # --------------------------------------------------------------------------
    def set_poster_frame(self,
                         asset_p,
                         asset_name,
                         version,
                         poster_frame,
                         local_mode):
        """
        Sets the poster frame for the given version of the asset.

        :param asset_p: The path to the parent directory in which the asset
               lives (not the path to the asset itself).
        :param asset_name: The name of the asset.
        :param version: The version to add keywords to.
        :param poster_frame: The frame number (as an integer or string that
               evaluates to an integer) that indicates which frame of the
               thumbnails to make the poster frame.
        :param local_mode: Whether to go through the repo system, or run
        locally.

        :return: The version the pin points to..
        """

        if self.local_mode or local_mode:

            self.store_interface.set_attributes(
                name=asset_name,
                asset_parent_d=asset_p)

            return self.store_interface.set_poster_frame(version,
                                                         poster_frame)

        else:
            raise SquirrelError("Remote operation not yet implemented.", 1)
