import errno
import os
import re
import shutil

import bvzfilesystemlib

import bvzconfig
from squirrel.asset.thumbnails import Thumbnails
from squirrel.shared import libtext
from squirrel.shared.squirrelerror import SquirrelError
from squirrel.shared.constants import *


# ======================================================================================================================
class Version(object):
    """
    Class responsible for managing a single version.
    """

    def __init__(self,
                 version_str,
                 asset_n,
                 asset_d,
                 config_obj,
                 localized_resource_obj):
        """
        :param version_str:
                The name of the version as a string.
        :param asset_n:
                The name of the parent asset.
        :param asset_d:
                The path to the asset root.
        :param config_obj:
                A config object.
        :param localized_resource_obj:
                The localized resource object.

        :return:
               Nothing.
        """

        assert type(version_str) is str
        assert type(config_obj) is bvzconfig.Config

        self.asset_n = asset_n
        self.asset_d = asset_d

        self.version_str = version_str
        self._verify_version_format()
        self.version_int = self._version_str_to_int(version_str)
        self._verify_max_version_value()

        self.metadata_str = "." + self.version_str

        self.version_d = os.path.join(self.asset_d, self.version_str)
        self.version_metadata_d = os.path.join(self.asset_d, self.metadata_str)

        thumbnail_d = os.path.join(self.version_metadata_d, "thumbnails")
        thumbnail_data_d = os.path.join(self.asset_d, ".thumbnaildata")

        self.localized_resource_obj = localized_resource_obj
        self.config_obj = config_obj

        self.thumbnails = Thumbnails(asset_n=self.asset_n,
                                     version_obj=self,
                                     thumbnail_d=thumbnail_d,
                                     thumbnail_data_d=thumbnail_data_d,
                                     localized_resource_obj=self.localized_resource_obj)

    # ------------------------------------------------------------------------------------------------------------------
    @staticmethod
    def _version_str_to_int(version_str) -> int:
        """
        Given a version as a string, return an integer.

        :param version_str:
                The version number as an integer.
        """

        return int(version_str.split("v")[1])

    # ------------------------------------------------------------------------------------------------------------------
    def _verify_version_format(self):
        """
        Raises an error if the version format is not valid.

        :return:
                Nothing.
        """

        assert type(self.version_str) is str

        pattern = "^v[0-9]{" + str(VERSION_NUM_DIGITS) + "}$"
        if re.match(pattern, self.version_str) is None:
            err_msg = self.localized_resource_obj.get_error_msg(11005)
            err_msg = err_msg.format(version=self.version_str)
            raise SquirrelError(err_msg, 11005)

    # ------------------------------------------------------------------------------------------------------------------
    def _verify_max_version_value(self):
        """
        If the version int is greater than the max number of possible versions, raise an error.

        :return:
                Nothing.
        """

        max_versions = (10**VERSION_NUM_DIGITS) - 1

        if self.version_int > max_versions:
            err_msg = self.localized_resource_obj.get_error_msg(11004)
            err_msg = err_msg.format(max=max_versions)
            raise SquirrelError(err_msg, 11004)

    # ------------------------------------------------------------------------------------------------------------------
    def _create_version_dir(self):
        """
        Creates the version directory on disk.

        :return:
                Nothing.
        """

        try:
            os.mkdir(self.version_d)
        except OSError as e:
            if e.errno == errno.EEXIST and os.path.isdir(self.version_d):
                return
            else:
                err_msg = self.localized_resource_obj.get_error_msg(1234)
                err_msg = err_msg.format(version_p=self.version_d)
                raise SquirrelError(err_msg, 1234)

    # ------------------------------------------------------------------------------------------------------------------
    def _create_metadata_dir(self):
        """
        Creates the version meta directory on disk.

        :return:
                Nothing.
        """

        try:
            os.mkdir(self.version_metadata_d)
        except OSError as e:
            if e.errno == errno.EEXIST and os.path.isdir(self.version_metadata_d):
                return
            else:
                err_msg = self.localized_resource_obj.get_error_msg(1234)
                err_msg = err_msg.format(metadata_p=self.version_metadata_d)
                raise SquirrelError(err_msg, 1234)

    # ------------------------------------------------------------------------------------------------------------------
    def _create_thumbnails_dir(self):
        """
        Creates the thumbnails directory on disk.

        :return:
                Nothing.
        """

        try:
            os.mkdir(os.path.join(self.version_metadata_d, "thumbnails"))
        except OSError as e:
            if e.errno == errno.EEXIST and os.path.isdir(self.version_metadata_d):
                return
            else:
                err_msg = self.localized_resource_obj.get_error_msg(1234)
                err_msg = err_msg.format(metadata_p=self.version_metadata_d)
                raise SquirrelError(err_msg, 1234)

    # ------------------------------------------------------------------------------------------------------------------
    def create_dirs(self):
        """
        Creates the version directory and meta directory on disk.

        :return:
                Nothing.
        """
        self._create_version_dir()
        self._create_metadata_dir()
        self._create_thumbnails_dir()

    # ------------------------------------------------------------------------------------------------------------------
    def add_notes(self,
                  notes,
                  overwrite):
        """
        Sets the notes for a specified version.

        :param notes:
                A string of notes to add.
        :param overwrite:
                If True, then the notes will overwrite the current set of notes. Otherwise they will be appended.

        :return:
                Nothing.
        """

        assert type(notes) is str
        assert type(overwrite) is bool

        notes_p = os.path.join(self.version_metadata_d, "notes")
        libtext.write_to_text_file(notes_p, notes, overwrite)

    # ------------------------------------------------------------------------------------------------------------------
    def delete_notes(self):
        """
        Removes all the notes for a specified version.

        :return:
                Nothing.
        """

        notes_p = os.path.join(self.version_metadata_d, "notes")
        if os.path.exists(notes_p):
            os.remove(notes_p)

    # ------------------------------------------------------------------------------------------------------------------
    def list_notes(self) -> str:
        """
        Display the notes for a specified version.

        :return:
                Nothing.
        """

        output = ""

        notes_p = os.path.join(self.version_metadata_d, "notes")
        if os.path.exists(notes_p):
            with open(notes_p, "r") as f:
                lines = f.readlines()
            output = [line.rstrip() for line in lines]
            output = "\n".join(output)

        return output

    # ------------------------------------------------------------------------------------------------------------------
    def add_thumbnails(self,
                       thumbnails_p,
                       poster_p=None):
        """
        Adds thumbnail images. If version is None, then the thumbnails will be set on the latest version. If
        poster_frame is not None, then the poster_frame will be set to that frame number. Otherwise it will be set to
        the first frame. Thumbnails are stored using the same deduplication method as regular asset files.

        :param thumbnails_p:
                The list of thumbnail files to add.
        :param poster_p:
                The path to an optional poster frame. If None, then the first frame of the thumbnails will be used.
                Defaults to None.

        :return:
                Nothing.
        """

        self.thumbnails.add_thumbnails(thumbnail_paths=thumbnails_p,
                                       poster_p=poster_p)

    # ------------------------------------------------------------------------------------------------------------------
    def delete_thumbnails(self,
                          all_version_objs):
        """
        Deletes the thumbnails and poster frame.

        :param all_version_objs:
                A list of all version objects. Necessary so that we don't remove any thumbnails files that may be
                referenced in another version.

        :return:
                Nothing.
        """

        self.thumbnails.delete_thumbnails(all_version_objs=all_version_objs)

    # ------------------------------------------------------------------------------------------------------------------
    def user_symlink_files(self) -> list:
        """
        Returns the user's symlink files.

        :return:
                A list of all the user's stored symlink files.
        """

        return bvzfilesystemlib.recursively_list_files_in_dirs(self.version_d)

    # ------------------------------------------------------------------------------------------------------------------
    def user_data_files(self) -> list:
        """
        Returns the user's data files (the targets in the .data directory for the symlinks being stored)

        :return:
                A list of all the user's stored data files (the actual targets for the symlink files)
        """

        return bvzfilesystemlib.recursively_list_symlink_targets_in_dirs(self.version_d)

    # ------------------------------------------------------------------------------------------------------------------
    def thumbnail_symlink_files(self) -> list:
        """
        Returns the thumbnail symlink files.

        :return:
                A list of all the thumbnail symlink files.
        """

        return self.thumbnails.thumbnail_symlink_files()

    # ------------------------------------------------------------------------------------------------------------------
    def thumbnail_data_files(self) -> list:
        """
        Returns the thumbnail data files (the targets in the .thumbnaildata directory for the symlinked thumbnail
        files being stored)

        :return:
                A list of the actual thumbnail files (the actual targets for the symlinked thumbnail files)
        """

        return self.thumbnails.thumbnail_data_files()

    # ------------------------------------------------------------------------------------------------------------------
    def thumbnail_poster_file(self) -> str:
        """
        Returns the thumbnail poster file.

        :return:
                A path to the poster file. If no poster is found, returns None.
        """

        return self.thumbnails.poster_file()

    # ------------------------------------------------------------------------------------------------------------------
    def delete_version(self,
                       all_version_objs,
                       pins):
        """
        Deletes the current version.

        :param all_version_objs:
                A list of all version objects. Necessary so that we don't remove any data files that they may be relying
                on.
        :param pins:
                A dictionary of pins and the version objects they point to. Necessary because we cannot delete this
                version if any pin points to it.

        :return:
                Nothing.
        """

        # TODO: MOVE TO ASSET LAYER
        linked_pins = list()

        for pin, version_obj in pins:
            if version_obj.version_int == self.version_int:
                linked_pins.append(pin)

        if linked_pins:
            err_msg = self.localized_resource_obj.get_error_msg(13001)
            err_msg = err_msg.format(version=self.version_str,
                                     pin=", ".join(linked_pins))
            raise SquirrelError(err_msg, 13001)

        target_files_to_delete = self.user_data_files()

        target_files_to_keep = list()
        for version_obj in all_version_objs:
            if version_obj.version_int != self.version_int:
                target_files_to_keep.extend(version_obj.user_data_files())
        target_files_to_keep = list(set(target_files_to_keep))

        for delete_target in target_files_to_delete:
            if delete_target not in target_files_to_keep:
                os.remove(delete_target)

        shutil.rmtree(self.version_d, ignore_errors=True)
        shutil.rmtree(self.version_metadata_d, ignore_errors=True)
