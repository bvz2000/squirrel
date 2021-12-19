import os

from squirrel.shared.squirrelerror import SquirrelError
from bvzlocalization import LocalizedResource


class KeyValuePairs(object):
    """
    A class to manage a specific metadata (key=value pairs) file within an asset.
    """

    # ------------------------------------------------------------------------------------------------------------------
    def __init__(self,
                 resources_obj,
                 asset_d):
        """
        Set up instance to hold the path to the keywords file.
        """

        assert type(resources_obj) is LocalizedResource
        assert type(asset_d) is str

        self.localized_resource_obj = resources_obj

        self.asset_d = asset_d
        self.keyvalues_p = os.path.join(asset_d, ".metadata", "keyvalues")

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
    def _verify_key_value_file_exists(self):
        """
        Checks to make sure the key value file exists.

        :return:
                Nothing.
        """

        if not os.path.exists(self.keyvalues_p):
            err_msg = self.localized_resource_obj.get_error_msg(11109)
            raise SquirrelError(err_msg, 11109)

    # ------------------------------------------------------------------------------------------------------------------
    def add_key_value_pairs(self,
                            key_value_pairs):
        """
        Adds key value pairs to the keyvalues metadata file.

        :param key_value_pairs:
                The dict of key value pairs to add.

        :return:
                Nothing.
        """

        assert type(key_value_pairs) is dict

        self._verify_asset_dir_exists()

        try:
            existing_keys = self.get_key_value_pairs()
        except SquirrelError:
            existing_keys = dict()

        for key, value in key_value_pairs.items():
            existing_keys[key.upper()] = value

        with open(self.keyvalues_p, "w") as f:
            for key, value in existing_keys.items():
                f.write(key + "=" + value + "\n")

    # ------------------------------------------------------------------------------------------------------------------
    def remove_key_value_pairs(self,
                               keys):
        """
        Removes key value pairs from the keyvalues metadata file.

        :param keys:
                The list of keys to remove.

        :return:
                Nothing.
        """

        self._verify_asset_dir_exists()

        assert type(keys) is list or type(keys) is str

        if type(keys) is str:
            keys = [keys]

        for i in range(len(keys)):
            keys[i] = keys[i].upper()

        existing_key_value_pairs = self.get_key_value_pairs()

        with open(self.keyvalues_p, "w") as f:
            for existing_key, value in existing_key_value_pairs.items():
                if existing_key.strip().upper() not in keys:
                    f.write(existing_key.strip().upper() + "=" + value + "\n")

    # ------------------------------------------------------------------------------------------------------------------
    def get_key_value_pairs(self):
        """
        Returns a dictionary of key value pairs from the keyvalues metadata file.

        :return:
                A dictionary of key value pairs.
        """

        self._verify_key_value_file_exists()

        with open(self.keyvalues_p, "r") as f:
            lines = f.readlines()

        output = dict()
        for line in lines:
            output[line.split("=", 1)[0]] = line.split("=", 1)[1].rstrip()

        return output
