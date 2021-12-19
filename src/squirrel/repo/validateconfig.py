from squirrel.shared.squirrelerror import SquirrelError


# ----------------------------------------------------------------------------------------------------------------------
def validate_config(config_obj,
                    localized_resource_obj):
    """
    Makes sure the config file is valid. Raises an asset error if not.

    :param config_obj:
            The config object responsible for managing preferences.
    :param localized_resource_obj:
            The localization object responsible for managing localized strings.

    :return:
           Nothing.
    """

    sections = dict()
    sections["repo_settings"] = [("warn_on_load_error", "bool"),
                                 ("fail_on_load_error", "bool"),
                                 ("default_gather_loc", "str")]

    failures = config_obj.validate(sections)
    if failures:
        if failures[1] is None:
            err_msg = localized_resource_obj.get_error_msg(501)
            err_msg = err_msg.format(config_p=config_obj.config_path,
                                     section=failures[0])
            raise SquirrelError(err_msg, 501)
        else:
            err_msg = localized_resource_obj.get_error_msg(502)
            err_msg = err_msg.format(config_p=config_obj.config_path,
                                     setting=failures[0],
                                     section=failures[1])
            raise SquirrelError(err_msg, 502)
