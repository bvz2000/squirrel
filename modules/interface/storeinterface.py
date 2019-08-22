
from store import asset
from store import libStore


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
                 verify_copy=False,
                 language="english"):
        """
        Initialize the interface.

        :param name: The name of the thing we are storing. Note that this is not
               necessarily the file name of the thing we are storing (though you
               could use the file name if desired).
        :param asset_parent_d: The full path to where the source directory will
               be copied to OR the full path to the parent directory of an
               existing asset we will be modifying.
        :param src_p: A full path to the directory OR file being copied. May be
               set to None for cases where we are modifying an existing asset.
               Defaults to None.
        :param metadata: A dictionary of key, value pairs that defines arbitrary
               metadata for this asset. If None, no metadata will be stored.
               Defaults to None.
        :param keywords: An optional list of keywords. If None, no keywords will
               be stored. Defaults to None.
        :param notes: An optional string containing free-form text. If None, no
               notes will be stored. Defaults to None.
        :param thumbnails: An optional list of full paths to thumbnail images.
               There may be as many thumbnails as desired (for example: a full
               turntable). The files MUST be named in the following format:

               asset_name.####.ext

               Where the asset_name is identical to the name of the asset_d dir,
               the #### digits are frame numbers (required even if there is only
               a single file), and ext is the file extension. If None, then no
               thumbnails will be stored (but any previously stored will be
               carried forward from the previous version as symlinks). Defaults
               to None.
        :param poster_frame: The frame number (as an integer or string that
               evaluates to an integer) that indicates which frame of the
               thumbnails to make the poster frame. If None, and thumbnails are
               provided, then the first frame will be made into the poster.
               Defaults to None.
        :param merge: If True, then carry forward an files from the previous
               version that were not explicitly added in this operation. This
               allows for multiple publishes to layer together (i.e. publish
               a model asset as version 1, and publish a material definition as
               version 2 -> The model file(s) will be carried forward to version
               2 as though they had been explicitly published a second time).
               Defaults to True.
        :param pins: A list of pins to set to point to the newly created
               version. These are in addition to the automatic "LATEST" and
               "CURRENT".
        :param verify_copy: If True, then an md5 checksum will be done on each
               source and each copy to ensure that the file was copied
               correctly. Defaults to False.
        :param language: The language used for communication with the end user.
               Defaults to "english".

        :return: Nothing.
        """

        self.asset_obj = asset.Asset(name=name,
                                     asset_parent_d=asset_parent_d,
                                     src_p=src_p,
                                     metadata=metadata,
                                     keywords=keywords,
                                     notes=notes,
                                     thumbnails=thumbnails,
                                     merge=merge,
                                     poster_frame=poster_frame,
                                     pins=pins,
                                     verify_copy=verify_copy,
                                     language=language)

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
