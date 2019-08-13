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

from bvzlib import resources

from librarian import librarianclient

from schema import repo


class Name(object):
    """
    A class responsible for managing and validating an asset name.

    A name consists of the following:

    Any number of tokens, followed by a description, followed by a variant.

    variants are always one or two upper case letters preceded by an underscore.

    descriptions are any text, including underscores.

    tokens are defined by the schema (and are also separated by underscores).
    """

    # --------------------------------------------------------------------------
    def __init__(self, name, repo_p, language="english"):
        """
        Init.

        :param name: The name of the asset.
        :param repo_p: The path to the root of the repo we are validating
               against.
        :param language: The language to use to communicate with the user. If
               omitted, defaults to "english".
        """

        self.name = name

        # Read in the resources
        module_d = os.path.split(inspect.stack()[0][1])[0]
        resources_d = os.path.join(module_d, "..", "..", "resources")
        self.resc = resources.Resources(resources_d, language)

        # Create a new repo object for this repo.
        self.repo = repo.Repo(repo_p, language)

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

        # Error out if there are multiple underscores
        if "__" in self.name:
            err = self.resc.error(900)
            raise NameError(err.msg)

        # Error out if the name begins with an underscore
        if self.name.startswith("_"):
            err = self.resc.error(907)
            raise NameError(err.msg)

        # Error out if there are multiple underscores
        if self.name.endswith("_"):
            err = self.resc.error(908)
            raise NameError(err.msg)

    # --------------------------------------------------------------------------
    def validate_name_variant(self):
        """
        Makes sure that the name ends with a one or two character, all caps
        variant string.

        :return: The variant. Will raise a SquirrelError with an appropriate
                 help message if the variant does not validate.
        """

        variant = self.name.split("_")[-1]

        # Assume it is there
        missing_var = False

        # Cannot be longer than two characters
        if len(variant) > 2:
            missing_var = True

        # Must exist
        if variant == "":
            missing_var = True

        # Must be an uppercase alphabetic character
        for char in variant:
            if char not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
                missing_var = True

        # If any of these fail, raise an error
        if missing_var:
            err = self.resc.error(901)
            raise NameError(err.msg)

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

        # Make sure we have no multiple underscores.
        self.validate_name_underscores()

        # Convert the name to a list
        name_elements = self.name.split("_")

        # Step through each of the tokens
        consumed_elements = list()
        for element in name_elements:

            # Build the current token and check its validity
            token_path = "/".join(consumed_elements + [element])
            if not self.repo.token_is_valid(token_path):
                break
            consumed_elements.append(element)

        # If there are consumed elements, we have a legal token. If there are no
        # consumed elements, then none of the tokens validated.
        if consumed_elements:
            token_path = "/".join(consumed_elements)
        else:
            possible_next = self.repo.get_next_tokens("")
            err = self.resc.error(904)
            err.msg = err.msg.format(possible_next=", ".join(possible_next))
            raise NameError(err.msg)

        # Though we now should have a fully legal token, this token must also
        # be a token all the way down to the leaf level.
        if not self.repo.token_is_leaf(token_path):

            # Help the user by listing what the next possible (legal) tokens are
            possible_next = self.repo.get_next_tokens(token_path)
            up_to_last_item = "_".join(consumed_elements).lstrip("_")
            err = self.resc.error(905)
            err.msg = err.msg.format(up_to_last_item=up_to_last_item,
                                     possible_next=", ".join(possible_next))
            raise NameError(err.msg)

        # Return the portion of the name that is the token
        token_str = token_path.lstrip("/").rstrip("/").replace("/", "_")
        assert self.name.startswith(token_str)

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

        assert self.name.startswith(token)
        assert self.name.endswith(variant)

        description = self.name[len(token):][:-1 * len(variant)]

        # description should be an underscore, followed by text, followed by
        # another underscore. So anything less than three characters long is not
        # really a description.
        if len(description) <= 2:
            err = self.resc.error(906)
            err.msg = err.msg.format(up_to_last_item=token)
            raise NameError(err.msg)

        # Get rid of the leading and trailing underscores.
        description = description.lstrip("_").rstrip("_")

        return description

    # --------------------------------------------------------------------------
    def extract_metadata_from_name(self):
        """
        Given a name, extracts the metadata from it.

        :return: A tuple the returns the name broken up into tokens, desc, and
                 variant. Raises a NameError with an appropriate help message if
                 the name is not properly formed.
        """

        # Make sure there are no doubled up underscores
        self.validate_name_underscores()

        # Validate the variant
        variant = self.validate_name_variant()

        # Check all of the tokens in the name
        tokens = self.validate_name_tokens()

        # Check to make sure there is a description
        desc = self.validate_name_desc(tokens, variant)

        # Return the results broken up into the repo, tokens, desc, and variant
        return tokens, desc, variant

    # --------------------------------------------------------------------------
    def validate_name(self):
        """
        Given a name, returns True if it is valid, False if not.

        :return: True if the name is valid. False otherwise.
        """

        try:
            self.extract_metadata_from_name()
        except NameError:
            return False
        return True
