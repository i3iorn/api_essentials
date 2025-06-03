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
    RequestId Class

    The `RequestId` class is a descriptor designed to generate and manage a unique UUID4-based request ID for each instance of a class where it is used. It provides utilities for encoding, decoding, and comparing these IDs, ensuring immutability and uniqueness.

    Attributes:
        _private_name (Optional[str]): The private attribute name used to store the request ID in the instance.
        _descriptor_uuid (uuid.UUID): A unique UUID4 assigned to the descriptor itself.

    Methods:
        __set_name__(owner: type, name: str) -> None:
            Sets the private attribute name for the descriptor when the owning class is defined.

        __get__(instance: Optional[Any], owner: type) -> uuid.UUID:
            Retrieves the request ID for the given instance. If the instance does not already have an ID, a new one is generated.

        __set__(instance: Any, value: Any) -> None:
            Prevents setting the request ID directly, ensuring immutability.

        __delete__(instance: Any) -> None:
            Prevents deleting the request ID, ensuring immutability.

        _generate_id() -> uuid.UUID:
            Generates a new UUID4.

        get_encoded(instance: Any, encoding: str = 'hex') -> str:
            Returns the encoded version of the request ID for the given instance. Supports 'hex' and 'base64' encodings.

        to_json(instance: Any) -> str:
            Returns the base64-encoded version of the request ID for JSON serialization.

        from_encoded(instance: Any, encoded: str, encoding: str = 'hex') -> None:
            Raises an error as setting the ID from an encoded string is not supported.

        inject(instance: Any, value: uuid.UUID) -> None:
            Raises an error as directly injecting an ID is not supported.

        is_equal(instance_a: Any, instance_b: Any) -> bool:
            Compares the request IDs of two instances for equality.

        __eq__(other: object) -> bool:
            Compares the descriptor's UUID with another `RequestId` instance for equality.

        __ne__(other: object) -> bool:
            Checks inequality between two `RequestId` instances.

        _reset(instance: Any) -> None:
            Resets the request ID for an instance by deleting the private attribute (used internally).

    Usage:
        The `RequestId` class is typically used as a descriptor in other classes to automatically assign and manage unique request IDs for each instance.

    Example:
        ```python
        class Example:
            request_id = RequestId()

        obj = Example()
        print(obj.request_id)  # Outputs a unique UUID4
        print(obj.request_id.get_encoded(obj, encoding='hex'))  # Outputs the hex-encoded UUID
        ```
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

    def _get_encoded(self, encoding: str = 'hex') -> str:
        """Get the encoded version of the RequestId."""
        if encoding == 'hex':
            return self._descriptor_uuid.hex
        elif encoding == 'base64':
            import base64
            return base64.urlsafe_b64encode(self._descriptor_uuid.bytes).rstrip(b'=').decode('ascii')
        else:
            raise EncodingError(f"Unsupported encoding '{encoding}'")

    def to_hex(self) -> str:
        """Return the hex-encoded RequestId."""
        return self._get_encoded(encoding='hex')

    def to_base64(self) -> str:
        """Return the base64-encoded RequestId."""
        return self._get_encoded(encoding='base64')

    def to_json(self) -> str:
        """Return the base64-encoded RequestId."""
        encoded = self._get_encoded(encoding='base64')
        return encoded

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
