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
import shutil

import remap


# ==============================================================================
class Gather(object):
    """
    A class responsible for gathering files from anywhere on disk to a single
    location, sorted by file type.
    """

    def __init__(self,
                 files,
                 dest,
                 mapping=None):
        """
        :param files: A list of file paths to be gathered.
        :param dest: The destination path root.
        :param mapping: A dict where the key is the file type (file extension)
               and the value is the relative path to where files of this type
               should live. Example:

               tif : maps/image
               tx : maps/textures
               abc : geo

               If None, uses a built-in, default map. Defaults to None.
        """

        self.files = files
        self.dest = dest
        self.mapping = mapping

        self.remap_objs = list()
        self.remapped = dict()

    # --------------------------------------------------------------------------
    def remap_files(self):
        """
        Given the list of files passed during the creation of the object, the
        destination where these files should be gathered to, and the dict of
        mappings, build a dict of where these individual files SHOULD be
        gathered to. Automatically compensates for internal collisions (where
        two files would be copied to the same destination file) and external
        collisions (where a copied file would overwrite an already existing file
        on disk). Also handles expanding files with the string <UDIM> and
        sequences containing .#### (with any number of # symbols). Does not
        actually copy any files.

        :return: Nothing.
        """

        already_remapped = list()
        for file_p in self.files:

            remap_obj = remap.Remap(file_p,
                                    self.dest,
                                    already_remapped,
                                    self.mapping)
            already_remapped.extend(remap_obj.already_remapped)
            self.remap_objs.append(remap_obj)

    # --------------------------------------------------------------------------
    def copy_files(self):
        """
        Steps through the remap objects list and copies files from the source to
        the destination. Does no checking to see if it might overwrite an
        existing file.

        :return: Nothing.
        """

        for remap_obj in self.remap_objs:

            parent_p = os.path.split(remap_obj.target_p)[0]
            if not os.path.exists(parent_p):
                os.makedirs(parent_p)

            for actual_source_p in remap_obj.mapping:

                copy_source_p = actual_source_p
                copy_target_p = remap_obj.mapping[actual_source_p]
                try:
                    print "Copying:", copy_source_p
                    print "     to:", copy_target_p
                    shutil.copyfile(copy_source_p, copy_target_p)
                except IOError:
                    raise

    # --------------------------------------------------------------------------
    def gather_files(self):
        """
        Copies the files passed during object creation to their new location.
        Returns a dict where the key is the file that was gathered, and the
        value is a tuple where the first item is the absolute path to where the
        file was copied, and the second item is the relative path (relative to
        "dest") where the file was copied. Keeps a dictionary where the key is
        the original file, and the value is the absolute path of where the files
        have been gathered to. Note: if the original path is a sequence - i.e.
        contains either <UDIM> or .### (with any number of # symbols) - the
        "absolute path of where the files have been gathered to" will also
        include this format (i.e. will also have the text "<UDIM>" or ".####" in
        it. That said, the actual files copied are the actual files that this
        representation refers to.
        """

        self.remap_files()
        self.copy_files()

        for remap_obj in self.remap_objs:
            self.remapped[remap_obj.source_p] = remap_obj.target_p
