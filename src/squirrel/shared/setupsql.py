import inspect
import configparser
import os.path


# ----------------------------------------------------------------------------------------------------------------------
def create_sql_object():
    """
    Create a sql resources object.

    :return:
            A sql resources object.
    """

    module_d = os.path.split(inspect.stack()[0][1])[0]
    resources_d = os.path.abspath(os.path.join(module_d, "..", "..", "..", "resources"))

    parser = configparser.ConfigParser()
    parser.read(os.path.join(resources_d, "sql.ini"))

    return parser
