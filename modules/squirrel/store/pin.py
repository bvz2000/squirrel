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

import inspect
import os

from bvzlib import resources

from squirrel.shared import libSquirrel
from squirrel.shared.squirrelerror import SquirrelError


# ==============================================================================
class Pin(object):
    """
    Class responsible for managing pins for squirrel. Pins are symlinks to
    specific versions.
    """

    # --------------------------------------------------------------------------
    def __init__(self,
                 language="english"):
        """
        An object responsible for managing pins.
        """

        module_d = os.path.split(inspect.stack()[0][1])[0]
        resources_d = os.path.join(module_d, "..", "..", "..", "resources")
        self.resc = resources.Resources(resources_d, "lib_store", language)

        self.pin_n = None
        self.pin_p = None
        self.ver_n = None

        self.attr_pin_p = None
        self.attr_ver_n = None

    # --------------------------------------------------------------------------
    def set_attributes(self,
                       asset_d,
                       version_name,
                       pin_name):
        """
        Sets the object attributes.

        :param asset_d: The full directory of the asset
        :param version_name: The version that the pin associates with
        :param pin_name: The name of the pin

        :return: Nothing.
        """

        assert os.path.exists(asset_d)
        assert os.path.isdir(asset_d)
        assert type(version_name) is str
        assert type(pin_name) is str

        self.pin_n = pin_name
        self.pin_p = os.path.join(asset_d, pin_name)
        self.ver_n = version_name

        self.attr_pin_p = os.path.join(asset_d, "." + pin_name)
        self.attr_ver_n = "." + version_name

        self.validate_pin_name()

    # --------------------------------------------------------------------------
    def validate_pin_name(self):
        """
        Pin names may not be one of the following reserved names:

        thumbnaildata
        data
        or any version number

        If they are, a SquirrelError will be raised.

        :return: Nothing.
        """

        if self.pin_n.upper() in ["THUMBNAILDATA", "DATA"]:
            err = self.resc.error(113)
            err.msg = err.msg.format(pin=os.path.split(self.pin_p)[1])
            raise SquirrelError(err.msg, err.code)

        if libSquirrel.validate_version(self.pin_n):
            err = self.resc.error(114)
            err.msg = err.msg.format(pin=os.path.split(self.pin_p)[1])
            raise SquirrelError(err.msg, err.code)

    # --------------------------------------------------------------------------
    def remove_pin(self):
        """
        Removes the pin.

        :return: Nothing.
        """
        if os.path.exists(self.pin_p):

            if not os.path.islink(self.pin_p):
                err = self.resc.error(108)
                err.msg = err.msg.format(pin=self.pin_p)
                raise SquirrelError(err.msg, err.code)

            os.unlink(self.pin_p)

        if os.path.exists(self.attr_pin_p):

            if not os.path.islink(self.attr_pin_p):
                err = self.resc.error(112)
                err.msg = err.msg.format(pin=self.attr_pin_p)
                raise SquirrelError(err.msg, err.code)

            os.unlink(self.attr_pin_p)

    # --------------------------------------------------------------------------
    def set_pin(self):
        """
        Sets a pin on a specific version of an asset.

        :return: Nothing.
        """

        # Remove the pin if it already exists
        self.remove_pin()

        # Create the pin (and the hidden metadata pin)
        os.symlink(os.path.join(".", self.ver_n), self.pin_p)
        os.symlink(os.path.join(".", self.attr_ver_n), self.attr_pin_p)
