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
            return schemainterface.repo_name_is_valid(repo_name)
        else:
            raise ValueError("Remote operation not yet implemented.")

    # --------------------------------------------------------------------------
    def get_default_repo(self):
        """
        Returns the name of the default repo. If there is no default, returns
        None.

        :return: The name of the default repo. If no default, returns None.
        """
        if self.local_mode:
            return schemainterface.get_default_repo()
        else:
            raise ValueError("Remote operation not yet implemented.")

    # --------------------------------------------------------------------------
    def file_is_within_repo(self,
                            file_p,
                            repo_name=None,
                            check_all_repos=True):
        """
        Returns whether or not a particular file is within a repo.

        :param file_p: The path to the file we are testing to see whether it is
               within a repo.
        :param repo_name: The name of the repo we are checking to see whether
               the file is published or not. May be set to None if
               check_all_repos is set to True. Defaults to None
        :param check_all_repos: If True, then all repos will be tested to see if
               they contain the passed file (and repo_name may be left as None).
               Defaults to True.

        :return: True if the file is within the passed repo (or within any repo
                 if check_all_repos is True. False otherwise.
        """

        if self.local_mode:
            return schemainterface.file_is_within_repo(file_p,
                                                       repo_name,
                                                       check_all_repos)
        else:
            raise ValueError("Remote operation not yet implemented.")

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
            raise ValueError("Remote operation not yet implemented.")

    # --------------------------------------------------------------------------
    def token_is_valid(self,
                       token_path):
        """
        Returns whether or not a token is valid.

        :return:
        """

        if self.local_mode:
            return schemainterface.token_is_valid(token_path)
        else:
            raise ValueError("Remote operation not yet implemented.")