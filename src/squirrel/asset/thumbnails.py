import os
import pathlib
import re
from typing import Union

import bvzversionedfiles
from squirrel.shared.squirrelerror import SquirrelError


class Thumbnails(object):

    # ------------------------------------------------------------------------------------------------------------------
    def __init__(self,
                 asset_n,
                 version_obj,
                 thumbnail_d,
                 thumbnail_data_d,
                 localized_resource_obj):
        """
        :param asset_n:
                The name of the asset (thumbnails must match this name).
        :param version_obj:
                A version object for the version that contains (or will contain) the thumbnails.
        :param thumbnail_d:
                The path to the thumbnail directory (where the symlinks will live).
        :param thumbnail_data_d:
                The path to the thumbnail data directory (where de-duplicated thumbnail files reside).
        :param localized_resource_obj:
                The localized resource object.

        :return:
               Nothing.
        """

        self.asset_n = asset_n
        self.version_obj = version_obj
        self.thumbnail_data_d = thumbnail_data_d
        self.thumbnail_d = thumbnail_d
        self.localized_resource_obj = localized_resource_obj

    # ------------------------------------------------------------------------------------------------------------------
    def _verify_thumbnail_paths(self,
                                thumbnail_paths):
        """
        Raises an error if any of the thumbnail files are missing or are actually directories (vs. files).

        :param thumbnail_paths:
                The list of full paths to the thumbnail files.

        :return:
                Nothing.
        """

        assert type(thumbnail_paths) is list

        for thumbnail in thumbnail_paths:

            if not os.path.exists(thumbnail):
                err_msg = self.localized_resource_obj.get_error_msg(11209)
                err_msg = err_msg.format(path=thumbnail)
                raise SquirrelError(err_msg, 11209)

            if os.path.isdir(thumbnail):
                err_msg = self.localized_resource_obj.get_error_msg(11300)
                raise SquirrelError(err_msg, 11300)

    # ------------------------------------------------------------------------------------------------------------------
    def _verify_thumbnail_names(self,
                                thumbnail_paths):
        """
        Raises an error if any of the thumbnail files has an incorrect name, or the frame range is not contiguous,
        starting from 1.

        The name format that the thumbnails must match is: asset_name.###.ext where:

        1) asset_name exactly matches the name of the asset
        2) ### is a frame sequence number of any length (does not have to be padded to 3 digits)
        3) ext is any valid image file extension.

        :param thumbnail_paths:
                The list of full paths to the thumbnail files.

        :return:
                Nothing.
        """

        pattern = r"(.+)\.([0-9]+)\.(.+)"

        frame_numbers = list()

        for thumbnail_p in thumbnail_paths:

            thumbnail_n = os.path.split(thumbnail_p)[1]
            result = re.match(pattern, thumbnail_n)

            if result is None:
                err_msg = self.localized_resource_obj.get_error_msg(1106)
                err_msg = err_msg.format(thumbnail_file=thumbnail_n, basename=self.asset_n)
                raise SquirrelError(err_msg, 1106)

            if result.groups()[0] != self.asset_n:
                err_msg = self.localized_resource_obj.get_error_msg(1106)
                err_msg = err_msg.format(thumbnail_file=thumbnail_n, basename=self.asset_n)
                raise SquirrelError(err_msg, 1106)

            frame_numbers.append(int(result.groups()[1]))

        frame_numbers.sort()
        if frame_numbers != list(range(1, len(frame_numbers) + 1)):
            err_msg = self.localized_resource_obj.get_error_msg(11301)
            raise SquirrelError(err_msg, 11301)

    # ------------------------------------------------------------------------------------------------------------------
    def set_poster_frame(self,
                         poster_p):
        """
        Sets the poster frame for the thumbnails.

        :param poster_p:
                The path to the poster frame.

        :return:
                Nothing.
        """

        self._verify_thumbnail_paths([poster_p])

        ext = os.path.splitext(poster_p)[1]

        bvzversionedfiles.copy_files_deduplicated(
            sources_p=poster_p,
            dest_d=self.thumbnail_d,
            dest_n="poster" + ext,
            data_d=self.thumbnail_data_d,
            ver_prefix="sqv",
            num_digits=4,
            do_verified_copy=False)

    # ------------------------------------------------------------------------------------------------------------------
    def add_thumbnails(self,
                       thumbnail_paths,
                       poster_p=None):
        """
        Adds thumbnail images. If version is None, then the thumbnails will be set on the latest version. If
        poster_frame is not None, then the poster_frame will be set to that frame number. Otherwise it will be set to
        the first frame. Thumbnails are stored using the same deduplication method as regular asset files.

        :param thumbnail_paths:
                The list of thumbnail files to add.
        :param poster_p:
                The path to an optional poster frame. If None, then the first frame of the thumbnails will be used.
                Defaults to None.

        :return:
                Nothing.
        """

        assert type(thumbnail_paths) is list
        assert poster_p is None or type(poster_p) is str

        self._verify_thumbnail_paths(thumbnail_paths=thumbnail_paths)
        self._verify_thumbnail_names(thumbnail_paths=thumbnail_paths)

        bvzversionedfiles.copy_files_deduplicated(
            sources_p=thumbnail_paths,
            dest_d=self.thumbnail_d,
            dest_n=None,
            data_d=self.thumbnail_data_d,
            ver_prefix="sqv",
            num_digits=4,
            do_verified_copy=False)

        self.set_poster_frame(poster_p=poster_p)

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

        target_files_to_delete = self.version_obj.thumbnail_data_files()

        target_files_to_keep = list()
        for version_obj in all_version_objs:
            if version_obj.version_int != self.version_obj.version_int:
                target_files_to_keep.extend(version_obj.user_data_files())
        target_files_to_keep = list(set(target_files_to_keep))

        for delete_target in target_files_to_delete:
            if delete_target not in target_files_to_keep:
                os.remove(delete_target)

        symlink_files_to_delete = self.version_obj.user_thumbnail_symlink_files()
        for symlink_file_to_delete in symlink_files_to_delete:
            os.remove(symlink_file_to_delete)

    # ------------------------------------------------------------------------------------------------------------------
    def thumbnail_symlink_files(self) -> list:
        """
        Returns a list of all of the thumbnail files (these are the symlink files, not the data files).

        :return:
                A list of all of the thumbnail files.
        """

        output = list()

        files_n = os.listdir(self.thumbnail_d)
        for file_n in files_n:
            if os.path.splitext(file_n)[0] == self.asset_n:
                link_p = os.path.join(self.thumbnail_d, file_n)
                if os.path.islink(link_p):
                    output.append(os.path.join(self.thumbnail_d, file_n))

        return output

    # ------------------------------------------------------------------------------------------------------------------
    def thumbnail_data_files(self) -> list:
        """
        Returns a list of all of the actual thumbnail data files (vs. the symlink files).

        :return:
                A list of all of the thumbnail files.
        """

        output = list()

        links_p = self.thumbnail_symlink_files()
        for link_p in links_p:
            output.append(pathlib.Path(link_p).resolve())

        return output

    # ------------------------------------------------------------------------------------------------------------------
    def poster_file(self) -> Union[str, None]:
        """
        Returns a path to the poster file.

        :return:
                A path to the poster file. If no poster frame is found, returns None.
        """

        files_p = self.thumbnail_symlink_files()
        for file_p in files_p:
            if os.path.splitext(os.path.split(file_p)[1])[0].lower() == "poster":
                return file_p
        return None