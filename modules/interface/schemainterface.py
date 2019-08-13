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
                        repo_name,
                        check_all_repos):
    repo_manager_obj = manager.RepoManager()
    return repo_manager_obj.file_is_within_repo(file_p,
                                                repo_name,
                                                check_all_repos)

# # ------------------------------------------------------------------------------
# def is_published(file_p):
#     """
#     Checks the publishing system to see if the current file path is a file that
#     is already published (i.e. being managed by the publishing system).
#
#     :param file_p: The full path to the file we are testing.
#
#     :return: True if it is being managed by the publishing system. False
#              otherwise.
#     """
#
#     squirrel_app = squirrel.application.Application()
#     return squirrel_app.item_is_in_any_repo(file_p)
#
#
# # ------------------------------------------------------------------------------
# def validate_asset_name(asset_name, repo):
#     """
#     Given a name and a repository, validates that the name is legal. If it is
#     not, raises a NameError with a description of how the name violates the
#     rules.
#
#     :param asset_name: The name being validated.
#     :param repo: The repository that knows what a legal name looks like.
#
#     :return: Nothing.
#     """
#
#     squirrel_app = squirrel.application.Application()
#     result = squirrel_app.validate_asset_name(asset_name, repo)
#
#     if not result[0]:
#         raise NameError(result[1])
#
#
# # ------------------------------------------------------------------------------
# def publish(repo, files_d):
#     """
#     Given a repository and a path to a directory of files, tell the back end
#     publishing system to publish this directory.
#
#     :param repo: The repository where we are publishing.
#     :param files_d: The directory of files to be published.
#
#     :return: Nothing (though I should return a status here I guess).
#     """
#
#     squirrel_app = squirrel.application.Application()
#     squirrel_app.publish(repo, files_d)
#
#
# # ------------------------------------------------------------------------------
# def token_is_valid(token_path):
#     """
#     Given a token path, returns whether it is valid or not.
#
#     :param token_path:
#     :return:
#     """
#
#     repo_obj = repo.
