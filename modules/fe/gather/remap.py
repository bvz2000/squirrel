"""
License
--------------------------------------------------------------------------------
squirrel is released under version 3 of the GNU General Public License.

squirrel
Copyright (C) 2019  Bernhard VonZastrow

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import os.path

from bvzlib import filesystem

GATHER_MAPPING = {
    "tif": os.path.join("maps", "images"),
    "jpg": os.path.join("maps", "images"),
    "png": os.path.join("maps", "images"),
    "tga": os.path.join("maps", "images"),
    "exr": os.path.join("maps", "images"),
    "tx": os.path.join("maps", "textures"),
    "obj": os.path.join("geo"),
    "abc": os.path.join("geo"),
    "fbx": os.path.join("geo"),
    "usd": os.path.join("geo"),
    "blend": os.path.join("blender"),
    "project": os.path.join("clarisse"),
    "ma": os.path.join("maya"),
    "mb": os.path.join("maya"),
    "hip": os.path.join("houdini"),
    "vdb": os.path.join("volumes"),
}


# ==============================================================================
class Remap(object):
    """
    An object responsible for the mapping between a SINGLE source file and its
    copied, destination files. Capable of handling existing files as well as
    collisions between about-to-be-copied files. If the SINGLE source file
    is an expandable list (i.e. has UDIM's or frame number patterns in it) then
    this will be expanded and all related files will be remapped.
    """

    # --------------------------------------------------------------------------
    def __init__(self,
                 source_p,
                 dest,
                 already_remapped,
                 mapping_def=None,
                 padding=None,
                 udim_identifier=None,
                 strict_udim_format=True,
                 match_hash_length=False):
        """
        Initializes the object. The source path is the actual string that
        defined the file path in the original Clarisse project.

        Some naming conventions:

        names ending in '_p' = full path to a file
        names ending in '_n' = just the name of a file, no path
        names ending in '_d' = a directory name, no file name

        :param source_p: The path to the external file that is to be remapped.
               It may be a real file or a sequence, UDIM, or contain a sequence
               identifier like (# or %0d).
        :param dest: The root path where the files will be gathered to when
               gathered.
        :param already_remapped: A list of the remapped paths of files
               that have already been remapped. Example: if a previous file has
               been remapped to "/new/dir/for/file.txt" then this list will
               contain this item.
        :param mapping_def: A dict where the key is the file type (file
               extension) and the value is the relative path to where files of
               this type should live. Example:

               tif : maps/image
               tx : maps/textures
               abc : geo

               If None, loads the GATHER_MAPPING defined at the top of this
               module. Defaults to None.
        :param padding: Any padding to use when expanding frame specs. If None,
               then the padding will be determined from the longest number in
               the sequence. Defaults to None.
        :param udim_identifier: The string that is used as the UDIM identifier.
               If None, then the pattern "<UDIM>" will be used. Defaults to
               None.
        :param strict_udim_format: If True, then UDIM's will have to conform to
               the #### format, where the starting value is 1001. If False, then
               the UDIM must start with four digits, but can then contain any
               extra characters. Substance Painter allows this for example.
               Note, setting this to False may lead to somewhat erroneous
               identification of UDIM's in files, so - unless absolutely
               needed - this should be se to True. Defaults to True.
        :param match_hash_length: If True, then the output regex will be
               designed such that the number of digits has to match the number
               of hashes. If False, then a single hash would match any number of
               digits. For example: if True, then filename.#.exr would only
               match files with a single digit sequence number. If False, then
               any sequence number, no matter how long, would match. If the
               sequence identifier is in the printf format, this argument is
               ignored.

        :return: Nothing.
        """

        self.source_p = source_p
        self.dest = dest
        self._already_remapped = already_remapped

        self.expanded_mapping = dict()
        self._target_p = None

        if mapping_def is None:
            self.mapping_def = GATHER_MAPPING
        else:
            self.mapping_def = mapping_def

        self.padding = padding
        self.udim_identifier = udim_identifier
        self.strict_udim_format = strict_udim_format
        self.match_hash_length = match_hash_length

        self.do_remapping()

    # --------------------------------------------------------------------------
    @property
    def already_remapped(self):
        """
        :return: An inverse dictionary of remapped files where the key is the
                 remapped path, and the value is the source path.
        """
        output = dict()
        for actual_source_p in self.expanded_mapping:
            output[self.expanded_mapping[actual_source_p]] = actual_source_p
        return output

    # --------------------------------------------------------------------------
    @property
    def target_p(self):
        """
        :return: The path to the target file. This will still contain the
        '<UDIM>' tag or the '.###' (any number of # symbols) tags if they were
        originally present.
        """

        return self._target_p

    # --------------------------------------------------------------------------
    @property
    def mapping(self):
        """
        :return: A dictionary of actual files that are remapped. The key is the
        source path. The value is the target path. If the source does not
        contain "<UDIM>" or ".####." then this will simply be a single item.
        However, if either of those is present, then this will contain a list of
        expanded source files and a list of expanded destination files.
        """

        return self.expanded_mapping

    # --------------------------------------------------------------------------
    def remap_file(self, path):
        """

        :param path:
        :return:
        """
        file_d, file_n = os.path.split(path)
        ext_n = os.path.splitext(file_n)[1]

        try:
            remap_d = os.path.join(self.dest,
                                   self.mapping_def[ext_n.lstrip(".")])
        except KeyError:
            remap_d = os.path.join(self.dest, "uncategorized")

        return os.path.join(remap_d, file_n)

    # --------------------------------------------------------------------------
    def do_remapping(self):
        """
        Takes the actual files and builds a pointer to their targets.

        Checks each of the expanded files to make sure we aren't overwriting
        existing files, and that they do not collide with any files that have
        already been remapped (by checking self._already_remapped). Sets the
        target name to be the new path plus any increments to accommodate for
        collisions.

        :return: Nothing.
        """

        expanded = filesystem.expand_files(self.source_p,
                                           self.padding,
                                           self.udim_identifier,
                                           self.strict_udim_format,
                                           self.match_hash_length)

        # Identify the increment number (if any is needed) before doing the
        # remap (check all files first to make sure any sequences are kept
        # together and not remapped to different increment numbers.
        max_incr = 0
        for file_to_remap in expanded:

            base, ext = os.path.splitext(file_to_remap)
            copy_str = ""
            incr = 0

            remap = self.remap_file(base + copy_str + ext)
            while os.path.exists(remap) or remap in self._already_remapped:

                if os.path.exists(remap):
                    if filesystem.files_are_identical(file_to_remap, remap):
                        break

                if remap in self._already_remapped:
                    original = self._already_remapped[remap]
                    if filesystem.files_are_identical(file_to_remap, original):
                        break

                incr += 1
                max_incr = max(max_incr, incr)
                copy_str = "_copy" + str(incr)
                remap = self.remap_file(base + copy_str + ext)

        # Build the copy string with the highest increment in case we found any
        # collisions
        if max_incr > 0:
            copy_str = "_copy" + str(max_incr)
        else:
            copy_str = ""

        # Now that we have the increment string (if any) do the actual remapping
        for file_to_remap in expanded:
            base, ext = os.path.splitext(file_to_remap)
            remap = self.remap_file(base + copy_str + ext)
            self.expanded_mapping[file_to_remap] = remap

        # Store a remapped version of the original string with any increment
        # numbers (the DCC app will most likely need this).
        base, ext = os.path.splitext(self.source_p)
        remap = self.remap_file(base + copy_str + ext)
        self._target_p = self.remap_file(remap)
