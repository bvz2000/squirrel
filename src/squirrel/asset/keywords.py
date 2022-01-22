import os

from squirrel.shared.squirrelerror import SquirrelError
from bvzlocalization import LocalizedResource


class Keywords(object):
    """
    A class to manage a specific keywords file within an asset.
    """

    # ------------------------------------------------------------------------------------------------------------------
    def __init__(self,
                 localized_resources_obj,
                 asset_d):
        """
        Set up instance to hold the path to the keywords file.
        """

        assert type(localized_resources_obj) is LocalizedResource
        assert type(asset_d) is str

        self.localized_resource_obj = localized_resources_obj

        self.asset_d = asset_d
        self.keywords_p = os.path.join(asset_d, ".metadata", "keywords")

    # ------------------------------------------------------------------------------------------------------------------
    def _verify_asset_dir_exists(self):
        """
        Checks to make sure the asset directory exists.

        :return:
                Nothing.
        """

        if not os.path.exists(self.asset_d):
            err_msg = self.localized_resource_obj.get_error_msg(11208)
            raise SquirrelError(err_msg, 11208)

    # ------------------------------------------------------------------------------------------------------------------
    def _verify_metadata_dir_exists(self):
        """
        Checks to make sure the metadata directory exists.

        :return:
                Nothing.
        """

        if not os.path.exists(os.path.join(self.asset_d, ".metadata")):
            err_msg = self.localized_resource_obj.get_error_msg(10010)
            raise SquirrelError(err_msg, 10010)

    # ------------------------------------------------------------------------------------------------------------------
    def _verify_keywords_file_exists(self):
        """
        Checks to make sure the keywords file exists.

        :return:
                Nothing.
        """

        if not os.path.exists(self.keywords_p):
            err_msg = self.localized_resource_obj.get_error_msg(11108)
            raise SquirrelError(err_msg, 11108)

    # ------------------------------------------------------------------------------------------------------------------
    def add_keywords(self,
                     keywords):
        """
        Adds keywords to the "keywords" metadata file.

        :param keywords:
                The list of keywords to add.

        :return:
                Nothing.
        """

        assert type(keywords) is list
        for keyword in keywords:
            assert type(keyword) is str

        self._verify_asset_dir_exists()
        self._verify_metadata_dir_exists()

        try:
            existing_keywords = self.list_keywords()
        except SquirrelError:
            existing_keywords = list()

        keywords.sort()
        if not os.path.exists(self.keywords_p):
            write_style = "w"
        else:
            write_style = "a"

        with open(self.keywords_p, write_style) as f:
            for keyword in keywords:
                if not keyword.upper() in [kw.upper() for kw in existing_keywords]:
                    f.write(keyword.upper() + "\n")

    # ------------------------------------------------------------------------------------------------------------------
    def remove_keywords(self,
                        keywords):
        """
        Removes keywords from the "keywords" metadata file.

        :param keywords:
                The list of keywords to remove.

        :return:
                Nothing.
        """

        self._verify_asset_dir_exists()

        assert type(keywords) is list
        for keyword in keywords:
            assert type(keyword) is str

        for i in range(len(keywords)):
            keywords[i] = keywords[i].upper()

        existing_keywords = self.list_keywords()

        with open(self.keywords_p, "w") as f:
            for existing_keyword in existing_keywords:
                if existing_keyword.strip().upper() not in keywords:
                    f.write(existing_keyword.strip().upper() + "\n")

    # ------------------------------------------------------------------------------------------------------------------
    def list_keywords(self):
        """
        Lists keywords from the "keywords" metadata file.

        :return:
                A list of keywords.
        """

        self._verify_keywords_file_exists()

        with open(self.keywords_p, "r") as f:
            lines = f.readlines()

        return [x.rstrip() for x in lines]
