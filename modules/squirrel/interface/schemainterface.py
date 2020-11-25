
from squirrel.schema import repomanager


# ==============================================================================
class SchemaInterface(object):
    """
    A very thin layer between the front end of Squirrel (the individual
    connections to the DCC apps, gather, and the librarian) and the back end
    repo schema (schema). This thin layer can be customized to work with
    whatever back end system you are using and is the single point of contact
    between the front end and the repo schema. This means you can swap out the
    back end and hopefully only have to modify this one module. When replacing
    the code in this module, you MUST implement all of the functions already
    present here.
    """

    # --------------------------------------------------------------------------
    def __init__(self,
                 language="english"):
        """
        Initialize the interface.

        :param language: The language used for communication with the end user.
               Defaults to "english".

        :return: Nothing.
        """

        self.repo_manager_obj = repomanager.RepoManager(language)

    # --------------------------------------------------------------------------
    def list_repos(self):
        return self.repo_manager_obj.list_repos()

    # --------------------------------------------------------------------------
    def list_broken_repos(self):
        return self.repo_manager_obj.list_broken_repos()

    # --------------------------------------------------------------------------
    def get_default_repo(self):
        return self.repo_manager_obj.default_repo

    # --------------------------------------------------------------------------
    def set_default_repo(self,
                         repo_n):
        self.repo_manager_obj.set_default_repo(repo_n)

    # --------------------------------------------------------------------------
    def get_repo_root(self,
                      repo_n):
        return self.repo_manager_obj.get_repo_root(repo_n)

    # --------------------------------------------------------------------------
    def repo_name_is_valid(self,
                           repo_n):
        return self.repo_manager_obj.repo_name_is_valid(repo_n)

    # --------------------------------------------------------------------------
    def remove_repo_from_config(self,
                                repo_n):
        self.repo_manager_obj.remove_repo_from_config(repo_n)

    # --------------------------------------------------------------------------
    def add_repo_to_config(self,
                           repo_p):
        self.repo_manager_obj.add_repo_to_config(repo_p)

    # --------------------------------------------------------------------------
    def list_assets_in_repo(self,
                            repo_n,
                            token,
                            keywords):
        return self.repo_manager_obj.list_asset_names_in_repo(repo_n,
                                                              token,
                                                              keywords)

    # --------------------------------------------------------------------------
    def file_is_within_repo(self,
                            file_p,
                            repo_names,
                            check_all_repos):
        return self.repo_manager_obj.file_is_within_repo(file_p,
                                                         repo_names,
                                                         check_all_repos)

    # --------------------------------------------------------------------------
    def get_gather_loc(self):
        return self.repo_manager_obj.get_gather_loc()

    # --------------------------------------------------------------------------
    def get_publish_loc(self,
                        token,
                        repo):
        return self.repo_manager_obj.get_publish_loc(token, repo)

    # --------------------------------------------------------------------------
    def token_is_valid(self,
                       token,
                       repo):
        return self.repo_manager_obj.token_is_valid(token, repo)

    # --------------------------------------------------------------------------
    def get_next_tokens(self,
                        token,
                        repo):
        return self.repo_manager_obj.get_next_tokens(token, repo)

    # --------------------------------------------------------------------------
    def token_is_leaf(self,
                      token,
                      repo):
        return self.repo_manager_obj.token_is_leaf(token, repo)

    # --------------------------------------------------------------------------
    def bless_tree(self,
                   tree_p,
                   repo_n):
        self.repo_manager_obj.bless_tree(tree_p, repo_n)

    # --------------------------------------------------------------------------
    def bless_root(self,
                   dir_p,
                   root_p,
                   repo_n):
        self.repo_manager_obj.bless_dir(dir_p,
                                        root_p,
                                        repo_n)

    # --------------------------------------------------------------------------
    def bless_dir(self,
                  dir_p):
        self.repo_manager_obj.bless_dir(dir_p)
