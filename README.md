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
Linux CentOS 7 system running Python 3.7.11.

# NOTE: Squirrel is in late alpha stage. The majority of its functions are complete, though there are features planned for future releases that have not yet been implemented. I am hoping to have a beta release available by mid Feb, 2022.

Features that will be part of the 1.0 release:
--------------------------------------------------------------------------------

- storing multiple versions of the same asset with file-level deduplication (so publishing the same asset 1000 times will only store changed files and not every single file every single time).
- arbitrary "pinning" of different versions so that, for example, version 2 of an asset can be pinned as "previs" and version 6 can be pinned as "trailer".
- awareness of already published assets and files so that assets can refer to each other, still be versioned up, and not lose connections to these other assets (this allows for compound assets).
- free-form naming structure. Squirrel will allow you to have pretty much any structure you want simply by creating the directories on disk).
- multiple repositories available at the same time, so you can separate assets by use (say, studio assets vs. show specific assets).
- works completely on the command line if needed, but also is being integrated into Clarisse and Maya right out of the box. It can be adapted to pretty much any DCC application as long as that application can run Python scripts. Even if that app cannot run Python, it might still be able to be integrated as long as there are some minimum requirements met (some sort of scripting language, some sort of method for extracting external file paths).
- no need for a database.
- assets are 100% relocatable simply by copying or moving their directories (even can be done in the finder with a simple dragging of an asset from one location to another).
- storage of metadata and keywords for each asset.
- storage of notes for each check-in of each asset (either on asset level or per check-in level).
- storage of (deduplicated) thumbnails and turntables for each check-in of each asset.
- no external dependencies other than Python and a series of python libraries (also developed by me)
- ready to be localized into other languages.

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

- a client server mode. Currently, Squirrel expects to run on a single network (like within a single studio). It will eventually be able to work over the internet and share assets from a single repository to multiple different users who may or may not be online at the same time.

Missing features planned for 1.4 release:
--------------------------------------------------------------------------------

- Windows compatibility. Squirrel was written to be as OS-agnostic as possible. But the deduplication features depend on a UNIX-like filesystem (symlinks to be specific). It is possible that Squirrel might already run under WSL (Linux Subsystem for Windows). But proper Windows compatibility will require that I modify the bits of code that use symbolic links to create windows symlinks. I think these are the only bits that are not Windows compatible.




# DOCUMENTATION

Installation
--------------------------------------------------------------------------------

Installation instructions coming as a part of the documentation process.


ARCHITECTURE
--------------------------------------------------------------------------------
Architecture description coming as a part of the documentation process.

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
Once this structure has been created, it needs to be "blessed" using the squirrel command line tool.
Once blessed, this is now a full-fledged repository on disk. The structure of this repo (via the directories on disk) acts as an organizational structure for your assets.

Assets are fully self-contained, including any and all metadata. Deleting an asset is as simple as deleting the directory it is in. Moving an asset is no more difficult than moving or copying this same directory. You can duplicate assets from one repo to another. You can store as many different repos on disk as you like.
Storing a robust set of keywords and metadata can offer many of the same benefits of a more complicated, database controlled asset management system.

Repos may not exist within another repo.

Once a repo (or several) has been created, the most common next step would be to publish files or a directory to the repo. Squirrel does file-level deduplication so multiple publishes with minor file changes do not necessarily take up a lot of space.

User Guide
-
Coming as a part of the documentation process.


Here is a list of the current state of squirrel's abilities:

