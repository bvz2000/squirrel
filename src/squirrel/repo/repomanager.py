"""
The RepoManager class is the entry point for all actions related to repositories. It manages the list of repos and is
responsible for passing requests from the rest of asset management system to the individual repos.
"""

import os

from squirrel.repo.repo import Repo
from squirrel.repo.cache import Cache
from squirrel.repo import setuprepolist
from squirrel.shared import constants
from squirrel.shared import setupconfig
from squirrel.shared import setuplocalization
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

        self._load_repos_from_repos_list()
        self._load_default_repo()

        self.cache_obj = Cache(config_obj=self.config_obj,
                               localized_resource_obj=self.localized_resource_obj)
        self.cache_obj.cache_if_needed(self.repos.values())

    # ------------------------------------------------------------------------------------------------------------------
    def disambiguate_uri(self,
                         uri,
                         repo_required=False,
                         path_required=False,
                         name_required=False,
                         name_must_exist=True):
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
        :param name_must_exist:
                If True, then the name (if provided) must exist as an existing asset on disk.

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

            if self.default_repo is None:
                err_msg = self.localized_resource_obj.get_error_msg(203)
                raise SquirrelError(err_msg, 203)

            repo_n = self.default_repo.repo_n

            if repo_n not in self.repos.keys():
                err_msg = self.localized_resource_obj.get_error_msg(910)
                err_msg = err_msg.format(name=repo_n)
                raise SquirrelError(err_msg, 910)

            return repo_n + ":/#"

        # Split up the string into a repo and the remaining text.
        try:
            repo_n, remaining_str = uri.split(":/", maxsplit=1)
        except ValueError:  # There is no repo name
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
            self.cache_obj.validate_uri_path_against_cache(repo_n=repo_n,
                                                           uri_path=uri_path)

        # If there is an asset name, validate it
        if asset_n and name_must_exist:
            uri_path = self.cache_obj.uri_path_from_asset_name(repo_n=repo_n,
                                                               asset_n=asset_n)

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
        return self.cache_obj.uri_from_asset_path(asset_p)

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

        return self.cache_obj.uri_path_from_asset_path(asset_p)

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
                        cache_obj=self.cache_obj,
                        config_obj=self.config_obj,
                        localized_resource_obj=self.localized_resource_obj)

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
    def _load_repos_from_repos_list(self):
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
    # TODO: Also remove repo data from cache
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

        self.repo_list_obj.replace_section("defaults", {"default_repo": self.default_repo.repo_n})

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
                        cache_obj=self.cache_obj,
                        config_obj=self.config_obj,
                        localized_resource_obj=self.localized_resource_obj)

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
                        cache_obj=self.cache_obj,
                        config_obj=self.config_obj,
                        localized_resource_obj=self.localized_resource_obj)

        # Make sure the repo name is not already taken
        if repo_obj.repo_n in self.repos.keys() and repo_d != self.repos[repo_obj.repo_n].repo_root_d:
            err_msg = self.localized_resource_obj.get_error_msg(303)
            err_msg = err_msg.format(repo_name=repo_d)
            raise SquirrelError(err_msg, 303)

        self.repos[repo_obj.repo_n] = repo_obj
        self.bless_repo(repo_obj.repo_n)

    # ------------------------------------------------------------------------------------------------------------------
    # TODO: Also cache this repo
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
                        cache_obj=self.cache_obj,
                        config_obj=self.config_obj,
                        localized_resource_obj=self.localized_resource_obj)

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
