import ConfigParser
import inspect
import os

from bvzlib import filesystem
from bvzlib import resources

from shared.squirrelerror import SquirrelError


# ==============================================================================
class Repo(object):
    """
    Class managing the schema of a single repository.

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
                only describe the structure of the repo itself. They may contain
                a leading slash, or omit it. Tokens with or without leading
                slashes are functionally identical. They may also end with a
                trailing slash or omit it. Again, tokens with or without
                trailing slashes are functionally identical.
    Structure:  Repositories are defined by a directory structure consisting of
                "blessed" directories (and no files). A directory is "blessed"
                if it contains a .repo or .repo_root file in it. This structure
                defines the hierarchy of the repo, with each sub-directory
                making up the "branches" of the repo. The very last
                sub-directory of each branch is considered a "leaf" structure.
                No files may live at any level of the structure. Only "blessed"
                directories may live within the repo structure. Likewise, no
                non-blessed directories may live at any level of the structure
                except within the final, leaf level. At this leaf level are the
                actual asset directories. The contents of the asset directories
                must be managed by a separate process (the store module for
                example).
    Managed:    A "managed" file or directory is any file or directory that is
                below the structure level of the repo (i.e. within an asset that
                lives at the end of a repo structure). Managed files and dirs
                are essentially the assets being stored by the repo.
    Assets:     Assets are directories that contain files. Assets are defined to
                only exist as special directories in the leaf structure dirs.
                Asset structure is defined outside of this repo and must be
                managed by another application (the store module for example).


    Some naming conventions:
    ------------------------
    Variables ending in "_d" are directory paths, without a file name attached.
    Variables ending in "_n" are file names, without a directory attached.
    Variables ending in "_p" are full paths, including both the path and name.
    Variables ending in "_f" are file-descriptor objects.

    More details about the repository structure:
    ----------------------------------------

    Repositories are simply "blessed" directories on disk. The root level of a
    repository is just a normal directory, but it has a hidden file in it called
    ".repo_root". This file is a standard .ini file that has a single section
    named "settings" that contains a single item called "name" that defines the
    name of the repo.

    There may be any number of sub-directories inside of this root directory,
    and any number of levels of these subdirectories.  Each of these directories
    is identified as being the "structure" of the repository by containing a
    hidden file in it called ".repo". The contents of this file is currently
    ignored. It exists merely as a semaphore to indicate a "blessed" directory.
    In the future metadata about that particular branch of the repo structure
    may be stored within this file.

    The very last level of sub-directories that are part of the repo structure
    (i.e. contain ".repo" files in them) are considered leaf structure dirs.
    Only these directories may contain anything other than other structure dirs,
    and they may only contain asset dirs.

    Once a dir is found that does not have a ".repo" file in it, that dir
    should be considered the asset that the system is tracking.

    There can be no gaps inside the structure of a repo. I.e. you cannot have
    the root directory followed by a structure dir (blessed dir) followed by a
    non-blessed dir which then contains another structure dir (blessed dir).
    This kind of non-contiguous structure may result in errors or undefined
    behavior.

    There is no requirement than any two branches in a repository have the same
    structure. One branch could have as many as three or four nested sub-dirs,
    and another might only have one. The structure of the repository is entirely
    free-form in this regard (and may be modified at any time).

    There may be as many repositories on disk as desired.
    """

    # --------------------------------------------------------------------------
    def __init__(self, path, language="english"):
        """
        Initialize the repo object (responsible for managing the schema of a
        single repo).

        :param path: The path on disk to where the repo root is.
        :param language: The language used for communication with the end user.
               Defaults to "english".
        """

        module_d = os.path.split(inspect.stack()[0][1])[0]
        resources_d = os.path.join(module_d, "..", "..", "resources")
        self.resc = resources.Resources(resources_d, "lib_schema", language)

        # Make sure the repo path even exists
        if not os.path.exists(path):
            err = self.resc.error(400)
            err.msg = err.msg.format(path=path)
            raise SquirrelError(err.msg, err.code)

        # Make sure this is a repo root
        if not os.path.exists(os.path.join(path, ".repo_root")):
            err = self.resc.error(200)
            err.msg = err.msg.format(root_path=path)
            raise SquirrelError(err.msg, err.code)

        self.repo_root_d = path

        repo_obj = ConfigParser.ConfigParser()
        repo_obj.read(os.path.join(path, ".repo_root"))

        if repo_obj.has_option("settings", "name"):
            self.name = repo_obj.get("settings", "name")
        else:
            err = self.resc.error(106)
            err.msg = err.msg.format(path=path)
            raise SquirrelError(err.msg, err.code)

    # --------------------------------------------------------------------------
    @staticmethod
    def format_token(token):
        """
        Tokens are relative paths from the root of the repo. Tokens are always
        expressed as a UNIX style path (i.e. /this/type/of/format/) regardless
        of whether this system is running on a UNIX-like OS or Windows.

        This function makes sure the token does not begin or end with a slash.
        If the token does not have a leading or trailing slash, it is returned
        unchanged.

        :param token: The token being formatted.

        :return: The same token, but with any leading and trailing slashes
                 removed.
        """

        return token.lstrip("/").rstrip("/")

    # --------------------------------------------------------------------------
    def get_path_from_token(self, token):
        """
        Given a token, returns a path appropriate to the OS being used. No error
        checking is done to ensure this is an actual path on disk. No error
        checking is done to ensure this ia a valid token.

        :param token: The unix-style relative path.

        :return: The OS appropriate path.
        """

        token = self.format_token(token)
        tokens_p = filesystem.convert_unix_path_to_os_path(token)
        return os.path.join(self.repo_root_d, tokens_p)

    # --------------------------------------------------------------------------
    def get_token_from_path(self, path_p):
        """
        Given a path, returns a token (a relative path in UNIX-style format). If
        the path is not a valid path in the current repo, raises an error. Note
        that the path may be deep inside of an asset that is within the repo.
        For example, the repo root might be:

        /show/repo/

        and within this repo, a structure path might be:

        asset/bldg

        If the path passed is:

        /show/repo/asset/bldg/asset_bldg_big_A/v0002/geo/bldg_big_A.abc

        then the token returned will be:

        asset/bldg

        :param path_p: The full path.

        :return: A token.
        """

        if not self.path_is_within_repo(path_p):
            err = self.resc.error(4)
            err.msg = err.msg.format(path=path_p)
            raise SquirrelError(err.msg, err.code)

        # Step backwards through the path to find the first instance structure
        # dir (this would be a leaf dir of the repo).
        test_dir = path_p.rstrip(os.path.sep)
        items = os.listdir(test_dir)
        while ".repo" not in items and ".repo_root" not in items:
            test_dir = os.path.split(test_dir)[0]
            items = os.listdir(test_dir)

        # This is the bottom-most rung of the repo structure in this branch.
        # Get its relative path from the root of the repo
        token = os.path.relpath(test_dir, self.repo_root_d)

        # Convert this into a token (it could be a windows path, and tokens are
        # always in the format of a Unix-style path.)
        return self.format_token(token.replace(os.path.sep, "/"))

    # --------------------------------------------------------------------------
    def token_is_valid(self, token):
        """
        Given a token, checks to see if it is a valid repo structure path.

        :param token: The unix-style relative path.

        :return: True if the token refers to a valid repo structure path, False
                 otherwise.
        """

        token = self.format_token(token)
        path_p = self.get_path_from_token(token)
        return self.path_is_repo_structure(path_p)

    # --------------------------------------------------------------------------
    def token_is_leaf(self, token):
        """
        Given a token, checks to see if it is a valid repo structure path AND
        that it is a leaf (i.e. the last directory in the repo structure before
        an asset is stored).

        :param token: The unix-style relative path.

        :return: True if the token refers to a valid repo structure path AND is
                 a leaf directory (the last directory in a repo structure before
                 assets are stored), False otherwise.
        """

        token = self.format_token(token)
        path_p = self.get_path_from_token(token)
        if not self.path_is_repo_structure(path_p):
            return False

        if not self.path_is_repo_leaf(path_p):
            return False

        return True

    # --------------------------------------------------------------------------
    def get_next_tokens(self, token):
        """
        Given a token, returns a list of the next possible tokens.

        :param token: token: The unix-style relative path.

        :return: A list of the next possible tokens after the one given.
        """

        assert self.token_is_valid(token)

        token = self.format_token(token)
        path_p = self.get_path_from_token(token)

        return self.get_next_structure_names(path_p)

    # --------------------------------------------------------------------------
    def path_is_within_repo(self, path_p):
        """
        Checks to see if the path is either part of the repo structure or
        contained with an asset managed by this repo. Does not validate that the
        path actually exists or not.

        :param path_p: The path being validated.

        :return: True if it is anywhere within the repo. False otherwise.
        """

        return path_p.startswith(self.repo_root_d)

    # --------------------------------------------------------------------------
    def path_is_repo_structure(self, path_p):
        """
        Checks to see if the given path is a part of the structure of the repo
        (vs. being an asset file or dir, or even outside of the repo
        altogether). Makes sure that the path given meets all of the following
        requirements:

        Does the path exist?
        Is the path a directory?
        Is the path a within the current repo?
        Does the path contain a .repo_root_d or .repo file?
        Is this .repo_root_d or .repo file actually a file (not a dir)?

        If all 5 tests pass, then this is a structure path of the current repo.

        :param path_p: The on-disk path being tested.

        :return: True if it is a valid structure directory of the current repo,
                 False otherwise.
        """

        if not os.path.exists(path_p):
            return False

        if not os.path.isdir(path_p):
            return False

        if not path_p.startswith(self.repo_root_d):
            return False

        if (not os.path.exists(os.path.join(path_p, ".repo")) and
                not os.path.exists(os.path.join(path_p, ".repo_root"))):
            return False

        if os.path.exists(os.path.join(path_p, ".repo")):
            if os.path.isdir(os.path.join(path_p, ".repo")):
                return False

        if os.path.exists(os.path.join(path_p, ".repo_root")):
            if os.path.isdir(os.path.join(path_p, ".repo_root")):
                return False

        return True

    # --------------------------------------------------------------------------
    def path_is_repo_root(self, path_p):
        """
        Returns true if the given path is the root path of the repo, False
        otherwise.

        :param path_p: The path we are testing.

        :return: True if is the root path of the repository, False otherwise.
        """

        return path_p == self.repo_root_d

    # --------------------------------------------------------------------------
    def get_next_structure_names(self, path_p):
        """
        Given a path, return the names (not paths) of any sub-directories that
        are also part of the repo structure.

        :param path_p: The path we are testing.

        :return: A list of directory names that are within this path that are
                 themselves also structure directories.
        """

        assert self.path_is_repo_structure(path_p)

        # Check all of the sub-dirs to see if any of them have a .repo file
        output = list()
        items = os.listdir(path_p)
        for item in items:
            if os.path.isdir(os.path.join(path_p, item)):
                if self.path_is_repo_structure(os.path.join(path_p, item)):
                    output.append(item)

        return output

    # --------------------------------------------------------------------------
    def get_next_from_broken_token(self, token):
        """
        Given a token that is broken (i.e. is not a valid token or is an
        incomplete token in that it does not extend all the way down to the leaf
        level), return the portion of the token that is valid, plus a list of
        possible next items.

        :param token: The broken token.

        :return: A tuple where the first item is the portion of the token that
                 is valid, and the second item is a list of possible next
                 tokens.
        """

        if self.token_is_valid(token) and self.token_is_leaf(token):
            return token, []

        valid = ""
        possible_next = list()

        token = self.format_token(token)

        for i in range(len(token.split("/")) + 1):
            test_token = "/".join(token.split("/")[:i])
            if self.token_is_valid(test_token):
                valid = test_token
            else:
                possible_next = self.get_next_tokens(valid)
                break

        if not possible_next and not self.token_is_leaf(valid):
            possible_next = self.get_next_tokens(valid)

        possible_next.sort()

        return valid, possible_next

    # --------------------------------------------------------------------------
    def path_is_repo_leaf(self, path_p):
        """
        Returns true if the given path is a leaf structure dir, False
        otherwise. A leaf is the very last path item in the repo structure.

        :param path_p: The path we are testing.

        :return: True if is leaf structure dir of the repo, False otherwise.
        """

        if not self.path_is_repo_structure(path_p):
            return False

        # Get a list of any sub-dirs that are also structure. If this is not
        # empty, then we are not a leaf.
        if self.get_next_structure_names(path_p):
            return False
        return True

    # --------------------------------------------------------------------------
    def list_asset_paths(self, token=""):
        """
        Returns a list of all the asset paths under the token given by token. If
        the token is not valid, raise an error.

        :param token: A relative path from the root of the repo. Defaults to
               "" which means the repo root (i.e. list all assets in the repo).

        :return: A list of asset paths
        """

        if not self.token_is_valid(token):
            err = self.resc.error(700)
            err.msg = err.msg.format(token=token, repo=self.name)
            raise SquirrelError(err.msg, err.code)

        # Because the token might not be a leaf node, we have to consider
        # sub-directories of this token as well.
        output = list()
        repo_d = self.get_path_from_token(token)

        for dir_d, files_n, dirs_n in os.walk(repo_d):
            if publisherInterface.path_is_asset_root(dir_d):
                output.append(dir_d.rstrip(os.path.sep) + os.path.sep)
        return output

    # --------------------------------------------------------------------------
    def list_asset_names(self, token=""):
        """
        Returns a list of all the asset names under the token given by token. If
        the token is not valid, raise an error.

        :param token: A relative path from the root of the repo. Defaults to
               "" which means the repo root (i.e. list all assets in the repo).

        :return: A list of asset paths
        """

        output = list()

        assets_p = self.list_asset_paths(token)
        for asset_p in assets_p:
            output.append(os.path.split(asset_p.rstrip("/"))[1])

        return output

    # --------------------------------------------------------------------------
    def get_publish_loc(self, token):
        """
        Returns the path where an asset should be stored.

        :param token: The token that defines where in the repo structure to
               publish.

        :return: Nothing
        """

        if not self.token_is_valid(token) or not self.token_is_leaf(token):

            valid, possible_next = self.get_next_from_broken_token(token)

            if valid:
                msg = self.resc.message("possible_next")
            else:
                msg = self.resc.message("possible_next_empty_valid")

            msg = msg.format(valid=valid,
                             possible_next="\n   ".join(possible_next))

            raise SquirrelError(msg, 0)

        return self.get_path_from_token(token)
