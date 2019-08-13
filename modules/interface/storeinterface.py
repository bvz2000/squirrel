"""
publisherInterface is a thin layer between some code and the back end storage
system.

This module implements a number of generic functions that various asset manager
applications need in order to work. These functions merely pass their requests
on to the back end storage system which is responsible for actually providing
the functionality. If you switch out the back end storage system (currently
"store"), make sure these wrapper functions call comparable functions your new
back end system.
"""

from store import libStore


# ------------------------------------------------------------------------------
def file_is_within_asset(file_p):
    return libStore.path_is_within_asset(file_p)


# ------------------------------------------------------------------------------
def path_is_asset_root(path_p):
    return libStore.path_is_asset_root(path_p)
#
#
# # ------------------------------------------------------------------------------
# def get_default_repo_name():
#     """
#     Returns the name of the default repo.
#
#     :return: The name of the default repo. Raises an error if there is no
#              default repo.
#     """
#
#     return libStore.path_is_asset_root(path_p)
#
#
# # ------------------------------------------------------------------------------
# def path_is_published(path_p):
#     """
#     Returns whether or not the given path is part of a published asset.
#
#     :param path_p: The path we are testing.
#
#     :return: True if it is within a published asset. False otherwise.
#     """
#
#     return libStore.path_is_asset_root(path_p)
#
#
#
# # --------------------------------------------------------------------------
# def path_is_asset_version(self, path_p):
#     """
#     Returns True if the path given is a version path of an asset.
#
#     In order to be a version, it must pass the following tests:
#
#     - The path exists on disk.
#     - The path is a directory.
#     - The path is sub-path of the current repo.
#     - The path's immediate parent is an asset root.
#     - The path name begins with a "v" and contains only digits after that.
#
#     :param path_p: The path we are testing to see if it is a version path.
#
#     :return: True if it is a version path, False otherwise.
#     """
#
#     if not os.path.exists(path_p):
#         return False
#
#     if not os.path.isdir(path_p):
#         return False
#
#     if not path_p.startswith(self.repo_root_d):
#         return False
#
#     if ".asset" not in os.listdir(os.path.split(path_p)[0]):
#         return False
#
#     if not path_p.startswith("v"):
#         return False
#
#     try:
#         int(path_p[1:])
#     except ValueError:
#         return False
#
#     return True
#
# # --------------------------------------------------------------------------
# def path_is_repo_content(self, path_p):
#     """
#     If the path given is a path within an asset being stored in this repo
#     return True. If not, return False. Note: paths that make up the
#     structure of the repo are not considered to be repo "content". Only
#     paths that are within an asset are considered content. The top-level
#     directory that defines the name of the asset, and the sub-directories
#     that define the version numbers are also not considered content, even
#     though they are not part of the repo-structure either.
#
#     The tests that indicate whether a path is content are as follows. If any
#     of these tests fail, the path is not repo content.
#
#     - The path exists on disk.
#     - The path is within the current repo.
#     - The path is not a structure path (contains .repo or .repo_root_d file).
#     - The path is not an asset root path.
#     - The path is not an asset version path.
#     - A parent path to the path (to any level of nesting) DOES contain a
#       .asset file.
#
#     If all 6 tests pass, this is a path that is part of a managed asset, and
#     as such is considered repo content.
#
#     :param path_p: The path being validated.
#
#     :return: True if the path represents a path that is within an asset
#              being managed by this repo, False otherwise.
#     """
#
#     if not os.path.exists(path_p):
#         return False
#
#     if not self.path_is_within_repo(path_p):
#         return False
#
#     if self.path_is_repo_structure(path_p):
#         return False
#
#     if self.path_is_asset_root(path_p):
#         return False
#
#     if self.path_is_asset_version(path_p):
#         return False
#
#     previous_parent_d = None
#     parent_d = os.path.split(path_p)[0]
#     while previous_parent_d != parent_d:
#         if ".asset" in os.listdir(parent_d):
#             return True
#         previous_parent_d = parent_d
#         parent_d = os.path.split(parent_d)[0]
#
#     return False
#
# # --------------------------------------------------------------------------
# def get_asset_path_of_item(self, path_p):
#     """
#     Returns the path to the asset that contains the item: path_p.
#
#     :param path_p: The path we are testing.
#
#     :return: The path to the enclosing asset. None if no asset is found.
#     """
#
#     assets = self.list_asset_paths()
#     for asset in assets:
#         if path_p.startswith(asset):
#             return asset
#     return None
#
# # --------------------------------------------------------------------------
# def get_asset_name_of_item(self, path_p):
#     """
#     Returns the name of the asset that contains the item: path_p.
#
#     :param path_p: The path we are testing.
#
#     :return: The name of the enclosing asset. None if no asset is found.
#     """
#
#     asset_path = self.get_asset_path_of_item(path_p).rstrip(os.path.sep)
#     if not asset_path:
#         return None
#     return os.path.split(asset_path)[1]
#
# # --------------------------------------------------------------------------
# def get_version_path_of_item(self, path_p):
#     """
#     Returns the path to the version inside an asset that contains the
#     item: path_p.
#
#     :param path_p: The path we are testing.
#
#     :return: The path to the enclosing version of an asset. None if no repo
#     or asset version is found.
#     """
#
#     asset_path = self.get_asset_path_of_item(path_p)
#     if not asset_path:
#         return None
#
#     items = os.listdir(asset_path)
#     for item in items:
#         if os.path.isdir(os.path.join(asset_path, item)):
#             pattern = r"v[0-9]+"
#             result = re.match(pattern, item)
#             if result:
#                 if path_p.startswith(os.path.join(asset_path, item)):
#                     return os.path.join(asset_path, item)
#     return None
#
# # --------------------------------------------------------------------------
# def get_version_name_of_item(self, path_p):
#     """
#     Returns the name of the version inside an asset that contains the
#     item: path_p.
#
#     :param path_p: The path we are testing.
#
#     :return: The name to the enclosing version of an asset. None if no repo
#     or asset version is found.
#     """
#
#     version_path = self.get_version_path_of_item(path_p)
#     if not version_path:
#         return None
#     return os.path.split(version_path)[1]
#
