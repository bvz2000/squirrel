from squirrel.store import asset
from squirrel.store import libStore


# ==============================================================================
class StoreInterface(object):
    """
    A very thin layer between the front end of Squirrel (the individual
    connections to the DCC apps, gather, and the librarian) and the back end
    store. This thin layer can be customized to work with whatever back end
    system you are using and is the single point of contact between the front
    end and the back end store. This means you can swap out the back end and
    hopefully only have to modify this one module. When replacing the code in
    this module, you MUST implement all of the functions already present here.
    """

    # --------------------------------------------------------------------------
    def __init__(self,
                 language="english"):

        self.language = language
        self.asset_obj = asset.Asset(language=language)

    # --------------------------------------------------------------------------
    def set_attributes(self,
                       name,
                       asset_parent_d,
                       src_p=None,
                       metadata=None,
                       keywords=None,
                       notes=None,
                       thumbnails=None,
                       poster_frame=None,
                       merge=True,
                       pins=None,
                       verify_copy=False):

        self.asset_obj.set_attributes(name=name,
                                      asset_parent_d=asset_parent_d,
                                      src_p=src_p,
                                      metadata=metadata,
                                      keywords=keywords,
                                      notes=notes,
                                      thumbnails=thumbnails,
                                      merge=merge,
                                      poster_frame=poster_frame,
                                      pins=pins,
                                      verify_copy=verify_copy)

    # --------------------------------------------------------------------------
    @staticmethod
    def file_is_within_asset(file_p):
        return libStore.path_is_within_asset(file_p)

    # --------------------------------------------------------------------------
    @staticmethod
    def path_is_asset_root(path_p):
        return libStore.path_is_asset_root(path_p)

    # --------------------------------------------------------------------------
    def store(self):
        self.asset_obj.store()

    # --------------------------------------------------------------------------
    def collapse(self,
                 del_orphaned_pins):
        self.asset_obj.collapse(del_orphaned_pins)

    # --------------------------------------------------------------------------
    def set_pin(self,
                pin_name,
                version):
        self.asset_obj.set_pin(pin_name, version)

    # --------------------------------------------------------------------------
    def remove_pin(self,
                   pin_name):
        self.asset_obj.remove_pin(pin_name)

    # --------------------------------------------------------------------------
    def pin_exists(self,
                   pin_name):
        return self.asset_obj.pin_exists(pin_name)

    # --------------------------------------------------------------------------
    def get_pin_version(self,
                        pin_name):
        return self.asset_obj.get_pin_version(pin_name)

    # --------------------------------------------------------------------------
    def version_exists(self,
                       version):
        return self.asset_obj.version_exists(version)

    # --------------------------------------------------------------------------
    def get_pins(self):
        return self.asset_obj.get_pins()

    # --------------------------------------------------------------------------
    def get_highest_ver(self):
        return self.asset_obj.get_highest_ver()

    # --------------------------------------------------------------------------
    def add_keywords(self,
                     version,
                     keywords):
        return self.asset_obj.add_keywords(version, keywords)

    # --------------------------------------------------------------------------
    def delete_keywords(self,
                        version,
                        keywords):
        return self.asset_obj.delete_keywords(version, keywords)

    # --------------------------------------------------------------------------
    def add_metadata(self,
                     version,
                     metadata):
        return self.asset_obj.add_metadata(version, metadata)

    # --------------------------------------------------------------------------
    def delete_metadata(self,
                        version,
                        metadata):
        return self.asset_obj.delete_metadata(version, metadata)

    # --------------------------------------------------------------------------
    def add_notes(self,
                  version,
                  notes,
                  append):
        return self.asset_obj.add_notes(version, notes, append)

    # --------------------------------------------------------------------------
    def add_thumbnails(self,
                       version,
                       thumbnails,
                       poster_frame=None):
        self.asset_obj.add_thumbnails(version, thumbnails, poster_frame)

    # --------------------------------------------------------------------------
    def delete_thumbnails(self,
                          version):
        self.asset_obj.delete_thumbnails(version)

    # --------------------------------------------------------------------------
    def set_poster_frame(self,
                         version,
                         poster_frame=None):
        self.asset_obj.set_poster_frame(version, poster_frame)
