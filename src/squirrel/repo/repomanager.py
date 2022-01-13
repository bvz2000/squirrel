"""
The RepoManager class is the entry point for all actions related to repositories. It manages the list of repos and is
responsible for passing requests from the rest of asset management system to the individual repos.
"""

import inspect
import os
import sqlite3

from squirrel.repo.repo import Repo
from squirrel.repo import setuprepolist
from squirrel.shared import constants
from squirrel.shared import setupconfig
from squirrel.shared import setuplocalization
from squirrel.shared import setupsql
from squirrel.shared import urilib
from squirrel.shared.squirrelerror import SquirrelError


# ======================================================================================================================
class RepoManager(object):
    """
    A class to manage multiple repos on disk, and to pass requests down to those repos.
    """

    # ------------------------------------------------------------------------------------------------------------------
    def __init__(self,
                 config_p=None,
                 repo_list_p=None,
                 language="english"):
        """
        Initialize the manager object responsible for managing different repos. The actual functionality for individual
        repos are managed by the repo class.

        :param config_p:
                An optional path to a config file. If omitted or None, use either the path given by an env var OR the
                standard location for the config file.
        :param repo_list_p:
                An optional path to a repo list file that identifies which repos are active in the system. If omitted or
                None, use either the path given by an env var OR the standard location for the repo list file.
        :param language:
                The language used for communication with the end user. Defaults to "english".
        """

        self.language = language

        self.localized_resource_obj = setuplocalization.create_localization_object(language=language)

        self.config_obj = setupconfig.create_config_object(validation_dict=constants.REPO_CONFIG_SECTIONS,
                                                           localized_resource_obj=self.localized_resource_obj,
                                                           config_p=config_p)

        self.repo_list_obj = setuprepolist.create_repo_list_object(localized_resource_obj=self.localized_resource_obj,
                                                                   repo_list_p=repo_list_p)

        self.repos = dict()
        self.default_repo = None

        self.cache_d = self._cache_dir()
        self.cache_p = self._cache_path()

        self.sql_resources = setupsql.create_sql_object()
        self.connection = self._connect()
        self.cursor = self.connection.cursor()

        self._load_repos_from_repos_list_object()
        self._load_default_repo()

        self.cache_all()

    # ------------------------------------------------------------------------------------------------------------------
    def disambiguate_uri(self,
                         uri,
                         repo_required=False,
                         path_required=False,
                         name_required=False):
        """
        Given a partial uri, try to create a full, legal, existing uri (this includes the asset name). The format of a
        full URI is as follows:

        repo_name://relative/path/to/asset#asset_name

        The purpose of this function is to encapsulate any ambiguity stemming from allowing the end user to supply an
        incomplete URI into a single location. All other functions can then require an explicit URI. The rules about
        dealing with this ambiguity are as follows:

        1) If name_required is True, then the partial uri MUST include the full asset name regardless of what other
           portions are included. If False, then the uri may or may not include an asset name. Asset names are separated
           from the rest of the URI by the # character.
        2) If there is a :/ then the repo name will be drawn from the text in front of the :/. If there is no such :/
           string then the repo name will be drawn from the default repo. If there is no default repo, an error is
           raised.
        3) If there is a / (not including the :/ listed above) then it is assumed that the partial uri refers to either
           a) a full uri_path to an asset (including the asset name - see #1 above for more details)
           b) a full uri_path to the parent of an asset (i.e. the full path only without the asset name)
           or
           c) a partial uri_path that contains the first N number of path elements. Partial uri paths may not begin in
              the middle of a path. They must always begin at the root of the URI path.
           If none of these are the case, then an error is raised.
        4) If there is no / (not including the :/ listed above) then it is assumed that the partial uri is an asset
           name only without a path. An attempt will be made to find that asset name. If it does not exist, or exists
           more than once, an error is raised.
        5) If any of the above rules result in more than one asset being returned, or no assets being returned, an
           error is raised.

        Examples:

            reponame://uri/path/including#asset_name  <- Complete URI
            reponame://uri/path/including  <- Full URI path, without asset name
            reponame://uri/path  <- Partial URI path, without asset name
            reponame:/#asset_name  <- Repo name and asset name, no URI path. Note the single /
            reponame:/asset_name  <- Repo name and asset name, no URI path. Note the single / and the missing #
            /uri/path/including/#asset_name  <- Full URI path, including asset name, no repo name
            /uri/path/including  <- Full URI path, no asset name, no repo name
            /uri/path  <- Partial URI path, no asset name, no repo name
            #asset_name  <- Asset name only, no repo name, no URI path.
            asset_name  <- Asset name only, no repo name, no URI path. Note the missing #

        :param uri:
                The partial or complete uri to process.
        :param repo_required:
                If True, then a repo name is required. Defaults to False.
        :param path_required:
                If true, then a path is required (may be a partial path). Defaults to False.
        :param name_required:
                If True, then the asset name is a required part of the URI. Defaults to False.

        :return:
                A three item tuple consisting of the repo, path, and asset name. If any of those are missing and not
                required, that particular item will be set to "".
        """

        # TODO: Split this up into smaller functions
        # If they supplied just a blank string (or None), return just the default repo.
        if not uri:

            if repo_required or path_required or name_required:
                required = list()
                if repo_required:
                    required.append("repo name")
                if path_required:
                    required.append("URI path")
                if name_required:
                    required.append("asset name")
                required_str = ", ".join(required)
                required_str = ",and ".join(required_str.rsplit(", ", 1))
                err_msg = self.localized_resource_obj.get_error_msg(901)
                err_msg = err_msg.format(required=required_str)
                raise SquirrelError(err_msg, 901)

            repo_n = self.default_repo.repo_n

            if repo_n not in self.repos.keys():
                err_msg = self.localized_resource_obj.get_error_msg(910)
                err_msg = err_msg.format(name=repo_n)
                raise SquirrelError(err_msg, 910)

            return repo_n + ":/#"

        # Split up the string into a repo and the remaining text.
        try:
            repo_n, remaining_str = uri.split(":/", maxsplit=1)
        except ValueError:
            repo_n = ""
            remaining_str = uri

        # Split up the remaining_str into the path and the asset name.
        try:
            uri_path, asset_n = remaining_str.split("#", maxsplit=1)
        except ValueError:
            if "/" in remaining_str:
                uri_path = remaining_str
                asset_n = ""
            else:
                uri_path = ""
                asset_n = remaining_str
        # If there is no repo name, but one was required, raise an error
        if repo_required and not repo_n:
            err_msg = self.localized_resource_obj.get_error_msg(902)
            raise SquirrelError(err_msg, 902)

        # If there is no uri_path, but one was required, raise an error
        if path_required and not uri_path:
            err_msg = self.localized_resource_obj.get_error_msg(903)
            raise SquirrelError(err_msg, 903)

        # If there is no asset name, but one was required, raise an error
        if name_required and not asset_n:
            err_msg = self.localized_resource_obj.get_error_msg(904)
            raise SquirrelError(err_msg, 904)

        # If there is no repo name, get the default repo name
        if not repo_n:
            repo_n = self.default_repo.repo_n

        # If the repo name is not the name of a valid repo, raise an error
        if repo_n not in self.repos.keys():
            err_msg = self.localized_resource_obj.get_error_msg(102)
            err_msg = err_msg.format(repo_name=repo_n)
            raise SquirrelError(err_msg, 102)

        # If there is a uri_path, validate it
        if uri_path:

            sql = self.sql_resources.get("disambiguate_uri", "uri_path_exists")
            rows = self.cursor.execute(sql, (repo_n, uri_path + "%")).fetchall()
            if len(rows) == 0:
                err_msg = self.localized_resource_obj.get_error_msg(907)
                err_msg = err_msg.format(uri_path=uri_path)
                raise SquirrelError(err_msg, 907)

        if asset_n:

            sql = self.sql_resources.get("disambiguate_uri", "asset_name_exists")
            rows = self.cursor.execute(sql, (repo_n, asset_n)).fetchall()

            # If no assets match this name, raise an error
            if len(rows) == 0:
                err_msg = self.localized_resource_obj.get_error_msg(905)
                err_msg = err_msg.format(repo_n=repo_n, asset_n=asset_n)
                raise SquirrelError(err_msg, 905)

            # If more than one asset matches this name, raise an error
            if len(rows) > 1:
                err_msg = self.localized_resource_obj.get_error_msg(906)
                err_msg = err_msg.format(repo_n=repo_n, asset_n=asset_n)
                raise SquirrelError(err_msg, 906)

            sql = self.sql_resources.get("disambiguate_uri", "get_uri_path_from_asset_n")
            rows = self.cursor.execute(sql, (repo_n, asset_n)).fetchall()

            if len(rows) == 0:
                err_msg = self.localized_resource_obj.get_error_msg(908)
                err_msg = err_msg.format(asset_n=asset_n)
                raise SquirrelError(err_msg, 908)

            if len(rows) > 1:
                err_msg = self.localized_resource_obj.get_error_msg(909)
                err_msg = err_msg.format(asset_n=asset_n)
                raise SquirrelError(err_msg, 909)

            uri_path = rows[0][0]

        return f"{repo_n}:/{uri_path}#{asset_n}"

    # ------------------------------------------------------------------------------------------------------------------
    def uri_from_asset_path(self,
                            asset_p):
        """
        Given an asset path, return the uri path.

        :param asset_p:
                The full path to the asset.

        :return:
                A URI.
        """

        sql = self.sql_resources.get("sql", "asset_uri_from_path")
        rows = self.cursor.execute(sql, (asset_p,)).fetchall()

        return rows[0][0]

    # ------------------------------------------------------------------------------------------------------------------
    def uri_path_from_asset_path(self,
                                 asset_p):
        """
        Given an asset path, return the uri path.

        :param asset_p:
                The full path to the asset.

        :return:
                A URI path.
        """

        sql = self.sql_resources.get("sql", "asset_uri_path_from_path")
        rows = self.cursor.execute(sql, (asset_p,)).fetchall()

        return rows[0][0]

    # ------------------------------------------------------------------------------------------------------------------
    def repo_obj_from_uri(self,
                          uri):
        """
        Given a URI, return a repo object.

        :param uri:
                The URI.

        :return:
                A repo object.
        """

        if not urilib.validate_uri_format(uri):
            err_msg = self.localized_resource_obj.get_error_msg(201)
            err_msg = err_msg.format(uri=uri)
            raise SquirrelError(err_msg, 201)

        repo_n = urilib.repo_name_from_uri(uri)

        try:
            return self.repos[repo_n]
        except KeyError:
            err_msg = self.localized_resource_obj.get_error_msg(304)
            err_msg = err_msg.format(repo_name=repo_n)
            raise SquirrelError(err_msg, 304)

    # ------------------------------------------------------------------------------------------------------------------
    def _load_default_repo(self):
        """
        Gets the default repository object. It will first attempt to get it from the user's environment from an env
        variable. If that variable does not exist, it will attempt to extract it from the repos list file.

        :return:
                The default repo object. If there is no default, return None.
        """

        try:
            default_repo_name = os.environ[constants.DEFAULT_REPO]
        except KeyError:
            if self.repo_list_obj.has_option("defaults", "default_repo"):
                default_repo_name = self.repo_list_obj.get_string("defaults", "default_repo")
            else:
                return None

        if not self._name_is_existing_repo(default_repo_name):
            return None

        if default_repo_name not in self.repos.keys():
            return None

        self.default_repo = self.repos[default_repo_name]

    # ----------------------------------------------------------------------------------------------------------------
    def _cache_dir(self):
        """
        Returns the path to the directory where the cache file is stored.

        :return:
                A path to the directory in which cache files are stored.
        """

        if constants.CACHE_PATH_ENV_VAR in os.environ.keys():
            cache_d = os.environ[constants.CACHE_PATH_ENV_VAR]
        elif self.config_obj.get_string("repo_settings", "cache_dir") != "":
            cache_d = self.config_obj.get_string("repo_settings", "cache_dir")
        else:
            module_d = os.path.split(inspect.stack()[0][1])[0]
            cache_d = os.path.join(module_d, "..", "..", "..", "cache")

        if not os.path.isdir(cache_d):
            err_msg = self.localized_resource_obj.get_error_msg(800)
            err_msg = err_msg.format(cache_dir=cache_d,
                                     config_dir_env_var=constants.CACHE_PATH_ENV_VAR)
            raise SquirrelError(err_msg, 800)

        return cache_d

    # ------------------------------------------------------------------------------------------------------------------
    def _cache_path(self):
        """
        Returns a path to the cache database file.

        :return:
                A path to the cache database file.
        """

        return os.path.join(self.cache_d, "squirrel.db")

    # ------------------------------------------------------------------------------------------------------------------
    def _connect(self):
        """
        Connects to the cache database.

        :return:
                A sqlite3 connection object.
        """

        return sqlite3.connect(self.cache_p)

    # ------------------------------------------------------------------------------------------------------------------
    def _drop_all_cache_tables(self):
        """
        Drops all of the tables from the cache db.

        :return:
                Nothing.
        """

        sql = self.sql_resources.get("sql", "delete_cache_list_tables")
        tables = self.cursor.execute(sql).fetchall()

        sql = self.sql_resources.get("sql", "delete_cache_drop_tables")
        for item in tables:
            self.cursor.execute(sql.format(table=item[0]))

        self.connection.commit()

    # ------------------------------------------------------------------------------------------------------------------
    def _build_cache_tables(self):
        """
        Creates the empty cache tables.

        :return:
                Nothing.
        """

        self._drop_all_cache_tables()

        sql = self.sql_resources.get("build_cache_tables", "assets")
        self.cursor.execute(sql)
        self.connection.commit()

        sql = self.sql_resources.get("build_cache_tables", "keywords")
        self.cursor.execute(sql)
        self.connection.commit()

        sql = self.sql_resources.get("build_cache_tables", "metadata")
        self.cursor.execute(sql)
        self.connection.commit()

        sql = self.sql_resources.get("build_cache_tables", "assets_keywords")
        self.cursor.execute(sql)
        self.connection.commit()

        sql = self.sql_resources.get("build_cache_tables", "assets_metadata")
        self.cursor.execute(sql)
        self.connection.commit()

        sql = self.sql_resources.get("build_cache_tables", "thumbnails")
        self.cursor.execute(sql)
        self.connection.commit()

        sql = self.sql_resources.get("build_cache_tables", "posters")
        self.cursor.execute(sql)
        self.connection.commit()

    # ------------------------------------------------------------------------------------------------------------------
    def build_cache_for_repo(self,
                             uri):
        """
        Builds the cache for a specific repo.

        :param uri:
                The URI that holds the name of the repo.

        :return:
                Nothing.
        """

        if not urilib.validate_uri_format(uri):
            err_msg = self.localized_resource_obj.get_error_msg(201)
            err_msg = err_msg.format(uri=uri)
            raise SquirrelError(err_msg, 201)

        repo_n = urilib.repo_name_from_uri(uri)
        repo_obj = self.repos[repo_n]
        repo_obj.cache_assets_from_filesystem()

    # ------------------------------------------------------------------------------------------------------------------
    def build_cache_for_all_repos(self):
        """
        Builds the cache from the data on the filesystem for all repos. If the cache already exists, the current data
        will be removed and replaced.

        :return:
                Nothing.
        """

        self._build_cache_tables()

        for repo_n in self.repos.keys():
            self.build_cache_for_repo(uri=f"{repo_n}:/#")

    # ------------------------------------------------------------------------------------------------------------------
    def cache_all(self):
        """
        If the cache does not exist, or if any table is missing, create a new cache. If it does exist and all the tables
        are good, do nothing.

        :return:
                Nothing.
        """

        if not os.path.exists(self.cache_p):
            self.build_cache_for_all_repos()
            return

        tables = self.sql_resources.get("tables", "tables").split(",")
        sql = self.sql_resources.get("sql", "delete_cache_list_tables")

        rows = self.cursor.execute(sql).fetchall()

        if len(rows) == 0:
            self.build_cache_for_all_repos()

        for row in rows:
            if row[0] not in tables:
                self.build_cache_for_all_repos()
                return

    # ------------------------------------------------------------------------------------------------------------------
    def _load_repo(self,
                   repo_p):
        """
        Loads a single repo given a path. If the path given does not point to a valid repo dir, an error will be raised.

        :param repo_p:
                The path to the repo to load. The path must exist and must be a valid repo. Raises an error if not.

        :return:
                Nothing.
        """

        assert type(repo_p) is str

        if not os.path.exists(repo_p) or not os.path.isdir(repo_p):
            err_msg = self.localized_resource_obj.get_error_msg(302)
            err_msg = err_msg.format(repo_path=repo_p)
            raise SquirrelError(err_msg, 302)

        repo_obj = Repo(repo_root_d=repo_p,
                        cache_d=self.cache_d,
                        config_obj=self.config_obj,
                        localized_resource_obj=self.localized_resource_obj,
                        sql_resources=self.sql_resources,
                        connection=self.connection,
                        cursor=self.cursor)

        if not repo_obj.is_repo():
            err_msg = self.localized_resource_obj.get_error_msg(301)
            err_msg = err_msg.format(repo_path=repo_p)
            raise SquirrelError(err_msg, 301)

        self.repos[repo_obj.repo_n] = repo_obj

    # ------------------------------------------------------------------------------------------------------------------
    def _load_repos(self,
                    repos):
        """
        Loads all of the repos given in the list repos. Kicks up an error if any are missing or corrupt AND
        warn_on_load_error OR fail_on_load_error is set to True in the config file.

        :param repos:
                A list of full paths to the repos to be loaded.

        :return:
                Nothing.
        """

        assert type(repos) is list

        warn_on_load_error = self.config_obj.get_boolean("repo_settings", "warn_on_load_error")
        fail_on_load_error = self.config_obj.get_boolean("repo_settings", "fail_on_load_error")

        for repo_path in repos:
            try:
                self._load_repo(repo_p=repo_path)
            except SquirrelError as e:
                if e.code in [301, 302]:
                    if fail_on_load_error:
                        err_msg = self.localized_resource_obj.get_error_msg(310)
                        err_msg = err_msg.format(message=str(e))
                        raise SquirrelError(err_msg, 310)
                    if warn_on_load_error:  # <- rely on upstream to check the code and not actually quit.
                        err_msg = self.localized_resource_obj.get_error_msg(311)
                        err_msg = err_msg.format(message=str(e))
                        raise SquirrelError(err_msg, 311)
                else:
                    raise

    # ------------------------------------------------------------------------------------------------------------------
    def _load_repos_from_repos_list_object(self):
        """
        Loads all of the repos listed in the repo list file. Kicks up an error if any are missing or corrupt AND
        warn_on_load_error OR fail_on_load_error is set to True in the config file.

        :return:
                Nothing.
        """

        repo_names = self.repo_list_obj.options("repos")
        repos_p = list()
        for repo_name in repo_names:
            repos_p.append(self.repo_list_obj.get_string("repos", repo_name))

        try:
            self._load_repos(repos_p)
        except SquirrelError as e:
            if e.code != 311:
                raise

    # ------------------------------------------------------------------------------------------------------------------
    def unload_repo(self,
                    repo_n):
        """
        Unloads a single repo.

        :param repo_n:
                The name of the repo to unload.

        :return:
                Nothing.
        """

        assert type(repo_n) is str and repo_n

        if repo_n not in self.repos.keys():
            err_msg = self.localized_resource_obj.get_error_msg(102)
            err_msg = err_msg.format(repo_name=repo_n)
            raise SquirrelError(err_msg, 102)

        del(self.repos[repo_n])

    # ------------------------------------------------------------------------------------------------------------------
    def _name_is_existing_repo(self,
                               repo_n):
        """
        Given a repo name, does a very minimal check to see if the repo is valid. Basically checks to see if the name is
        in the list of loaded repos.

        :param repo_n:
                The name of the repo we are testing.

        :return:
                True if the repo is valid. False otherwise.
        """

        assert type(repo_n) is str

        return repo_n in self.repos.keys()

    # ------------------------------------------------------------------------------------------------------------------
    def _update_repo_list_file(self,
                               purge=False):
        """
        Updates the repo list file to reflect the current state of all loaded repos.

        :param purge:
                If true, repos listed in the repo list file that do not exist on disk will be removed. If False, then
                these repos will be left in the file. Defaults to False.

        :return:
                Nothing.
        """

        assert type(purge) is bool

        repos = dict()
        for key, value in self.repos.items():
            repos[key] = value.repo_root_d

        if purge:
            self.repo_list_obj.replace_section("repos", repos)
        else:
            self.repo_list_obj.merge_section("repos", repos)

        self.repo_list_obj.replace_section("defaults", {"default_repo": self.default_repo})

    # ------------------------------------------------------------------------------------------------------------------
    def save_repo_list_file(self):
        """
        Saves the repo list file with all of the changes made during the current session (by add_repo, make_repo).

        :return:
                Nothing.
        """

        self._update_repo_list_file(purge=True)
        self.repo_list_obj.save()

    # ------------------------------------------------------------------------------------------------------------------
    def bless_repo(self,
                   repo_p):
        """
        Given a path to a repo, blesses all of the directories within the root path.

        :param repo_p:
                The repo path.

        :return:
                Nothing.
        """

        # Create a temporary repo object that points to this path.
        if not os.path.isdir(repo_p):
            err_msg = self.localized_resource_obj.get_error_msg(302)
            err_msg = err_msg.format(repo_path=repo_p)
            raise SquirrelError(err_msg, 302)

        repo_obj = Repo(repo_root_d=repo_p,
                        cache_d=self.cache_d,
                        config_obj=self.config_obj,
                        localized_resource_obj=self.localized_resource_obj,
                        sql_resources=self.sql_resources,
                        connection=self.connection,
                        cursor=self.cursor)

        repo_obj.bless_repo()

    # ------------------------------------------------------------------------------------------------------------------
    def make_repo(self,
                  repo_d):
        """
        Given a path, creates a new repo out of this path by blessing the directory structure. Automatically adds the
        new repo to the list of existing repos.

        :param repo_d:
                The path to the directory structure that should be made into a repo.

        :return:
                Nothing.
        """

        if not os.path.isdir(repo_d):
            err_msg = self.localized_resource_obj.get_error_msg(100)
            err_msg = err_msg.format(dir=repo_d)
            raise SquirrelError(err_msg, 100)

        repo_obj = Repo(repo_root_d=repo_d,
                        cache_d=self.cache_d,
                        config_obj=self.config_obj,
                        localized_resource_obj=self.localized_resource_obj,
                        sql_resources=self.sql_resources,
                        connection=self.connection,
                        cursor=self.cursor)

        # Make sure the repo name is not already taken
        if repo_obj.repo_n in self.repos.keys() and repo_d != self.repos[repo_obj.repo_n].repo_root_d:
            err_msg = self.localized_resource_obj.get_error_msg(303)
            err_msg = err_msg.format(repo_name=repo_d)
            raise SquirrelError(err_msg, 303)

        self.repos[repo_obj.repo_n] = repo_obj
        self.bless_repo(repo_obj.repo_n)

    # ------------------------------------------------------------------------------------------------------------------
    def add_repo(self,
                 repo_d):
        """
        Adds the repo to the dictionary of repos as well as to the config file.

        :param repo_d:
                The path to the repository. Must be a blessed root path. Note: if the name of this directory is the same
                as an existing repo, an error will be raised.

        :return:
                Nothing.
        """

        assert os.path.isdir(repo_d)

        repo_obj = Repo(repo_root_d=repo_d,
                        config_obj=self.config_obj,
                        cache_d=self.cache_d,
                        localized_resource_obj=self.localized_resource_obj,
                        sql_resources=self.sql_resources,
                        connection=self.connection,
                        cursor=self.cursor)

        # Make sure the repo name is not already taken
        if repo_obj.repo_n in self.repos.keys() and repo_d != self.repos[repo_obj.repo_n].repo_root_d:
            err_msg = self.localized_resource_obj.get_error_msg(303)
            err_msg = err_msg.format(repo_name=repo_d)
            raise SquirrelError(err_msg, 303)

        # Make sure the path points to a valid, blessed repo
        if not repo_obj.is_repo():
            err_msg = self.localized_resource_obj.get_error_msg(301)
            err_msg = err_msg.format(repo_path=repo_d)
            raise SquirrelError(err_msg, 301)

        self.repos[repo_obj.repo_n] = repo_obj

    # ------------------------------------------------------------------------------------------------------------------
    def list_repos(self):
        """
        Returns a list containing all of the repo objects.

        :return:
                A list of repo objects.
        """

        return list(self.repos.values())

    # ------------------------------------------------------------------------------------------------------------------
    def list_broken_repos(self):
        """
        Returns a dictionary where the key is the name of the repo that is missing from disk, and the value is the path
        where this repo should have been.

        :return:
                a dictionary where the key is the name of the repo that is missing from disk, and the value is the path
                where this repo should have been.
        """

        repo_names = self.repo_list_obj.options("repos")

        output = dict()
        for repo_name in repo_names:
            if repo_name not in self.repos.keys():
                output[repo_name] = self.repo_list_obj.get_string("repos", repo_name)

        return output

    # ------------------------------------------------------------------------------------------------------------------
    def set_default_repo(self,
                         repo_n):
        """
        Sets the default repository.

        :param repo_n:
                The name of the default repo. This repo must exist in the list of current repos.

        :return:
        """

        assert type(repo_n) is str and repo_n

        # The target repo must exist in the list of repos
        if repo_n not in self.repos.keys():
            err_msg = self.localized_resource_obj.get_error_msg(102)
            err_msg = err_msg.format(repo_name=repo_n)
            raise SquirrelError(err_msg, 102)

        self.default_repo = self.repos[repo_n].repo_n
