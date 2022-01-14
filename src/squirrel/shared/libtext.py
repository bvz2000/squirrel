import os


# ----------------------------------------------------------------------------------------------------------------------
def write_to_text_file(file_p,
                       text,
                       overwrite):
    """
    Adds a freeform text to a text file located at file_p.

    :param file_p:
            The full path to the freeform text file.
    :param text:
            The string to add to this file.
    :param overwrite:
            If True, then the notes will overwrite the current set of notes, otherwise they will be appended.

    :return:
            Nothing.
    """

    assert os.path.exists(os.path.split(file_p)[0])
    assert type(text) is str
    assert type(overwrite) is bool

    if not overwrite and os.path.exists(file_p):
        open_as = "a"
    else:
        open_as = "w"

    with open(file_p, open_as) as f:
        f.write(text + "\n")
