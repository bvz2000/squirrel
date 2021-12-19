import inspect
import os

from bvzconfig import Config

from squirrel.shared.constants import *
from squirrel.shared.squirrelerror import SquirrelError


# ----------------------------------------------------------------------------------------------------------------------
def validate_config(config_obj,
                    localized_resource_obj,
                    validation_dict):
    """
    Makes sure the config file is valid. Raises an asset error if not.

    :param config_obj:
            The config object responsible for managing preferences.
    :param localized_resource_obj:
            The localization object responsible for managing localized strings.
    :param validation_dict:
            A dictionary where the key is the section that must exist. The value may be None which indicates that there
            is no defined set of options in the section (in other words, the section must exist, but it can have any
            content (or even no content).

            If there are defined items that must exist in the section then the value must be in the form of:

            [(option name1, data type), (option name2, data type)]

            For example:

            {"asset_settings": [("auto_create_default_pin", "bool"), ("default_pin_name", "str")]}

            This means there must be a section called "asset_settings" and it must have two options in it:
            auto_create_default_pin (type boolean) and default_pin_name (type string).

    :return:
           Nothing.
    """

    failures = config_obj.validate(validation_dict)

    if failures:
        if failures[1] is None:
            err_msg = localized_resource_obj.get_error_msg(501)
            err_msg = err_msg.format(config_p=config_obj.config_path,
                                     section=failures[0])
            raise SquirrelError(err_msg, 501)
        else:
            if failures[2] is None:
                err_msg = localized_resource_obj.get_error_msg(502)
                err_msg = err_msg.format(config_p=config_obj.config_path,
                                         setting=failures[1],
                                         section=failures[0])
                raise SquirrelError(err_msg, 502)
            else:
                err_msg = localized_resource_obj.get_error_msg(504)
                err_msg = err_msg.format(config_p=config_obj.config_path,
                                         setting=failures[1],
                                         section=failures[0],
                                         datatype=failures[2])
                raise SquirrelError(err_msg, 504)


# ----------------------------------------------------------------------------------------------------------------------
def create_config_object(validation_dict,
                         localized_resource_obj,
                         config_p=None):
    """
    Create a config object.

    :param validation_dict:
            A dictionary where the key is the section that must exist. The value may be None which indicates that there
            is no defined set of options in the section (in other words, the section must exist, but it can have any
            content (or even no content).

            If there are defined items that must exist in the section then the value must be in the form of:

            [(option name1, data type), (option name2, data type)]

            For example:

            {"asset_settings": [("auto_create_default_pin", "bool"), ("default_pin_name", "str")]}

            This means there must be a section called "asset_settings" and it must have two options in it:
            auto_create_default_pin (type boolean) and default_pin_name (type string).
    :param localized_resource_obj:
            The localization object responsible for managing localized strings.
    :param config_p:
            If provided, this path will be used instead of any provided by an env variable or the default config
            file location. If None, then the config file will be read from the path given by the env variable or,
            if that is not set, from the default location. Defaults to None.

    :return:
            A config object.
    """

    assert config_p is None or type(config_p) is str
    assert type(validation_dict) is dict

    if config_p is None:
        if CONFIG_PATH_ENV_VAR in os.environ.keys():
            config_p = os.environ[CONFIG_PATH_ENV_VAR]
        else:
            module_d = os.path.split(inspect.stack()[0][1])[0]
            config_p = os.path.abspath(os.path.join(module_d, "..", "..", "..", "config", "squirrel.config"))

    if not os.path.exists(config_p):
        err_msg = localized_resource_obj.get_error_msg(503)
        err_msg = err_msg.format(config=config_p)
        raise SquirrelError(err_msg, 503)

    config_obj = Config(config_p)
    validate_config(config_obj=config_obj,
                    localized_resource_obj=localized_resource_obj,
                    validation_dict=validation_dict)

    return config_obj