The following functions are fully functional:

    make-repo (mr)       
                        MAKE NEW REPOSITORY
                        Takes the given directory and turns it (and all sub-
                        directories) into a repository and adds that
                        repository to the list of active repos. Use this
                        command if you want to create a brand new repository
                        out of an existing directory structure. The directory
                        passed must already exist on disk.
                         
                        If you are just adding an already created repository
                        to the list of repositories, use the add-repo command.
                        You may add sub-directories to this newly created repo
                        at any time in the future and re-build the repo
                        structure by using the rebuild-repo command.
                         
    add-repo (ar)        
                        ADD EXISTING REPOSITORY
                        Takes the given directory and - assuming it is a
                        legal, existing repository - adds that repository to
                        the list of active repos. Use this command if there is
                        an existing repository on disk that you want to add to
                        your system. The directory passed must already exist
                        on disk and be a valid repository.
                         
                        If you want to create a NEW repository out of an
                        existing directory structure, use the make-repo
                        command.
                         
    remove-repo (remr)   
                        REMOVE EXISTING REPOSITORY
                        Removes the give repo from the list of active repos.
                        Note: This does NOT delete the repo. It merely removes
                        it from the internal list of active repos. If you want
                        to re-add this repo again at any time in the future,
                        simply use the add-repo command. If you want to
                        actually delete the repo from disk, use your standard
                        file system tools to delete the directories that
                        contain the repo.
                         
    rebuild-repo (rr)    
                        REBUILD EXISTING REPOSITORY
                        Takes the given repository and  - assuming it is a
                        legal, existing repository - rebuilds the associated
                        repository structure. This is entirely non-destructive
                        and can be run on existing repos without any danger.
                        Used primarily when new sud-directories are added to
                        an existing repo and these sub-directories need to be
                        added to the repo structure.
                         
    list-repos (lr)      
                        LIST ACTIVE REPOSITORIES
                        Lists all of the active repos.
                         
    list-missing_repos (lmr)
                        LIST MISSING REPOSITORIES
                        Lists all of the active repos that do not actually
                        exist on disk.
                         
    remove-missing_repos (rmr)
                        REMOVE MISSING REPOSITORIES
                        Removes any active repos that do not actually exist on
                        disk. Note: this is always a safe action and does not
                        remove any data from disk.
                         
    list-default-repo (ldr)
                        LIST DEFAULT REPOSITORY
                        Displays the default repo if it exists and is valid.
                         
    set-default-repo (sdr)
                        SET THE DEFAULT REPOSITORY
                        Set the default repo. Must be a valid repo name.
                         
    update-repo-caches (urc)
                        UPDATE REPOSITORY CACHE
                        Forces the repository to update its cache file. Note:
                        this is always a safe operation and does not destroy
                        any data on disk.
                         
    list-cache-path (lcp)
                        LIST CACHE PATH
                        Displays the path to the cache file.
                         
    list-assets (la)     
                        LIST ASSETS
                        Lists all of the assets in a repo (or a subset of
                        these assets based on categories, metadata, or
                        keywords).
                         
    list-keywords (lk)   
                        LIST KEYWORDS
                        Lists all of the keywords used anywhere in a repo.
                         
    add-keywords (ak)    
                        ADD KEYWORDS TO ASSET
                        Add keywords to a specific asset.
                         
    delete-keywords (dk)
                        DELETE KEYWORDS FROM ASSET
                        Delete specific keywords from a specific asset.
                         
    delete-all-keywords (dak)
                        DELETE ALL KEYWORDS FROM ASSET
                        Delete all of the keywords from a specific asset.
                         
    list-metadata (lm)   
                        LIST METADATA
                        Lists all of the metadata KEYS used anywhere in a
                        repo.
                         
    add-metadata (am)    
                        ADD METADATA TO ASSET
                        Add metadata (key=value pairs) to a specific asset.
                         
    delete-metadata (dm)
                        DELETE METADATA FROM ASSET
                        Delete specific metadata from a specific asset. Note:
                        this deletes the metadata in total (both key AND
                        value), not just the value of the metadata.
                         
    delete-all-metadata (dam)
                        DELETE ALL METADATA FROM ASSET
                        Delete all metadata from a specific asset. Note: this
                        deletes the metadata in total (both key AND value),
                        not just the value of the metadata.
                         
    list-version-notes (lvn)
                        LIST VERSION NOTES ON ASSET
                        Lists the notes for a specific version of a specific
                        asset.
                         
    add-version-notes (avn)
                        ADD VERSION NOTES TO ASSET
                        Add notes to a specific version of a specific asset.
                         
    delete-version-notes (dvn)
                        DELETE VERSION NOTES FROM ASSET
                        Delete notes from a specific version of a specific
                        asset.
                         
    list-asset-notes (lan)
                        LIST NOTES ON ASSET
                        Lists the notes on an asset. These are the asset-level
                        notes, not version level notes.
                         
    add-asset-notes (aan)
                        ADD NOTES TO ASSET
                        Add notes to an asset. These are the asset-level
                        notes, not version level notes.
                         
    delete-asset-notes (dan)
                        DELETE NOTES FROM ASSET
                        Delete notes from an asset. These are the asset-level
                        notes, not version level notes.
                         
    list-thumbnails (lt)
                        LIST THUMBNAILS
                        List thumbnail files from a specific version of a
                        specific asset.
                         
    add-thumbnails (at)
                        ADD THUMBNAILS TO ASSET
                        Add thumbnail files to a specific version of a
                        specific asset.
                         
    delete-thumbnails (dt)
                        DELETE THUMBNAILS FROM ASSET
                        Delete thumbnail files from a specific version of a
                        specific asset.
                         
    set-pin (sp)         
                        SET PIN ON ASSET
                        Sets a pin pointing to a specific version within an
                        asset.
                         
    delete-pin (dp)      
                        DELETE PIN ON ASSET
                        Deletes a pin (if it is unlocked).
                         
    lock-pin (lp)        
                        LOCK PIN
                        Locks a pin on one or more assets (locked pins may not
                        be deleted or reassigned).
                         
    unlock-pin (up)      
                        UNLOCK PIN
                        Unlocks a pin on an assets (unlocked pins may be
                        deleted or reassigned).
                         
    publish (p)          
                        PUBLISH
                        Publishes a file, list of files, or directory to a
                        repo.
                         
    delete-version (dv)
                        DELETE VERSION
                        Removes the specified version from an asset.
                         
    collapse (c)         
                        COLLAPSE
                        Removes all versions from an asset except the latest
                        version.
                         
    display-log (dl)     
                        DISPLAY LOG
                        Displays the log for a specific asset.
