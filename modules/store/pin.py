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


class Pin(object):
    """
    Class responsible for managing pins for squirrel. Pins are symlinks to
    specific versions.
    """

    # --------------------------------------------------------------------------
    def __init__(self, asset_d, version_name, pin_name, language="english"):
        """
        An object responsible for managing pins.
        """

        assert os.path.exists(asset_d)
        assert os.path.isdir(asset_d)

        module_d = os.path.split(inspect.stack()[0][1])[0]
        resources_d = os.path.join(module_d, "..", "..", "resources")
        self.resc = resources.Resources(resources_d, "lib_store", language)

        self.pin_p = os.path.join(asset_d, pin_name)
        self.ver_n = version_name

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
                raise ValueError(err.msg)

            os.unlink(self.pin_p)

    # --------------------------------------------------------------------------
    def set_pin(self):
        """
        Sets a pin on a specific version of an asset.

        :return: Nothing.
        """

        # Remove the pin if it already exists
        self.remove_pin()

        # Create the pin
        os.symlink(os.path.join(".", self.ver_n), self.pin_p)
