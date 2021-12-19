import inspect
import os.path
import sys

from bvzlocalization import LocalizedResource
from bvzlocalization import LocalizationError


# ----------------------------------------------------------------------------------------------------------------------
def create_localization_object(language):
    """
    Create a localization object.

    :param language:
            The language to use for this resource.

    :return:
            A localization object.
    """

    module_d = os.path.split(inspect.stack()[0][1])[0]
    resources_d = os.path.join(module_d, "..", "..", "..", "resources")
    try:
        return LocalizedResource(resources_d, "squirrel", language)
    except LocalizationError as err:
        print(err.message)
        sys.exit(err.code)
