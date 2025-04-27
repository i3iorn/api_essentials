import uuid


class Flag:
    """
    A class to represent a flag with a unique identifier.
    """

    def __init__(self, name: str):
        self.name = name
        self.id = uuid.uuid4().hex

    def __repr__(self):
        return f"Flag(name={self.name}, id={self.id})"

    def __eq__(self, other):
        if isinstance(other, Flag):
            return self.id == other.id
        return False

    def __hash__(self):
        return hash(self.id)



USE_DEFAULT_POST_RESPONSE_HOOK = Flag("USE_DEFAULT_POST_RESPONSE_HOOK")
FORCE_HTTPS = Flag("FORCE_HTTPS")
ALLOW_UNSECURE = Flag("ALLOW_UNSECURE")