import enum


class Flag(enum.Flag):
    """A class for creating flag enums."""

    def __str__(self):
        """Return the string representation of the flag."""
        return self.name

    def __repr__(self):
        """Return the string representation of the flag."""
        return self.name

    TRUST_UNDEFINED_PARAMETERS = enum.auto()


TRUST_UNDEFINED_PARAMETERS = Flag.TRUST_UNDEFINED_PARAMETERS