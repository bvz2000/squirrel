import os
import pathlib
import re


# ----------------------------------------------------------------------------------------------------------------------
def validate_uri_format(uri):
    """
    Given a URI, validates that it matches the basic structure of a legal URI. Does not validate that the URI
    actually exists.

    :param uri:
            The uri to be validated.

    :return:
            True if the uri is valid. False otherwise.
    """

    pattern = r'.*:\/.*#.*'
    result = re.match(pattern=pattern, string=uri)
    if result:
        return True
    return False


# ----------------------------------------------------------------------------------------------------------------------
def repo_name_from_uri(uri):
    """
    Given a valid and complete URI, return just the repo name portion. Does no validation as to whether this is a
    valid repo or uri.

    :param uri:
            The valid and complete URI.

    :return:
            A repo name.
    """

    return uri.split(":/")[0]


# ----------------------------------------------------------------------------------------------------------------------
def repo_path_from_uri(uri):
    """
    Given a valid and complete URI, return just the path portion. Does no validation as to whether this is a
    valid path.

    :param uri:
            The valid and complete URI.

    :return:
            A uri path.
    """

    return uri.split(":/")[1].split("#")[0]


# ----------------------------------------------------------------------------------------------------------------------
def asset_name_from_uri(uri):
    """
    Given a valid and complete URI, return just the asset name. Does no validation as to whether this is a
    valid asset name.

    :param uri:
            The valid and complete URI.

    :return:
            An asset name.
    """

    return uri.split("#")[1]

#
#
# # ------------------------------------------------------------------------------------------------------------------
# def asset_uri_from_path(self,
#                         asset_p):
#     """
#     Given an asset path, return the uri path.
#
#     :param asset_p:
#             The full path to the asset.
#
#     :return:
#             A URI.
#     """
#
#     sql = self.sql_resources.get("sql", "asset_uri_from_path")
#     rows = self.cursor.execute(sql, (asset_p,)).fetchall()
#
#     return rows[0][0]
#
#
# # ------------------------------------------------------------------------------------------------------------------
# def asset_uri_path_from_path(self,
#                              asset_p):
#     """
#     Given an asset path, return the uri path.
#
#     :param asset_p:
#             The full path to the asset.
#
#     :return:
#             A URI path.
#     """
#
#     sql = self.sql_resources.get("sql", "asset_uri_path_from_path")
#     rows = self.cursor.execute(sql, (asset_p,)).fetchall()
#
#     return rows[0][0]
