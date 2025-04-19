import enum

class UserRole(str, enum.Enum):
    @classmethod
    def list(cls):
        return list(map(lambda c: c.value, cls))

    """ Defines the roles a user can have """
    BOOKER = "booker"
    MODERATOR = "moderator"