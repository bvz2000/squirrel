#! /usr/bin/env python2
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

# TODO: Add a resources file just like squirrel
# TODO: Refactor how to handle errors (should just pass them up the chain)

import os.path
import re
import shutil
import tempfile

from fe.gather import gather
from libClarisse import libClarisse
from publisherInterface import publisherInterface

from clamError import ClamError


# ------------------------------------------------------------------------------
def pdir_to_path(path, project_p):
    """
    Given a project path, convert path to an absolute path if it contains the
    variable $PDIR. If it does not contain this variable, return path unchanged.

    :param path: The path that may or may not contain $PDIR.
    :param project_p: The path to the project against which $PDIR is referenced.

    :return: An absolute path where $PDIR has been converted to a real dir. Does
             no checking to ensure that this path actually exists.
    """

    if project_p.endswith(".project"):
        project_p = os.path.split(project_p)[0]

    path = path.replace("$PDIR", project_p)
    path = os.path.abspath(path)

    return path


# ------------------------------------------------------------------------------
def list_references_in_project(project_p):
    """
    Given a path to a clarisse project, open that project's text file and
    extract all of the references to non-clarisse files. We do this via a text
    file vs. build in clarisse api functions because it is MUCH easier this way
    (even if it is a bit janky).

    :param project_p: The path to the project we are testing.

    :return: A list of all the referenced files in this project.
    """

    output = list()

    outer_pattern = '\h*(?:filename|filename_sys)\s*(.*)\n'
    inner_pattern = '"([^"]*)"'
    with open(project_p, "r") as f:
        lines = f.readlines()

    data = ""
    for line in lines:
        if line.startswith("#preferences"):
            break
        data += line

    references = re.findall(outer_pattern, data)

    if references:

        for ref in references:
            file_names = re.findall(inner_pattern, ref)
            for file_name in file_names:
                file_name = pdir_to_path(file_name, project_p)
                if not file_name.endswith(".project"):
                    output.append(file_name)

    return output


# ------------------------------------------------------------------------------
def recursively_list_sub_projects_in_project(project_p):
    """
    Given a path to a clarisse project, open that project's text file and
    extract all of the other project tiles it references. We do this via a text
    file vs. build in clarisse api functions because it is MUCH easier this way
    (even if it is a bit janky).

    :param project_p: The path to the project we are testing.

    :return: A list of all the referenced sub-projects in this project.
    """

    output = list()

    pattern = r'\h*(?:filename|filename_sys)\s*"(.*\.project)"\s*\n'
    with open(project_p, "r") as f:
        lines = f.readlines()

    data = ""
    for line in lines:
        if line.startswith("#preferences"):
            break
        data += line

    sub_projects = re.findall(pattern, data)

    if sub_projects:

        for sub_project in sub_projects:
            sub_project = pdir_to_path(sub_project, project_p)
            output.append(sub_project)
            output.extend(recursively_list_sub_projects_in_project(sub_project))

    return output


# ------------------------------------------------------------------------------
def recursively_get_all_file_refs_in_project(project_p):
    """
    Given a project, return a tuple of two lists: 1) All projects referenced in
    this or any sub-project, and 2) All other files referenced in this or any
    sub-project.

    :param project_p: A path to the project file we are testing.

    :return: A tuple where the first element is a list of all sub-projects
             (recursively) and the second element is a list of all other, non-
             project files referenced in any of these projects.
    """

    projects = recursively_list_sub_projects_in_project(project_p)
    projects = list(set(projects))

    references = list_references_in_project(project_p)
    for sub_project_p in projects:
        references.extend(list_references_in_project(sub_project_p))
    references = list(set(references))

    return projects, references


# ------------------------------------------------------------------------------
def gather_project(project_p, dest):
    """
    Given a path to a clarisse project, open that project and recursively
    gather all the files referenced in this project or any of its references.
    We do this via a text file vs. build in clarisse api functions because it is
    MUCH easier this way (even if it is a bit janky).

    :param project_p: The path to the project we are gathering.
    :param dest: The destination where the context should be gathered to. This
           should be a directory that IS the asset directory (i.e. the
           individual files will be gathered into this directory directly).
           created.

    :return: The directory into which the project is gathered.
    """

    assert os.path.exists(dest)
    assert os.path.isdir(dest)

    projects, references = recursively_get_all_file_refs_in_project(project_p)
    projects.append(project_p)

    all_files = list()
    all_files.extend(projects)
    all_files.extend(references)

    remapped = gather.gather_files(all_files, dest, None, True)

    for key in remapped.keys():
        if key.endswith(".project"):
            munge_project(remapped[key], remapped, True)

    return dest


