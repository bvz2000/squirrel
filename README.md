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


USAGE
--------------------------------------------------------------------------------

ARCHITECTURE
--------------------------------------------------------------------------------

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