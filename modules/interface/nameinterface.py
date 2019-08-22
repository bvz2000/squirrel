
from name import name


# ==============================================================================
class NameInterface(object):
    """
    A very thin layer between the front end of Squirrel (the individual
    connections to the DCC apps, gather, and the librarian) and the back end
    name validator. This thin layer can be customized to work with whatever back
    end system you are using and is the single point of contact between the
    front end and the name validator. This means you can swap out the back end
    and hopefully only have to modify this one module. When replacing the code
    in this module, you MUST implement all of the functions already present
    here.
    """

    # --------------------------------------------------------------------------
    def __init__(self,
                 item_n,
                 repo_n,
                 language="english"):
        """
        Initialize the interface.

        :param item_n: The name we are trying to validate.
        :param repo_n: The repo against which we are validating the name.
        :param language: The language used for communication with the end user.
               Defaults to "english".

        :return: Nothing.
        """

        self.name_obj = name.Name(name=item_n,
                                  repo_n=repo_n,
                                  language=language)

    # --------------------------------------------------------------------------
    def validate_name(self):
        return self.name_obj.validate_name()

    # --------------------------------------------------------------------------
    def extract_metadata_from_name(self):
        return self.name_obj.extract_metadata_from_name()
