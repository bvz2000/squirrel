import os
from pathlib import Path
import re

from bvzlocalization import LocalizedResource
from squirrel.asset.version import Version
from squirrel.shared.squirrelerror import SquirrelError
from squirrel.shared.constants import *


# ======================================================================================================================
class Pin(object):
    """
    Class responsible for managing a single pin. Pins are symlinks to specific versions.
    """

    # ------------------------------------------------------------------------------------------------------------------
    def __init__(self,
                 pin_n,
                 asset_d,
                 must_exist,
                 localized_resource_obj):
        """
        An object responsible for managing a single pin.

        :param pin_n:
                The name of the pin.
        :param asset_d:
                The path to the asset root.
        :param must_exist:
                If True, the pin must exist on disk. If it does not exist, an error is raised.
        :param localized_resource_obj:
                Localization object.
        """

        assert type(pin_n) is str
        assert type(asset_d) is str
        assert type(must_exist) is bool
        assert type(localized_resource_obj) is LocalizedResource

        self.localized_resource_obj = localized_resource_obj

        self.asset_d = asset_d
        self._validate_asset_d()

        self.pin_n = pin_n.upper()
        self._validate_pin_name(self.pin_n)

        self.pin_p = os.path.join(asset_d, pin_n)
        self.attr_pin_p = os.path.join(asset_d, "." + pin_n)
        self.locked_semaphore_p = os.path.join(asset_d, f".{pin_n.upper()}_locked")

        if must_exist:
            self._validate_pin_exists()
            self.version_str = self._get_version_str()
            self.version_int = self._version_int_from_str(self.version_str)
        else:
            self.version_str = None
            self.version_int = None

    # ------------------------------------------------------------------------------------------------------------------
    def exists(self) -> bool:
        """
        Returns True if the pin exists on disk, and points to a valid version.

        :return:
                True if the pin exists on disk.
        """

        # TODO: Must point to a valid version.
        return os.path.exists(self.pin_p) and os.path.islink(self.pin_p)

    # ------------------------------------------------------------------------------------------------------------------
    @staticmethod
    def _version_int_from_str(version_str) -> int:
        """
        Given a version as a string, return an integer. Does not check whether this value equates to an actual version
        on disk.

        :param version_str:
                The version number as a string.
        """

        assert type(version_str) is str

        result = re.match(pattern=VERSION_PATTERN, string=version_str)

        return int(result.groups()[1])

    # ------------------------------------------------------------------------------------------------------------------
    def _validate_pin_exists(self):
        """
        Raises an error if the pin does not exist on disk.

        :return:
                Nothing.
        """

        if not self.exists():
            err_msg = self.localized_resource_obj.get_error_msg(11002)
            err_msg = err_msg.format(pin=self.pin_n)
            raise SquirrelError(err_msg, 11002)

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
    def _validate_pin_name(self,
                           pin_n):
        """
        Pin names may not be one of the following reserved names: thumbnaildata, data.
        Pin names may not begin with a ".". Pin names may not end with "_locked".

        :param pin_n:
                Then name of the pin.

        :return:
                Nothing.
        """

        assert type(pin_n) is str

        if pin_n[0] == ".":
            err_msg = self.localized_resource_obj.error(11112)
            err_msg = err_msg.format(pin=pin_n)
            raise SquirrelError(err_msg, 11112)

        if pin_n.upper() in ["THUMBNAILDATA", "DATA"]:
            err_msg = self.localized_resource_obj.get_error_msg(11103)
            err_msg = err_msg.format(pin=pin_n)
            raise SquirrelError(err_msg, 11103)

        if pin_n.upper().endswith("_LOCKED"):
            err_msg = self.localized_resource_obj.get_error_msg(11111)
            raise SquirrelError(err_msg, 11111)

    # ------------------------------------------------------------------------------------------------------------------
    def _get_version_str(self):
        """
        If the pin exists, gets the name of the version the pin references. The pin must exist on disk.

        :return:
                A string representing the name of the version the pin references.
        """

        return os.path.split(str(Path(self.pin_p).resolve()))[1]

    # ------------------------------------------------------------------------------------------------------------------
    def is_locked(self):
        """
        Returns True if the pin is locked.

        :return:
                True if the pin is locked.
        """

        return os.path.exists(self.locked_semaphore_p)

    # ------------------------------------------------------------------------------------------------------------------
    def lock(self):
        """
        Locks the pin by dropping a semaphore file next to the pin.

        :return:
                Nothing.
        """

        with open(self.locked_semaphore_p, 'w') as _:
            pass

    # ------------------------------------------------------------------------------------------------------------------
    def unlock(self):
        """
        Unlocks the pin by removing the semaphore file if it exists.

        :return:
                Nothing.
        """

        if self.is_locked():
            os.remove(self.locked_semaphore_p)

    # ------------------------------------------------------------------------------------------------------------------
    def create_link(self,
                    version_obj,
                    allow_delete_locked,
                    lock):
        """
        Creates the symlink on disk.

        :param version_obj:
                The version object we are linking to.
        :param allow_delete_locked:
                If True, then the previous link may be deleted, even if it is locked. If False, the link may not be
                deleted if it is locked. Must be set to True in order to UPDATE a locked link.
        :param lock:
                If True, then the link being created will be "locked". I.e. for a pin named "PIN" a semaphore file
                named .PIN_locked will be created.
                
        :return:
                Nothing.
        """

        assert type(version_obj) is Version
        assert type(allow_delete_locked) is bool
        assert type(lock) is bool

        self.delete_link(allow_delete_locked=allow_delete_locked)

        src = "./" + version_obj.version_str
        dst = os.path.join(".", self.asset_d, self.pin_n)
        if os.path.islink(dst):
            os.unlink(dst)
        os.symlink(src, dst)

        src = "./." + version_obj.version_str
        dst = os.path.join(".", self.asset_d, "." + self.pin_n)
        if os.path.islink(dst):
            os.unlink(dst)
        os.symlink(src, dst)

        if lock:
            self.lock()

    # ------------------------------------------------------------------------------------------------------------------
    def delete_link(self,
                    allow_delete_locked):
        """
        Creates the symlink on disk.

        :param allow_delete_locked:
                If True, then the link may be deleted, even if it is locked. If False, the link may not be deleted if it
                is locked.

        :return:
                Nothing.
        """

        assert type(allow_delete_locked) is bool

        if not allow_delete_locked and self.is_locked():
            err_msg = self.localized_resource_obj.get_error_msg(11106)
            err_msg = err_msg.format(pin=self.pin_p)
            raise SquirrelError(err_msg, 11106)

        if os.path.exists(os.path.abspath(self.pin_p)):
            if not os.path.islink(self.pin_p):
                err_msg = self.localized_resource_obj.get_error_msg(11008)
                err_msg = err_msg.format(pin=self.pin_p)
                raise SquirrelError(err_msg, 11008)
            os.unlink(self.pin_p)

        if os.path.exists(self.attr_pin_p):
            if not os.path.islink(self.attr_pin_p):
                err_msg = self.localized_resource_obj.get_error_msg(11102)
                err_msg = err_msg.format(pin=self.attr_pin_p)
                raise SquirrelError(err_msg, 11102)
            os.unlink(self.attr_pin_p)

        self.unlock()
