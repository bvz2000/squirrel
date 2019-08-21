"""
This module is a very thin layer between the front end of Squirrel (the
individual connections to the DCC apps, gather, and the librarian) and the back
end storage system (store). This thin layer can be customized to work with
whatever back end system you are using and is the single point of contact
between the front end and the back end store. This means you can swap out the
back end and hopefully only have to modify this one module. When replacing the
code in this module, you MUST implement all of the functions already present
here.
"""

from store import asset
from store import libStore


# ------------------------------------------------------------------------------
def file_is_within_asset(file_p):
    return libStore.path_is_within_asset(file_p)


# ------------------------------------------------------------------------------
def path_is_asset_root(path_p):
    return libStore.path_is_asset_root(path_p)


# ------------------------------------------------------------------------------
def publish(path_p):

    asset_obj = asset.Asset(name=opts.name,
                        asset_parent_d=opts.destination,
                        src_p=opts.source,
                        metadata=metadata,
                        keywords=opts.keywords,
                        notes=opts.notes,
                        thumbnails=opts.thumbnails,
                        merge=not opts.nomerge,
                        poster_frame=opts.poster_frame,
                        pins=opts.pins,
                        verify_copy=opts.verify,
                        language=opts.language,
                        )

    asset_obj.publish()
