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
    location, sorted by file type. Note: This process requires that the files
    passed still contain any UDIM identifiers (<UDIM> for example) and sequence
    identifiers (.### or %03d for example) and sequence specs (1-10x2 for
    example) that they may have had in the original, calling DCC app. This is
    needed so that if collisions between files are found, an entire sequence
    of files (sequence as defined by being grouped sequence files or grouped
    UDIM files) are rev'ed up together. If these sequences are expanded BEFORE
    this object has a chance to work on them, then if there are any collisions
    only some of the files may be rev'ed up, and as such the sequence will
    break.
    """

    def __init__(self,
                 files,
                 dest,
                 mapping=None,
                 padding=None,
                 udim_identifier=None,
                 strict_udim_format=True,
                 match_hash_length=False):
        """
        :param files: A list of file paths to be gathered. Note that these can
               also be in the format of a sequence, contain sequence identifiers
               (# symbols or %0d), and/or UDIM identifiers.
        :param dest: The destination path root.
        :param mapping: A dict where the key is the file type (file extension)
               and the value is the relative path to where files of this type
               should live. Example:

               tif : maps/image
               tx : maps/textures
               abc : geo

               If None, uses a built-in, default map. Defaults to None.

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
        """

        self.files = files
        self.dest = dest
        self.mapping = mapping
        self.padding = padding
        self.udim_identifier = udim_identifier
        self.strict_udim_format = strict_udim_format
        self.match_hash_length = match_hash_length

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
        on disk). Also handles expanding files with sequence specs (1-10x2 for
        example), UDIM identifiers (<UDIM> for example), and sequences
        containing .#### (with any number of # symbols) or the printf format of
        %0d. Does not actually copy any files.

        :return: Nothing.
        """

        already_remapped = dict()
        for file_p in self.files:

            remap_obj = remap.Remap(file_p,
                                    self.dest,
                                    already_remapped,
                                    self.mapping,
                                    self.padding,
                                    self.udim_identifier,
                                    self.strict_udim_format,
                                    self.match_hash_length)
            already_remapped.update(remap_obj.already_remapped)
            self.remap_objs.append(remap_obj)

        for remap_obj in self.remap_objs:
            self.remapped[remap_obj.source_p] = remap_obj.target_p

    # --------------------------------------------------------------------------
    def copy_files(self):
        """
        Steps through the remap objects list and copies files from the source to
        the destination. Skips any files that might be overwritten (by this
        point, those are to be skipped by default because they are known to be
        identical files).

        :return: Nothing.
        """

        for remap_obj in self.remap_objs:

            parent_p = os.path.split(remap_obj.target_p)[0]
            if not os.path.exists(parent_p):
                os.makedirs(parent_p)

            for actual_source_p in remap_obj.mapping:

                copy_source_p = actual_source_p
                copy_target_p = remap_obj.mapping[actual_source_p]

                if not os.path.exists(copy_target_p):
                    shutil.copyfile(copy_source_p, copy_target_p)

    # --------------------------------------------------------------------------
    def cull_file(self,
                  file_p):
        """
        Given the path to a source file, removes that file from the list of
        remapped files, thereby preventing it from being gathered when the
        copy_files method is invoked. This cull_file method should be invoked
        between calling remap_files and copy_files.

        :param file_p: The full path to the source file that should be removed
               from the list of remapped files.

        :return: Nothing.
        """

        output = list()
        for remap_obj in self.remap_objs:
            if remap_obj.source_p != file_p:
                output.append(remap_obj)
        self.remap_objs = output

        keys = self.remapped.keys()
        for key in keys:
            del self.remapped[key]

    # --------------------------------------------------------------------------
    def gather_files(self):

        """
        Remaps the files (those that were passed to this object when it was
        created) and then copies those files to their remapped location. If
        some of the remapped files need to be culled (because they may point to
        already published assets, for example, then do not call this function.
        Call remap_files and copy_files separately. This is just a convenience
        function in case no culling is required.

        :return: Nothing.
        """

        self.remap_files()
        self.copy_files()

        #for remap_obj in self.remap_objs:
        #    self.remapped[remap_obj.source_p] = remap_obj.target_p
