import os.path
import sys

from squirrel.schema import repo


# ==============================================================================
class AssetData(object):
    """
    An object that stores all of the data for a single asset.
    """

    def __init__(self,
                 asset_n,
                 asset_p):
        """
        Set up the asset.

        :param asset_n: The name of the asset
        :param asset_p: The path to the asset on disk
        """

        self.asset_n = asset_n
        self.asset_p = asset_p

        self.keywords = list()
        self.metadata = dict()
        self.notes = ""

    # --------------------------------------------------------------------------
    def load_keywords(self,
                      version=None):
        """
        Loads the keywords from the asset.

        :param version: The version to load keywords from. If None, it will
               default to CURRENT.

        :return: Nothing.
        """

        if not version:
            version = ".CURRENT"
        else:
            version = "." + version

        version_p = os.path.join(self.asset_p, version)
        if not os.path.exists(version_p):
            print("Error: the version", version, "does not exist")
            sys.exit(1)

        keywords_p = os.path.join(version_p, "keywords")
        with open(keywords_p, "r") as f:
            self.keywords = f.readlines()
        for i in range(len(self.keywords)):
            self.keywords[i] = self.keywords[i].rstrip("\n")

    # --------------------------------------------------------------------------
    def load_metadata(self,
                      version=None):
        """
        Loads the metadata from the asset.

        :param version: The version to load keywords from. If None, it will
               default to CURRENT.

        :return: Nothing.
        """

        if not version:
            version = ".CURRENT"
        else:
            version = "." + version

        version_p = os.path.join(self.asset_p, version)
        if not os.path.exists(version_p):
            print("Error: the version", version, "does not exist")
            sys.exit(1)

        metadata_p = os.path.join(version_p, "metadata")
        with open(metadata_p, "r") as f:
            metadata = f.readlines()
        for i in range(len(metadata)):
            metadata[i] = metadata[i].rstrip("\n")

        for metadata_item in metadata:
            key, value = metadata_item.split("=")
            self.metadata[key.strip()] = value.strip()

    # --------------------------------------------------------------------------
    def load_notes(self,
                   version=None):
        """
        Loads the notes from the asset.

        :param version: The version to load keywords from. If None, it will
               default to CURRENT.

        :return: Nothing.
        """

        if not version:
            version = ".CURRENT"
        else:
            version = "." + version

        version_p = os.path.join(self.asset_p, version)
        if not os.path.exists(version_p):
            print("Error: the version", version, "does not exist")
            sys.exit(1)

        notes_p = os.path.join(version_p, "notes")
        with open(notes_p, "r") as f:
            self.notes = f.readlines()
        for i in range(len(self.notes)):
            self.notes[i] = self.notes[i].rstrip("\n")


# ==============================================================================
class RepoDatabase(object):
    """
    An object that lives in memory and stores all of the information for a
    single repo.
    """

    # --------------------------------------------------------------------------
    def __init__(self,
                 repo_p):
        """
        Open up the repo

        :param repo_p: The path to the repo to store.
        """

        self.repo_p = repo_p
        self.repo_obj = repo.Repo(repo_p)

        self.assets = dict()
        self.keywords = dict()
        self.metadata = dict()

    # --------------------------------------------------------------------------
    def load_data(self,
                  smart_refresh=False):
        """
        Forces the system to read all of the data from the repo.

        :param smart_refresh: If True, then only those files that have a
               timestamp newer than the last read will be processed.

        :return: Nothing.
        """

        asset_paths = self.repo_obj.list_asset_paths()

        for asset_p in asset_paths:
            asset_n = os.path.split(asset_p)[1]
            asset = AssetData(asset_n, asset_p)
            asset.load_keywords()
            asset.load_metadata()
            asset.load_notes()

            self.add_keywords(asset)
            self.add_metadata(asset)

            self.assets[asset_n] = asset

    # --------------------------------------------------------------------------
    def refresh_asset(self,
                      asset_n):
        """
        Refreshes the data for the asset named asset_n.

        :param asset_n: The name of the asset to refresh.

        :return: Nothing.
        """

        pass

    # --------------------------------------------------------------------------
    def add_keywords(self,
                     asset_n):
        """
        Adds the keywords from the passed asset to the list of keywords for the
        repo.

        :param asset_n: The name of the asset to refresh.

        :return: Nothing.
        """

        for asset in self.assets:
            for keyword in asset.keywords:
                try:
                    self.keywords[keyword] = self.keywords[keyword].append(asset.asset_n)
                except KeyError:
                    self.keywords[keyword] = [asset.asset_n]

    # --------------------------------------------------------------------------
    def add_metadata(self,
                     asset_n):
        """
        Adds the metadata from the passed asset to the list of keywords for the
        repo. This ONLY adds the metadata keys (as though they were keywords).

        :param asset_n: The name of the asset to refresh.

        :return: Nothing.
        """

        # TODO: this needs to strip out the keys
        for asset in self.assets:
            for metadata in asset.keywords:
                try:
                    self.keywords[metadata] = self.keywords[metadata].append(asset.asset_n)
                except KeyError:
                    self.keywords[metadata] = [asset.asset_n]

    # --------------------------------------------------------------------------
    def get_asset_from_name(self,
                            asset_n):
        """
        Returns the asset_data object from the name of the asset.

        :param asset_n: The name of the asset to refresh.

        :return: An asset data object.
        """


        pass
