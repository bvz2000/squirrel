import inspect
import os

from bvzconfig import Config

from squirrel.shared.constants import *
from squirrel.shared.squirrelerror import SquirrelError


# ----------------------------------------------------------------------------------------------------------------------
def validate_repo_list(repo_list_obj,
                       localized_resource_obj):
    """
    Makes sure the repo list file is valid. Raises an asset error if not.

    :param repo_list_obj:
            The repo list object responsible for managing the list of repos.
    :param localized_resource_obj:
            The localization object responsible for managing localized strings.

    :return:
           Nothing.
    """

    sections = dict()
    sections["repos"] = None
    sections["defaults"] = [("default_repo", "str")]

    failures = repo_list_obj.validate(sections)
    if failures:
        if failures[1] is None:
            err_msg = localized_resource_obj.get_error_msg(601)
            err_msg = err_msg.format(repo_list_p=repo_list_obj.config_path,
                                     section=failures[0])
            raise SquirrelError(err_msg, 601)


# ----------------------------------------------------------------------------------------------------------------------
def create_repo_list_object(localized_resource_obj,
                            repo_list_p=None):
    """
    Create a repo list object.

    :param localized_resource_obj:
            The localization object responsible for managing localized strings.
    :param repo_list_p:
            If provided, this path will be used instead of any provided by an env variable or the default repo list
            file location. If None, then the repo list file will be read from the path given by the env variable or,
            if that is not set, from the default location. Defaults to None.

    :return:
            A repo list object.
    """

    assert repo_list_p is None or type(repo_list_p) is str

    if repo_list_p is None:
        if REPO_LIST_PATH_ENV_VAR in os.environ.keys():
            repo_list_p = os.environ[REPO_LIST_PATH_ENV_VAR]
        else:
            module_d = os.path.split(inspect.stack()[0][1])[0]
            repo_list_p = os.path.join(module_d, "..", "..", "..", "config", "repos")

    if not os.path.exists(repo_list_p):
        err_msg = localized_resource_obj.get_error_msg(603)
        err_msg = err_msg.format(repo_list_file=repo_list_p)
        raise SquirrelError(err_msg, 603)

    repo_list_obj = Config(repo_list_p)
    validate_repo_list(repo_list_obj, localized_resource_obj)

    return repo_list_obj
