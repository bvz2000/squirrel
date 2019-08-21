"""
This module is a very thin layer between the front end of Squirrel (the
individual connections to the DCC apps, gather, and the librarian) and the back
end repo schema (schema). This thin layer can be customized to work with
whatever back end system you are using and is the single point of contact
between the front end and the repo schema. This means you can swap out the back
end and hopefully only have to modify this one module. When replacing the code
in this module, you MUST implement all of the functions already present here.
"""

# import squirrel.application

from schema import manager


# --------------------------------------------------------------------------
def get_default_repo():
    repo_manager_obj = manager.RepoManager()
    return repo_manager_obj.default_repo


# --------------------------------------------------------------------------
def repo_name_is_valid(repo_name):
    repo_manager_obj = manager.RepoManager()
    return repo_manager_obj.repo_name_is_valid(repo_name)


# --------------------------------------------------------------------------
def file_is_within_repo(file_p,
                        repo_names,
                        check_all_repos):
    repo_manager_obj = manager.RepoManager()
    return repo_manager_obj.file_is_within_repo(file_p,
                                                repo_names,
                                                check_all_repos)


# --------------------------------------------------------------------------
def get_gather_loc():
    repo_manager_obj = manager.RepoManager()
    return repo_manager_obj.get_gather_loc()


# --------------------------------------------------------------------------
def get_publish_loc(token, repo):
    repo_manager_obj = manager.RepoManager()
    return repo_manager_obj.get_publish_loc(token, repo)
