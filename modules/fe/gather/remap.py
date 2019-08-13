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
import re

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
                 udim_strings=None,
                 seq_num_strings=None):
        """
        Initializes the object. The source path is the actual string that
        defined the file path in the original Clarisse project.

        Some naming conventions:

        names ending in '_p' = full path to a file
        names ending in '_n' = just the name of a file, no path
        names ending in '_d' = a directory name, no file name

        :param source_p: The path to the external file that is to be remapped.
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
        :param udim_strings: The pattern to use for identifying the UDIM place-
               holder in a file name. For example, Clarisse uses: "<UDIM>". This
               may also accept a list in case there is more than one pattern to
               search for. Defaults to "<UDIM>".
        :param seq_num_strings: The symbol used to indicate a sequence number
               placeholder. For example, Clarisse uses "#". This may also accept
               a list in case there is more than one placeholder. Defaults to #.

        :return: Nothing.
        """

        self.source_p = source_p
        self.dest = dest
        self._already_remapped = already_remapped

        if udim_strings is None:
            udim_strings = ["<UDIM>"]
        if not type(udim_strings) is list:
            self.udim_strings = [udim_strings]
        else:
            self.udim_strings = udim_strings

        if seq_num_strings is None:
            seq_num_strings = ["#"]
        if not type(seq_num_strings) is list:
            self.seq_num_strings = [seq_num_strings]
        else:
            self.seq_num_strings = seq_num_strings

        self.expanded_mapping = dict()
        self._target_p = None

        if mapping_def is None:
            self.mapping_def = GATHER_MAPPING
        else:
            self.mapping_def = mapping_def

        self.do_remapping()

    # --------------------------------------------------------------------------
    @property
    def already_remapped(self):
        """
        :return: The list of target files that were calculated.
        """
        output = list()
        for actual_source_p in self.expanded_mapping:
            output.append(self.expanded_mapping[actual_source_p])
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
    def expand_files(self):
        """
        Expands the source path to multiple paths if the source path contains
        <UDIM> or .####. (any number of pound signs). These expanded paths are
        stored as the keys of the expanded_mapping dictionary. If there are no
        files to expand to (i.e. the source_p does not contain either <UDIM> or
        .# (any number of # symbols) then the expanded_mapping dictionary will
        contain a single item that matches the source_p.

        :return: Nothing.
        """

        udim_patterns = list()
        for item in self.udim_strings:
            udim_patterns.append(r"(.*)(" + item + ")(.*)")

        seq_num_patterns = list()
        for item in self.seq_num_strings:
            seq_num_patterns.append(r"^([^.]*)(\." + item + "+)(\..*)?$")

        expanded = list()
        matched = False

        for udim_pattern in udim_patterns:
            if re.match(udim_pattern, self.source_p):
                expanded.extend(filesystem.expand_udims(self.source_p))
                matched = True

        for seq_num_pattern in seq_num_patterns:
            if re.match(seq_num_pattern, self.source_p):
                expanded.extend(filesystem.expand_sequences(self.source_p))
                matched = True

        if not matched:
            expanded = [self.source_p]

        for path in expanded:
            self.expanded_mapping[path] = None

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

        self.expand_files()

        # Identify the increment number (if any is needed) before doing the
        # remap (check all files first to make sure any sequences are not
        # remapped to different increment numbers.
        max_incr = 0
        for file_to_remap in self.expanded_mapping:

            base, ext = os.path.splitext(file_to_remap)
            copy_str = ""
            incr = 0

            remap = self.remap_file(base + copy_str + ext)
            while os.path.exists(remap) or remap in self._already_remapped:
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
        for file_to_remap in self.expanded_mapping:
            base, ext = os.path.splitext(file_to_remap)
            remap = self.remap_file(base + copy_str + ext)
            self.expanded_mapping[file_to_remap] = remap

        # Store a remapped version of the original string with any increment
        # numbers (the DCC app will most likely need this).
        base, ext = os.path.splitext(self.source_p)
        remap = self.remap_file(base + copy_str + ext)
        self._target_p = self.remap_file(remap)
