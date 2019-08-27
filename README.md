# squirrel

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

Description
--------------------------------------------------------------------------------
Squirrel is an asset management tool designed for individuals or small
DCC (Digital Content Creation) studios. It is an open-source python tool 
that runs under Linux and MacOS. At the moment, it does not run under
Windows, though this is planned for a future release. It was developed on a
Linux Manjaro system running Python 2.7.

# NOTE: Squirrel is in pre-alpha and does not fully work yet.

Features that will be part of the 1.0 release:
--------------------------------------------------------------------------------

- storing multiple versions of the same asset with file-level deduplication (so publishing the same asset 1000 times will only store changed files and not every single file every single time).
- arbitrary "pinning" of different versions so that, for example, version 2 of an asset can be pinned as "previs" and version 6 can be pinned as "trailer".
- awareness of already published assets and files so that assets can refer to each other, still be versioned up, and not lose connections to these other assets (this allows for compound assets).
- free-form naming structure. Squirrel will allow you to have pretty much any structure you want simply by creating the directories on disk).
- optional name validation: If you want, it will enforce names to match whatever structure you have come up with (currently still requiring a description and variant) OR it can accept any name whatsoever, but still store the asset in a location that is enforced by you.
- multiple repositories available at the same time, so you can separate assets by use (say, studio assets vs. show specific assets).
- works completely on the command line if needed, but also is being integrated into Clarisse and Maya right out of the box. It can be adapted to pretty much any DCC application as long as that application can run Python scripts. Even if that app cannot run Python, it might still be able to be integrated as long as there are some minimum requirements met (some sort of scripting language, some sort of method for extracting external file paths).
- no need for a database.
- assets are 100% relocatable simply by copying or moving their directories (even can be done in the finder with a simple dragging of an asset from one location to another).
- storage of metadata and keywords for each check-in of each asset.
- storage of notes for each check-in of each asset.
- storage of (deduplicated) thumbnails and turntables for each check-in of each asset.
- no external dependencies other than Python and a single, separate library also distributed by me.
- designed to be modular so that if a studio already has a partial asset management system in place, it is possible (with varying degrees of difficulty depending on the existing asset management system) to integrate parts of Squirrel into that. That said, this is not a trivial undertaking, and may not even be fully possible in many circumstances.
- ready to be localized into other languages.
- a metric ton of bugs no doubt!!!!!!!

Missing features planned for 1.1 release:
--------------------------------------------------------------------------------

- Documentation. It isn't an especially difficult system to use, but without docs, it will almost be useless to most people.

Missing features planned for 1.2 release:
--------------------------------------------------------------------------------

- a GUI. Currently squirrel only runs from the command line or from within Clarisse or Maya. I'd like to have a simple UI that manages assets, etc. Probably a web-based UI because it will be cross platform.
- ability to search the metadata, keywords, and notes.
- blender integration
- a UI for browsing thumbnails and turntables, including searches by metadata, keywords, and notes. GIve this UI the ability to load assets into a DCC application. Probably also web-based.

Missing features planned for 1.3 release:
--------------------------------------------------------------------------------

- a client server mode. Currently Squirrel expects to run on a single network (like within a single studio). It want will eventually be able to work over the internet and share assets from a single repository to multiple different users who may or may not be online at the same time. It should also handle slow connections by duplicating the necessary data to the local network. There are hooks in the current code to do this, but it will take a fair bit of work to get it finalized.

Missing features planned for 1.4 release:
--------------------------------------------------------------------------------

- Windows compatibility. Squirrel was written to be as OS agnostic as possible. But the deduplication features depend on a UNIX-like filesystem. It is possible that Squirrel might already run under WSL (Linux Subsystem for Windows). But proper Windows compatibiity will require that I modify the bits of code that use symbolic links. I think this is the only bits that are not Windows compatible. This should hopefully not be too hard, but it is also a really really low priority for me at the moment since I don't do Windows myself.




# DOCUMENTATION

Installation
--------------------------------------------------------------------------------

Installation is fairly basic. 

1) Download the Squirrel .zip file from Github.
https://github.com/bvz2000/squirrel

2) Unzip this file into a location of your choosing. This will be the location
where Squirrel will run from, so you may wish to choose a location that makes
sense for your particular network. Under MacOS, I am installing it directly into
/Applications. But this is a fairly unorthodox way to install a Python tool. You
should do what you will in this regard.

3) Set your python PATH to point to the modules sub-directory of the Squirrel
directory. For example, if you installed it to -- /Applications/Squirrel -- 
then the path you are adding to your python path should be: -- 
/Applications/Squirrel/modules

4) Download the bvzlib library from Github. This is a series of generic
functions that Squirrel needs to run. https://github.com/bvz2000/bvzlib

