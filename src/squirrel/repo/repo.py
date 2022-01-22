import configparser
import os
import pathlib

import bvzversionedfiles.bvzversionedfiles as bvzversionedfiles

from squirrel.asset.asset import Asset
from squirrel.shared import urilib
from squirrel.shared.squirrelerror import SquirrelError
from bvzframespec import Framespec


# ======================================================================================================================
class Repo(object):
    """
    Class managing the schema of a single repository.

    Some terminology:
    -----------------
    Repository (repo):
            A repository is a series of directories on disk. A repo may contain multiple levels (nested subdirectories)
            which define the repo structure. At the very ends of these nested directories are the actual assets being
            stored in the repository. There may be any number of repos on a filesystem.
    URI path:
            A string in a UNIX path format (i.e. /using/this/format) that describes a relative path to a point inside
            the repository structure. This path is relative to the repo root. URI paths are always references to actual
            directories, and they are always passed as UNIX style relative paths even on Windows systems. URI paths
            never resolve all the way down to the asset level. They only describe the structure of the repo itself. They
            may contain a leading slash, or omit it. URI paths with or without leading slashes are functionally
            identical. They may also end with a trailing slash or omit it. Again, URI paths with or without trailing
            slashes are functionally identical.
    Structure:
            Repositories are defined by a directory structure consisting of "blessed" directories (and no files). A
            directory is "blessed" if it contains a .repo or .repo_root file in it. This structure defines the hierarchy
            of the repo, with each subdirectory making up the "branches" of the repo. The very last subdirectory of
            each branch is considered a "leaf" structure. No files may live at any level of the structure. Only
            "blessed" directories may live within the repo structure. Likewise, no non-blessed directories may live at
            any level of the structure except within the final, leaf level. At this leaf level are the actual asset
            directories. The contents of the asset directories are managed by the asset module.
    Managed:
            A "managed" file or directory is any file or directory that is below the structure level of the repo (i.e.
            within an asset that lives at the end of a repo structure). Managed files and dirs are essentially the
            assets being stored by the repo.
    Assets:
            Assets are directories that contain files. Assets are defined to only exist as special directories in the
            leaf structure dirs. Asset structure is defined outside of this repo and are managed by the asset module.


    Some naming conventions:
    ------------------------
    Variables ending in "_d" are directory paths, without a file name attached.
    Variables ending in "_n" are file names, without a directory attached.
    Variables ending in "_p" are full paths, including both the path and name.
    Variables ending in "_f" are file-descriptor objects.

    More details about the repository structure:
    ----------------------------------------

    Repositories are simply "blessed" directories on disk. The root level of a repository is just a normal directory,
    but it has a hidden file in it called ".repo_root".

    There may be any number of subdirectories inside of this root directory, and any number of levels of these
    subdirectories.  Each of these directories is identified as being the "structure" of the repository by containing a
    hidden file in it called ".repo". The contents of this file is currently ignored. It exists merely as a semaphore to
    indicate a "blessed" directory. In the future metadata about that particular branch of the repo structure may be
    stored within this file.

    The very last level of subdirectories that are part of the repo structure (i.e. the final directory that contains a
    ".repo" files in them) are considered leaf structure dirs. Only these directories may contain anything other than
    other structure dirs, and they may only contain asset dirs.

    Once a dir is found that does not have a ".repo" file in it, that dir should be considered the asset that the system
    is tracking.

    There can be no gaps inside the structure of a repo. I.e. you cannot have the root directory followed by a structure
    dir (blessed dir) followed by a non-blessed dir which then contains another structure dir (blessed dir). This kind
    of non-contiguous structure may result in errors or undefined behavior.

    There is no requirement than any two branches in a repository have the same structure. One branch could have as many
    as three or four nested sub-dirs, and another might only have one. The structure of the repository is entirely
    free-form in this regard (and may be modified at any time).

    There may be as many repositories on disk as desired.
    """

    # ------------------------------------------------------------------------------------------------------------------
    def __init__(self,
                 repo_root_d,
                 cache_d,
                 config_obj,
                 localized_resource_obj,
                 sql_resources,
                 connection,
                 cursor):
        """
        :param repo_root_d:
                The repo directory
        :param cache_d:
                The path to the cache directory (where the cache file is stored)
        :param config_obj:
                A config object.
        :param localized_resource_obj:
                The localized resources object to manage language specific strings.
        :param sql_resources:
                A sql resources object.
        :param connection:
                A sqlite3 connection object that is already connected to the cache database.
        :param cursor:
                A sqlite3 cursor object that is already connected to connection object.

        :return:
               Nothing.
        """

        assert type(repo_root_d) is str
        assert type(cache_d) is str

        self.repo_root_d = repo_root_d
        self._validate_repo_root_d()

        self.repo_n = os.path.split(repo_root_d.rstrip(os.sep))[1]

        self.cache_d = cache_d
        self._validate_cache_d()

        self.localized_resource_obj = localized_resource_obj
        self.config_obj = config_obj

        self.sql_resources = sql_resources
        self.connection = connection
        self.cursor = cursor

    # ------------------------------------------------------------------------------------------------------------------
    def _validate_repo_root_d(self):
        """
        Raises an error if repo_root_d is missing or not a directory.

        :return:
                Nothing.
        """

        if not os.path.isdir(self.repo_root_d):
            err_msg = self.localized_resource_obj.get_error_msg(302)
            err_msg = err_msg.format(repo_path=self.repo_root_d)
            raise SquirrelError(err_msg, 302)

    # ------------------------------------------------------------------------------------------------------------------
    def _validate_cache_d(self):
        """
        Raises an error if cache_d is missing or not a directory.

        :return:
                Nothing.
        """

        if not os.path.isdir(self.cache_d):
            err_msg = self.localized_resource_obj.get_error_msg(800)
            err_msg = err_msg.format(cache_dir=self.cache_d)
            raise SquirrelError(err_msg, 800)

    # ------------------------------------------------------------------------------------------------------------------
    def is_repo(self):
        """
        Returns whether the current path for the repo is actually a repo (contains a .repo_root semaphore file).

        :return:
            True if the Asset refers to an actual asset on disk (has a .asset semaphore file). False otherwise.
        """

        return os.path.exists(os.path.join(self.repo_root_d, ".repo_root"))

    # ------------------------------------------------------------------------------------------------------------------
    def _flush_asset_keywords_from_cache(self,
                                         asset_id):
        """
        Removes all the keywords from a specific asset.

        :param asset_id:
                The id of the asset from which to remove all keywords.

        :return:
                Nothing.
        """

        sql = self.sql_resources.get("flush_asset_keywords_from_cache", "flush_assets_keywords")
        self.cursor.execute(sql, (asset_id,))

    # ------------------------------------------------------------------------------------------------------------------
    def _flush_asset_metadata_from_cache(self,
                                         asset_id):
        """
        Removes all the metadata from a specific asset.

        :param asset_id:
                The id of the asset from which to remove all metadata.

        :return:
                Nothing.
        """

        sql = self.sql_resources.get("flush_asset_metadata_from_cache", "flush_assets_metadata")
        self.cursor.execute(sql, (asset_id,))

    # ------------------------------------------------------------------------------------------------------------------
    def _flush_asset_id_from_cache(self,
                                   asset_id):
        """
        Removes a specific asset from the assets table (does not clean the keywords or metadata join tables).

        :param asset_id:
                The id of the asset to remove.

        :return:
                Nothing.
        """

        sql = self.sql_resources.get("flush_asset_id_from_cache", "flush_asset_id")
        self.cursor.execute(sql, (asset_id,))

    # ------------------------------------------------------------------------------------------------------------------
    def _flush_asset_from_cache(self,
                                asset_id):
        """
        Removes a single asset from the cache.

        :param asset_id:
                The id of the asset to be removed.

        :return:
                Nothing.
        """

        self._flush_asset_id_from_cache(asset_id=asset_id)
        self._flush_asset_keywords_from_cache(asset_id=asset_id)
        self._flush_asset_metadata_from_cache(asset_id=asset_id)

        self.connection.commit()

    # ------------------------------------------------------------------------------------------------------------------
    def _flush_cache(self):
        """
        Removes all of the elements from the cache that pertain to the current repo.

        :return:
                Nothing.
        """

        sql = self.sql_resources.get("sql", "flush_repo_from_cache_list_asset_ids")
        asset_ids = self.cursor.execute(sql, (self.repo_n,)).fetchall()
        asset_ids = [item[0] for item in asset_ids]

        for asset_id in asset_ids:
            self._flush_asset_from_cache(asset_id=asset_id)

    # ------------------------------------------------------------------------------------------------------------------
    def _cache_keyword(self,
                       keyword,
                       asset_id):
        """
        Adds the keyword to the cache for the given asset_id.

        :param keyword:
                The keyword to add to the cache for this asset.
        :param asset_id:
                The asset id for the asset for which we are caching a keyword.

        :return:
                Nothing.
        """

        sql = self.sql_resources.get("cache_keyword", "cache_keyword")
        self.cursor.execute(sql, (keyword,))

        sql = self.sql_resources.get("cache_keyword", "cache_keyword_get_keyword_id")
        keyword_id = self.cursor.execute(sql, (keyword,)).fetchone()[0]

        sql = self.sql_resources.get("cache_keyword", "cache_keyword_assets_keywords")
        self.cursor.execute(sql, (asset_id, keyword_id,))

        self.connection.commit()

    # ------------------------------------------------------------------------------------------------------------------
    def _cache_metadata(self,
                        key,
                        value,
                        asset_id):
        """
        Adds the metadata to the cache for the given asset_id.

        :param key:
                The metadata key to add to the cache for this asset.
        :param value:
                The metadata value to add to the cache for this asset.
        :param asset_id:
                The asset id for the asset for which we are caching the metadata.

        :return:
                Nothing.
        """

        try:
            num_value = float(value)
        except ValueError:
            num_value = None

        sql = self.sql_resources.get("cache_metadata", "cache_asset_metadata")
        self.cursor.execute(sql, (key, value, num_value))

        sql = self.sql_resources.get("cache_metadata", "cache_asset_get_metadata_id")
        metadata_id = self.cursor.execute(sql, (key, value,)).fetchone()[0]

        sql = self.sql_resources.get("cache_metadata", "cache_asset_asset_metadata")
        self.cursor.execute(sql, (asset_id, metadata_id,))

        self.connection.commit()

    # ------------------------------------------------------------------------------------------------------------------
    def _cache_thumbnail(self,
                         version_int,
                         thumbnail_p,
                         asset_id):
        """
        Adds a single thumbnail path to the cache for the given asset_id and version.

        :param version_int:
                The asset version number that has this particular thumbnail.
        :param thumbnail_p:
                The thumbnail path.
        :param asset_id:
                The asset id for the asset for which we are caching the thumbnails.

        :return:
                Nothing.
        """

        # self.connection.set_trace_callback(print)

        sql = self.sql_resources.get("cache_thumbnail", "list_thumbnail")
        rows = self.cursor.execute(sql, (asset_id, version_int)).fetchall()
        if len(rows) > 0:
            sql = self.sql_resources.get("cache_thumbnail", "update_thumbnail")
        else:
            sql = self.sql_resources.get("cache_thumbnail", "cache_thumbnail")
        self.cursor.execute(sql, (thumbnail_p, asset_id, version_int))

        self.connection.commit()

        # self.connection.set_trace_callback(None)

    # ------------------------------------------------------------------------------------------------------------------
    def _cache_thumbnails(self,
                          asset_id):
        """
        Finds all the thumbnails for all versions and pins and caches them.

        :param asset_id:
                The asset id for the asset for which we are caching the thumbnails.

        :return:
                Nothing.
        """

        sql = self.sql_resources.get("cache_thumbnails", "asset_obj_from_id")
        rows = self.cursor.execute(sql, (asset_id,)).fetchall()

        if len(rows) == 0:
            err_msg = self.localized_resource_obj.get_error_msg(913)
            raise SquirrelError(err_msg, 913)

        if len(rows) > 1:
            err_msg = self.localized_resource_obj.get_error_msg(914)
            raise SquirrelError(err_msg, 914)

        parent_d, asset_n = rows[0]

        asset_obj = Asset(asset_parent_d=parent_d,
                          name=asset_n,
                          config_obj=self.config_obj,
                          localized_resource_obj=self.localized_resource_obj)

        version_ints = asset_obj.version_objs.keys()
        pins_n = asset_obj.pin_objs.keys()

        for version_int in version_ints:
            framespec_obj = Framespec()
            framespec_obj.files = asset_obj.list_thumbnails(version_int)
            thumbnails_p = framespec_obj.framespec_str
            self._cache_thumbnail(version_int=version_int,
                                  thumbnail_p=thumbnails_p,
                                  asset_id=asset_id)

        for pin_n in pins_n:
            version_int = asset_obj.pin_objs[pin_n].version_int
            framespec_obj = Framespec()
            framespec_obj.files = asset_obj.list_thumbnails(version_int)
            thumbnails_p = framespec_obj.framespec_str
            # TODO: Version_int cannot store pin_n
            self._cache_thumbnail(version_int=pin_n,
                                  thumbnail_p=thumbnails_p,
                                  asset_id=asset_id)

        self.connection.commit()

    # ------------------------------------------------------------------------------------------------------------------
    def _cache_poster(self,
                      version_int,
                      poster_p,
                      asset_id):
        """
        Adds a single poster path to the cache for the given asset_id and version.

        :param version_int:
                The asset version number that has this particular poster.
        :param poster_p:
                The poster path.
        :param asset_id:
                The asset id for the asset for which we are caching the poster.

        :return:
                Nothing.
        """

        # self.connection.set_trace_callback(print)
        # TODO: Check that this works with version_int instead of version_str
        sql = self.sql_resources.get("cache_poster", "list_poster")
        rows = self.cursor.execute(sql, (asset_id, version_int)).fetchall()
        if len(rows) > 0:
            sql = self.sql_resources.get("cache_poster", "update_poster")
        else:
            sql = self.sql_resources.get("cache_poster", "cache_poster")
        self.cursor.execute(sql, (poster_p, asset_id, version_int))

        self.connection.commit()

        # self.connection.set_trace_callback(None)

    # ------------------------------------------------------------------------------------------------------------------
    def _cache_posters(self,
                       asset_id):
        """
        Finds all the posters for all versions and pins and caches them.

        :param asset_id:
                The asset id for the asset for which we are caching the posters.

        :return:
                Nothing.
        """

        sql = self.sql_resources.get("cache_posters", "asset_obj_from_id")
        rows = self.cursor.execute(sql, (asset_id,)).fetchall()

        if len(rows) == 0:
            err_msg = self.localized_resource_obj.get_error_msg(913)
            raise SquirrelError(err_msg, 913)

        if len(rows) > 1:
            err_msg = self.localized_resource_obj.get_error_msg(914)
            raise SquirrelError(err_msg, 914)

        parent_d, asset_n = rows[0]

        asset_obj = Asset(asset_parent_d=parent_d,
                          name=asset_n,
                          config_obj=self.config_obj,
                          localized_resource_obj=self.localized_resource_obj)

        version_ints = asset_obj.version_objs.keys()
        pins_n = asset_obj.pin_objs.keys()

        for version_int in version_ints:
            poster_p = asset_obj.list_poster(version_int)
            if not poster_p:
                poster_p = ""
            self._cache_poster(version_int=version_int,
                               poster_p=poster_p,
                               asset_id=asset_id)

        for pin_n in pins_n:
            version_int = asset_obj.pin_objs[pin_n].version_int
            poster_p = asset_obj.list_poster(version_int)
            if not poster_p:
                poster_p = ""
            # TODO: How to cache this with a pin name
            self._cache_poster(version_int=pin_n,
                               poster_p=poster_p,
                               asset_id=asset_id)

        self.connection.commit()

    # ------------------------------------------------------------------------------------------------------------------
    def cache_asset(self,
                    asset_obj):
        """
        Stores the cached data for a single asset in the cache database.

        :param asset_obj:
                The asset we are caching.

        :return:
                Nothing.
        """

        # self.connection.set_trace_callback(print)

        uri_path = self._uri_path_from_file_path(asset_obj.asset_d)
        uri = f"{self.repo_n}:/{uri_path}#{asset_obj.asset_n}"

        sql = self.sql_resources.get("cache_asset", "insert_into_assets")
        self.cursor.execute(sql, (uri,
                                  uri_path,
                                  self.repo_n,
                                  asset_obj.asset_n,
                                  asset_obj.asset_parent_d,
                                  asset_obj.asset_d))
        last_row_id = self.cursor.lastrowid

        sql = self.sql_resources.get("cache_asset", "asset_id_from_last_row_id")
        asset_id = self.cursor.execute(sql, (last_row_id,)).fetchone()[0]
        self.connection.commit()

        for keyword in asset_obj.list_keywords():
            self._cache_keyword(keyword=keyword,
                                asset_id=asset_id)

        for key, value in asset_obj.list_key_value_pairs().items():
            self._cache_metadata(key=key,
                                 value=value,
                                 asset_id=asset_id)

        self._cache_thumbnails(asset_id=asset_id)

        self._cache_posters(asset_id=asset_id)

        # connection.set_trace_callback(None)

    # ------------------------------------------------------------------------------------------------------------------
    def cache_assets_from_filesystem(self):
        """
        Loads all the assets in the repo from the filesystem and into a sqlite3 database.

        :return:
                Nothing.
        """

        self._flush_cache()

        for dir_d, dirs_n, files_n in os.walk(self.repo_root_d):
            if os.path.exists(os.path.join(dir_d, ".repo")):
                continue
            if os.path.exists(os.path.join(dir_d, ".repo_root")):
                continue
            parent_d, name = os.path.split(dir_d)
            asset_obj = Asset(asset_parent_d=parent_d,
                              name=name,
                              config_obj=self.config_obj,
                              localized_resource_obj=self.localized_resource_obj)
            if asset_obj.is_asset():
                self.cache_asset(asset_obj=asset_obj)
                dirs_n[:] = []  # Empty out the dirs_n list so that we don't go any deeper down this directory branch

    # ------------------------------------------------------------------------------------------------------------------
    def _path_is_within_repo(self,
                             path_p):
        """
        Checks to see if the given path is either part of the repo structure or contained with an asset managed by this
        repo. Does not validate that the path actually exists or not.

        :param path_p:
                The path being validated.

        :return:
                True if it is anywhere within the repo. False otherwise.
        """

        return path_p.startswith(self.repo_root_d)

    # ------------------------------------------------------------------------------------------------------------------
    def _path_is_part_of_repo_structure(self,
                                        path_p):
        """
        Checks to see if the given path is a part of the structure of the repo (vs. being an asset file or dir, or even
        outside of the repo altogether). Note that this is slightly different than simply determining whether a path is
        within a repo. There may be paths within a repo that are not a part of the repo structure. Paths inside of
        assets for example. Or a directory inside of the repo that has not been blessed. To determine whether a path is
        a part of the structure of a repo, it must meet all of the following requirements:

        Does the path exist?
        Is the path a directory?
        Is the path a within the current repo?
        Does the path contain a .repo_root or .repo file?
        Is this .repo_root or .repo file actually a file (not a dir)?

        If all 5 tests pass, then this is a valid path in the current repo.

        :param path_p:
                The on-disk path being tested.

        :return:
                True if it is a valid directory within the current repo, False otherwise.
        """

        if not os.path.exists(path_p):
            return False

        if not os.path.isdir(path_p):
            return False

        if not self._path_is_within_repo(path_p):
            return False

        if (not os.path.exists(os.path.join(path_p, ".repo")) and
                not os.path.exists(os.path.join(path_p, ".repo_root"))):
            return False

        if os.path.isdir(os.path.join(path_p, ".repo")):
            return False

        if os.path.isdir(os.path.join(path_p, ".repo_root")):
            return False

        return True

    # ------------------------------------------------------------------------------------------------------------------
    def _uri_path_is_valid(self,
                           uri_path):
        """
        Given a uri_path, checks to see if it exists in the repo.

        :param uri_path:
            The unix-style relative path.

        :return:
            True if the uri_path refers to an existing repo directory, False otherwise.
        """

        path_p = os.path.join(self.repo_root_d, *uri_path.split("/"))
        return self._path_is_part_of_repo_structure(path_p)

    # ------------------------------------------------------------------------------------------------------------------
    def _file_path_from_uri_path(self,
                                 uri_path):
        """
        Given a uri_path, returns a file path appropriate to the OS being used. No error checking is done to ensure this
        is an actual path on disk. No error checking is done to ensure this ia a valid uri_path.

        :param uri_path:
            The unix-style relative path.

        :return:
            The OS appropriate path.
        """

        return os.path.join(self.repo_root_d, *uri_path.split("/"))

    # ------------------------------------------------------------------------------------------------------------------
    def _uri_path_from_file_path(self,
                                 path_p):
        """
        Given a path, returns a uri_path (a relative path in UNIX-style format). If the path is not a valid path in the
        current repo, raises an error. Note that the path may be deep inside of an asset that is within the repo.
        For example, the repo root might be:

        /show/repo/

        and within this repo, a structure path might be:

        asset/bldg

        If the path passed is:

        /show/repo/asset/bldg/asset_bldg_big_A/v0002/geo/bldg_big_A.abc

        then the uri_path returned will be:

        /asset/bldg

        :param path_p:
                The full path.

        :return:
                A uri_path.
        """

        assert self._path_is_within_repo(path_p)

        # Strip off the path leading up to the repo root.
        path_p = path_p.split(self.repo_root_d)[1].lstrip(os.sep)

        # Split the remaining bits into a list
        uri_path = ""
        path_items = pathlib.Path(path_p).parts

        # Step through the remaining bits and check each to see if it is a valid uri_path. Once it fails (or if we run
        # out of paths to check) then we have a complete uri_path.
        for i in range(1, len(path_items) + 1):
            test_uri_path = "/".join(path_items[:i])  # <- URI paths always use the linux style paths (/ separator)
            if not self._uri_path_is_valid(test_uri_path):
                return f"/{uri_path.strip('/')}"
            uri_path = "/" + test_uri_path.lstrip("/")

        return f"/{uri_path.strip('/')}"

    # ------------------------------------------------------------------------------------------------------------------
    def _uri_path_is_leaf(self,
                          uri_path):
        """
        Returns true if the given uri_path is a leaf structure dir, False otherwise. A leaf is the very last path item
        in the repo structure.

        :param uri_path:
                The unix-style relative path.

        :return:
                True if the uri_path refers to a valid repo structure path AND is a leaf directory (the last directory
                in a repo structure before assets are stored), False otherwise.
        """

        assert self._uri_path_is_valid(uri_path)

        if self.get_next_uri_paths(uri_path):
            return False
        return True

    # ------------------------------------------------------------------------------------------------------------------
    def get_next_uri_paths(self,
                           uri_path):
        """
        Given a uri_path, returns a list of the next possible uri_paths.

        :param uri_path:
                The unix-style relative path.

        :return:
                A list of the next possible uri_paths after the one given.
        """

        assert self._uri_path_is_valid(uri_path)

        path_p = self._file_path_from_uri_path(uri_path)
        output = list()
        items = os.listdir(path_p)
        for item in items:
            if os.path.isdir(os.path.join(path_p, item)):
                if self._path_is_part_of_repo_structure(os.path.join(path_p, item)):
                    output.append(item)

        return output

    # ------------------------------------------------------------------------------------------------------------------
    def _bless_dir(self,
                   dir_p,
                   root=False):
        """
        "Blesses" a particular path to include it as part of a repository. There are two types of blessed directories:
        Root and Normal. A Root directory can only live at the top of a hierarchy. A Normal directory can only live
        inside of another Normal directory or a Root directory. Being "blessed" simply means there is a .repo file in
        the directory (.repo_root if it is the root directory).

        :param dir_p:
                The full path to the directory being blessed.
        :param root:
                If True, then this is a root dir, otherwise it is a normal structure dir.

        :return:
                Nothing.
        """

        assert type(dir_p) is str
        assert type(root) is bool

        if not os.path.exists(dir_p):
            err_msg = self.localized_resource_obj.get_error_msg(100)
            err_msg = err_msg.format(dir=dir_p)
            raise SquirrelError(err_msg, 100)

        if root:
            semaphore_p = os.path.join(dir_p, ".repo_root")
        else:
            semaphore_p = os.path.join(dir_p, ".repo")

        if os.path.isdir(semaphore_p):
            err_msg = self.localized_resource_obj.get_error_msg(101)
            err_msg = err_msg.format(file_path=semaphore_p)
            raise SquirrelError(err_msg, 101)

        if os.path.exists(semaphore_p):
            os.remove(semaphore_p)

        if root:
            semaphore_obj = configparser.ConfigParser()
            semaphore_obj.add_section("settings")
            semaphore_obj.set("settings", "repo_name", self.repo_n)
            with open(semaphore_p, "w") as f:
                semaphore_obj.write(f)
        else:
            open(semaphore_p, "w").close()

    # ------------------------------------------------------------------------------------------------------------------
    def _bless_root(self):
        """
        Blesses the root directory of the repo.

        :return:
            Nothing.
        """

        self._bless_dir(self.repo_root_d, True)

    # ------------------------------------------------------------------------------------------------------------------
    def bless_repo(self):
        """
        Blesses every subdirectory in the hierarchy under self.repo_root_d. Does not descend into directories that are
        asset directories.

        :return: Nothing.
        """

        root = True
        for dir_d, dirs_n, files_n in os.walk(self.repo_root_d):

            if root:
                self._bless_root()
                root = False
            else:
                self._bless_dir(dir_d, False)

            # Skip any sub-dirs are assets by removing them from the list of sub-dirs to descend into
            del_dirs_n = list()
            for dir_n in dirs_n:
                test_asset_obj = Asset(asset_parent_d=dir_d,
                                       name=dir_n,
                                       config_obj=self.config_obj,
                                       localized_resource_obj=self.localized_resource_obj)
                if test_asset_obj.is_asset():
                    del_dirs_n.append(dir_n)
            for del_n in del_dirs_n:
                dirs_n.remove(del_n)

    # ------------------------------------------------------------------------------------------------------------------
    def _asset_id_from_uri(self,
                           uri):
        """
        Returns a single asset_id based on the URI.

        :param uri:
                The uri.

        :return:
                An asset id.
        """

        assert uri is None or type(uri) is str

        if not urilib.validate_uri_format(uri):
            err_msg = self.localized_resource_obj.get_error_msg(201)
            err_msg = err_msg.format(uri=uri)
            raise SquirrelError(err_msg, 201)

        sql = self.sql_resources.get("asset_id_from_uri", "asset_id_from_uri")
        rows = self.cursor.execute(sql, (uri,)).fetchall()

        if len(rows) == 0:
            err_msg = self.localized_resource_obj.get_error_msg(911)
            err_msg = err_msg.format(uri=uri)
            raise SquirrelError(err_msg, 911)

        if len(rows) > 1:
            err_msg = self.localized_resource_obj.get_error_msg(912)
            err_msg = err_msg.format(uri=uri)
            raise SquirrelError(err_msg, 912)

        return rows[0][0]

    # ------------------------------------------------------------------------------------------------------------------
    def _asset_ids_from_uri_path(self,
                                 uri_path=None,
                                 asset_n=None):
        """
        Returns a list of all the asset id's under the uri_path given by uri_path. If the uri_path is not valid, raise
        an error. If the uri_path is a blank string or None, gets all assets in the repo. Incomplete uri_paths are
        allowed. I.e. if an asset lives at the uri_path: asset/veh/land/commercial and the uri_path passed is simply
        asset/veh then this asset will be included in the output.

        :param uri_path:
                A relative path from the root of the repo. Lists only the assets that are children of that uri_path.
                Defaults to None which means the repo root (i.e. get all assets in the repo).
        :param asset_n:
                An optional asset name to limit the result to. If None or a zero length string, then any asset matching
                the other attributes will be returned. If given, only those assets with this name will be returned.

        :return:
                A list of asset id's
        """

        assert uri_path is None or type(uri_path) is str
        assert asset_n is None or type(asset_n) is str

        if uri_path is None:
            uri_path = "/"

        if not self._uri_path_is_valid(uri_path):
            err_msg = self.localized_resource_obj.get_error_msg(700)
            err_msg = err_msg.format(uri_path=uri_path, repo=self.repo_n)
            raise SquirrelError(err_msg, 700)

        output = list()

        if not asset_n:
            sql = self.sql_resources.get("asset_ids_from_uri_path", "asset_ids_from_uri_path")
            rows = self.cursor.execute(sql, (uri_path + "%",)).fetchall()
        else:
            sql = self.sql_resources.get("asset_ids_from_uri_path", "asset_ids_from_uri_path_and_name")
            rows = self.cursor.execute(sql, (uri_path + "%", asset_n)).fetchall()

        for row in rows:
            output.append(row[0])

        return output

    # ------------------------------------------------------------------------------------------------------------------
    def _asset_ids_from_keywords(self,
                                 keywords,
                                 kw_match_use_and=False):
        """
        Given a list of keywords, return a list of asset ids for any assets that have these keywords.

        :param keywords:
                A list of keywords.
        :param kw_match_use_and:
                If True, then the match will be done as an AND match. If False, then as an OR match. Defaults to False.

        :return:
                A list of asset id's
        """

        assert type(keywords) is list
        assert type(kw_match_use_and) is bool

        output = list()

        keywords = [item.upper() for item in keywords]

        where_clause = ["keywords.keyword = ?" for _ in range(len(keywords))]

        if kw_match_use_and:
            where_clause = " OR ".join(where_clause)
            sql = self.sql_resources.get("sql", "asset_ids_from_keywords_using_and")
            sql = sql.format(where_clause=where_clause, count=len(keywords))
        else:
            where_clause = " OR ".join(where_clause)
            sql = self.sql_resources.get("sql", "asset_ids_from_keywords_using_or")
            sql = sql.format(where_clause=where_clause)

        rows = self.cursor.execute(sql, keywords).fetchall()

        for row in rows:
            output.append(row[0])

        return output

    # ------------------------------------------------------------------------------------------------------------------
    def _asset_ids_from_metadata_keys(self,
                                      metadata_keys,
                                      meta_match_use_and=False):
        """
        Given a list of metadata keys, return a list of asset ids for any assets that have the metadata keys, regardless
        of the metadata value.

        :param metadata_keys:
                A list of metadata keys.
        :param meta_match_use_and:
            If True, then the match will be done as an AND match. If False, then as an OR match. Defaults to False.

        :return:
                A list of asset id's
        """

        assert type(metadata_keys) is list
        assert type(meta_match_use_and) is bool

        output = list()

        keys = [item.upper() for item in metadata_keys]
        where_clause = ["metadata.metadata_key = ?" for _ in range(len(keys))]

        if meta_match_use_and:
            where_clause = " OR ".join(where_clause)
            sql = self.sql_resources.get("sql", "asset_ids_from_metadata_keys_using_and")
            sql = sql.format(where_clause=where_clause, count=len(keys))
        else:
            where_clause = " OR ".join(where_clause)
            sql = self.sql_resources.get("sql", "asset_ids_from_metadata_keys_using_or")
            sql = sql.format(where_clause=where_clause)

        rows = self.cursor.execute(sql, keys).fetchall()

        for row in rows:
            output.append(row[0])

        return output

    # ------------------------------------------------------------------------------------------------------------------
    def _asset_ids_from_metadata_key_and_values_using_or(self,
                                                         metadata):
        """
        Given a list of metadata keys, comparison_types, and values, return a list of asset ids for any assets that have
        ANY of these metadata keys AND matching metadata value. Both the key and the value have to match in order for it
        to be considered a match.

        :param metadata:
                An list of metadata to filter on. Each element of this list must be a 3-item tuple. The first
                element is the metadata key, the second is the comparison_type (either >, <, =, or !=) and the third
                item is the value of the metadata.

        :return:
                A list of asset id's
        """

        assert type(metadata) is list
        for item in metadata:
            assert type(item) is tuple
            assert len(item) == 3
            assert item[1] in ["!=", "=", "<", ">", ">=", "<=", ""]

        output = list()

        where_clause = list()
        where_values = list()
        for key, comparison_type, value in metadata:

            key = key.upper()
            value = value.upper()

            if comparison_type in ["<", ">", ">=", "<="]:
                where_str = "(metadata.metadata_key = ? AND metadata.metadata_num_value {comparison_type} ?)"
            else:
                where_str = "(metadata.metadata_key = ? AND metadata.metadata_value {comparison_type} ?)"
            where_str = where_str.format(comparison_type=comparison_type)
            where_clause.append(where_str)

            where_values.extend([key, value])

        where_clause = " OR ".join(where_clause)
        sql = self.sql_resources.get("sql", "asset_ids_from_metadata_key_and_values_using_or")
        sql = sql.format(where_clause=where_clause)

        rows = self.cursor.execute(sql, where_values).fetchall()

        for row in rows:
            output.append(row[0])

        return output

    # ------------------------------------------------------------------------------------------------------------------
    def _asset_ids_from_metadata_key_and_values_using_and(self,
                                                          metadata):
        """
        Given a list of metadata keys, comparison_types, and values, return a list of asset ids for any assets that have
        ALL of these metadata keys AND matching metadata value. Both the key and the value have to match in order for it
        to be considered a match. And these both have to match for EVERY combination of metadata key and value given.

        Note: This method was getting really hairy to try and do in a single sql statement. So the job was split up into
        multiple statements and a set intersection used to find the intersection of all the individual queries.

        :param metadata:
                An list of metadata to filter on. Each element of this list must be a 3-item tuple. The first
                element is the metadata key, the second is the comparison_type (either >, <, =, or !=) and the third
                item is the value of the metadata.

        :return:
                A list of asset id's
        """

        assert type(metadata) is list
        for item in metadata:
            assert type(item) is tuple
            assert len(item) == 3
            assert item[1] in ["!=", "=", "<", ">", ">=", "<=", ""]

        output = list()

        for key, comparison_type, value in metadata:

            key = key.upper()
            value = value.upper()

            if comparison_type in ["<", ">", ">=", "<="]:
                where_str = "metadata.metadata_key = ? AND metadata.metadata_num_value {comparison_type} ?"
            else:
                where_str = "metadata.metadata_key = ? AND metadata.metadata_value {comparison_type} ?"
            where_str = where_str.format(comparison_type=comparison_type)

            sql = self.sql_resources.get("sql", "asset_ids_from_metadata_key_and_values_using_and")
            sql = sql.format(where_clause=where_str)

            rows = self.cursor.execute(sql, (key, value)).fetchall()

            asset_ids = list()
            for row in rows:
                asset_ids.append(row[0])

            output.append(set(asset_ids))

        output = list(set.intersection(*output))

        return output

    # ------------------------------------------------------------------------------------------------------------------
    def _asset_ids_from_metadata_key_and_values(self,
                                                metadata_keys_and_values,
                                                meta_match_use_and=False):
        """
        Given a dict of metadata, return a list of asset ids for any assets that have the metadata keys AND values. Both
        the key AND value must match in order for the asset to be considered a match.

        :param metadata_keys_and_values:
                An list of metadata to filter on. Each element of this list must be a 3-item tuple. The first
                element is the metadata key, the second is the comparison_type (either >, <, =, or !=) and the third
                item is the value of the metadata.
        :param meta_match_use_and:
            If True, then the match will be done as an AND match. If False, then as an OR match. Defaults to False.

        :return:
                A list of asset id's
        """

        assert type(metadata_keys_and_values) is list
        for item in metadata_keys_and_values:
            assert type(item) is tuple
            assert len(item) == 3
            assert item[1] in ["!=", "=", "<", ">", ">=", "<=", ""]
        assert type(meta_match_use_and) is bool

        if meta_match_use_and:
            return self._asset_ids_from_metadata_key_and_values_using_and(metadata=metadata_keys_and_values)
        else:
            return self._asset_ids_from_metadata_key_and_values_using_or(metadata=metadata_keys_and_values)

    # ------------------------------------------------------------------------------------------------------------------
    def _asset_ids_from_attributes(self,
                                   uri=None,
                                   keywords=None,
                                   metadata_keys=None,
                                   metadata_keys_and_values=None,
                                   kw_match_use_and=False,
                                   meta_match_use_and=False):
        """
        list all the asset ids in the repo filtered on keywords, metadata, and uri_paths. Filters are performed as
        follows:

            Between types, the filter is always done as an "AND". For example, if the keyword filter is set and the
            metadata is set, then both need to be satisfied in order for the filter to be satisfied.

            Within a type, the filter may be done as an "OR" or "AND" depending on the match_use_and argument. For
            example, if more than one keyword is supplied and kw_match_use_and is set to False, then any asset that has
            ANY of the keywords will be included.

        :param uri:
                An optional URI to limit the list of assets returned. If None or a zero length string, then no filtering
                based on the URI is done. Defaults to None.
        :param keywords:
                An optional list of keywords to filter on. If None or a zero length list then no filtering based on
                keywords is done. Defaults to None.
        :param metadata_keys:
                An optional list of metadata keys. Defaults to None.
        :param metadata_keys_and_values:
                An optional list of metadata to filter on. Each element of this list must be a 3-item tuple. The first
                element is the metadata key, the second is the comparison_type (either >, <, =, or !=) and the third
                item is the value of the metadata. If None or an empty list then no filtering is done. Defaults to None.
        :param kw_match_use_and:
                An optional boolean that controls whether matches WITHIN keywords are done as OR matches or as AND
                matches. Defaults to False (which means OR matches).
        :param meta_match_use_and:
                An optional boolean that controls whether matches WITHIN metadata are done as OR matches or as AND
                matches. Defaults to False (which means OR matches).

        :return:
                A list containing all the asset paths.
        """

        assert uri is None or type(uri) is str
        assert keywords is None or type(keywords) is list
        assert metadata_keys is None or type(metadata_keys) is list
        assert metadata_keys_and_values is None or type(metadata_keys_and_values) is list
        if metadata_keys_and_values is not None:
            for item in metadata_keys_and_values:
                assert type(item) is tuple
                assert len(item) == 3
                assert item[1] in ["!=", "=", "<", ">", ">=", "<=", ""]
        assert type(kw_match_use_and) is bool

        uri_path = urilib.repo_path_from_uri(uri)
        asset_n = urilib.asset_name_from_uri(uri)

        asset_ids = list()

        # Filter by uri_path and asset name
        asset_ids.extend(self._asset_ids_from_uri_path(uri_path=uri_path,
                                                       asset_n=asset_n))

        # Filter by keywords
        if keywords is not None:
            keyword_asset_ids = self._asset_ids_from_keywords(keywords=keywords,
                                                              kw_match_use_and=kw_match_use_and)
            asset_ids = list(set(asset_ids) & set(keyword_asset_ids))

        # Filter by metadata keys
        if metadata_keys is not None:
            new_ids = self._asset_ids_from_metadata_keys(metadata_keys=metadata_keys,
                                                         meta_match_use_and=meta_match_use_and)
            asset_ids = list(set(asset_ids) & set(new_ids))

        # Filter by metadata keys and values
        if metadata_keys_and_values is not None:
            new_ids = self._asset_ids_from_metadata_key_and_values(metadata_keys_and_values=metadata_keys_and_values,
                                                                   meta_match_use_and=meta_match_use_and)
            asset_ids = list(set(asset_ids) & set(new_ids))

        return asset_ids

    # ------------------------------------------------------------------------------------------------------------------
    def list_asset_objs(self,
                        uri=None,
                        keywords=None,
                        metadata_keys=None,
                        metadata_key_and_values=None,
                        kw_match_use_and=False,
                        meta_match_use_and=False):
        """
        list all the asset objects in the repo. Optionally filter on keywords, metadata, and uri_paths. Filters are
        performed as follows:

            Between types, the filter is always done as an "AND". For example, if the keyword filter is set and the
            metadata is set, then both need to be satisfied in order for the filter to be satisfied.

            Within a type, the filter may be done as an "OR" or "AND" depending on the match_type_and argument. For
            example, if more than one keyword is supplied and match_type_and is set to False, then any asset that has
            ANY of the keywords will be included.

        :param uri:
                An optional URI to limit the list of assets returned. If None or a zero length string, then no filtering
                based on the URI is done. Defaults to None.
        :param keywords:
                An optional list of keywords to filter on. If None or a zero length list then no filtering based on
                keywords is done. Defaults to None.
        :param metadata_keys:
                An optional list of metadata keys to filter on. Defaults to None.
        :param metadata_key_and_values:
                An optional list of metadata to filter on. Each element of this list must be a 3-item tuple. The first
                element is the metadata key, the second is the comparison_type (either >, <, =, or !=) and the third
                item is the value of the metadata. If None or an empty list then no filtering is done. Defaults to None.
        :param kw_match_use_and:
                An optional boolean that controls whether matches WITHIN keywords are done as OR matches or as AND
                matches. Defaults to False (which means OR matches).
        :param meta_match_use_and:
                An optional boolean that controls whether matches WITHIN metadata are done as OR matches or as AND
                matches. Defaults to False (which means OR matches).

        :return:
                A list containing all the matching asset objects.
        """

        assert uri is None or type(uri) is str
        assert keywords is None or type(keywords) is list
        assert metadata_keys is None or type(metadata_keys) is list
        assert metadata_key_and_values is None or type(metadata_key_and_values) is list
        if metadata_key_and_values is not None:
            for item in metadata_key_and_values:
                assert type(item) is tuple
                assert len(item) == 3
                assert item[1] in ["!=", "=", "<", ">", ">=", "<=", ""]
        assert type(kw_match_use_and) is bool
        assert type(meta_match_use_and) is bool

        if not urilib.validate_uri_format(uri):
            err_msg = self.localized_resource_obj.get_error_msg(201)
            err_msg = err_msg.format(uri=uri)
            raise SquirrelError(err_msg, 201)

        output = list()

        asset_ids = self._asset_ids_from_attributes(uri=uri,
                                                    keywords=keywords,
                                                    metadata_keys=metadata_keys,
                                                    metadata_keys_and_values=metadata_key_and_values,
                                                    kw_match_use_and=kw_match_use_and,
                                                    meta_match_use_and=meta_match_use_and)

        sql = self.sql_resources.get("sql", "list_asset_objs_get_asset")
        sql = sql.format(range=",".join([str(i) for i in asset_ids]))
        rows = self.cursor.execute(sql, (self.repo_n,)).fetchall()

        for row in rows:

            if not os.path.exists(row[1]):
                err_msg = self.localized_resource_obj.get_error_msg(1234)
                err_msg = err_msg.format(asset_d=row[1])
                raise SquirrelError(err_msg, 1234)

            output.append(Asset(asset_parent_d=row[0],
                                name=row[2],
                                config_obj=self.config_obj,
                                localized_resource_obj=self.localized_resource_obj))

        return output

    # ------------------------------------------------------------------------------------------------------------------
    def asset_obj_from_uri(self,
                           uri):
        """
        Given a URI, return an asset object that lives at that location.

        :param uri:
                The full URI that identifies the asset (repo_name://uri_path/asset_name)

        :return:
                An asset object.
        """

        assert type(uri) is str

        sql = self.sql_resources.get("asset_obj_from_url", "asset_d_from_uri")
        rows = self.cursor.execute(sql, (uri,)).fetchall()

        if len(rows) == 0:
            err_msg = self.localized_resource_obj.get_error_msg(911)
            err_msg = err_msg.format(uri=uri)
            raise SquirrelError(err_msg, 911)

        if len(rows) > 1:
            err_msg = self.localized_resource_obj.get_error_msg(912)
            err_msg = err_msg.format(uri=uri)
            raise SquirrelError(err_msg, 912)

        asset_parent_d, asset_n = rows[0]

        if not os.path.isdir(asset_parent_d):
            err_msg = self.localized_resource_obj.get_error_msg(103)
            err_msg.format(asset_parent_d=asset_parent_d)
            raise SquirrelError(err_msg, 103)

        asset_obj = Asset(asset_parent_d=asset_parent_d,
                          name=asset_n,
                          config_obj=self.config_obj,
                          localized_resource_obj=self.localized_resource_obj)

        if not asset_obj.is_asset():
            err_msg = self.localized_resource_obj.get_error_msg(104)
            err_msg.format(dir_p=os.path.join(asset_parent_d, asset_n))
            raise SquirrelError(err_msg, 104)

        return asset_obj

    # ------------------------------------------------------------------------------------------------------------------
    def list_keywords(self,
                      uri):
        """
        Lists all of the keywords from the assets under the URI given by uri.

        :param uri:
                The URI to limit the results to. At the very minimum it must supply a repo name.

        :return:
                A list of keywords.
        """

        assert type(uri) is str

        if not urilib.validate_uri_format(uri):
            err_msg = self.localized_resource_obj.get_error_msg(201)
            err_msg = err_msg.format(uri=uri)
            raise SquirrelError(err_msg, 201)

        repo_n = urilib.repo_name_from_uri(uri)
        uri_path = urilib.repo_path_from_uri(uri)
        asset_n = urilib.asset_name_from_uri(uri)

        output = list()

        if asset_n:
            sql = self.sql_resources.get("list_keywords", "list_keywords_by_uri_path_and_name")
            rows = self.cursor.execute(sql, (repo_n, uri_path, asset_n)).fetchall()
        else:
            sql = self.sql_resources.get("list_keywords", "list_keywords_by_uri_path")
            rows = self.cursor.execute(sql, (repo_n, uri_path + "%")).fetchall()

        for row in rows:
            output.append(row[0])

        return output

    # ------------------------------------------------------------------------------------------------------------------
    def add_keywords(self,
                     uri,
                     keywords,
                     log_str=None):
        """
        Given a URI that uniquely identifies an asset, adds the list of keywords to that asset.

        :param uri:
                The full URI that identifies the asset (repo_name://uri_path#asset_name)
        :param keywords:
                A list of keywords to add. Keywords are case-insensitive.
        :param log_str:
                A string to append to the log. If None, nothing will be appended to the log. Defaults to None.

        :return:
                Nothing.
        """

        assert type(uri) is str
        assert type(keywords) is list

        if not urilib.validate_uri_format(uri):
            err_msg = self.localized_resource_obj.get_error_msg(201)
            err_msg = err_msg.format(uri=uri)
            raise SquirrelError(err_msg, 201)

        asset_obj = self.asset_obj_from_uri(uri)
        asset_obj.add_keywords(keywords=keywords,
                               log_str=log_str)

        # Get the full list of keywords (not just the ones being added) from the asset.
        keywords = asset_obj.list_keywords()

        asset_id = self._asset_id_from_uri(uri)
        self._flush_asset_keywords_from_cache(asset_id)
        for keyword in keywords:
            self._cache_keyword(asset_id=asset_id, keyword=keyword)

    # ------------------------------------------------------------------------------------------------------------------
    def delete_keywords(self,
                        uri,
                        keywords,
                        log_str=None):
        """
        Given a URI that uniquely identifies an asset, deletes any keywords in the list of keywords given.

        :param uri:
                The full URI that identifies the asset (repo_name://uri_path#asset_name)
        :param keywords:
                A list of keywords to delete. Keywords are case-insensitive.
        :param log_str:
                A string to append to the log. If None, nothing will be appended to the log. Defaults to None.


        :return:
                Nothing.
        """

        assert type(uri) is str
        assert type(keywords) is list

        if not urilib.validate_uri_format(uri):
            err_msg = self.localized_resource_obj.get_error_msg(201)
            err_msg = err_msg.format(uri=uri)
            raise SquirrelError(err_msg, 201)

        asset_obj = self.asset_obj_from_uri(uri)
        asset_obj.delete_keywords(keywords=keywords,
                                  log_str=log_str)

        # Get the full list of keywords (not just the ones being added) from the asset.
        keywords = asset_obj.list_keywords()

        asset_id = self._asset_id_from_uri(uri)
        self._flush_asset_keywords_from_cache(asset_id)
        for keyword in keywords:
            self._cache_keyword(asset_id=asset_id, keyword=keyword)

    # ------------------------------------------------------------------------------------------------------------------
    def delete_all_keywords(self,
                            uri,
                            log_str=None):
        """
        Given a URI that uniquely identifies an asset, deletes all keywords from that asset.

        :param uri:
                The full URI that identifies the asset (repo_name://uri_path#asset_name)
        :param log_str:
                A string to append to the log. If None, nothing will be appended to the log. Defaults to None.

        :return:
                Nothing.
        """

        assert type(uri) is str

        if not urilib.validate_uri_format(uri):
            err_msg = self.localized_resource_obj.get_error_msg(201)
            err_msg = err_msg.format(uri=uri)
            raise SquirrelError(err_msg, 201)

        asset_obj = self.asset_obj_from_uri(uri)

        keywords = asset_obj.list_keywords()
        asset_obj.delete_keywords(keywords=keywords,
                                  log_str=log_str)

        asset_id = self._asset_id_from_uri(uri)
        self._flush_asset_keywords_from_cache(asset_id)

    # ------------------------------------------------------------------------------------------------------------------
    def list_metadata_keys(self,
                           uri):
        """
        Lists all of the metadata keys from the assets under the URI given by uri. Metadata is in the format key=value.
        This lists ONLY the keys.

        :param uri:
                The URI to limit the results to. At the very minimum it must supply a repo name.

        :return:
                A list of keywords.
        """

        assert type(uri) is str

        if not urilib.validate_uri_format(uri):
            err_msg = self.localized_resource_obj.get_error_msg(201)
            err_msg = err_msg.format(uri=uri)
            raise SquirrelError(err_msg, 201)

        repo_n = urilib.repo_name_from_uri(uri)
        uri_path = urilib.repo_path_from_uri(uri)
        asset_n = urilib.asset_name_from_uri(uri)

        output = list()

        if asset_n:
            sql = self.sql_resources.get("list_metadata_keys", "list_metadata_keys_by_uri_path_and_name")
            rows = self.cursor.execute(sql, (repo_n, uri_path, asset_n)).fetchall()
        else:
            sql = self.sql_resources.get("list_metadata_keys", "list_metadata_keys_by_uri_path")
            rows = self.cursor.execute(sql, (repo_n, uri_path + "%")).fetchall()

        for row in rows:
            output.append(row[0])

        return output

    # ------------------------------------------------------------------------------------------------------------------
    def add_metadata(self,
                     uri,
                     metadata,
                     log_str=None):
        """
        Given a URI that uniquely identifies an asset, adds the list of metadata key value pairs to that asset.

        :param uri:
                The full URI that identifies the asset (repo_name://uri_path#asset_name)
        :param metadata:
                A list of metadata key=value pairs to add. Metadata (both keys and values) is case-insensitive.
       :param log_str:
                A string to append to the log. If None, nothing will be appended to the log. Defaults to None.

        :return:
                Nothing.
        """

        if metadata is None or not metadata:
            err_msg = self.localized_resource_obj.get_error_msg(1000)
            raise SquirrelError(err_msg, 1000)

        assert type(uri) is str
        assert type(metadata) is list

        for key_value_pair in metadata:
            if "=" not in key_value_pair:
                err_msg = self.localized_resource_obj.get_error_msg(150)
                raise SquirrelError(err_msg, 150)
            if " " in key_value_pair.split("=")[0]:
                err_msg = self.localized_resource_obj.get_error_msg(150)
                raise SquirrelError(err_msg, 150)

        if not urilib.validate_uri_format(uri):
            err_msg = self.localized_resource_obj.get_error_msg(201)
            err_msg = err_msg.format(uri=uri)
            raise SquirrelError(err_msg, 201)

        key_value_pairs = dict()
        for key_value_pair in metadata:
            key, value = key_value_pair.split("=")
            key_value_pairs[key] = value

        asset_obj = self.asset_obj_from_uri(uri)
        asset_obj.add_key_value_pairs(key_value_pairs=key_value_pairs,
                                      log_str=log_str)

        # Get the full list of metadata (not just the ones being added) from the asset.
        key_value_pairs = asset_obj.list_key_value_pairs()

        asset_id = self._asset_id_from_uri(uri)
        self._flush_asset_metadata_from_cache(asset_id)
        for key, value in key_value_pairs.items():
            self._cache_metadata(asset_id=asset_id, key=key, value=value)

    # ------------------------------------------------------------------------------------------------------------------
    def delete_metadata(self,
                        uri,
                        metadata_keys,
                        log_str=None):
        """
        Given a URI that uniquely identifies an asset, deletes any metadata in the list of metadata keys given.

        :param uri:
                The full URI that identifies the asset (repo_name://uri_path#asset_name)
        :param metadata_keys:
                A list of metadata keys to delete. Keys are case-insensitive.
       :param log_str:
                A string to append to the log. If None, nothing will be appended to the log. Defaults to None.

        :return:
                Nothing.
        """

        if metadata_keys is None or not metadata_keys:
            err_msg = self.localized_resource_obj.get_error_msg(1001)
            raise SquirrelError(err_msg, 1001)

        assert type(uri) is str
        assert type(metadata_keys) is list

        # TODO: Should the following check be on all of the user called functions?
        if not urilib.validate_uri_format(uri):
            err_msg = self.localized_resource_obj.get_error_msg(201)
            err_msg = err_msg.format(uri=uri)
            raise SquirrelError(err_msg, 201)

        asset_obj = self.asset_obj_from_uri(uri)
        asset_obj.delete_key_value_pairs(keys=metadata_keys,
                                         log_str=log_str)

        # Get the full list of metadata key value pairs (not just the ones being deleted) from the asset.
        key_value_pairs = asset_obj.list_key_value_pairs()

        asset_id = self._asset_id_from_uri(uri)
        self._flush_asset_metadata_from_cache(asset_id)
        for key, value in key_value_pairs.items():
            self._cache_metadata(asset_id=asset_id, key=key, value=value)

    # ------------------------------------------------------------------------------------------------------------------
    def delete_all_metadata(self,
                            uri,
                            log_str=None):
        """
        Given a URI that uniquely identifies an asset, deletes all metadata from the asset.

        :param uri:
                The full URI that identifies the asset (repo_name://uri_path#asset_name)
        :param log_str:
                A string to append to the log. If None, nothing will be appended to the log. Defaults to None.

        :return:
                Nothing.
        """

        assert type(uri) is str

        if not urilib.validate_uri_format(uri):
            err_msg = self.localized_resource_obj.get_error_msg(201)
            err_msg = err_msg.format(uri=uri)
            raise SquirrelError(err_msg, 201)

        asset_obj = self.asset_obj_from_uri(uri)
        keys = list(asset_obj.list_key_value_pairs().keys())
        asset_obj.delete_key_value_pairs(keys=keys,
                                         log_str=log_str)

        asset_id = self._asset_id_from_uri(uri)
        self._flush_asset_metadata_from_cache(asset_id)

    # ------------------------------------------------------------------------------------------------------------------
    def list_version_notes(self,
                           uri,
                           version_int=None):
        """
        Lists all of the notes from the asset given by the URI. If a version is given, then the notes will be taken from
        that version. If version is None, then the notes will be taken from the latest version.

        :param uri:
                The URI of the asset.
        :param version_int:
                The version number to retrieve notes from. If None, then the latest version is used. Defaults to None.

        :return:
                The notes as a string.
        """

        assert type(uri) is str
        assert version_int is None or type(version_int) is int

        asset_obj = self.asset_obj_from_uri(uri)

        return asset_obj.list_version_notes(version_int=version_int)

    # ------------------------------------------------------------------------------------------------------------------
    def add_version_notes(self,
                          notes,
                          uri,
                          version_int=None,
                          overwrite=False,
                          log_str=None):
        """
        Adds notes to the asset defined by the URI and version. Notes are stored on the version level.

        :param notes:
                A string to add to the asset.
        :param uri:
                The asset URI.
        :param version_int:
                The version number on which to set the notes. If None, then the latest version will be used. Defaults to
                None.
        :param overwrite:
                If True, then the notes will overwrite the current set of notes, otherwise they will be appended.
                Defaults to False.
        :param log_str:
                A string to append to the log. If None, nothing will be appended to the log. Defaults to None.

        :return:
                Nothing.
        """

        assert type(notes) is str
        assert type(uri) is str
        assert version_int is None or type(version_int) is int
        assert type(overwrite) is bool
        assert log_str is None or type(log_str) is str

        asset_obj = self.asset_obj_from_uri(uri)
        asset_obj.add_version_notes(version_int=version_int,
                                    notes=notes,
                                    overwrite=overwrite,
                                    log_str=log_str)

    # ------------------------------------------------------------------------------------------------------------------
    def delete_version_notes(self,
                             uri,
                             version_int=None,
                             log_str=None):
        """
        Deletes all of the notes from the asset given by the URI.

        :param uri:
                The URI of the asset.
        :param version_int:
                The version number from which to delete the notes. If None, then the latest version will be used.
                Defaults to None.
        :param log_str:
                A string to append to the log. If None, nothing will be appended to the log. Defaults to None.

        :return:
                The notes as a string.
        """

        assert type(uri) is str

        asset_obj = self.asset_obj_from_uri(uri)
        asset_obj.delete_version_notes(version_int=version_int,
                                       log_str=log_str)

    # ------------------------------------------------------------------------------------------------------------------
    def list_asset_notes(self,
                         uri):
        """
        Lists all of the notes from the asset given by the URI.

        :param uri:
                The URI of the asset.

        :return:
                The notes as a string.
        """

        assert type(uri) is str

        asset_obj = self.asset_obj_from_uri(uri)

        return asset_obj.list_asset_notes()

    # ------------------------------------------------------------------------------------------------------------------
    def add_asset_notes(self,
                        notes,
                        uri,
                        overwrite=False,
                        log_str=None):
        """
        Adds notes to the asset defined by the URI and version. Notes are stored on the asset level.

        :param notes:
                A string to add to the asset.
        :param uri:
                The asset URI.
        :param overwrite:
                If True, then the notes will overwrite the current set of notes, otherwise they will be appended.
                Defaults to False.
        :param log_str:
                A string to append to the log. If None, nothing will be appended to the log. Defaults to None.

        :return:
                Nothing.
        """

        assert type(notes) is str
        assert type(uri) is str
        assert type(overwrite) is bool
        assert log_str is None or type(log_str) is str

        asset_obj = self.asset_obj_from_uri(uri)
        asset_obj.add_asset_notes(notes=notes,
                                  overwrite=overwrite,
                                  log_str=log_str)

    # ------------------------------------------------------------------------------------------------------------------
    def delete_asset_notes(self,
                           uri,
                           log_str=None):
        """
        Deletes all of the notes from the asset given by the URI.

        :param uri:
                The URI of the asset.
        :param log_str:
                A string to append to the log. If None, nothing will be appended to the log. Defaults to None.

        :return:
                The notes as a string.
        """

        assert type(uri) is str

        asset_obj = self.asset_obj_from_uri(uri)
        asset_obj.delete_asset_notes(log_str=log_str)

    # ------------------------------------------------------------------------------------------------------------------
    def add_thumbnails(self,
                       uri,
                       thumbnails_p,
                       poster_p,
                       version_int=None,
                       log_str=None):
        """
        Adds thumbnails to the asset defined by the URI and version.

        :param uri:
                The asset URI.
        :param thumbnails_p:
                A list of file paths of the thumbnail files.
        :param poster_p:
                A path to the poster file.
        :param version_int:
                The version number to which the thumbnails should be added. If None, then the latest version will be
                used. Defaults to None.
        :param log_str:
                A string to append to the log. If None, nothing will be appended to the log. Defaults to None.

        :return:
                Nothing.
        """

        assert type(uri) is str
        assert type(thumbnails_p) is list
        assert type(poster_p) is str
        assert version_int is None or type(version_int) is int
        assert log_str is None or type(log_str) is str

        asset_obj = self.asset_obj_from_uri(uri)
        asset_obj.add_thumbnails(thumbnails_p=thumbnails_p,
                                 poster_p=poster_p,
                                 version_int=version_int,
                                 log_str=log_str)

    # ------------------------------------------------------------------------------------------------------------------
    def delete_thumbnails(self,
                          uri,
                          version_int,
                          log_str=None):
        """
        Deletes thumbnails from the asset defined by the URI and version.

        :param uri:
                The asset URI.
        :param version_int:
                The version number from which the thumbnails should be deleted.
        :param log_str:
                A string to append to the log. If None, nothing will be appended to the log. Defaults to None.

        :return:
                Nothing.
        """

        assert type(uri) is str
        assert version_int is None or type(version_int) is int
        assert log_str is None or type(log_str) is str

        asset_obj = self.asset_obj_from_uri(uri)
        asset_obj.delete_thumbnails(version_int=version_int,
                                    log_str=log_str)

    # ------------------------------------------------------------------------------------------------------------------
    def set_pin(self,
                uri,
                pin_n,
                version_int,
                log_str=None):
        """
        Sets the pin on the given asset.

        :param uri:
                The URI of the asset.
        :param pin_n:
                The pin to set.
        :param version_int:
                The version number that the pin should point to.
        :param log_str:
                A string to append to the log. If None, nothing will be appended to the log. Defaults to None.

        :return:
                Nothing.
        """

        assert type(uri) is str
        assert type(pin_n) is str
        assert type(version_int) is str
        assert log_str is None or type(log_str) is str

        asset_obj = self.asset_obj_from_uri(uri)
        asset_obj.set_pin(pin_n=pin_n,
                          version_int=version_int,
                          locked=False,
                          allow_delete_locked=False,
                          log_str=log_str)

    # ------------------------------------------------------------------------------------------------------------------
    def delete_pin(self,
                   uri,
                   pin_n,
                   allow_delete_locked,
                   log_str=None):
        """
        Deletes the pin on the given asset.

        :param uri:
                The URI of the asset.
        :param pin_n:
                The pin to set.
        :param allow_delete_locked:
                If True, allow the deletion of locked pins. If False, locked pins may not be deleted.
        :param log_str:
                A string to append to the log. If None, nothing will be appended to the log. Defaults to None.

        :return:
                Nothing.
        """

        assert type(uri) is str
        assert type(pin_n) is str
        assert log_str is None or type(log_str) is str

        asset_obj = self.asset_obj_from_uri(uri)
        asset_obj.delete_pin(pin_n=pin_n,
                             allow_delete_locked=allow_delete_locked,
                             log_str=log_str)

    # ------------------------------------------------------------------------------------------------------------------
    def lock_pin(self,
                 uri,
                 pin_n,
                 log_str=None):
        """
        Locks the pin on the given asset.

        :param uri:
                The URI of the asset.
        :param pin_n:
                The pin to set.
        :param log_str:
                A string to append to the log. If None, nothing will be appended to the log. Defaults to None.

        :return:
                Nothing.
        """

        assert type(uri) is str
        assert type(pin_n) is str
        assert log_str is None or type(log_str) is str

        asset_obj = self.asset_obj_from_uri(uri)
        asset_obj.lock_pin(pin_n=pin_n,
                           log_str=log_str)

    # ------------------------------------------------------------------------------------------------------------------
    def unlock_pin(self,
                   uri,
                   pin_n,
                   log_str=None):
        """
        Unlocks the pin on the given asset.

        :param uri:
                The URI of the asset.
        :param pin_n:
                The pin to set.
        :param log_str:
                A string to append to the log. If None, nothing will be appended to the log. Defaults to None.

        :return:
                Nothing.
        """

        assert type(uri) is str
        assert type(pin_n) is str
        assert log_str is None or type(log_str) is str

        asset_obj = self.asset_obj_from_uri(uri)
        asset_obj.unlock_pin(pin_n=pin_n,
                             log_str=log_str)

    # ------------------------------------------------------------------------------------------------------------------
    def _is_file_list(self,
                      items):
        """
        Given a list of items that are either files or a directory, determine whether it is a list of files or a single
        directory. Also verify that it is not a mix of the two and, if it is a directory, there is only a single entry.

        :param items:
                A list of files or a list of a single directory. May not mix both types. May not be more than one
                directory if it is a directory.

        :return:
                True if it is a list of files. False if it is a single directory.
        """

        item_types = None
        for item in items:
            if not os.path.exists(item):
                err_msg = self.localized_resource_obj.get_error_msg(2000)
                err_msg = err_msg.format(file_p=item)
                raise SquirrelError(err_msg, 2000)
            if os.path.isfile(item):
                if not item_types:
                    item_types = "file"
                elif item_types != "file":
                    err_msg = self.localized_resource_obj.get_error_msg(2001)
                    raise SquirrelError(err_msg, 2001)
            elif os.path.isdir(item):
                if not item_types:
                    item_types = "dir"
                elif item_types != "dir":
                    err_msg = self.localized_resource_obj.get_error_msg(2001)
                    raise SquirrelError(err_msg, 2001)
                if len(items) > 1:
                    err_msg = self.localized_resource_obj.get_error_msg(2002)
                    raise SquirrelError(err_msg, 2002)

        return item_types == "file"

    # ------------------------------------------------------------------------------------------------------------------
    def publish(self,
                uri,
                items,
                merge,
                do_verified_copy,
                link_in_place=False,
                log_str=None):
        """
        Publishes a set of files or directory to an asset.

        :param uri:
                The URI of the asset.
        :param items:
                A list of items to publish. Either a list of files, or a single directory. May not be a mix of files and
                directories. May not be multiple directories.
        :param merge:
                If True, then merge the current publish with any files that were in the previous version (if there was a
                previous version).
        :param do_verified_copy:
                If True, then each file will be verified that it copied correctly by using an md5 checksum.
        :param link_in_place:
                If True, then the files will not be copied, but instead symlinks to the original files will be published
                instead. Defaults to False.
        :param log_str:
                A string to append to the log. If None, nothing will be appended to the log. Defaults to None.

        :return:
                Nothing.
        """

        assert type(uri) is str
        assert type(items) is list

        if self._is_file_list(items):
            copydescriptors = bvzversionedfiles.file_list_to_copydescriptors(items=items,
                                                                             relative_d=None,
                                                                             link_in_place=link_in_place)
        else:
            copydescriptors = bvzversionedfiles.directory_to_copydescriptors(dir_d=items[0],
                                                                             link_in_place=link_in_place)

        uri_path = uri.split(":/")[1].split("#")[0]
        asset_n = uri.split(":/")[1].split("#")[1]

        asset_parent_d = self._get_publish_path(uri_path)
        asset_obj = Asset(asset_parent_d=asset_parent_d,
                          name=asset_n,
                          config_obj=self.config_obj,
                          localized_resource_obj=self.localized_resource_obj)

        asset_obj.store(copydescriptors=copydescriptors,
                        merge=merge,
                        verify_copy=do_verified_copy,
                        log_str=log_str)

        # TODO: Have to update the cache with this newly published asset/version.

    # ------------------------------------------------------------------------------------------------------------------
    def collapse(self,
                 uri,
                 log_str=None):
        """
        Removes all versions from an asset except the latest version.

        :param uri:
                The URI of the asset.
        :param log_str:
                A string to append to the log. If None, nothing will be appended to the log. Defaults to None.

        :return:
                Nothing.
        """

        assert type(uri) is str

        uri_path = uri.split(":/")[1].split("#")[0]
        asset_n = uri.split(":/")[1].split("#")[1]

        asset_parent_d = self._get_publish_path(uri_path)
        asset_obj = Asset(asset_parent_d=asset_parent_d,
                          name=asset_n,
                          config_obj=self.config_obj,
                          localized_resource_obj=self.localized_resource_obj)

        asset_obj.collapse(log_str=log_str)

        # TODO: Have to update the cache with this newly published asset/version.

    # ------------------------------------------------------------------------------------------------------------------
    def _get_publish_path(self,
                          uri_path):
        """
        Returns the path where an asset should be stored based on its uri_path.

        :param uri_path:
                The uri_path that defines where in the repo structure to publish.

        :return:
                Nothing
        """

        if not self._uri_path_is_valid(uri_path):
            err_msg = self.localized_resource_obj.get_error_msg(201)
            err_msg = err_msg.format(uri_path=uri_path)
            raise SquirrelError(err_msg, 201)

        if not self._uri_path_is_leaf(uri_path):
            err_msg = self.localized_resource_obj.get_error_msg(202)
            err_msg = err_msg.format(pub_path=self._file_path_from_uri_path(uri_path))
            raise SquirrelError(err_msg, 202)

        return self._file_path_from_uri_path(uri_path)
