import logging
import uuid
from typing import Optional, Any

logger = logging.getLogger(__name__)

class RequestIdError(Exception):
    """General error for RequestId issues."""

class EncodingError(RequestIdError):
    """Raised when encoding/decoding fails."""

class RequestId:
    """
    Descriptor for generating and managing a per-instance UUID4 request ID.
    Provides hex and base64 encoding/decoding utilities.
    """
    def __init__(self) -> None:
        self._private_name: Optional[str] = None
        self._descriptor_uuid: uuid.UUID = uuid.uuid4()

    def __set_name__(self, owner: type, name: str) -> None:
        self._private_name = f"_{owner.__name__}__{name}"

    def __get__(self, instance: Optional[Any], owner: type) -> uuid.UUID:
        if instance is None:
            return self._descriptor_uuid
        if not hasattr(instance, self._private_name):
            new_id = self._generate_id()
            setattr(instance, self._private_name, new_id)
            logger.debug("[RequestId] Generated new ID for %s: %s", instance, new_id)
        return getattr(instance, self._private_name)

    def __set__(self, instance: Any, value: Any) -> None:
        raise AttributeError("Cannot set request ID directly.")

    def __delete__(self, instance: Any) -> None:
        raise AttributeError("Cannot delete request ID.")

    def _generate_id(self) -> uuid.UUID:
        return uuid.uuid4()

    def get_encoded(self, instance: Any, encoding: str = 'hex') -> str:
        """Get the encoded version of the RequestId."""
        raw = self.__get__(instance, instance.__class__)
        if encoding == 'hex':
            return raw.hex
        elif encoding == 'base64':
            import base64
            return base64.urlsafe_b64encode(raw.bytes).rstrip(b'=').decode('ascii')
        else:
            raise EncodingError(f"Unsupported encoding '{encoding}'")

    def to_json(self, instance: Any) -> str:
        """Return the base64-encoded RequestId."""
        return self.get_encoded(instance, encoding='base64')

    def from_encoded(self, instance: Any, encoded: str, encoding: str = 'hex') -> None:
        """Set the ID from an encoded string (not supported for immutability)."""
        raise AttributeError("Cannot set request ID directly.")

    def inject(self, instance: Any, value: uuid.UUID) -> None:
        """Inject an ID directly into an instance (not supported for immutability)."""
        raise AttributeError("Cannot set request ID directly.")

    def is_equal(self, instance_a: Any, instance_b: Any) -> bool:
        return self.__get__(instance_a, instance_a.__class__) == self.__get__(instance_b, instance_b.__class__)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, RequestId):
            return False
        return getattr(self, '_descriptor_uuid', None) == getattr(other, '_descriptor_uuid', None)

    def __ne__(self, other: object) -> bool:
        return not self.__eq__(other)

    def _reset(self, instance: Any) -> None:
        if hasattr(instance, self._private_name):
            delattr(instance, self._private_name)
