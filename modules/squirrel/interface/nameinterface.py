from squirrel.name import name


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
                 language="english"):
        self.name_obj = name.Name(language=language)

    # --------------------------------------------------------------------------
    def set_attributes(self,
                       item_n=None,
                       repo_n=None):
        self.name_obj.set_attributes(item_n, repo_n)

    # --------------------------------------------------------------------------
    def validate_name(self):
        return self.name_obj.validate_name()

    # --------------------------------------------------------------------------
    def extract_metadata_from_name(self):
        return self.name_obj.extract_metadata_from_name()
