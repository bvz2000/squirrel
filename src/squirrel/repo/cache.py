import inspect
import os
import sqlite3

from bvzframespec import Framespec

from squirrel.asset.asset import Asset
from squirrel.shared.squirrelerror import SquirrelError
from squirrel.shared import constants
from squirrel.shared import urilib
from squirrel.shared import setupsql


# ======================================================================================================================
class Cache(object):

    """
    The Cache class is responsible for caching all of the repositories to a sqlite3 database. This data is strictly used
    for data access speed. If this data becomes corrupt or the database is deleted, a new one can be generated from the
    actual repository and asset data on disk.
    """

    # ------------------------------------------------------------------------------------------------------------------
    def __init__(self,
                 config_obj,
                 localized_resource_obj):
        """
        Set up the cache object.
        """

        self.config_obj = config_obj
        self.localized_resource_obj = localized_resource_obj

        self.cache_d = self._cache_dir()
        self._validate_cache_d()
        self.cache_p = self._cache_path()

        self.sql_resources = setupsql.create_sql_object()
        self.connection = self._connect()
        self.cursor = self.connection.cursor()

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

        sql = self.sql_resources.get("drop_all_cache_tables", "list_tables")
        tables = self.cursor.execute(sql).fetchall()

        sql = self.sql_resources.get("drop_all_cache_tables", "drop_tables")
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
    def _flush_repo_from_cache(self,
                               repo_n):
        """
        Removes all of the elements from the cache that pertain to the given repo.

        :param repo_n:
                The name of the repo to be flushed.

        :return:
                Nothing.
        """

        assert type(repo_n) is str

        sql = self.sql_resources.get("sql", "flush_repo_from_cache_list_asset_ids")
        asset_ids = self.cursor.execute(sql, (repo_n,)).fetchall()
        asset_ids = [item[0] for item in asset_ids]

        for asset_id in asset_ids:
            self._flush_asset_from_cache(asset_id=asset_id)

    # ------------------------------------------------------------------------------------------------------------------
    def _flush_all_repos_from_cache(self,
                                    repos_n):
        """
        Removes all of the elements from all repos from the cache.

        :param repos_n:
                A list of repo names.

        :return:
                Nothing.
        """

        assert type(repos_n) is list
        for repo_n in repos_n:
            assert type(repo_n) is str

        for repo_n in repos_n:
            self._flush_repo_from_cache(repo_n)

    # ------------------------------------------------------------------------------------------------------------------
    def _cache_keyword_by_asset_id(self,
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
    def cache_keywords_by_uri(self,
                              uri,
                              keywords):
        """
        Given a URI and some keywords, cache those keywords.

        :param uri:
                The URI for which we want to cache the keywords.
        :param keywords:
                The list of keywords to cache.
        """

        assert type(uri) is str
        assert type(keywords) is list

        asset_id = self._asset_id_from_uri(uri)
        self._flush_asset_keywords_from_cache(asset_id)
        for keyword in keywords:
            self._cache_keyword_by_asset_id(asset_id=asset_id, keyword=keyword)

    # ------------------------------------------------------------------------------------------------------------------
    def _cache_metadata_by_asset_id(self,
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
    def cache_metadata_by_uri(self,
                              uri,
                              key_value_pairs):
        """
        Given a URI and some keywords, cache those keywords.

        :param uri:
                The URI for which we want to cache the keywords.
        :param key_value_pairs:
                The dictionary of metadata to cache.
        """

        assert type(uri) is str
        assert type(key_value_pairs) is dict

        asset_id = self._asset_id_from_uri(uri)
        self._flush_asset_metadata_from_cache(asset_id)
        for key, value in key_value_pairs.items():
            self._cache_metadata_by_asset_id(asset_id=asset_id, key=key, value=value)

    # ------------------------------------------------------------------------------------------------------------------
    def _cache_thumbnail(self,
                         version_int,
                         thumbnail_p,
                         asset_id):
        """
        Caches the paths to the thumbnails for a singe version (and asset_id).

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
        Caches the poster path for a specific version (and asset_id).

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
                    repo_obj,
                    asset_obj):
        """
        Stores the cached data for a single asset in the cache database.

        :param repo_obj:
                The repo object that contains the asset.
        :param asset_obj:
                The asset we are caching.

        :return:
                Nothing.
        """

        # self.connection.set_trace_callback(print)

        uri_path = repo_obj.uri_path_from_file_path(asset_obj.asset_d)
        uri = f"{repo_obj.repo_n}:/{uri_path}#{asset_obj.asset_n}"

        sql = self.sql_resources.get("cache_asset", "insert_into_assets")
        self.cursor.execute(sql, (uri,
                                  uri_path,
                                  repo_obj.repo_n,
                                  asset_obj.asset_n,
                                  asset_obj.asset_parent_d,
                                  asset_obj.asset_d))
        last_row_id = self.cursor.lastrowid

        sql = self.sql_resources.get("cache_asset", "asset_id_from_last_row_id")
        asset_id = self.cursor.execute(sql, (last_row_id,)).fetchone()[0]
        self.connection.commit()

        for keyword in asset_obj.list_keywords():
            self._cache_keyword_by_asset_id(keyword=keyword,
                                            asset_id=asset_id)

        for key, value in asset_obj.list_key_value_pairs().items():
            self._cache_metadata_by_asset_id(key=key,
                                             value=value,
                                             asset_id=asset_id)

        self._cache_thumbnails(asset_id=asset_id)

        self._cache_posters(asset_id=asset_id)

        # connection.set_trace_callback(None)

    # ------------------------------------------------------------------------------------------------------------------
    def cache_repo(self,
                   repo_obj):
        """
        Loads all the assets in the repo from the filesystem and into a sqlite3 database.

        :param repo_obj:
                The repo object being cached.

        :return:
                Nothing.
        """

        self._flush_repo_from_cache(repo_obj.repo_n)

        asset_objs = repo_obj.list_asset_objs_from_filesystem()
        for asset_obj in asset_objs:
            self.cache_asset(repo_obj=repo_obj,
                             asset_obj=asset_obj)

    # ------------------------------------------------------------------------------------------------------------------
    def cache_all_repos(self,
                        repo_objs):
        """
        Builds the cache from the data on the filesystem for all repos. If the cache already exists, the current data
        will be removed and replaced.

        :param repo_objs:
                A list of all repo objects.

        :return:
                Nothing.
        """

        self._build_cache_tables()

        for repo_obj in repo_objs:
            self.cache_repo(repo_obj)

    # ------------------------------------------------------------------------------------------------------------------
    def cache_if_needed(self,
                        repo_objs):
        """
        If the cache does not exist, or if any table is missing, create a new cache. If it does exist and all the tables
        are good, do nothing.

        :param repo_objs:
                A list of all repo objects.

        :return:
                Nothing.
        """

        # If the cache does not already exist, build a whole new cache.
        if not os.path.exists(self.cache_p):
            self.cache_all_repos(repo_objs)
            return

        tables = self.sql_resources.get("tables", "tables").split(",")
        sql = self.sql_resources.get("drop_all_cache_tables", "list_tables")
        rows = self.cursor.execute(sql).fetchall()

        # If there are no tables, build a whole new cache.
        if len(rows) == 0:
            self.cache_all_repos(repo_objs)

        # Check to see if any tables are missing. If any are missing, build a whole new cache.
        for row in rows:
            if row[0] not in tables:
                self.cache_all_repos(repo_objs)
                return

    # ------------------------------------------------------------------------------------------------------------------
    def validate_uri_path_against_cache(self,
                                        repo_n,
                                        uri_path):
        """
        Given a uri_path, validate it against the cache. If it is not valid, raise an error.

        :param repo_n:
                The repo name.
        :param uri_path:
                The path we are validating.

        :return:
                Nothing.
        """

        sql = self.sql_resources.get("disambiguate_uri", "uri_path_exists")
        rows = self.cursor.execute(sql, (repo_n, uri_path + "%")).fetchall()
        if len(rows) == 0:
            err_msg = self.localized_resource_obj.get_error_msg(907)
            err_msg = err_msg.format(uri_path=uri_path)
            raise SquirrelError(err_msg, 907)

    # ------------------------------------------------------------------------------------------------------------------
    def uri_path_from_asset_name(self,
                                 repo_n,
                                 asset_n):
        """
        Given a uri_path, validate it against the cache. If it is not valid, raise an error. If it is valid, return the
        uri_path.

        :param repo_n:
                The repo name.
        :param asset_n:
                The asset name.

        :return:
                The uri path.
        """

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

        # If no uri path match this asset name
        if len(rows) == 0:
            err_msg = self.localized_resource_obj.get_error_msg(908)
            err_msg = err_msg.format(asset_n=asset_n)
            raise SquirrelError(err_msg, 908)

        # If more than one uri paths match this name
        if len(rows) > 1:
            err_msg = self.localized_resource_obj.get_error_msg(909)
            err_msg = err_msg.format(asset_n=asset_n)
            raise SquirrelError(err_msg, 909)

        return rows[0][0]

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
    def metadata_keys_from_uri(self,
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
    def list_keywords_by_uri(self,
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
    def asset_parent_d_and_name_from_uri(self,
                                         uri):
        """
        Given a URI, return tuple containing the asset parent_d and asset_n.

        :param uri:
                The full URI that identifies the asset (repo_name://uri_path/asset_name)

        :return:
                A tuple containing the asset parent_d and asset_n.
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

        return asset_parent_d, asset_n

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
    def asset_ids_from_attributes(self,
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
    def asset_location_data_from_asset_ids(self,
                                           repo_n,
                                           asset_ids):
        """
        Given a repo name and a list of asset ids, return a list of tuples containing the parent_d, asset_d, asset_n,
        and uri_path of the asset.

        :param repo_n:
                The name of the repo.
        :param asset_ids:
                The list of asset id's.

        :return:
                A list of tuples containing: parent_d, asset_d, asset_n, uri_path
        """

        sql = self.sql_resources.get("sql", "list_asset_objs_get_asset")
        sql = sql.format(range=",".join([str(i) for i in asset_ids]))

        return self.cursor.execute(sql, (repo_n,)).fetchall()
