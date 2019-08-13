'''
#! /usr/bin/env python3

# Needed in case this code is called from python 2.7
try:
    import configparser
except ImportError:
    import ConfigParser as configparser

import os

import repo
from modules.amSchema.repo import repo, config, lib

from .squirrelerror import SquirrelError


class Application(object):
    """
    Main application object for the squirrel app.
    Some terminology:
    -----------------
    Repository: A repository is a series of directories on disk. A repo may
                contain multiple levels (nested sub-directories) which define
                the repo structure. At the very ends of these nested directories
                are the actual assets being stored in the repository. There may
                be any number of repos on a filesystem.
    Token:      A string in a UNIX path format (i.e. /using/this/format) that
                describes a relative path to a point inside the repository
                structure. This path is relative to the repo root. Tokens are
                always references to actual directories, and they are always
                passed as UNIX style relative paths even on Windows systems.
                Tokens never resolve all the way down to the asset level. They
                only describe the structure of the repo itself.
    Structure:  Repositories are defined by a directory structure consisting of
                "blessed" directories (and no files). This structure defines the
                hierarchy of the repo, with each sub-directory making up the
                "branches" of the repo. The very last sub-directory of each
                branch is considered a "leaf" structure. No files or non-blessed
                directories may live at any level of the structure except the
                final, leaf level. Within the leaf level are the asset sub-dirs
                and any files being managed by this repo.
    Managed:    A "managed" file or directory is any file or directory that is
                below the structure level of the repo. Managed files and dirs
                are essentially the assets being stored by the repo.
    Assets:     Assets are directories that contain files. Assets are defined to
                only exist as special directories in the leaf structure dirs.
                Assets always have a .asset file in them (at the top level) that
                marks them as actually being an asset. There should never be
                any managed files outside of an asset. Assets only contain
                version sub-directories and other squirrel-related metadata.
    Versions:   Versions are sub-directories inside of an asset. These dirs
                contain any number of files and sub-directories (to any level
                of nesting) that define the contents of the asset. Versions do
                not have any special files or directories within them other than
                the data being managed for the end users.
    Some naming conventions:
    ------------------------
    Variables ending in "_d" are directory paths, without a file name attached.
    Variables ending in "_n" are file names, without a directory attached.
    Variables ending in "_p" are full paths, including both the path and name.
    Variables ending in "_f" are file-descriptor objects.
    About the Squirrel repository structure:
    ----------------------------------------
    Squirrel repositories are simply "blessed" directories on disk. The root
    level of a repository is just a normal directory, but it has a hidden file
    in it called .squirrel_root.
    There may be any number of sub-directories inside of this root directory,
    and any number of levels of these subdirectories.  Each of these directories
    is identified as being the "structure" of the repository by containing a
    hidden file in it called .squirrel.
    The very last level of sub-directories that are part of the repo structure
    (i.e. contain .squirrel files in them) are considered leaf structure dirs.
    Only these directories may contain anything other than other structure dirs,
    and they may only contain asset dirs.
    Once a dir is found that does not have a .squirrel file in it, that dir
    should be considered the asset that the system is tracking. These dirs must
    contain an .asset file in them to denote that they are assets.
    There can be no gaps inside the structure of a repo. I.e. you cannot have
    the root directory followed by a level (blessed dir) followed by a
    non-blessed dir which then contains another structure dir (blessed dir).
    This kind of non-contiguous structure may result in errors or undefined
    behavior.
    There is no requirement than any two branches in a repository have the same
    structure. One branch could have as many as three or four nested sub-dirs,
    and another might only have one. The structure of the repository is entirely
    free-form in this regard (and may be modified at any time).
    There may be as many repositories on disk as desired.
    """
    def __init__(self, app_d, resc):
        """
        Init.
        :param app_d: The path to this application on disk.
        :param resc: The resources object.
        :return: Nothing.
        """
        self.app_d = app_d
        self.resc = resc
        # Create and read the config object
        self.cfg = config.Config(self.app_d, self.resc)
        # Create a repo object for each repo.
        self.repos = dict()
        self.load_repos()
        # Get the default repo
        default_repo_name = self.cfg.get_default_repo()
        if default_repo_name is not None:
            try:
                self.default_repo = self.repos[default_repo_name]
            except KeyError:
                self.default_repo = None
        else:
            self.default_repo = None
    # --------------------------------------------------------------------------
    def load_repos(self):
        """
        Loads all of the repos.
        :return: Nothing.
        """
        self.repos = dict()
        for repo_path in self.cfg.repo_paths:
            try:
                self.load_repo(repo_path)
            except SquirrelError:
                if self.cfg.ignore_broken_or_missing_repos:
                    if self.cfg.warn_broken_or_missing_repos:
                        err = self.resc.error(202)
                        err.msg = err.msg.format(repo_path=repo_path)
                        lib.process_error(err.msg, err.code, True, False, False)
                    continue
                else:
                    err = self.resc.error(203)
                    err.msg = err.msg.format(repo_path=repo_path)
                    raise SquirrelError(err.msg, err.code)
    # --------------------------------------------------------------------------
    def load_repo(self, repo_path):
        """
        Loads a single repo.
        :param repo_path: The path to the repo to load. Assumes that the path
               exists and is a valid repo. Raises an error if not.
        :return: Nothing.
        """
        repo_obj = repo.Repo(self, repo_path)
        self.repos[repo_obj.name] = repo_obj
    # --------------------------------------------------------------------------
    def add_repo(self, repo_p):
        """
        Adds an existing (already blessed) repo to the config file.
        :param repo_p: The path to the already blessed repo.
        :return: Nothing.
        """
        repo_p = os.path.abspath(repo_p)
        # Verify that the path exists.
        if not os.path.exists(repo_p):
            err = self.resc.error(400)
            err.msg = err.msg.format(path=repo_p)
            raise SquirrelError(err.msg, err.code)
        # Verify that it is a directory.
        if not os.path.isdir(repo_p):
            err = self.resc.error(401)
            err.msg = err.msg.format(path=repo_p)
            raise SquirrelError(err.msg, err.code)
        # Verify that it is a blessed root dir.
        if not os.path.exists(os.path.join(repo_p, ".squirrel_root")):
            err = self.resc.error(203)
            err.msg = err.msg.format(repo_path=repo_p)
            raise SquirrelError(err.msg, err.code)
        # Verify that a repo of this name does not already exist.
        squirrel_obj = configparser.ConfigParser()
        squirrel_obj.read(os.path.join(repo_p, ".squirrel_root"))
        if squirrel_obj.has_option("settings", "name"):
            repo_name = squirrel_obj.get("settings", "name")
        else:
            err = self.resc.error(205)
            err.msg = err.msg.format(path=repo_p)
            raise SquirrelError(err.msg, err.code)
        if repo_name in self.repos.keys():
            err = self.resc.error(601)
            err.msg = err.msg.format(repo=repo_name,
                                     path=self.repos[repo_name].path)
            raise SquirrelError(err.msg, err.code)
        self.cfg.add_repo(repo_p)
    # --------------------------------------------------------------------------
    def set_default_repo(self, repo_n):
        """
        Given the name of a repo, makes it the default in the config file.
        :param repo_n: The name of the repo.
        :return: Nothing.
        """
        # Verify that the repo exists
        if repo_n not in self.repos.keys():
            err = self.resc.error(204)
            err.msg = err.msg.format(repo=repo_n)
            raise SquirrelError(err.msg, err.code)
        # Set it as the default
        self.cfg.set_default_repo(repo_n)
    # --------------------------------------------------------------------------
    def list_repository_names(self):
        """
        Returns a list of the repository names.
        :return: a list of the repositories as strings.
        """
        return self.repos.keys()
    # ------------------------------------------------------------------------------
    def get_formatted_list_of_repo_names(self):
        """
        Returns a formatted string of all the repository names.
        :return: A string.
        """
        output = list()
        repo_names = list(self.list_repository_names())
        repo_names.sort()
        # Get the default repo name
        default_repo_name = ""
        if self.default_repo is not None:
            default_repo_name = self.default_repo.name
        for repo_name in repo_names:
            if repo_name == default_repo_name:
                output.append("(default) " + repo_name)
            else:
                output.append("          " + repo_name)
        return "\n".join(output)
    # --------------------------------------------------------------------------
    def list_repository_paths(self):
        """
        Returns a list of the full path to all of the repositories.
        :return: a list of the repository paths as strings.
        """
        output = list()
        for repo_name in self.repos.keys():
            output.append(self.repos[repo_name].path)
        return output
    # ------------------------------------------------------------------------------
    def get_formatted_list_of_repo_paths(self):
        """
        Returns a formatted string of all the repository paths.
        :return: A string.
        """
        output = list()
        repo_paths = list(self.list_repository_paths())
        repo_paths.sort()
        # Get the default repo name
        default_repo_name = ""
        if self.default_repo is not None:
            default_repo_name = self.default_repo.name
        # Get the repo names
        repo_names = list()
        for repo_path in repo_paths:
            repo_names.append(self.get_repo_name_from_path(repo_path))
        max_len = lib.get_max(repo_names)
        for repo_path in repo_paths:
            repo_path = repo_path.rstrip(os.path.sep)
            repo_name = self.get_repo_name_from_path(repo_path)
            repo_name = repo_name.rjust(max_len, " ")
            if repo_name == default_repo_name:
                output.append("(default) " + repo_name + " - " + repo_path)
            else:
                output.append("          " + repo_name + " - " + repo_path)
        return "\n".join(output)
    # --------------------------------------------------------------------------
    def get_repo_name_from_path(self, path_d):
        """
        Given a repo path, return the name. Raise an error if the path does not
        exist in self.repos.
        :param path_d: The repo path
        :return: The name of the repo
        """
        compare_d = path_d.rstrip(os.path.sep)
        for repo_n in self.repos.keys():
            if self.repos[repo_n].path.rstrip(os.path.sep) == compare_d:
                return repo_n
        err = self.resc.error(203)
        err.msg = err.msg.format(repo_path=path_d)
        raise SquirrelError(err.msg, err.code)
    # --------------------------------------------------------------------------
    def repo_exists(self, repo_name):
        """
        Validates the repo. Just a basic True if the repo exists. False
        otherwise.
        :param repo_name: The name of the repo to validate.
        :return: True if the repo is valid, False otherwise.
        """
        return repo_name in self.repos.keys()
    # --------------------------------------------------------------------------
    def get_repo_object(self, repo_name):
        """
        Given a repo name, returns the repo object. Raises an error if the repo
        does not exist.
        :param repo_name: The name of the repo.
        :return: A repo object of this name.
        """
        if repo_name not in self.repos.keys():
            err = self.resc.error(600)
            err.msg = err.msg.format(repo=repo_name,
                                     repos=", ".join(self.repos.keys()))
            raise SquirrelError(err.msg, err.code)
        return self.repos[repo_name]
    # --------------------------------------------------------------------------
    def get_repo_object_of_item(self, path_p, managed_only=True):
        """
        Returns the repo object that contains the item: path_p.
        :param path_p: The path we are testing.
        :param managed_only: If True, only managed items will be considered.
               (managed items are contents of a repo, not structure). If False,
               then both managed items and structure dirs will be accepted.
        :return: The repo object that manages the item.
        """
        for repo_obj in self.repos.values():
            if managed_only:
                if repo_obj.path_is_repo_content(path_p):
                    return repo_obj
            else:
                if repo_obj.path_is_within_repo(path_p):
                    return repo_obj
        return None
    # --------------------------------------------------------------------------
    def get_token_of_item(self, item_p):
        """
        Given a full path to an item, returns the token for this item (if it is
        managed by a repository).
        :param item_p: The path to the item.
        :return: The token for this path.
        """
        repo_obj = self.get_repo_object_of_item(item_p, True)
        if repo_obj is None:
            err = self.resc.error(300)
            err.msg = err.msg.format(path=item_p)
            raise SquirrelError(err.msg, err.code)
        return repo_obj.get_token_from_path(item_p)
    # --------------------------------------------------------------------------
    def asset_exists(self, asset_name, repo_name, token="/"):
        """
        Given a name of a potential asset, returns True if that asset lives in
        the repo given by repo_name. If token is anything other than "/", then
        only assets that live in that sub-branch of the repository will be
        searched.
        :param asset_name: The name of the asset being tested.
        :param repo_name: The name of the repo to search.
        :param token: An optional sub-section of the repo to limit the search.
        :return: True if the asset exists in the passed repo and token. False
                 otherwise.
        """
        repos = self.list_asset_names(repo_name, token)
        return asset_name in repos
    # --------------------------------------------------------------------------
    def list_asset_names(self, repo_name, token="/"):
        """
        Returns a string list all of the asset names in the passed repo.
        :param repo_name: The name of the repo we are interested in.
        :param token: The token used to limit the results. Defaults to "/" which
               means do not filter.
        :return: Nothing.
        """
        repo_obj = self.get_repo_object(repo_name)
        return repo_obj.list_asset_names(token)
    # --------------------------------------------------------------------------
    def get_formatted_list_of_asset_names(self, repo_name, token="/"):
        """
        Returns a string list all of the asset names in the passed repo.
        :param repo_name: The name of the repo we are interested in.
        :param token: The token used to limit the results. Defaults to "/" which
               means do not filter.
        :return: Nothing.
        """
        return "\n".join(self.list_asset_names(repo_name, token))
    # --------------------------------------------------------------------------
    def list_asset_paths(self, repo_name, token="/"):
        """
        Returns a string list all of the asset paths in the passed repo.
        :param repo_name: The name of the repo we are interested in.
        :param token: The token used to limit the results. Defaults to "/" which
               means do not filter.
        :return: Nothing.
        """
        repo_obj = self.get_repo_object(repo_name)
        return repo_obj.list_asset_paths(token)
    # --------------------------------------------------------------------------
    def get_formatted_list_of_asset_paths(self, repo_name, token="/"):
        """
        Returns a string list all of the asset paths in the passed repo.
        :param repo_name: The name of the repo we are interested in.
        :param token: The token used to limit the results. Defaults to "/" which
               means do not filter.
        :return: Nothing.
        """
        return "\n".join(self.list_asset_paths(repo_name, token))
    # --------------------------------------------------------------------------
    def get_repo_name_of_item(self, path_p, managed_only=True):
        """
        Returns the name of the repo that contains the item: path_p.
        :param path_p: The path we are testing.
        :param managed_only: If True, only managed items will be considered.
               (managed items are contents of a repo, not structure). If False,
               then both managed items and structure dirs will be accepted.
        :return: The name of the repo that contains the path: path_p. None if no
                 repo contains the path.
        """
        repo_obj = self.get_repo_object_of_item(path_p, managed_only)
        if repo_obj:
            return repo_obj.name
        return None
    # --------------------------------------------------------------------------
    def get_repo_path_of_item(self, path_p, managed_only=True):
        """
        Returns the path of the repo that contains the item: path_p.
        :param path_p: The path we are testing.
        :param managed_only: If True, only managed items will be considered.
               (managed items are contents of a repo, not structure). If False,
               then both managed items and structure dirs will be accepted.
        :return: The path of the repo that contains the path: path_p. None if no
                 repo contains the path.
        """
        repo_obj = self.get_repo_object_of_item(path_p, managed_only)
        if repo_obj:
            return repo_obj.path
        return None
    # --------------------------------------------------------------------------
    def item_is_in_any_repo(self, path_p, managed_only=True):
        """
        Returns whether a given path is within any of the repos.
        :param path_p: The path we are testing.
        :param managed_only: If True, only managed items will be considered.
               (managed items are contents of a repo, not structure). If False,
               then both managed items and structure dirs will be accepted.
        :return: True if it is within a repo. False otherwise.
        """
        repo_obj = self.get_repo_object_of_item(path_p, managed_only)
        if repo_obj:
            return True
        return False
    # --------------------------------------------------------------------------
    def item_is_in_specific_repo(self, path_p, repo_name, managed_only=True):
        """
        Returns whether a given path is within a repo given by repo_name or not.
        Raises an error if the repo named repo_name does not exist.
        :param path_p: The path we are testing.
        :param repo_name: The repo we are testing.
        :param managed_only: If True, only managed items will be considered.
               (managed items are contents of a repo, not structure). If False,
               then both managed items and structure dirs will be accepted.
        :return: True if it is within a repo. False otherwise.
        """
        if repo_name not in self.repos.keys():
            err = self.resc.error(204)
            err.msg = err.msg.format(repo=repo_name)
            raise SquirrelError(err.msg, err.code)
        if managed_only:
            return self.repos[repo_name].path_is_repo_content(path_p)
        return self.repos[repo_name].path_is_within_repo(path_p)
    # --------------------------------------------------------------------------
    def path_is_asset(self, path_p):
        """
        Given a path, returns True if the path points to an asset. False
        otherwise.
        :param path_p: The path we want to see if it is an asset or not.
        :return: True if it is an asset, False otherwise.
        """
        if os.path.exists(os.path.join(path_p, ".asset")):
            if self.item_is_in_any_repo(path_p):
                return True
        return False
    # --------------------------------------------------------------------------
    def get_asset_path_of_item(self, path_p):
        """
        Returns the path of the asset that contains the item: path_p. If no
        asset is found, returns None.
        :param path_p: The path we are testing.
        :return: The path of the asset that contains the path: path_p. None if
                 no asset contains the path.
        """
        repo_obj = self.get_repo_object_of_item(path_p)
        if not repo_obj:
            return None
        return repo_obj.get_asset_path_of_item(path_p)
    # --------------------------------------------------------------------------
    def get_asset_name_of_item(self, path_p):
        """
        Returns the name of the asset that contains the item: path_p. If no
        asset is found, returns None.
        :param path_p: The path we are testing.
        :return: The path of the asset that contains the path: path_p. None if
                 no asset contains the path.
        """
        repo_obj = self.get_repo_object_of_item(path_p)
        if not repo_obj:
            return None
        return repo_obj.get_asset_name_of_item(path_p)
    # --------------------------------------------------------------------------
    def get_version_path_of_item(self, path_p):
        """
        Returns the path of the specific version in an asset that contains the
        item: path_p. If no asset is found, returns None.
        :param path_p: The path we are testing.
        :return: The path of the specific version of an asset that contains the
                 path: path_p. None if no asset contains the path.
        """
        repo_obj = self.get_repo_object_of_item(path_p)
        if not repo_obj:
            return None
        return repo_obj.get_version_path_of_item(path_p)
    # --------------------------------------------------------------------------
    def get_version_name_of_item(self, path_p):
        """
        Returns the name of the version of an asset that contains the item:
        path_p. If no asset is found, returns None.
        :param path_p: The path we are testing.
        :return: The name of the version of an asset that contains the path:
                 path_p. None if no asset contains the path.
        """
        repo_obj = self.get_repo_object_of_item(path_p)
        if not repo_obj:
            return None
        return repo_obj.get_version_name_of_item(path_p).rstrip(os.path.sep)
    # --------------------------------------------------------------------------
    def bless_dir(self, path, root=False, data_type="", name=None):
        """
        "Blesses" a particular path to include it as part of a repository. There
        are two types of blessed directories: Root and Normal. A Root directory
        can only live at the top of a hierarchy. A Normal directory can only
        live inside of another Normal directory or a Root directory. If the
        dirtype is set to "Root" then a name of the repository must also be
        included. Note: if more than one repository with the same name exists in
        the system, it would be undefined where assets will be placed, so
        duplicate repo names are not permitted.
        :param path: The path to where the blessed dir is. This dir must exist.
        :param root: If True, then this is a root dir. Otherwise it is a normal
               structure dir.
        :param data_type: An optional string that identifies the type of the
               dir.
        :param name: If the dirtype is "Root", then a name of the repo must also
               be included.
        :return: Nothing.
        """
        if root:
            assert name is not None
        if not os.path.exists(path):
            err = self.resc.error(400)
            err.msg = err.msg.format(path=path)
            raise SquirrelError(err.msg, err.code)
        if not os.path.isdir(path):
            err = self.resc.error(401)
            err.msg = err.msg.format(dir=path)
            raise SquirrelError(err.msg, err.code)
        if name:
            if name in self.repos.keys():
                err = self.resc.error(601)
                err.msg = err.msg.format(repo=name, path=self.repos[name].path)
                raise SquirrelError(err.msg, err.code)
        # Get the parent repo of the item (it many or may not exist)
        parent_repo = self.get_repo_object_of_item(path, False)
        if root:
            # Check to see if they can write to the config file
            if not self.cfg.check_access():
                err = self.resc.error(105)
                raise SquirrelError(err.msg, err.code)
            if parent_repo:
                err = self.resc.error(800)
                err.msg = err.msg.format(path=path, repo=parent_repo.name)
                raise SquirrelError(err.msg, err.code)
        else:
            if not parent_repo:
                err = self.resc.error(801)
                raise SquirrelError(err.msg, err.code)
        # Let the user know what is happening
        msg = self.resc.message("blessing")
        msg = msg.format(dir=path)
        lib.display_message(msg)
        # Create a config parser and save it in the directory
        bless_obj = configparser.ConfigParser()
        bless_obj.add_section("settings")
        bless_obj.set("settings", "datatype", data_type)
        if root:
            bless_obj.set("settings", "name", name)
            with open(os.path.join(path, ".squirrel_root"), "w") as f:
                bless_obj.write(f)
            self.cfg.add_repo(path)
            self.load_repo(path)
        else:
            with open(os.path.join(path, ".squirrel"), "w") as f:
                bless_obj.write(f)
    # --------------------------------------------------------------------------
    def bless_tree(self, root_d, repo_name):
        """
        Given a root directory, this will bless every sub-directory in the
        hierarchy (essentially creating a repo out of the hierarchy). If it runs
        out of sub-directories, it will stop. It will also not descend into
        sub-directories that have a .asset file (i.e. treating those as though
        they did not exist).
        :param root_d: The directory that will be the root of the repo. It must
               be an absolute path.
        :param repo_name: The name of the repo we are creating.
        :return: Nothing.
        """
        if not os.path.exists(root_d):
            err = self.resc.error(400)
            err.msg = err.msg.format(path=root_d)
            raise SquirrelError(err.msg, err.code)
        if not os.path.isdir(root_d):
            err = self.resc.error(401)
            err.msg = err.msg.format(dir=root_d)
            raise SquirrelError(err.msg, err.code)
        # bless the root directory as a root of the repo
        root = True
        for dir_d, dirs_n, files_n in os.walk(root_d):
            if root:
                if not os.path.exists(os.path.join(dir_d, ".squirrel_root")):
                    self.bless_dir(dir_d, True, "root", repo_name)
                else:
                    # See if the repo name is the same (error if not)
                    repo_obj = repo.Repo(self, dir_d)
                    if repo_obj.name != repo_name:
                        err = self.resc.error(602)
                        err.msg = err.msg.format(repo=repo_obj.name)
                        lib.process_error(err.msg, err.code, True, True, True)
                root = False
            else:
                if not os.path.exists(os.path.join(dir_d, ".squirrel")):
                    self.bless_dir(dir_d, False)
            # Skip any sub-dirs are assets by removing them from the list
            dels_n = list()
            for dir_n in dirs_n:
                if self.path_is_asset(os.path.join(dir_d, dir_n)):
                    dels_n.append(dir_n)
            for del_n in dels_n:
                dirs_n.remove(del_n)
    # --------------------------------------------------------------------------
    def format_version(self, ver):
        """
        Given either a string in the format of v#### (with any number of #'s) or
        as an integer, returns a formatted version in the format of: v####. If
        the integer portion is greater than 4 digits, returns a string with
        the increased number of digits.
        :param ver: The version we are looking for. May be passed as an integer
               or as a string version of an integer, or in the format "vNNNN".
               where there are any number of N's.
        :return: A string in the format of v####.
        """
        assert type(ver) == str or type(ver) == int
        # If it is a string, convert it to an integer
        if type(ver) is str:
            ver_str = ver
            if ver.startswith("v"):
                ver_str = ver[1:]
            try:
                ver = int(ver_str)
            except ValueError:
                err = self.resc.err("invalid_version_string")
                err.msg = err.msg(ver=ver)
                raise SquirrelError(err.msg, err.code)
        # Convert it back to a string (this ensures correct formatting)
        ver_str = "v" + str(ver).rjust(4, "0")
        return ver_str
    # --------------------------------------------------------------------------
    def version_exists(self, asset_d, ver):
        """
        If the version passed exists in the asset dir, return True. Return False
        otherwise.
        :param asset_d: Dir we are searching
        :param ver: The version we are looking for. May be passed as an integer
               or as a string version of an integer, or in the format "vNNNN".
        :return: True if the version exists. False otherwise.
        """
        assert os.path.exists(asset_d)
        assert os.path.isdir(asset_d)
        assert os.path.exists(os.path.join(asset_d, ".asset"))
        # Convert it back to a string (this ensures correct formatting)
        ver_str = self.format_version(ver)
        if os.path.exists(os.path.join(asset_d, ver_str)):
            if os.path.isdir(os.path.join(asset_d, ver_str)):
                if self.path_is_asset(asset_d):
                    return True
        return False
    # --------------------------------------------------------------------------
    def publish(self, repo_name, source_p, notes, metadata, tokens=None,
                set_current=True):
        """
        Publishes a file or directory.
        :param repo_name: The repository being published into.
        :param source_p: The full path to the source (file or dir)
        :param notes: An arbitrary string containing notes from the user.
        :param metadata: A list of strings in the format: "key=value" to be
               stored as metadata. If no metadata is to be passed, can also be
               given None.
        :param tokens: Tokens to define where the asset should be published.
               If tokens is None, then extract the tokens from the asset name.
               Defaults to None.
        :param set_current: If True, then set the "CURRENT" pin to point to the
               newly stored asset. Defaults to True.
        :return: Nothing.
        """
        source_p = source_p.rstrip(os.path.sep)
        # Validate the repo_name
        if not self.repo_exists(repo_name):
            if not self.repos.keys():
                err = self.resc.error(500)
                err.msg = err.msg.format(squirrel_ini=self.cfg.get_path(),
                                         root_env_var=self.cfg.repos_env_var)
            else:
                repos = ", ".join(list(self.repos.keys()))
                err = self.resc.error(600)
                err.msg = err.msg.format(repo=repo_name,
                                         repos=repos)
            raise SquirrelError(err.msg, err.code)
        # Verify that the item being published exists
        if not os.path.exists(source_p):
            err = self.resc.error(1101)
            err.msg = err.msg.format(item=source_p)
            raise SquirrelError(err.msg, err.code)
        # Get the repo object we are publishing to
        repo_obj = self.get_repo_object(repo_name)
        # If the tokens are None, then extract the tokens from the name.
        if not tokens:
            asset_n = os.path.split(source_p)[1]
            tokens = repo_obj.extract_metadata_from_name(asset_n)[1]
            tokens = "/".join(tokens)
        repo_obj.publish(source_p, notes, metadata, tokens, set_current)
    # --------------------------------------------------------------------------
    def set_pin(self, repo_name, token, asset_n, version_n, pin):
        """
        Sets a pin on a specific version of an asset, given the repo, the name
        of the asset, the token, and the version name.
        :param repo_name: The name of the repo containing the asset.
        :param token: The token where the asset lives.
        :param asset_n: The name of the asset.
        :param version_n: The name of the version.
        :param pin: The name of the pin.
        :return: Nothing.
        """
        # Verify the repo_name name
        if repo_name not in self.repos.keys():
            err = self.resc.error(204)
            err.msg = err.msg.format(repo=repo_name)
            raise SquirrelError
        repo_obj = self.repos[repo_name]
        repo_obj.set_pin(token, asset_n, version_n, pin)
    # --------------------------------------------------------------------------
    def set_pin_by_path(self, repo_name, version_p, pin_name):
        """
        Sets a pin on a specific version of an asset, given the path to that
        version.
        :param repo_name: The name of the repository.
        :param version_p: The path to the version.
        :param pin_name: The name of the pin.
        :return: Nothing.
        """
        repo_obj = self.get_repo_object(repo_name)
        token = repo_obj.get_token_from_path(version_p)
        asset_n = repo_obj.get_asset_name_of_item(version_p)
        version_n = repo_obj.get_version_name_of_item(version_p)
        self.set_pin(repo_name, token, asset_n, version_n, pin_name)
    # --------------------------------------------------------------------------
    def delete_pin(self, path):
        """
        Deletes a pin given by path.
        :param path: The path to the pin.
        :return: Nothing.
        """
        # Get the repo from the path
        repo_name = self.get_repo_name_of_item(path, managed_only=False)
        repo_obj = self.get_repo_object(repo_name)
        token = repo_obj.get_token_from_path(path)
        asset_n = repo_obj.get_asset_name_of_item(path)
        version_n = repo_obj.get_version_name_of_item(path)
        pin = os.path.split(path.rstrip(os.path.sep))[1]
        repo_obj.remove_pin(token, asset_n, pin)
    # --------------------------------------------------------------------------
    def remove_broken_repos(self):
        """
        Goes through all of the repos listed in the config file, and removes any
        that do not exist as repos on disk.
        :return: A string of the repos removed.
        """
        valid_repos = list()
        for repo_name in self.repos.keys():
            valid_repos.append(self.repos[repo_name].path)
        removed_repos = list()
        existing_repos = self.cfg.get_section("repos")
        for existing_repo in existing_repos:
            if existing_repo not in valid_repos:
                self.cfg.remove_item("repos", existing_repo)
                removed_repos.append(existing_repo)
        self.cfg.write_config()
        if removed_repos:
            output = self.resc.message("removed_repos")
            output += "\n".join(removed_repos)
        else:
            output = self.resc.message("no_broken_repos")
        return output





[error_codes]
100=There are no repos currently added to the system. They may already exist on disk, but the system is not aware of them. Use schema-config to add these repos, or use schema-bless to create new repos.
101=The repo you are trying to make default ({{COLOR_RED}}repo{{COLOR_NONE}}) has not yet been added to the system. It might exist on disk, but it would need to be added using schema-config, or use schema-bless to create the new repo first.
200=The path {root_path} is not actually a repo root path. It is missing a hidden file called .repo_root.
400=The path ({path}) does not exist.
401=The path ({path}) is not a directory.
601=A repository with the name {repo} already exists (currently located at: {path}).
602=You cannot create a new repo inside of an already existing repo. The repo you are trying to create ({{COLOR_RED}}{path}{{COLOR_NONE}}) is inside of an existing repo ({{COLOR_RED}}{repo}{{COLOR_NONE}}).
603=A non-root directory may only be added to an existing repo. The dir you are trying to bless ({{COLOR_RED}}path{{COLOR_NONE}}) is not inside of a repo.

[error_codes_old]
100=Unable to locate the application config file {config_file}.
101=Application config file {config_file} is actually a directory.
102=The config file is corrupted. It is missing the option: {missing_option}
103=Unable to locate the application config directory {config_dir}. Check the (optional) SQUIRREL_CONFIG env variable? Otherwise, it should be in a directory called 'resources' that is in the same directory where this app lives.
104=There are no repos on the system.
105=You do not have permissions to perform this operation. Perhaps try again as the super-user?
106=The language resources file ({path}) is corrupted. It is missing the section: {section}.
107=The language resources file ({path}) is corrupted. The section {section} is missing the setting: {setting}.
108=You may not use both the --run-locally and --run-as-client flags at the same time.
200=The path {root_path} is not actually a repo root path. It is missing a hidden file called .repo_root.
201=The path {root_path} is not actually a squirrel root path. The .squirrel_root file must contain key/value pair (name=<value>) in the [settings] section that defines the name of the repo.
202=The repo path {repo_path} is not a valid repo, is missing, or is corrupt in some way. Skipping this repository.
203=The repo path {repo_path} is not a valid repo, is missing, or is corrupt in some way.
204=The repo named {repo} does not exist on the system. If it exists on disk, perhaps it needs to be added first.
205=The .squirrel_root file is malformed ({path})
300=The path ({path}) is not within any repo.
400=The path ({path}) does not exist.
401=The path ({path}) is not a directory.
500={{COLOR_RED}}You have not set up any repos yet.{{COLOR_NONE}}\n\nPerhaps you have not set up the squirrel.ini file to point to the repos? (This file is currently being read from {squirrel_ini}).\n\nOptionally, you could also set up the {root_env_var} env variable to point to the different repos. Regardless of method, any repos you define_options will need to exist on disk and have "blessed" directories in them. See the documentation for more details.
600=The repository ({repo}) does not exist. Please select from the following repos: {repos}
601=A repository with the name {repo} already exists (currently located at: {path}).
602=You are trying to bless a repo that already has been blessed with a different name (currently this directory has been blessed as a repo named: {repo}).
700=The token {token} does not exist in the current repo {repo} (A token is a relative path from the root of the repo).
701=The asset {name} does not exist in the repo {repo}.
702=The version {version} does not exist in the asset {name} in the repo {repo}.
800=Cannot create a repo inside of another repo. The path passed ({path}) is inside of the repo: {repo}.
801=You cannot create a Squirrel repository structure directory that isn't inside of a repo. See the documentation for more information.
900=The asset name has multiple underscores adjacent to each other and not separated by other text (i.e. something like this: __). This is not allowed.
901=The asset name is missing a variant. The variant must be no more than two character long, and only consist of upper case letters (for a grand total of 702 possible variants).
902=The asset name is missing the repository (it must begin with one of the following: {repo_list})
903=The asset name begins with a valid repository, but that is not the repository that was passed into the system. The repository being used is: {actual_repo}, but the repository in the name is {name_repo}.
904=The asset name is missing some of its tokens. At the very minimum it should start with one of the following: {possible_next}
905=The asset name is missing some of its tokens. At the very minimum, after "{up_to_last_item}" there should be one of the following: {possible_next}
906=The asset name is missing a description. It should have a descriptive item in the name in after "{up_to_last_item}"
950=Metadata being passed by the user contains two or more items with the same key. ({key})
1000=Wrong number of arguments.
1001=You must supply a name for the repository. Use the -l/--list-repos option to list available repos. Use the --set-default-repo option to set a default repo (after which you will not be required to supply a repo on the command line).
1002=You must supply a name for the repository. Use the -l/--list-repos option to list available repos.
1100=Your system is set up to not require the asset name to contain metadata. Because of this you need to provide the metadata about the asset. This data is missing.
1101=The item being published ({item}) does not exist on disk. Is it a full path to the item?
1102=Unable to reserve a slot for the asset version {asset_name} after {num_attempts} attempts.
1103=Asset has too many revisions. The max is 9999.
1104=The pin you are trying to delete ({pin}) is actually a file or directory. It is not a symlink. Out of an abundance of caution, this item will NOT be deleted.

[messages]
blessing=Blessing: {dir}
removed_repos=Removed the following repos from the config:
no_broken_repos=No broken or missing repos.

[description]
This is a an arbitrarily long list of text.
SQUIRREL_CONFIG is an optional var where you may define_options the path to a dir
where the .squirrel.ini config file lives. In this manner you may define_options
different behaviors for different environments.

[publish]
short_flag = -p
long_flag = --publish
action = store
default =
type = str
metavar = item-path
nargs = 1
description = Publish the passed file or directory to the repository given by the -r/--repo-name flag (if no such flag is provided, publish to the default repository).

[notes]
short_flag = -n
long_flag = --notes
action = store
default =
type = str
metavar = notes
nargs = 1
description = When publishing, this is an optional set of notes to include with the publish.

[metadata]
short_flag = -m
long_flag = --metadata
action = append
default =
type = list
metavar = metadata
nargs = 1
description = An unlimited number of key=value pairs of arbitrary metadata to add to the publish. This would be given in the format: -m key1=value1 -m key2=value2 ... -m keyN=valueN. This data will be stored with the metadata for the version being publsihed.

[keywords]
short_flag = -k
long_flag = --keywords
action = append
default =
type = list
metavar = keywords
nargs = 1
description = An unlimited number of keywords to add to the publish. This would be given in the format: -k keyword1 -k keyword2 ... -k keywordN. This data will be stored with the metadata for the version being publsihed.

[repo_name]
short_flag = -r
long_flag = --repo-name
action = store
default =
type = str
metavar = name
nargs = 1
description = Which repo to use. If omitted, then the default repo will be used.

[tokens]
short_flag = -t
long_flag = --tokens
action = store
default = /
type = str
metavar = tokens
nargs = 1
description = Tokens that describe where inside a repository an action is to take place. Tokens are relative paths from the root of the repository, and are always given as unix-style paths (even on windows systems). An example of a token would be: /asset/bldg/commercial/ (note, the trailing slash is optional, but the leading slash is required). If the repository path were, for example, /show/studio/squirrel/, then this token would refer to the directory /show/studio/squirrel/asset/bldg/commercial/. Tokens are required for certain operations. See the individual options to see which require a token.

[names_only]
short_flag = -N
long_flag = --names-only
action = store_true
default = False
type = bool
metavar =
nargs =
description = If used, this flag will limit any outputs that normally display full paths to only display names.

[list_repos]
short_flag = -l
long_flag = --list-repos
action = store_true
default = False
type = bool
metavar =
nargs = 0
description = Display a list of all the repos currently on this system. If the names only flag is set (-N or --names-only) then only the names will be returned (instead of the full paths).

[list_assets]
short_flag = -L
long_flag = --list-assets
action = store_true
default = False
type = bool
metavar =
nargs = 0
description = Returns a list of the assets in the repo given by the -r/--repo-name flag (or if no repo is passed with this flag, then in the default repo). If a token is passed using the -t/--token flag (in the format /relative/path/to/item), then only the assets that are in this sub-branch of the repository will be listed. If the names only flag is set (-N or --names-only) then only the names will be returned (instead of the full paths).

[list_assets_with_keywords]
short_flag = -K
long_flag = --list-assets-with-keywords
action = store_true
default = False
type = bool
metavar =
nargs = 0
description = Returns a list of assets that have any of the keywords given by the -k/--keyword flag. Only the repo given by the -r/--repo-name flag will be searched (or if no repo is passed with this flag, then in the default repo). If a token is passed using the -t/--token flag (in the format /relative/path/to/item), then only the assets that are in this sub-branch of the repository will be searched. If the names only flag is set (-N or --names-only) then only the names will be returned (instead of the full paths).

[pin]
short_flag = -i
long_flag = --pin
action = store
default =
type = str
metavar = path-to-version, pin-name
nargs = 2
description = Sets a pin (symlink inside an asset that points to a specific version of that asset). Requires a path to the version you want to pin, and the name of the pin.

[delete_pin]
short_flag =
long_flag = --delete-pin
action = store
default =
type = str
metavar = path-to-pin
nargs = 1
description = Deletes a pin (symlink inside an asset that points to a specific version of that asset). Requires the path to the pin you want to delete.

[item_is_managed]
short_flag = -M
long_flag = --item-is-managed
action = store
default =
type = str
metavar = item-path
nargs = 1
description = Returns whether the given file or directory is managed by any repo. Expects a full path to the item.

[item_is_managed_by_repo]
short_flag = -P
long_flag = --item-is-managed-by-repo
action = store
default =
type = str
metavar = item-path
nargs = 1
description = Returns whether the given file given in this argument is managed by the repo given using the -r/--repo-name argument (if no such arg is used, then the default repo will be checked.)

[asset_exists]
short_flag = -E
long_flag = --asset-exists
action = store
default =
type = str
metavar = asset-name
nargs = 1
description = Returns whether or not the passed asset name exists in the repo given by the -r/--repo-name flag (if no such flag is given, then the default repo will be used.) If the -t/--tokens flag is given, then the search will be limited to just that branch of the repository.

[get_item_version]
short_flag = -V
long_flag = --get-item-version
action = store
default =
type = str
metavar = item-path
nargs = 1
description = Returns the version of a passed file or directory. Expects a path to a file or directory. If the -N/--names-only flag is set then only the name will be returned (instead of the full path).

[get_item_asset]
short_flag = -A
long_flag = --get-item-asset
action = store
default =
type = str
metavar = item-path
nargs = 1
description = Returns the asset containing the passed file or directory. Expects a path to a file or directory. If the -N/--names-only flag is set then only the name will be returned (instead of the full path).

[get_item_repo]
short_flag = -R
long_flag = --get-item-repo
action = store
default =
type = str
metavar = item-path
nargs = 1
description = Returns the repo containing the passed file or directory. Expects a path to a file or directory. If the -N/--names-only flag is set then only the name will be returned (instead of the full path).

[get_item_token]
short_flag = -T
long_flag = --get-item-token
action = store
default =
type = str
metavar = item-path
nargs = 1
description = Returns the token for the passed file or directory. Expects a path to a file or directory. The token is a relative path from the root of the repository to the end of the repository structure (i.e. the last directory before the actual assets). Tokens are always in the format of a unix-style path (even on Windows).

[bless_dir]
short_flag =
long_flag = --bless-dir
action = store
default =
type = str
metavar = directory-path
nargs = 1
description = Blesses the passed directory as a Squirrel directory. Each dir in a repo needs to be "blessed" in order for that dir to show up as an organizational element. If a dir is not "bessed", then it is assumed to be an actual asset stored in the repo. Note that this command can only be used to bless a directory inside an existing repo. Use --bless-root or --bless-tree to set up a new repo. Normally, for most 'blessing' operations, it is easier to use '--bless-tree'. See the documentation for more info.

[bless_root]
short_flag =
long_flag = --bless-root
action = store
default =
type = str
metavar = directory-path
nargs = 1
description = Blesses the passed directory as a new repo. Note that this command can only be used to set up a new repo, and that it will not set up any structure inside the repo. Use --bless-dir or --bless-tree to set up the structure inside a repo. Use the -r/--repo-name argument to provide the name of the repo (it will not be derived from the directory name). The use of this -r option is required. Normally, for most 'blessing' operations, it is easier to use '--bless-tree'. See the documentation for more info.

[bless_tree]
short_flag =
long_flag = --bless-tree
action = store
default =
type = str
metavar = directory-path
nargs = 1
description = Blesses the passed directory as a new repo, and traverses the sub-directories and blesses them as the repo structure. This command is smart enough to only bless directories that have not already been 'blessed'. Additionally, it will not descend into existing assets, so it is safe to use on existing repos (in case, for example, you have added new structure to an existing repo and need that new structure to be registered as part of the repo). Use the -r/--repo-name argument to provide the name of the repo (it will not be derived from the directory name). The use of this -r option is required. See the documentation for more info.

[add_repo]
short_flag =
long_flag = --add-repo
action = store
default =
type = str
metavar = repo-path
nargs = 1
description = Add an existing repo to the system. Use this if you have a repo already blessed (via bless-tree or bless-root) but that for some reason is not in the list of currently managed repos. You may have to run this command as a super-user depending on the configuration of your system.

[set_default_repo]
short_flag =
long_flag = --set-default-repo
action = store
default =
type = str
metavar = repo-name
nargs = 1
description = Sets the default repo for the system. Use this to change or set the repo that will be used if no repo name is explicitly given for any command. You may have to run this command as a super-user depending on the configuration of your system.

[remove_broken_repos]
short_flag =
long_flag = --remove-broken-repos
action = store_true
default = False
type = bool
metavar =
nargs = 0
description = If there are missing or broken repos in the config file, this command will remove them. Note: this does NOT delete any data on disk, and if you run this in error, it is easy to re-add these repos to the system using the --add-repo command. Also note that this does not adjust the repos environment variable (defined in squirrel.ini)

[delete_version]
short_flag =
long_flag = --delete-version
action = store
default =
type = str
metavar = version-path
nargs = 1
description = Deletes a version (given as a path). This will also remove any unused de-duplication data.

[consolidate_versions]
short_flag =
long_flag = --consolidate-versions
action = store
default =
type = str
metavar = asset-path
nargs = 1
description = Deletes all but the latest version in an asset (given as a path). This will also remove any unused de-duplication data.

[delete_asset]
short_flag =
long_flag = --delete-asset
action = store
default =
type = str
metavar = asset-path
nargs = 1
description = Deletes all data associated with an asset (given as a path). This will also remove any unused de-duplication data.

[server]
short_flag = -S
long_flag = --server
action = store_true
default = False
type = bool
metavar =
nargs = 0
description = Run as a server. The system will listen for requests on the port given by --port.

[port]
short_flag =
long_flag = --port
action = store
default = 87233
type = int
metavar = port
nargs = 1
description = When running as either a client or a server, use this port number. If this flag is not used, the default port is 87233.

[run_locally]
short_flag =
long_flag = --run-locally
action = store_true
default = False
type = bool
metavar =
nargs = 0
description = Run locally (instead of as a client contacting a server). The system is designed to normally run in a client-server mode. Running locally can potentially lead to some (extremely rare) race conditions. Running locally also has some performance implications when accessing large repos with thousands of assets. Locking assets is also only partially supported when running locally (assets themselves are locked, but the repo directory structure is not). That said, running locally is much easier to manage than a full client-server system and perfectly acceptable for a solo artist with a single system, or a small studio but with multiple systems. If you want the system to default to running locally, you may also set the run_local setting in the config file to True. If you use this flag and the --run-as-client flag an error will be raised.

[run_as_client]
short_flag =
long_flag = --run-as-client
action = store_true
default = False
type = bool
metavar =
nargs = 0
description = If run_locally is set to true in the config file, this flag will override that and run the app as a client in a client-server mode. This really should only be used when testing the system. Normally, the system should simply do what the config file is set up to do. If you use this and the --run-locally flag an error will be raised.

[host]
short_flag = -H
long_flag = --host
action = store
default =
type = str
metavar = server-ip
nargs = 1
description = If running as a client in a client-server configuration, this may be used to define the host ip address. Normally this host ip would be defined in either the config file, or in an environmental variable defined in the config file. If this is not the case, or if you wish to temporarily override these settings, use this flag to specify the server's IP address. The loop-back address of 127.0.0.0 can be used if the server is running on the same system as the client.

[language]
short_flag =
long_flag = --language
action = store
default = english
type = str
metavar = language
nargs = 1
description = Use this language. If none given, or if the language is not installed, defaults to 'english'.
'''