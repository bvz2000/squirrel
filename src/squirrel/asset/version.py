import errno
import os
import shutil

import bvzfilesystemlib

from bvzconfig import Config
from bvzlocalization import LocalizedResource
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
                 version_int,
                 asset_n,
                 asset_d,
                 must_exist,
                 config_obj,
                 localized_resource_obj):
        """
        :param version_int:
                The version number as an integer.
        :param asset_n:
                The name of the parent asset.
        :param asset_d:
                The path to the asset root.
        :param must_exist:
                A boolean that determines whether the version must already exist on disk or not.
        :param config_obj:
                A config object.
        :param localized_resource_obj:
                The localized resource object.

        :return:
               Nothing.
        """

        assert type(version_int) is int
        assert type(asset_n) is str
        assert type(asset_d) is str
        assert type(config_obj) is Config
        assert type(localized_resource_obj) is LocalizedResource

        self.localized_resource_obj = localized_resource_obj
        self.config_obj = config_obj

        self.asset_n = asset_n
        self.asset_d = asset_d
        self._validate_asset_d()

        self.version_int = version_int
        self._validate_max_version_value()

        self.version_str = f"v{str(version_int).rjust(VERSION_NUM_DIGITS, '0')}"
        self.metadata_str = "." + self.version_str

        self.version_d = os.path.join(self.asset_d, self.version_str)
        self.version_metadata_d = os.path.join(self.asset_d, self.metadata_str)
        if must_exist:
            self._validate_exists()

        thumbnail_d = os.path.join(self.version_metadata_d, "thumbnails")
        thumbnail_data_d = os.path.join(self.asset_d, ".thumbnaildata")

        self.thumbnails = Thumbnails(asset_n=self.asset_n,
                                     thumbnail_d=thumbnail_d,
                                     thumbnail_data_d=thumbnail_data_d,
                                     localized_resource_obj=self.localized_resource_obj)

    # ------------------------------------------------------------------------------------------------------------------
    def exists(self):
        """
        Returns True if the version as stored in self.version_str exists on disk. Both the version and the metadata
        version must exist.

        :return:
                True if the version and metadata version exists on disk. False otherwise.
        """

        return os.path.exists(self.version_d) and os.path.exists(self.version_metadata_d)

    # ------------------------------------------------------------------------------------------------------------------
    def _validate_asset_d(self):
        """
        Makes sure that the asset directory exists.
        """

        if not os.path.isdir(self.asset_d):
            err_msg = self.localized_resource_obj.get_error_msg(11208)
            err_msg = err_msg.format(asset_dir=self.asset_d)
            raise SquirrelError(err_msg, 11208)

    # ------------------------------------------------------------------------------------------------------------------
    def _validate_exists(self):
        """
        Validates that a version string references an actual, existing version on disk. Raises an error if the version
        does not properly validate.

        :return:
                Nothing.
        """

        if not self.exists():
            err_msg = self.localized_resource_obj.get_error_msg(11000)
            err_msg = err_msg.format(version=self.version_str)
            raise SquirrelError(err_msg, 11000)

    # ------------------------------------------------------------------------------------------------------------------
    def _validate_max_version_value(self):
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
        Creates the "thumbnails" directory on disk.

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
                If True, then the notes will overwrite the current set of notes. If False, they will be appended.

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
        Adds thumbnail images. If version is None, then the thumbnails will be set on the latest version. If poster_p
        is not None, then the poster_frame will be set to that file. If poster_p None, then the poster will be set to
        the first frame. Thumbnails are stored using the same deduplication method as regular asset files.

        :param thumbnails_p:
                The list of thumbnail files to add.
        :param poster_p:
                The path to an optional poster frame. If None, then the first frame of the thumbnails will be used.
                Defaults to None.

        :return:
                Nothing.
        """

        assert type(thumbnails_p) is list
        for thumbnail_p in thumbnails_p:
            assert type(thumbnail_p) is str

        self.thumbnails.add_thumbnails(thumbnail_paths=thumbnails_p,
                                       poster_p=poster_p)

    # ------------------------------------------------------------------------------------------------------------------
    def delete_thumbnails(self,
                          files_to_keep):
        """
        Deletes the thumbnails and poster frame.

        :param files_to_keep:
                A list of thumbnail files NOT to delete.

        :return:
                Nothing.
        """

        assert type(files_to_keep) is list
        for file_to_keep in files_to_keep:
            assert type(file_to_keep) is str

        self.thumbnails.delete_thumbnails(files_to_keep=files_to_keep)

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
                       files_to_keep):
        """
        Deletes the current version. Needs a list of files in the .data directory that should not be deleted (because
        these files are also referenced by another version).

        :param files_to_keep:
                A list of files in the data directory that we do NOT want to delete. Essentially this would be a list of
                files that are in the other versions.

        :return:
                Nothing.
        """

        assert type(files_to_keep) is list
        for file_to_keep in files_to_keep:
            assert type(file_to_keep) is str

        files_to_potentially_delete = self.user_data_files()
        for file_to_potentially_delete in files_to_potentially_delete:
            if file_to_potentially_delete not in files_to_keep:
                os.remove(file_to_potentially_delete)

        shutil.rmtree(self.version_d, ignore_errors=True)
        shutil.rmtree(self.version_metadata_d, ignore_errors=True)
