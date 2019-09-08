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

import inspect
import os

from bvzlib import config
from bvzlib import resources

from squirrel.interface import schemainterface
from squirrel.shared import envvars
from squirrel.shared.squirrelerror import SquirrelError


# ==============================================================================
class Name(object):
    """
    A class responsible for managing and validating a name.

    A name consists of the following:

    Any number of tokens, followed by a description, followed by a variant.

    variants are always one or two upper case letters preceded by an underscore.

    descriptions are any text, including underscores.

    tokens are defined by the schema (and are also separated by underscores).
    """

    # --------------------------------------------------------------------------
    def __init__(self,
                 language="english"):
        """
        Init.

        :param language: The language to use to communicate with the user. If
               omitted, defaults to "english".
        """

        self.name = None
        self.repo_n = None

        # Read in the resources
        module_d = os.path.split(inspect.stack()[0][1])[0]
        resources_d = os.path.join(module_d, "..", "..", "..", "resources")
        config_d = os.path.join(module_d, "..", "..", "..", "config")
        self.resc = resources.Resources(resources_d, "lib_name", language)

        self.config_p = os.path.join(config_d, "name.config")
        self.config_p = os.path.abspath(self.config_p)
        self.config_obj = config.Config(self.config_p,
                                        envvars.SQUIRREL_STORE_CONFIG_PATH)

        self.validate_config()

        self.schema_interface = schemainterface.SchemaInterface()

    # --------------------------------------------------------------------------
    def validate_config(self):
        """
        Makes sure the config file is valid. Raises a squirrel error if not.

        :return: Nothing.
        """

        sections = dict()
        sections["tokens"] = ["allow_uppercase", "allow_lowercase"]
        sections["description"] = ["allow_uppercase", "allow_lowercase"]
        sections["variant"] = ["allow_uppercase", "allow_lowercase"]

        failures = self.config_obj.validation_failures(sections)
        if failures:
            if failures[1] is None:
                err = self.resc.error(501)
                err.msg = err.msg.format(config_p=self.config_p,
                                         section=failures[0])
                raise SquirrelError(err.msg, err.code)
            else:
                err = self.resc.error(502)
                err.msg = err.msg.format(config_p=self.config_p,
                                         setting=failures[0],
                                         section=failures[1])
                raise SquirrelError(err.msg, err.code)

        # Check for conflicting settings
        for section in sections:
            allow_upper = self.config_obj.getboolean(section, "allow_uppercase")
            allow_lower = self.config_obj.getboolean(section, "allow_lowercase")
            if allow_upper is False and allow_lower is False:
                err = self.resc.error(503)
                err.msg = err.msg.format(config_p=self.config_p,
                                         section=section)
                raise SquirrelError(err.msg, err.code)

    # --------------------------------------------------------------------------
    def set_attributes(self,
                       name,
                       repo_n=None):
        """
        Set the attributes for this object.

        :param name: The name of the asset we are validating.
        :param repo_n: The name of the repo we are validating against. If None,
               then the default repo will be used.

        :return: Nothing.
        """

        assert type(name) is str and name
        assert repo_n is None or (type(repo_n) is str and repo_n)

        self.name = name

        if not repo_n:
            repo_n = self.schema_interface.get_default_repo()
        self.repo_n = repo_n

    # --------------------------------------------------------------------------
    def validate_name_underscores(self):
        """
        Makes sure that the name does not contain multiple contiguous
        underscores, does not begin with an underscore, and does not end with
        an underscore. Raise an error if it does.

        :return: Nothing, but raises a NameError with an appropriate help
                 message if there are doubled up underscores, or if the name
                 begins or ends with an underscore.
        """

        assert type(self.name) is str and self.name

        # Error out if there are multiple underscores
        if "__" in self.name:
            err = self.resc.error(900)
            raise SquirrelError(err.msg, err.code)

        # Error out if the name begins with an underscore
        if self.name.startswith("_"):
            err = self.resc.error(907)
            raise SquirrelError(err.msg, err.code)

        # Error out if there are multiple underscores
        if self.name.endswith("_"):
            err = self.resc.error(908)
            raise SquirrelError(err.msg, err.code)

    # --------------------------------------------------------------------------
    def validate_name_variant(self):
        """
        Makes sure that the name ends with a one or two character, all caps
        variant string.

        :return: The variant. Will raise a SquirrelError with an appropriate
                 help message if the variant does not validate.
        """

        assert type(self.name) is str and self.name

        allow_upper = self.config_obj.getboolean("variant", "allow_uppercase")
        allow_lower = self.config_obj.getboolean("variant", "allow_lowercase")
        assert not(allow_upper is False and allow_lower is False)

        variant = self.name.split("_")[-1]

        # Assume it is there
        missing_var = False

        # Cannot be longer than two characters
        if len(variant) > 2:
            missing_var = True

        # Must exist
        if variant == "":
            missing_var = True

        legal_upper_chars = ""
        if allow_upper:
            legal_upper_chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

        legal_lower_chars = ""
        if allow_lower:
            legal_lower_chars = "abcdefghijklmnopqrstuvwxyz"

        legal_chars = legal_upper_chars + legal_lower_chars
        for char in variant:
            if char not in legal_chars:
                missing_var = True

        # If any of these fail, raise an error
        if missing_var:
            if not allow_upper:
                err = self.resc.error(902)
            if not allow_lower:
                err = self.resc.error(903)
            if allow_lower and allow_upper:
                err = self.resc.error(901)
            raise SquirrelError(err.msg, err.code)

        return variant

    # --------------------------------------------------------------------------
    def validate_name_tokens(self):
        """
        Validates that the name has all the needed tokens. Because tokens are
        separated by underscores AND descriptions can have underscores, we need
        to peel off one item from the front of the name at a time, check to see
        if it is a token, and then move to the next one until we find one that
        is no longer a token. From there, the remaining elements are only
        description and variant.

        :return: The portion of the name that is a valid token.
        """

        assert type(self.name) is str and self.name
        assert type(self.repo_n) is str and self.repo_n

        allow_upper = self.config_obj.getboolean("tokens", "allow_uppercase")
        allow_lower = self.config_obj.getboolean("tokens", "allow_lowercase")
        assert not(allow_upper is False and allow_lower is False)

        # Make sure we have no multiple underscores.
        self.validate_name_underscores()

        # Convert the name to a list
        name_elements = self.name.split("_")

        # Step through each of the tokens
        consumed_elements = list()
        for element in name_elements:

            # Build the current token and check its validity
            token_path = "/".join(consumed_elements + [element])
            if not self.schema_interface.token_is_valid(token_path,
                                                        self.repo_n):
                break
            consumed_elements.append(element)

        # If there are consumed elements, we have a legal token. If there are no
        # consumed elements, then none of the tokens validated.
        if consumed_elements:
            token_path = "/".join(consumed_elements)
        else:
            possible_next = self.schema_interface.get_next_tokens("",
                                                                  self.repo_n)
            err = self.resc.error(904)
            err.msg = err.msg.format(possible_next="\n   ".join(possible_next))
            raise SquirrelError(err.msg, err.code)

        # Though we now should have a fully legal token, this token must also
        # be a token all the way down to the leaf level.
        if not self.schema_interface.token_is_leaf(token_path, self.repo_n):

            # Help the user by listing what the next possible (legal) tokens are
            possible_next = self.schema_interface.get_next_tokens(token_path,
                                                                  self.repo_n)
            up_to_last_item = "_".join(consumed_elements).lstrip("_")
            err = self.resc.error(905)
            err.msg = err.msg.format(up_to_last_item=up_to_last_item,
                                     possible_next="\n   ".join(possible_next))
            raise SquirrelError(err.msg, err.code)

        # Return the portion of the name that is the token
        token_str = token_path.lstrip("/").rstrip("/")
        token_name = token_str.replace("/", "_")
        assert self.name.startswith(token_name)

        if not allow_upper and allow_lower:
            if not allow_lower:
                if token_name.islower():
                    err = self.resc.error(801)
                    err.msg = err.msg.format(token=token_name)
                    raise SquirrelError(err.msg, err.code)

            if not allow_upper:
                if token_name.isupper():
                    err = self.resc.error(802)
                    err.msg = err.msg.format(token=token_name)
                    raise SquirrelError(err.msg, err.code)

        return token_str

    # --------------------------------------------------------------------------
    def validate_name_desc(self, token, variant):
        """
        Validates that the name contains a description.

        :param token: The portion of the name that is the token
        :param variant: The portion of the name that is the variant.

        :return: The portion of the name that is the description. Raises a
                 NameError if there is no description
        """

        allow_upper = self.config_obj.getboolean("description",
                                                 "allow_uppercase")
        allow_lower = self.config_obj.getboolean("description",
                                                 "allow_lowercase")

        assert type(token) is str and token
        assert type(variant) is str and variant
        assert self.name
        assert self.name.startswith(token.replace("/", "_"))
        assert self.name.endswith(variant)
        assert not(allow_upper is False and allow_lower is False)

        description = self.name[len(token):][:-1 * len(variant)]

        # description should be an underscore, followed by text, followed by
        # another underscore. So anything less than three characters long is not
        # really a description.
        if len(description) <= 2:
            err = self.resc.error(906)
            err.msg = err.msg.format(up_to_last_item=token.replace("/", "_"))
            raise SquirrelError(err.msg, err.code)

        # Get rid of the leading and trailing underscores.
        description = description.lstrip("_").rstrip("_")

        # Validate the case
        if not allow_upper and allow_lower:
            if not allow_lower:
                if description.islower():
                    err = self.resc.error(801)
                    err.msg = err.msg.format(description=description)
                    raise SquirrelError(err.msg, err.code)

            if not allow_upper:
                if description.isupper():
                    err = self.resc.error(802)
                    err.msg = err.msg.format(description=description)
                    raise SquirrelError(err.msg, err.code)

        return description

    # --------------------------------------------------------------------------
    def extract_metadata_from_name(self):
        """
        Given a name, extracts the metadata from it.

        :return: A tuple the returns the name broken up into tokens, desc, and
                 variant. Raises a SquirrelError with an appropriate help
                 message if the name is not properly formed.
        """

        assert type(self.name) is str and self.name
        assert type(self.repo_n) is str and self.repo_n

        # Make sure there are no doubled up underscores
        self.validate_name_underscores()

        # Validate the variant
        variant = self.validate_name_variant()

        # Check all of the tokens in the name
        tokens = self.validate_name_tokens()

        # Check to make sure there is a description
        desc = self.validate_name_desc(tokens, variant)

        # Return the results broken up into the tokens, desc, and variant
        return tokens, desc, variant

    # --------------------------------------------------------------------------
    def extract_token_from_name(self):
        """
        Given a name, extracts the token from it.

        :return: A string that is a token (i.e. if the name is:
                 asset_bldg_com_description_A, then this will return
                 asset/bldg/com).
        """

        assert type(self.name) is str and self.name
        assert type(self.repo_n) is str and self.repo_n

        metadata = self.extract_metadata_from_name()
        return metadata[0]

    # --------------------------------------------------------------------------
    def validate_name(self):
        """
        Given a name, tries to validate it. Raises a SquirrelError if it does
        not validate.

        :return: Nothing.
        """

        assert type(self.name) is str and self.name
        assert type(self.repo_n) is str and self.repo_n

        self.extract_metadata_from_name()
