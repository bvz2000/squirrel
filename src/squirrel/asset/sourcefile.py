import os.path
from dataclasses import dataclass

"""
A basic data class to store a single file that is to be stored in an asset.
"""


# ======================================================================================================================
@dataclass
class Sourcefile:

    source_p: str
    dest_relative_p: str
    link_in_place: bool

    # ------------------------------------------------------------------------------------------------------------------
    def __post_init__(self):
        """
        Verify that the source file exists.
        """
        if not os.path.exists(self.source_p):
            raise ValueError(f"Source file {self.source_p} does not exist.")
