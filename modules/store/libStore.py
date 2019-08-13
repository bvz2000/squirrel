import os.path

from bvzlib import filesystem


# ------------------------------------------------------------------------------
def path_is_asset_root(path_p):
    """
    Returns True if the path given is the root path of an asset (I.e. is
    the named root of the asset that contains all of the version sub-dirs).

    In order to be the asset root, it must pass the following tests:

    - The path exists on disk.
    - The path is a directory.
    - The path contains a file called .asset

    :param path_p: The path we are testing to see if it is an asset root
           path.

    :return: True if it is an asset root, False otherwise.
    """

    if not os.path.exists(path_p):
        return False

    if not os.path.isdir(path_p):
        return False

    if ".asset" not in os.listdir(path_p):
        return False

    return True


# ------------------------------------------------------------------------------
def path_is_within_asset(path_p):
    """
    Returns whether or not the path given is within an asset (i.e. it or any
    parent is an asset root path).

    :param path_p: The path we are testing.

    :return: True if any parent is an asset root. False otherwise.
    """

    return filesystem.ancestor_contains_file(path_p, ".asset")
