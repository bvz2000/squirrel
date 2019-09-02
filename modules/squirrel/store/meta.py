"""
License
--------------------------------------------------------------------------------
Squirrel is released under version 3 of the GNU General Public License.

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

import ConfigParser
import inspect
import os
import re

from bvzlib import filesystem
from bvzlib import resources
from bvzlib import listTools

from squirrel.shared import libSquirrel
from squirrel.shared.squirrelerror import SquirrelError


# ==============================================================================
class Metadata(object):
    """
    Class responsible for managing thumbnails for squirrel.
    """

    # --------------------------------------------------------------------------
    def __init__(self,
                 language="english"):
        """
        An object responsible for adding metadata to a directory. Expects a very
        specific directory structure to already exist. This structure is as
        follows:

        Inside asset_d, there should already be a structure similar to the
        following:

        asset_d
        - .v0001
        --- thumbnails
        - .v0002
        --- thumbnails
        - .v####
        --- thumbnails
        - .thumbnaildata

        :param language: The language used for communication with the end user.
               Defaults to "english".
        """

        assert type(language) is str

        module_d = os.path.split(inspect.stack()[0][1])[0]
        resources_d = os.path.join(module_d, "..", "..", "..", "resources")
        self.resc = resources.Resources(resources_d, "lib_store", language)

        self.asset_n = None
        self.asset_d = None
        self.curr_ver_n = None
        self.curr_ver_d = None
        self.prev_ver_n = None
        self.prev_ver_d = None
        self.thumbnail_data_d = None
        self.thumbnail_d = None
        self.prev_thumbs_p = None
        self.prev_keywords_p = None
        self.prev_metadata_p = None
        self.metadata = None
        self.keywords = None
        self.notes = None
        self.thumbnails = None
        self.merge = None
        self.poster_frame = None

    # --------------------------------------------------------------------------
    def set_attributes(self,
                       asset_d,
                       version,
                       metadata=None,
                       keywords=None,
                       notes=None,
                       thumbnails=None,
                       merge=True,
                       poster_frame=None):
        """
        :param asset_d: The full path to where the version metadata
               sub-directories live. This is the top-level dir of the asset.
        :param version: The name of the version sub-directory we will be
               adding metadata to. This should be in the format: "v####" without
               the leading dot.
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

               "asset_name" is identical to the name of the asset_d directory,
               "####" represents frame numbers (required even if there is only
               a single file). Note that there do not need to be exactly four
               digits. Any kind of frame padding is accepted.
               ".ext" is the file extension, and is also required.

               If thumbnails is None, then no thumbnails will be stored (but any
               previously stored may be carried forward from the previous
               version as symlinks if merge_thumbnails is True). Defaults to
               None.
        :param merge: If True, then metadata from the previous version will be
               carried forward to be merged with the new metadata. Applies to
               keywords, metadata, and thumbnails, but not notes. Defaults to
               True.
        :param poster_frame: The frame number (as an integer or string that
               evaluates to an integer) that indicates which frame of the
               thumbnails to make the poster frame. If None, and thumbnails are
               provided, then the first frame will be made into the poster.
               Defaults to None.
        """

        assert os.path.exists(asset_d)
        assert os.path.isdir(asset_d)
        assert libSquirrel.validate_version(version, "v", 4)
        assert metadata is None or type(metadata) is dict
        assert keywords is None or type(keywords) is list
        assert notes is None or type(notes) is str
        assert thumbnails is None or type(thumbnails) is list
        if thumbnails:
            for thumbnail in thumbnails:
                assert os.path.exists(thumbnail)
                assert os.path.isfile(thumbnail)
        assert type(merge) is bool
        assert poster_frame is None or type(poster_frame) is int

        self.asset_n = os.path.split(asset_d)[1]
        self.asset_d = asset_d

        self.curr_ver_n = version
        self.curr_ver_d = os.path.join(self.asset_d, "." + version)

        self.prev_ver_n = self.get_previous_version()
        if self.prev_ver_n:
            self.prev_ver_d = os.path.join(self.asset_d, "." + self.prev_ver_n)
        else:
            self.prev_ver_d = None

        self.thumbnail_data_d = os.path.join(self.asset_d, ".thumbnaildata")
        self.thumbnail_d = os.path.join(self.curr_ver_d, "thumbnails")

        if self.prev_ver_d:
            self.prev_thumbs_p = os.path.join(self.prev_ver_d, "thumbnails")
            self.prev_keywords_p = os.path.join(self.prev_ver_d, "keywords")
            self.prev_metadata_p = os.path.join(self.prev_ver_d, "metadata")
        else:
            self.prev_thumbs_p = None
            self.prev_keywords_p = None
            self.prev_metadata_p = None

        self.metadata = metadata

        self.keywords = keywords
        if not self.keywords:
            self.keywords = list()

        self.notes = notes
        self.thumbnails = thumbnails
        self.merge = merge
        self.poster_frame = poster_frame

        self.validate_thumbnails()

    # --------------------------------------------------------------------------
    def get_previous_version(self):
        """
        Decrements the version by one.

        :return: The previous version number, formatted as v####. If there is
                 no previous version, returns None.
        """

        current = int(self.curr_ver_n.split("v")[1])
        if current <= 1:
            return None
        return "v" + str(current - 1).rjust(4, "0")

    # --------------------------------------------------------------------------
    def validate_thumbnails(self):
        """
        Validates the list of thumbnails. There may be as many thumbnails
        as desired (for example: a full turntable). That said, the files MUST be
        named in the following format:

        asset_name.####.ext

        Where the asset_name is identical to the name of the asset_d dir, the
        #### digits are frame numbers (required even if there is only a single
        file), and ext is the file extension. If self.thumbnails is None, then
        no thumbnails will be stored (but any previously stored will be carried
        forward from the previous version as symlinks).

        Raises a SquirrelError if the thumbnails do not validate.

        :return: Nothing.
        """

        if self.thumbnails is None:
            return

        assert type(self.thumbnails) == list

        pattern = "(" + os.path.split(self.asset_d)[1] + "\.)([0-9]+)(\..+)"

        for thumbnail in self.thumbnails:
            thumbnail_n = os.path.split(thumbnail)[1]
            if not re.match(pattern, thumbnail_n):
                err = self.resc.error(106)
                err.msg = err.msg.format(thumbnail_file=thumbnail_n,
                                         basename=self.asset_n)
                raise SquirrelError(err.msg, err.code)

    # --------------------------------------------------------------------------
    def get_metadata_obj_from_ver(self,
                                  version):
        """
        Returns the metadata configparser object from a specific version.

        :param version: The version to extract keywords from. Expects version to
               be in the form: "v####" (Note, there is no leading dot).

        :return: A dictionary of metadata from the most recent version where the
                 key is the metadata key and the value is the metadata value. If
                 there is no previous version, returns an empty dict.
        """

        assert libSquirrel.validate_version(version, "v", 4)

        metadata_obj = ConfigParser.SafeConfigParser()

        if not version:
            metadata_obj.add_section("metadata")
            return metadata_obj

        ver_d = os.path.join(self.asset_d, "." + version.lstrip("."))
        metadata_p = os.path.join(ver_d, "metadata")

        if os.path.exists(metadata_p):
            metadata_obj.read(metadata_p)
        else:
            metadata_obj.add_section("metadata")

        return metadata_obj

    # --------------------------------------------------------------------------
    def write_metadata(self,
                       version,
                       metadata_obj):
        """
        Writes the metadata to disk for the version given.

        :param version: The version where we will be writing the metadata. Any
               previous version of the metadata will be overwritten.
        :param metadata_obj: The configparser object.

        :return: Nothing.
        """

        assert libSquirrel.validate_version(version, "v", 4)
        assert isinstance(metadata_obj, ConfigParser.SafeConfigParser)

        metadata_p = os.path.join(self.asset_d, "." + version, "metadata")
        with open(metadata_p, "w") as f:
            metadata_obj.write(f)

    # --------------------------------------------------------------------------
    def delete_metadata(self,
                        version,
                        keys):
        """
        Deletes the given metadata keys from the given version.

        :param version: The version to delete metadata from.
        :param keys: A list of keys to delete.

        :return: Nothing.
        """

        assert libSquirrel.validate_version(version, "v", 4)
        assert type(keys) is list

        meta_obj = self.get_metadata_obj_from_ver(version)
        if not meta_obj.has_section("metadata"):
            meta_obj.add_section("metadata")

        # Store the metadata
        for key in keys:
            meta_obj.remove_option("metadata", key)

        # Write it out
        self.write_metadata(version, meta_obj)

    # --------------------------------------------------------------------------
    def add_metadata(self,
                     version,
                     metadata):
        """
        Adds the given metadata to the given version.

        :param version: The version to add metadata to.
        :param metadata: The dictionary of key=value metadata to add.

        :return: Nothing.
        """

        assert libSquirrel.validate_version(version, "v", 4)
        assert type(metadata) is dict

        meta_obj = self.get_metadata_obj_from_ver(version)
        if not meta_obj.has_section("metadata"):
            meta_obj.add_section("metadata")

        # Store the metadata
        for key in metadata.keys():
            meta_obj.set("metadata", key, metadata[key])

        # Write it out
        self.write_metadata(version, meta_obj)

    # --------------------------------------------------------------------------
    def save_metadata(self):
        """
        Saves the metadata to the metadata directory.

        :return: Nothing.
        """

        if self.merge and self.prev_ver_n:
            prev_meta_obj = self.get_metadata_obj_from_ver(self.prev_ver_n)
            if not prev_meta_obj.has_section("metadata"):
                prev_meta_obj.add_section("metadata")
            items = prev_meta_obj.items("metadata")

            if not self.metadata:
                self.metadata = dict()

            for item in items:
                self.metadata[item[0]] = item[1]

        self.add_metadata(self.curr_ver_n, self.metadata)

    # --------------------------------------------------------------------------
    def get_keywords_from_ver(self,
                              version):
        """
        Returns the keywords from the given version.

        :param version: The version to extract keywords from. Expects version to
               be in the form: "v####".

        :return: A list of keywords from the version given. If there are no
                 keywords, returns an empty list.
        """

        assert libSquirrel.validate_version(version, "v", 4)

        output = list()

        if not version:
            return output

        ver_d = os.path.join(self.asset_d, "." + version.lstrip("."))
        ver_p = os.path.join(ver_d, "keywords")

        # Read in the previous version's keywords
        lines = list()
        if os.path.exists(ver_p):
            with open(ver_p, "r") as f:
                lines = f.readlines()

        for line in lines:
            output.append(line.rstrip("\n"))

        return output

    # --------------------------------------------------------------------------
    def write_keywords(self,
                       version,
                       keywords):
        """
        Writes the keywords to disk for the version given.

        :param version: The version where we will be writing the keywords. Any
               previous version of the keywords will be overwritten.
        :param keywords: The list of keywords to write.

        :return: Nothing.
        """

        assert libSquirrel.validate_version(version, "v", 4)
        assert type(keywords) is list

        # Write the keywords to disk
        keywords.sort()
        keywords_p = os.path.join(self.asset_d, "." + version, "keywords")
        with open(keywords_p, "w") as f:
            for keyword in keywords:
                f.write(keyword + "\n")

    # --------------------------------------------------------------------------
    def delete_keywords(self,
                        version,
                        keywords):
        """
        Given a list of keywords, deletes them from the keywords file for the
        version given by version.

        :param version: The version to delete keywords from.
        :param keywords: The list of keywords to delete.

        :return: Nothing.
        """

        assert libSquirrel.validate_version(version, "v", 4)
        assert type(keywords) is list

        # Get the existing keywords
        existing_keywords = self.get_keywords_from_ver(version)

        # delete the new keywords (case preserving, but case insensitive)
        new_keywords = list()
        keywords_lowercased = [item.lower() for item in keywords]
        for existing_keyword in existing_keywords:
            if existing_keyword.lower() not in keywords_lowercased:
                new_keywords.append(existing_keyword)
        new_keywords = list(set(new_keywords))

        # Write the keywords to disk
        self.write_keywords(version, new_keywords)

    # --------------------------------------------------------------------------
    def add_keywords(self,
                     version,
                     keywords):
        """
        Given a list of keywords, adds them to the keywords file for the version
        given by version.

        :param version: The version to add keywords to.
        :param keywords: The list of keywords to add.

        :return: Nothing.
        """

        assert libSquirrel.validate_version(version, "v", 4)
        assert type(keywords) is list

        # Get the existing keywords
        existing_keywords = list(set(self.get_keywords_from_ver(version)))

        # Merge the two sets of keywords
        output = listTools.merge_lists_unique(existing_keywords,
                                              keywords,
                                              False)

        # Write the keywords to disk
        self.write_keywords(version, output)

    # --------------------------------------------------------------------------
    def save_keywords(self):
        """
        Saves the keywords to the metadata directory.

        :return: Nothing.
        """

        if self.merge and self.prev_ver_n:
            prev_keywords = self.get_keywords_from_ver(self.prev_ver_n)
            self.keywords = listTools.merge_lists_unique(prev_keywords,
                                                         self.keywords)

        self.add_keywords(self.curr_ver_n, self.keywords)

    # --------------------------------------------------------------------------
    def get_notes_from_ver(self,
                           version):
        """
        Returns the notes from the given version.

        :param version: The version to extract notes from. Expects version to
               be in the form: "v####".

        :return: A string of the notes from the version given. If there are no
                 notes, returns an empty string.
        """

        assert libSquirrel.validate_version(version, "v", 4)

        output = ""

        ver_d = os.path.join(self.asset_d, "." + version.lstrip("."))
        ver_p = os.path.join(ver_d, "notes")

        # Read in the previous version's keywords
        lines = list()
        if os.path.exists(ver_p):
            with open(ver_p, "r") as f:
                lines = f.readlines()

        for line in lines:
            output += line.rstrip("\n") + "\n"

        return output

    # --------------------------------------------------------------------------
    def write_notes(self,
                    version,
                    notes):
        """
        Saves the notes to the metadata directory.

        :param version: The version where we will be writing the keywords. Any
               previous version of the keywords will be overwritten.
        :param notes: The notes string to write.

        :return: Nothing.
        """

        assert libSquirrel.validate_version(version, "v", 4)
        assert type(notes) is str

        # Write the keywords to disk
        notes_p = os.path.join(self.asset_d, "." + version, "notes")
        with open(notes_p, "w") as f:
            f.write(notes + "\n")

    # --------------------------------------------------------------------------
    def add_notes(self,
                  version,
                  notes,
                  append=True):
        """
        Given notes, adds them to the notes file for the version given by
        version.

        :param version: The version to add keywords to.
        :param notes: The string to add.
        :param append: If True, then the notes will be appended to the existing
               notes. If False, the notes will overwrite the existing notes.
               Defaults to True.

        :return: Nothing.
        """

        assert libSquirrel.validate_version(version, "v", 4)
        assert type(notes) is str
        assert type(append) is bool

        existing_notes = ""
        if append:
            existing_notes = self.get_notes_from_ver(version)

        notes = existing_notes.rstrip("\n") + "\n" + notes
        notes = notes.lstrip("\n").rstrip("\n")

        self.write_notes(version, notes)

    # --------------------------------------------------------------------------
    def save_notes(self):
        """
        Saves the notes to the metadata directory.

        :return: Nothing.
        """

        # Write the notes to disk
        self.add_notes(self.curr_ver_n, self.notes)

    # --------------------------------------------------------------------------
    def set_poster(self,
                   version,
                   frame):
        """
        Given and version and a frame number, creates a symlink named
        "poster.ext" that points to the frame given as poster_source (where ext
        will match the extension of that file).

        :param version: The version we want to set the poster frame on.
        :param frame: The frame # that will be the poster. If the frame numbers
               have padding (i.e. are name.01.exr vs name.1.exr for example),
               then be sure to pass this as a string.

        :return: Nothing.
        """

        assert libSquirrel.validate_version(version, "v", 4)
        assert type(frame) is int

        ver_d = os.path.join(self.asset_d, "." + version)
        thumb_d = os.path.join(ver_d, "thumbnails")

        thumbnails = os.listdir(thumb_d)

        if frame:
            pattern = self.asset_n + "\." + str(frame) + "\..*"
            for thumbnail in thumbnails:
                result = re.match(pattern, thumbnail)
                if result:
                    ext = os.path.splitext(thumbnail)[1]
                    src = os.path.join(thumb_d, thumbnail)
                    lnk = os.path.join(thumb_d, "poster" + ext)
                    if os.path.exists(lnk) and os.path.islink(lnk):
                        os.unlink(lnk)
                    os.link(src, lnk)
                    return
        else:
            thumbnails.sort()
            ext = os.path.splitext(thumbnails[0])[1]
            src = os.path.join(thumb_d, thumbnails[0])
            lnk = os.path.join(thumb_d, "poster" + ext)
            if os.path.exists(lnk) and os.path.islink(lnk):
                os.unlink(lnk)
            os.link(src, lnk)
            return

        err = self.resc.error(109)
        err.msg = err.msg.format(frame=str(frame),
                                 thumbnail_file=self.asset_n + "." + str(frame))
        raise SquirrelError(err.msg, err.code)

    # --------------------------------------------------------------------------
    def carry_forward_thumbnails(self):
        """
        Makes symlinks to the highest versioned thumbnail files in the
        .thumbnaildata directory in the current version metadata dir.

        :return: Nothing.
        """

        if self.prev_ver_d is None or self.prev_thumbs_p is None:
            return

        # Get a list of the thumbnail symlinks in the previous version
        prev_thumbs_n = os.listdir(self.prev_thumbs_p)

        # Step through each of the previous version thumbnail symlinks
        for prev_thumb_n in prev_thumbs_n:

            # Build the path to where this current thumbnail symlinks will live
            prev_thumb_p = os.path.join(self.prev_thumbs_p, prev_thumb_n)
            curr_thumb_p = os.path.join(self.thumbnail_d, prev_thumb_n)

            # Make a new symlink that points to the same file as the previous
            # version
            if os.path.islink(prev_thumb_p):
                link_to = os.readlink(prev_thumb_p)
                os.symlink(link_to, curr_thumb_p)
            else:
                err = self.resc.error(107)
                err.msg = err.msg.format(thumbnail_file=prev_thumb_n)
                raise SquirrelError(err.msg, err.code)

    # --------------------------------------------------------------------------
    def delete_thumbnails(self,
                          version):
        """
        Deletes the thumbnails from the version given. Only removes the links,
        but leaves the source files in place. Does no evaluation to see if this
        would leave behind a source file that is not being referenced by any of
        the versions.

        :param version: The version to delete thumbnails from.

        :return: Nothing.
        """

        assert libSquirrel.validate_version(version, "v", 4)

        thumbnail_d = os.path.join(self.asset_d, "." + version, "thumbnails")

        files_n = os.listdir(thumbnail_d)
        for file_n in files_n:
            lnk = os.path.join(thumbnail_d, file_n)
            if os.path.islink(lnk):
                os.unlink(lnk)

    # --------------------------------------------------------------------------
    def add_thumbnails(self,
                       version,
                       thumbnails,
                       poster_frame=None):
        """
        Adds thumbnails to the version passed.

        :param version: The version to add keywords to.
        :param thumbnails: The list of thumbnail files to add.
        :param poster_frame: The frame number (as an integer or string that
               evaluates to an integer) that indicates which frame of the
               thumbnails to make the poster frame. If None, and thumbnails are
               provided, then the first frame will be made into the poster.
               Defaults to None.

        :return:
        """

        assert libSquirrel.validate_version(version, "v", 4)
        assert type(thumbnails) is list
        for thumbnail in thumbnails:
            assert os.path.exists(thumbnail)
            assert os.path.isfile(thumbnail)
        assert poster_frame is None or type(poster_frame) is int

        data_sizes = filesystem.dir_files_keyed_by_size(self.thumbnail_data_d)

        for source_p in thumbnails:

            thumbnail_n = os.path.split(source_p)[1]
            thumbnail_d = os.path.join(self.asset_d,
                                       "." + version,
                                       "thumbnails")

            filesystem.copy_file_deduplicated(source_p=source_p,
                                              dest_d=thumbnail_d,
                                              dest_n=thumbnail_n,
                                              data_d=self.thumbnail_data_d,
                                              data_sizes=data_sizes,
                                              do_verified_copy=False)

        self.set_poster(version, poster_frame)

    # --------------------------------------------------------------------------
    def save_thumbnails(self):
        """
        Copies the files in the self.thumbnails list to the thumbnailsdata dir
        and then makes symlinks to these files in the metadata dir. Does
        de-duplication against previous thumbnails.

        The actual thumbnail files are stored in the thumbnailsdata directory.
        These files are named as follows:

        asset_name_vNNNN.####.ext

        where the vNNNN represents a version number used to prevent overwriting
        thumbnails with the same name but different contents.

        If self.thumbnails is None, then instead of copying any files, symlinks
        to the highest versioned existing thumbnails will be created -
        effectively carrying forward the previous thumbnails and making them
        represent the current version as well..

        :return: Nothing.
        """

        if not self.thumbnails:
            if self.merge:
                self.carry_forward_thumbnails()
            return

        self.add_thumbnails(self.curr_ver_n, self.thumbnails, self.poster_frame)
