class SquirrelError(Exception):
    """
    Squirrel exception
    """

    def __init__(self, message, errno=0):

        super(SquirrelError, self).__init__()

        self.code = errno
        self.message = message

    @property
    def errno(self):
        return self.code
