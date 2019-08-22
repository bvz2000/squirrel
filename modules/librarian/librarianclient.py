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

from interface import schemainterface
from interface import storeinterface

from shared import envvars
from shared.squirrelerror import SquirrelError


# ==============================================================================
class LibrarianClient(object):
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
        resources_d = os.path.join(module_d, "..", "..", "resources")
        config_d = os.path.join(module_d, "..", "..", "config")
        self.resc = resources.Resources(resources_d, "lib_librarian", language)

        self.schema_interface = schemainterface.SchemaInterface()

        # Read the repo config file (if the user sets "REPO_CONFIG_PATH"
        # then that value will be used. Otherwise, read it from the app
        # resources directory
        config_p = os.path.join(config_d, "librarian.config")
        self.config_obj = config.Config(config_p,
                                        envvars.SQUIRREL_SCHEMA_CONFIG_PATH)

        self.language = language

        self.local_mode = self.config_obj.getboolean("main", "local_mode")

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

    # ------------------------------------------------------------------------------
    def publish(self,
                path_p):

        # TODO
        if self.local_mode:

            asset_obj = asset.Asset(name=opts.name,
                                asset_parent_d=opts.destination,
                                src_p=opts.source,
                                metadata=metadata,
                                keywords=opts.keywords,
                                notes=opts.notes,
                                thumbnails=opts.thumbnails,
                                merge=not opts.nomerge,
                                poster_frame=opts.poster_frame,
                                pins=opts.pins,
                                verify_copy=opts.verify,
                                language=opts.language,
                                )
