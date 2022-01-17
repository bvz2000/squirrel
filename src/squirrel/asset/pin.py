import os

from bvzlocalization import LocalizedResource
from squirrel.asset.version import Version
from squirrel.shared.squirrelerror import SquirrelError


# ======================================================================================================================
class Pin(object):
    """
    Class responsible for managing a single pin squirrel. Pins are symlinks to specific versions.
    """

    # ------------------------------------------------------------------------------------------------------------------
    def __init__(self,
                 pin_n,
                 asset_d,
                 version_obj,
                 is_locked,
                 localized_resource_obj,
                 config_obj):
        """
        An object responsible for managing a single pin.

        :param pin_n:
                The name of the pin.
        :param asset_d:
                The path to the asset root.
        :param version_obj:
                The version object this pin references. If None, then this pin is not yet connected to a version.
                Defaults to None.
        :param is_locked:
                A boolean determining whether this pin is locked against deletion or not.
        :param localized_resource_obj:
                Localization object.
        :param config_obj:
                The configuration object.
        """

        assert type(pin_n) is str
        assert type(asset_d) is str
        assert type(is_locked) is bool
        assert os.path.exists(asset_d)
        assert os.path.isdir(asset_d)
        assert type(localized_resource_obj) is LocalizedResource

        self.pin_n = pin_n.upper()
        self.asset_d = asset_d
        self.version_obj = version_obj
        self.is_locked = is_locked
        self.localized_resource_obj = localized_resource_obj
        self.config_obj = config_obj

        self._validate_pin_name(self.pin_n)

        self.pin_p = os.path.join(asset_d, pin_n)
        self.attr_pin_p = os.path.join(asset_d, "." + pin_n)

        if os.path.exists(self.pin_p) and not os.path.islink(self.pin_p):
            err_msg = self.localized_resource_obj.get_error_msg(11107)
            err_msg = err_msg.format(pin=pin_n)
            raise SquirrelError(err_msg, 11107)

    # ------------------------------------------------------------------------------------------------------------------
    def _validate_pin_name(self,
                           pin_n):
        """
        Pin names may not be one of the following reserved names: thumbnaildata, data.
        Pin names may not begin with a ".".

        :param pin_n:
                Then name of the pin.

        :return:
                Nothing.
        """

        if pin_n[0] == ".":
            err_msg = self.localized_resource_obj.error(113)
            err_msg = err_msg.format(pin=pin_n)
            raise SquirrelError(err_msg, 113)

        if pin_n.upper() in ["THUMBNAILDATA", "DATA"]:
            err_msg = self.localized_resource_obj.get_error_msg(11103)
            err_msg = err_msg.format(pin=pin_n)
            raise SquirrelError(err_msg, 11103)

    # ------------------------------------------------------------------------------------------------------------------
    def create_link(self,
                    allow_delete_locked):
        """
        Creates the symlink on disk.

        :param allow_delete_locked:
                If True, then the previous link may be deleted, even if it is locked. If False, the link may not be
                deleted if it is locked. Must be set to True in order to update a locked link.
                
        :return:
                Nothing.
        """

        self.delete_link(allow_delete_locked=allow_delete_locked)

        src = "/" + self.version_obj.version_str
        dst = os.path.join(".", self.asset_d, self.pin_n)
        if os.path.islink(dst):
            os.unlink(dst)
        os.symlink(src, dst)

        src = "./" + self.version_obj.metadata_str
        dst = os.path.join(".", self.asset_d, "." + self.pin_n)
        if os.path.islink(dst):
            os.unlink(dst)
        os.symlink(src, dst)

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

        if not allow_delete_locked and self.is_locked:
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

    # ------------------------------------------------------------------------------------------------------------------
    def get_pin_version_obj(self) -> Version:
        """
        Returns the version object associated with the pin

        :return:
                The version this pin references. If it does not exist, returns None.
        """

        return self.version_obj
