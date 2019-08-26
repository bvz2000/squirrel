"""
License
--------------------------------------------------------------------------------
amfe is released under version 3 of the GNU General Public License.

amfe
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

import os
import re
import shutil
import tempfile

from amFe import gather


# ------------------------------------------------------------------------------
def list_references_in_scene(scene_p):
    """
    Given a path to a maya scene as an ascii file, open that scene's text file
    and extract all of the references to external files. We do this via a text
    file vs. built in maya api functions because it is MUCH easier this way
    (even if it is a bit janky).

    :param scene_p: The path to the maya ascii scene file we are testing.

    :return: A list of all the referenced files in this scene.
    """

    output = list()

    pattern = r'\s*setAttr\s+"\.ftn"\s+-type\s+"string"\s+"(.*)";\s*\n'
    with open(scene_p, "r") as f:
        line = f.readline()
        while line:
            reference = re.match(pattern, line)
            if reference:
                output.append(reference.groups()[0])
            line = f.readline()

    return output


# ------------------------------------------------------------------------------
def gather_scene(scene_p, dest=None):
    """
    Given a path to a maya ascii scene, open that scene and gather all the files
    referenced in this scene. We do this via a text file vs. built in Maya api
    functions because it is MUCH easier this way (even if it is a bit janky).

    :param scene_p: The path to the maya ascii scene we are gathering.
    :param dest: The destination where the scene should be gathered to. If
           None, then a temp directory will be generated and the references
           gathered to that location.

    :return: The directory into which the project is gathered.
    """

    if dest is None:
        gather_name = os.path.splitext(os.path.split(scene_p)[1])[0]
        dest = os.path.join(tempfile.mkdtemp(prefix="gather_"), gather_name)
        os.mkdir(dest)

    references = list_references_in_scene(scene_p)

    remapped = gather.gather_files(references, dest, None, True)

    munge_scene(scene_p, remapped, True)

    return dest


# ------------------------------------------------------------------------------
def munge_scene(scene_p, remapped, relative=True):
    """
    Given a Maya ascii scene, opens that scene and does a text replace on any
    files to point to the new location. If relative is True, then the path will
    be converted to a relative path relative to scene_p.

    :param scene_p: The path to the project we are munging.
    :param remapped: The dictionary where the key is the original path that
           would be found in a project file, and the value is the path of where
           this file has been gathered to.
    :param relative: If True, then the munged path will be made relative to
           project we are munging. Defaults to True.

    :return: Nothing.
    """

    if scene_p.endswith(".ma"):
        source_p = os.path.split(scene_p)[0]
    else:
        source_p = scene_p

    out_p = scene_p + ".out"

    with open(scene_p, "r") as f:
        with open(out_p, "w") as fOut:
            line = f.readline()
            while line:
                for key in remapped:
                    if key in line:
                        if relative:
                            rel_path = os.path.relpath(remapped[key], source_p)
                            line = line.replace(key, rel_path)
                        else:
                            line = line.replace(key, remapped[key])
                fOut.write(line + "\n")
                line = f.readline()

    shutil.copyfile(out_p, scene_p)
    os.remove(out_p + ".out")