5) As before, unzip this file to a location of your choosing. I install mine
into /Applications/libraries. But once again, this is a VERY unorthodox location
for a python library. Install yours where you will.

6) Add another path to your python PATH variable that points to the modules
sub-directory of the bvzlib directory. For example, if you installed it to:
-- /Applications/libraries/bvzlib -- then the path you are adding to your
python path should be: -- /Applications/libraries/bvzlib/modules

7) Set your PATH to point to the bin directory of Squirrel. Again, using the
above example, the path you would be adding to your PATH variable would be: -- 
/Applications/Squirrel/bin

That is it.  From here, you can use the command: "squirrel -h" to get a list of
options. Each option has its own help. So, for example, if you wanted to get
help on publishing, you would issue the command:

squirrel publish -h



ARCHITECTURE
--------------------------------------------------------------------------------
![image](https://user-images.githubusercontent.com/31168744/63748777-da82d880-c85e-11e9-9730-ad3aaf7a0448.png)

Squirrel consists of a few basic parts.

On the back end, there are several packages:

schema: Manages the structure of the "database" that organizes down to the
asset level, but does not manage the internal structure of an asset. These
structures are known as "repos".

store: Manages the internal structure of an asset, including all metadata,
versioning, and deduplication.

name: Helper to convert strings to locations in the repo.

On the front end there are the DCC applications as well as a number of command
line tools:

squirrel-env
squirrel-collapse
squirrel-gather
squirrel-keyword
squirrel-metadata
squirrel-notes
squirrel-pin
squirrel-thumbnail
squirrel-publish
squirrel-store
squirrel-schema

With the exception of squirrel-schema and squirrel-env, each of these front-end
tools communicates with a thin layer called the "librarian".

The librarian's sole purpose to to either communicate with a second instance of
itself, but located on a remote server OR to communicate with the interface
layer on the local machine. Note: currently only the local mode is functional.

The interface layer is another thin layer who's sole purpose is to separate the
individual packages from each other so as to allow a (relatively) painless
substitution of different back end packages. For example, the schema could be
swapped out for a custom schema at a particular studio, and the only modifications
to Squirrel would happen in the interface layer. The rest of the tool would not
need to be modified in any way.

QUICK START
-
A basic primer on how to use Squirrel involves first creating one or more repos
to store data.

A repo is nothing more than a directory structure somewhere on disk. An example
would be:

```
repo
    asset
       bldg
       veh
       char
       prop
    material
       bldg
       veh
       char
       prop
    hdri
       interior
       exterior
```
Once this structure has been created, it needs to be "blessed" using the squirrel-schema tool.
Once blessed, this is now a full-fledged repository on disk. The structure of this
repo (via the directories on disk) acts as an organizational structure for your assets.
An asset may only exist in a single location, somewhat limiting the usefulness that you
might get from a more database-centric asset manager. The flip side, however, is the
absolute simplicity of this system. Assets are fully self-contained, including any and all
metadata. Deleting an asset is as simple as deleting the directory it is in. Moving an
asset is no more difficult than moving or copying this same directory. You can duplicate
assets from one repo to another. You can store as many different repos on disk as you like.
Storing a robust set of keywords and metadata can offer many of the same benefits of a more
complicated, database controlled asset management system.

The only restriction is that a repo may not exist within another repo. See the help for the squirrel-schema tool
for more information and options when managing repos.

Once a repo (or several) has been created, the most common next step would be to "gather" files together in
preparation for publishing. Gathering files essentially makes copies of these files, no
matter where they live on disk, into a single, structured directory. These files will be
sorted into sub-directories within this directory based on file type. Use the squirrel-gather
tool to accomplish this task. Note: You do NOT have to gather your files before publishing.
You may publish any directory or single file you wish without first gathering. The only
purpose to gathering files is that the publish does not accept more than a single path. If you have
files that are distributed across the filesystem that you wish to have published as a single
asset, then gather them first.

Next, this directory of gathered files (or any directory or file on disk) may be published (with versioning and de-duplication)
to the repo of your choice, using the squirrel-publish tool. Again, see the help message for
this tool for more information. 

There are also plugins that run in some DCC applications (Clarisse iFX and Maya at the moment)
that handle much of this for you. These plugins are currently not functional, but will be
brought online in the very near future.

User Guide
-
Coming soon.


TO DO
--------------------------------------------------------------------------------
I am rapidly approaching the alpha release.

Here are a few notes for my own use:

make store create symlinks to the current metadata dir, and have that move when
CURRENT gets moved. Same with LATEST.

make symlinks for each PIN that is the pin name, preceded by a dot, that points
to the metadata dir for that pin (and gest moved/deleted when the pin does).

Do a general clean up on the resources files (some may be deleted I am sure).

Verify the ENV vars are all there and all work.

make squirrel bin app fail better when the user enters a wrong command.

make squirrel bin app auto-complete with tab.