# ------------------------------------------------------------------------------
def munge_project(project_p, remapped, relative=True):
    """
    Given a project, opens that project and does a text replace on any files to
    point to the new location. If relative is True, then the path will be
    converted to a relative path from source_p.

    :param project_p: The path to the project we are munging.
    :param remapped: The dictionary where the key is the original path that
           would be found in a project file, and the value is the path of where
           this file has been gathered to.
    :param relative: If True, then the munged path will be made relative to
           project we are munging. Defaults to True.

    :return: Nothing.
    """

    if project_p.endswith(".project"):
        source_p = os.path.split(project_p)[0]
    else:
        source_p = project_p

    out_p = project_p + ".out"

    with open(project_p, "r") as f:
        with open(out_p, "w") as fOut:
            line = f.readline()
            while line:
                for key in remapped:
                    if key in line:
                        if relative:
                            rel_path = os.path.relpath(remapped[key], source_p)
                            rel_path = os.path.join("$PDIR", rel_path)
                            line = line.replace(key, rel_path)
                        else:
                            line = line.replace(key, remapped[key])
                fOut.write(line + "\n")
                line = f.readline()

    shutil.copyfile(out_p, project_p)
    os.remove(out_p + ".out")


# ------------------------------------------------------------------------------
def gather_context(context, dest):
    """
    Given a context, gather all of the files in it (and any referenced
    contexts).

    :param context: The context we want to gather.
    :param dest: The destination where the context should be gathered to. This
           should be a directory, inside of which the asset directory will be
           created (i.e. the individual files will be gathered into a sub-dir
           inside this dir that is named the same as the context).

    :return: The directory where the context was gathered. I.e. the sub-dir of
             dest that is the gathered context.
    """

    assert(context.is_context())
    assert(os.path.exists(dest))
    assert(os.path.isdir(dest))

    if not libClarisse.contexts_are_atomic(context):
        raise ClamError("Context is not atomic", 1001)

    temp_project_dir = tempfile.mkdtemp(prefix="temp_project_")

    exported_p = libClarisse.export_context_with_deps(context, temp_project_dir,
                                                      True)

    dest = os.path.join(dest, context.get_name())

    try:
        gather_project(exported_p, dest)
    except IOError as e:
        # TODO: This needs to be fixed
        print e

    os.remove(exported_p)

    return dest


# ------------------------------------------------------------------------------
def publish_context(context, repo=None):
    # TODO: how do I reconcile the need to pass a repo with trying to be back
    # TODO: end agnostic?
    """
    Given a context, gather all of the files in it (and any referenced
    contexts) to a temp location. Then publish these files to the publishing
    back end.

    :param context: The context we want to gather.
    :param repo: The repository to publish to. If None, then the default
           repository will be used. Defaults to None.

    :return: The directory where the context was gathered.
    """

    assert(context.is_context())

    if not libClarisse.contexts_are_atomic(context):
        raise ClamError("Context is not atomic", 1001)

    asset_name = context.get_name()
    publisherInterface.validate_asset_name(asset_name, repo)

    dest = os.path.join(tempfile.mkdtemp(prefix="gather_"), context.get_name())
    os.mkdir(dest)

    gather_loc = gather_context(context, dest)

    publisherInterface.publish(repo, gather_loc)
    # TODO: Delete the gather_loc, return the path to the published project


# ------------------------------------------------------------------------------
def publish_context_as_ref(context, repo=None):
    """
    Given a context, gather all of the files in it (and any referenced
    contexts) to a temp location. Then publish these files to publishing back
    end. Replace the context with a reference to the published project.

    :param context: The context we want to gather.
    :param repo: The back end repository to publish to. If None, then the
           default repository will be used. Defaults to None.

    :return: The directory where the context was gathered.
    """

    assert(context.is_context())

    if not libClarisse.contexts_are_atomic(context):
        raise ClamError("Context is not atomic", 1001)

    published_project = publish_context(context, repo)

    # TODO: Replace the local context with a reference to the published project


# ------------------------------------------------------------------------------
def validate_names(names):
    """
    Given a list of asset names, returns None if all of the names are valid.
    Returns a dictionary if any of the names are not valid). The key is the
    name that is not valid, and the value is a string describing how the name
    is not valid.

    :param names: A list of asset names (in string format).

    :return: None if all of the names are valid. If any are invalid, returns a
             dictionary where the keys are any names that are not valid and the
             values are the reasons why the names are not valid.
    """
    # TODO: Implement
    pass
