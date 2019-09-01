import ConfigParser
import inspect
import os
import tempfile

from bvzlib import config
from bvzlib import filesystem
from bvzlib import resources

from squirrel.shared import envvars
from squirrel.shared.squirrelerror import SquirrelError

from squirrel.interface import storeinterface

from squirrel.schema import repo


# ==============================================================================
class RepoManager(object):
    """
    A class to manage repos on disk.
    """

    # --------------------------------------------------------------------------
    def __init__(self,
                 language="english"):
        """
        Initialize the manager object responsible for managing different repos.
        Individual repos are managed by the repo class.

        :param language: The language used for communication with the end user.
               Defaults to "english".
        """

        module_d = os.path.split(inspect.stack()[0][1])[0]
        resources_d = os.path.join(module_d, "..", "..", "..", "resources")
        config_d = os.path.join(module_d, "..", "..", "..", "config")
        self.resc = resources.Resources(resources_d, "lib_schema", language)

        self.config_p = os.path.join(config_d, "schema.config")
        self.config_p = os.path.abspath(self.config_p)
        self.config_obj = config.Config(self.config_p,
                                        envvars.SQUIRREL_SCHEMA_CONFIG_PATH)

        self.store_interface = storeinterface.StoreInterface(language)

        self.validate_config()

        self.language = language

        self.repos = dict()

        self.load_repos_from_config(silence=True)

        self.default_repo = self.get_default_repo()

    # --------------------------------------------------------------------------
    def validate_config(self):
        """
        Makes sure the config file is valid. Raises a squirrel error if not.

        :return: Nothing.
        """
        sections = dict()
        sections["repos"] = [None]
        sections["settings"] = ["warn_on_load_error",
                                "fail_on_load_error",
                                "default_repo",
                                "default_gather_loc"]

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
    def load_repo(self,
                  repo_p):
        """
        Loads a single repo.

        :param repo_p: The path to the repo to load. Assumes that the path
               exists and is a valid repo. Raises an error if not.

        :return: Nothing.
        """

        repo_obj = repo.Repo(repo_p, self.language)
        self.repos[repo_obj.name] = repo_obj

    # --------------------------------------------------------------------------
    def unload_repo(self,
                    repo_n):
        """
        Unloads a single repo.

        :param repo_n: The name of the repo to unload.

        :return: Nothing.
        """

        if repo_n in self.repos.keys():
            del(self.repos[repo_n])

    # --------------------------------------------------------------------------
    def load_repos_from_config(self,
                               silence=False):
        """
        Loads all of the repos listed in the config file. Kicks up an error if
        any are missing or corrupt AND warn_on_load_error or fail_on_load_error
        is set to True in the config file.

        :param silence: If True, no warnings or errors will be displayed.
               Defaults to False.

        :return: Nothing.
        """

        try:
            warn = self.config_obj.getboolean("settings", "warn_on_load_error")
        except (ConfigParser.NoSectionError,
                ConfigParser.NoOptionError,
                ValueError):
            warn = True
        try:
            fail = self.config_obj.getboolean("settings", "fail_on_load_error")
        except (ConfigParser.NoSectionError,
                ConfigParser.NoOptionError,
                ValueError):
            fail = False

        try:
            repos = self.config_obj.items("repos")
        except ConfigParser.NoSectionError:
            return

        for repo_name, repo_path in repos:
            try:
                self.load_repo(repo_p=repo_path)
            except SquirrelError as e:
                if not silence:
                    if fail:
                        raise SquirrelError(str(e), e.code)
                    if warn:
                        e = "Warning: " + str(e) + " Cannot load this repo."
                        print(str(e))

    # --------------------------------------------------------------------------
    def repo_name_is_valid(self,
                           repo_n):
        """
        Given a repo name, does a very minimal check to see if the repo is
        valid. Basically checks to see if the name is in the list of loaded
        repos. Since only valid repos will be loaded, if the name is not there,
        it isn't a valid repo.

        :param repo_n: The name of the repo we are testing.

        :return: True if the repo is valid. False otherwise.
        """
        return repo_n in self.repos.keys()

    # --------------------------------------------------------------------------
    @staticmethod
    def repo_path_is_valid(repo_p):
        """
        Given a repo path, does a very minimal check to see if the repo is
        valid. Basically checks to see if the path is a directory and whether
        there is a file in this directory named .repo_root.

        :param repo_p: The path to the repo we are testing.

        :return: True if the repo is valid. False otherwise.
        """
        if not os.path.exists(repo_p):
            return False

        if not os.path.isdir(repo_p):
            return False

        if not os.path.exists(os.path.join(repo_p, ".repo_root")):
            return False

        return True

    # --------------------------------------------------------------------------
    def add_repo_to_config(self,
                           repo_p):
        """
        Adds the repo given by the path repo_p to the config file.

        :param repo_p: The path to the repository. Must be a blessed root path.

        :return: Nothing.
        """

        assert os.path.isabs(repo_p)

        # The following may error out, let the calling function deal with it.
        repo_obj = repo.Repo(repo_p, self.language)

        if not self.config_obj.has_section("repos"):
            self.config_obj.add_section("repos")

        if self.config_obj.has_option("repos", repo_obj.name):
            self.config_obj.remove_option("repos", repo_obj.name)

        self.config_obj.set("repos", repo_obj.name, repo_p)

        self.config_obj.save()

    # --------------------------------------------------------------------------
    def add_repo(self,
                 repo_p):
        """
        Adds the repo to the current object as well as to the config file.

        :param repo_p: The path to the repository. Must be a blessed root path.

        :return: Nothing.
        """

        self.load_repo(repo_p)
        self.add_repo_to_config(repo_p)

    # --------------------------------------------------------------------------
    def remove_repo_from_config(self,
                                repo_n):
        """
        Removes a repo from the config file.

        :param repo_n: The name of the repo. This is not necessarily the name of
               directory that is the repo root. The name is stored within the
               .repo_root_d file.

        :return: Nothing.
        """

        if not self.config_obj.has_section("repos"):
            self.config_obj.add_section("repos")

        if self.config_obj.has_option("repos", repo_n):
            self.config_obj.remove_option("repos", repo_n)

        self.config_obj.save()

    # --------------------------------------------------------------------------
    def remove_repo(self,
                    repo_n):
        """
        Removes the repo to the current object as well as from the config file.

        :param repo_n: The name of the repository.

        :return: Nothing.
        """

        self.unload_repo(repo_n)
        self.remove_repo_from_config(repo_n)

    # --------------------------------------------------------------------------
    def list_repos(self):
        """
        Returns a list containing all of the repo names.

        :return: A list of repo names.
        """
        return self.repos.keys()

    # --------------------------------------------------------------------------
    def list_broken_repos(self):
        """
        Looks through the config file and returns any repos that are broken.
        "Broken" in this case means that the name in the config does not match
        the name in the .repo_root file OR that the path given does not point to
        a root directory of a repository (either it does not exist or the
        required .repo_root file does not exist).

        :return: A list of tuples containing the repo name and path of repos
                 that are broken.
        """

        try:
            repos = self.config_obj.items("repos")
        except ConfigParser.NoSectionError:
            return

        broken_repos = list()
        for repo_name, repo_path in repos:
            if not self.repo_name_is_valid(repo_name):
                broken_repos.append((repo_name, repo_path))

        return broken_repos

    # --------------------------------------------------------------------------
    def get_default_repo(self):
        """
        Gets the default repository. It will first attempt to get it from the
        user's environment from a variable named: SQUIRREL_DEFAULT_REPO. If that
        variable does not exist, it will attempt to extract it from the config
        file.

        :return: The name of the default repo. If there is no default, return
                 None.
        """

        try:
            default_repo = os.environ[envvars.SQUIRREL_DEFAULT_REPO]
        except KeyError:
            if self.config_obj.has_option("settings", "default_repo"):
                default_repo = self.config_obj.get("settings", "default_repo")
            else:
                return None

        if not self.repo_name_is_valid(default_repo):
            return None

        return default_repo

    # --------------------------------------------------------------------------
    def set_default_repo(self,
                         repo_n):
        """
        Sets the default repository.

        :param repo_n: The name of the default repo. This repo must exist in the
               list of current repos.

        :return:
        """

        # The target repo must exist in the list of repos
        if not self.config_obj.has_section("repos"):
            err = self.resc.error(100)
            err.msg = err.msg.format()
            raise SquirrelError(err.msg, err.code)

        if not self.config_obj.has_option("repos", repo_n):
            err = self.resc.error(101)
            err.msg = err.msg.format(repo_name=repo_n)
            raise SquirrelError(err.msg, err.code)

        # The target repo must exist on disk as a real repo (if it does not, the
        # following will raise an error)
        repo.Repo(self.config_obj.get("repos", repo_n))

        # Store the default
        if not self.config_obj.has_section("settings"):
            self.config_obj.add_section("settings")

        if self.config_obj.has_option("settings", "default_repo"):
            self.config_obj.remove_option("settings", "default_repo")

        self.config_obj.set("settings", "default_repo", repo_n)

        self.config_obj.save()

    # --------------------------------------------------------------------------
    def get_repo_root(self,
                      repo_n):
        """
        Given a repo name, return the path to the repo root.

        :param repo_n: The name of the repo.

        :return: A path to the root of the repo. Raises a SquirrelError if the
                 name cannot resolve to a real repo.
        """

        try:
            return self.repos[repo_n].repo_root_d
        except KeyError:
            err = self.resc.error(102)
            err.msg = err.msg.format(repo_name=repo_n)
            raise SquirrelError(err.msg, 102)

    # --------------------------------------------------------------------------
    def bless_dir(self,
                  path_d,
                  root=False,
                  repo_n=None):
        """
        "Blesses" a particular path to include it as part of a repository. There
        are two types of blessed directories: Root and Normal. A Root directory
        can only live at the top of a hierarchy. A Normal directory can only
        live inside of another Normal directory or a Root directory. If the
        dirtype is set to "Root" then a name of the repository must also be
        included. Note: if more than one repository with the same name exists in
        the system, it would be undefined where assets will be placed, so
        duplicate repo names are not permitted.

        :param path_d: The path to where the blessed dir is. This dir must exist
               or an error will be raised.
        :param root: If True, then this is a root dir. Otherwise it is a normal
               structure dir.
        :param repo_n: If the dirtype is "Root", then a name of the repo must
               also be included.

        :return: Nothing.
        """
        if root:
            assert repo_n is not None
            if os.path.exists(os.path.join(path_d, ".repo_root")):
                semaphore_obj = ConfigParser.ConfigParser()
                semaphore_obj.read(os.path.join(path_d, ".repo_root"))
                existing_name = semaphore_obj.get("settings", "name", repo_n)
                if existing_name != repo_n:
                    self.remove_repo_from_config(existing_name)

        if not os.path.exists(path_d):
            err = self.resc.error(400)
            err.msg = err.msg.format(path=path_d)
            raise SquirrelError(err.msg, err.code)

        if not os.path.isdir(path_d):
            err = self.resc.error(401)
            err.msg = err.msg.format(dir=path_d)
            raise SquirrelError(err.msg, err.code)

        if repo_n:
            if repo_n in self.repos.keys():
                existing_real_p = os.path.realpath(self.repos[repo_n].repo_root_d)
                new_real_p = os.path.realpath(path_d)
                if existing_real_p != new_real_p:
                    err = self.resc.error(601)
                    err.msg = err.msg.format(repo=repo_n,
                                             path=self.repos[repo_n].repo_root_d)
                    raise SquirrelError(err.msg, err.code)

        # Create a config parser and save it in the directory, removing any
        # existing files if needed
        bless_obj = ConfigParser.ConfigParser()

        if root:

            # Root dirs can not be within an existing repo (no ancestor may be
            # a repo root directory)
            ancestor_d = filesystem.ancestor_contains_file(path_d,
                                                           [".repo_root"])
            if ancestor_d:
                err = self.resc.error(602)
                err.msg = err.msg.format(path=path_d, repo=ancestor_d)
                raise SquirrelError(err.msg, err.code)

            bless_obj.add_section("settings")
            bless_obj.set("settings", "name", repo_n)

            semaphore_p = os.path.join(path_d, ".repo_root")
            if os.path.exists(semaphore_p):
                os.remove(semaphore_p)

            with open(os.path.join(path_d, ".repo_root"), "w") as f:
                bless_obj.write(f)

            # Add this repo to the list of repos
            self.add_repo(path_d)

        else:

            # Non-root dirs can only be within an existing repo (immediate
            # parent needs to be a repo root or repo structure file)
            if not filesystem.ancestor_contains_file(path_d,
                                                     [".repo", ".repo_root"],
                                                     1):
                err = self.resc.error(603)
                err.msg = err.msg.format(path=path_d)
                raise SquirrelError(err.msg, err.code)

            semaphore_p = os.path.join(path_d, ".repo")
            if os.path.exists(semaphore_p):
                os.remove(semaphore_p)

            with open(os.path.join(path_d, ".repo"), "w") as f:
                bless_obj.write(f)

    # --------------------------------------------------------------------------
    def bless_tree(self,
                   root_d,
                   repo_n):
        """
        Given a root directory, this will bless every sub-directory in the
        hierarchy (essentially creating a repo out of the hierarchy). If it runs
        out of sub-directories, it will stop. It will also not descend into
        sub-directories that are already assets.

        :param root_d: The directory that will be the root of the repo. It must
               be an absolute path.
        :param repo_n: The name of the repo we are creating.

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

        root = True
        for dir_d, dirs_n, files_n in os.walk(root_d):

            if root:
                self.bless_dir(dir_d, True, repo_n)
                root = False
            else:
                self.bless_dir(dir_d, False)

            # Skip any sub-dirs are assets by removing them from the list of
            # sub-dirs to descend into
            del_dirs_n = list()
            for dir_n in dirs_n:
                test_p = os.path.join(dir_d, dir_n)
                if self.store_interface.path_is_asset_root(test_p):
                    del_dirs_n.append(dir_n)
            for del_n in del_dirs_n:
                dirs_n.remove(del_n)

    # --------------------------------------------------------------------------
    def file_is_within_repo(self,
                            file_p,
                            repo_names,
                            check_all_repos):
        """
        Given the path to a file, check either the given repo or all repos (if
        check_all_repos is True) to see if that file is within the repo.

        :param file_p: The path to the file being tested
        :param repo_names: A list of the names of the repos to check. This value
               is ignored if check_all_repos is True.
        :param check_all_repos: If True, then every repo will be checked to see
               if the file is within one of them.

        :return: True if the file is within the repo structure. False otherwise.
        """

        if not check_all_repos:
            assert repo_names is not None
            assert type(repo_names) is list

        if check_all_repos:
            repo_names = self.repos.keys()
        else:
            for repo_name in repo_names:
                if repo_names and not self.repo_name_is_valid(repo_name):
                    err = self.resc.error(102)
                    err.msg = err.msg.format(repo_name=repo_name)
                    raise SquirrelError(err.msg, err.code)

        for repo_name in repo_names:
            repo_obj = self.repos[repo_name]
            if repo_obj.path_is_within_repo(file_p):
                return True

        return False

    # --------------------------------------------------------------------------
    def get_gather_loc(self):
        """
        Returns the path where files should be gathered to.

        :return: A path where files should be gathered to.
        """

        try:
            gather_loc = envvars.SQUIRREL_DEFAULT_GATHER_LOC
            return gather_loc
        except KeyError:
            pass

        try:
            gather_loc = self.config_obj.get("settings", "default_gather_loc")
            return gather_loc
        except (ConfigParser.NoSectionError,
                ConfigParser.NoOptionError,
                ValueError):
            pass

        return tempfile.gettempdir()

    # --------------------------------------------------------------------------
    def get_repo(self,
                 repo_n=None):
        """
        Returns the repo object associated with the repo_name. Can accept a
        repo_name of None which means return the default repo. Also manages
        raising an error if no repo matches the name and/or no default repo
        is set.

        :param repo_n: The name of the repo. If None, the default repo will
               be returned. If there is no repo of this name, raises an error.
               If None, and there is no default repo, raises an error. Defaults
               to None.

        :return: A repo object corresponding to the name given.
        """

        if not repo_n:

            repo_n = self.get_default_repo()

            if not repo_n:
                err = self.resc.error(103)
                err.msg = err.msg.format()
                raise SquirrelError(err.msg, err.code)

        if not self.repo_name_is_valid(repo_n):
            err = self.resc.error(102)
            err.msg = err.msg.format(repo_name=repo_n)
            raise SquirrelError(err.msg, err.code)

        return self.repos[repo_n]

    # --------------------------------------------------------------------------
    def get_publish_loc(self,
                        token,
                        repo_n=None):
        """
        Returns the path where files should be published to.

        :return: A path where files should be published to.
        """

        repo_obj = self.get_repo(repo_n)

        return repo_obj.get_publish_loc(token)

    # --------------------------------------------------------------------------
    def token_is_valid(self,
                       token,
                       repo_n=None):
        """
        Returns whether the given token is valid for the given repo.

        :param token: The token we are evaluating.
        :param repo_n: The name of the repo we are validating against. If
               None, then the default repo will be used.

        :return: A path where files should be published to.
        """

        repo_obj = self.get_repo(repo_n)

        return repo_obj.token_is_valid(token)

    # --------------------------------------------------------------------------
    def get_next_tokens(self,
                        token,
                        repo_n=None):
        """
        Given a token, returns what the next possible tokens will be.

        :param token: The token we are evaluating.
        :param repo_n: The name of the repo we are validating against. If
               None, then the default repo will be used.

        :return: A list of the next possible tokens.
        """

        repo_obj = self.get_repo(repo_n)

        return repo_obj.get_next_tokens(token)

    # --------------------------------------------------------------------------
    def token_is_leaf(self,
                      token,
                      repo_n=None):
        """
        Given a token, returns whether it evaluates all the way down to the
        leaf level.

        :param token: The token we are evaluating.
        :param repo_n: The name of the repo we are validating against. If
               None, then the default repo will be used.

        :return: True if the given token is a leaf, False otherwise.
        """

        repo_obj = self.get_repo(repo_n)

        return repo_obj.token_is_leaf(token)
