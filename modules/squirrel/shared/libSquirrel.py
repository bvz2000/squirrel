import re


# ------------------------------------------------------------------------------
def validate_version(version,
                     version_prefix="v",
                     num_digits=4):
    """
    Returns True if the version matches the pattern.

    :param version: The version string being tested.
    :param version_prefix: The prefix of the version number. Defaults to "v".
    :param num_digits: The number of padding digits in the version number.
           Defaults to 4.

    :return: True if the version matches the pattern. False otherwise.
    """

    assert type(version) is str
    assert type(version_prefix) is str
    assert type(num_digits) is int

    digits_pattern = "[0-9]{" + str(num_digits) + "}"

    pattern = "^" + version_prefix + digits_pattern + "$"

    return not re.match(pattern, version) is None
