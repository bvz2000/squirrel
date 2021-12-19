CONFIG_PATH_ENV_VAR = "SQUIRREL_CONFIG"
CACHE_PATH_ENV_VAR = "SQUIRREL_CACHE_PATH"
REPO_LIST_PATH_ENV_VAR = "SQUIRREL_REPO_LIST"
DEFAULT_REPO = "SQUIRREL_DEFAULT_REPO"

DEFAULT_ASSET_PATH_ENV = "BVZASSET_DEFAULT_ASSET_PATH"
BVZASSET_STRUCTURE_VERSION = "1.0"  # <- this should be updated whenever the structure of an asset is changed.
VERSION_NUM_DIGITS = 4

ASSET_CONFIG_SECTIONS = dict()
ASSET_CONFIG_SECTIONS["skip list regex"] = None
ASSET_CONFIG_SECTIONS["asset_settings"] = [("auto_create_default_pin", "bool"),
                                           ("default_pin_name", "str"),
                                           ("file_count_warning", "int")]

REPO_CONFIG_SECTIONS = dict()
REPO_CONFIG_SECTIONS["repo_settings"] = [("warn_on_load_error", "bool"),
                                         ("fail_on_load_error", "bool"),
                                         ("default_gather_loc", "str"),
                                         ("cache_dir", "str")]

COMMAND_LINE_CONFIG_SECTIONS = dict()
COMMAND_LINE_CONFIG_SECTIONS["command_line_settings"] = [("default_fields", "str")]