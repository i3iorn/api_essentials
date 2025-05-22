import os
import base64
from typing import Optional
from dataclasses import dataclass
import logging
import threading
import uuid

# Set up logging for debugging and error reporting
logger = logging.getLogger(__name__)


# Custom exceptions for more specific error handling
class RequestIdError(Exception):
    """General error for RequestId issues."""


class InvalidIdError(RequestIdError):
    """Raised when the ID doesn't meet validation criteria."""


class EncodingError(RequestIdError):
    """Raised when encoding/decoding fails."""


# Configuration dataclass for easy management of default settings
@dataclass
class RequestIdConfig:
    length: int = 64
    prefix: Optional[bytes] = None
    debug: bool = False


# Helper classes for ID generation and validation
class IdGenerator:
    @staticmethod
    def generate(length: int, prefix: Optional[bytes] = None) -> bytes:
        """Generate a random ID with optional prefix."""
        raw = os.urandom(length - len(prefix or b''))
        return (prefix or b'') + raw


class RequestIdValidator:
    @staticmethod
    def validate(value: bytes, expected_length: int, prefix: Optional[bytes]):
        """Validate the ID's type, length, and prefix."""
        if not isinstance(value, bytes):
            raise InvalidIdError("ID must be of type 'bytes'.")
        if len(value) != expected_length:
            raise InvalidIdError(f"ID must be {expected_length} bytes long.")
        if prefix and not value.startswith(prefix):
            raise InvalidIdError("Injected ID does not match expected prefix.")


# Encoder and decoder helpers
class HexEncoder:
    @staticmethod
    def encode(value: bytes) -> str:
        """Encode bytes to hex."""
        return value.hex()

    @staticmethod
    def decode(encoded: str) -> bytes:
        """Decode hex-encoded string to bytes."""
        return bytes.fromhex(encoded)


class Base64Encoder:
    @staticmethod
    def encode(value: bytes) -> str:
        """Encode bytes to base64."""
        return base64.urlsafe_b64encode(value).rstrip(b'=').decode('ascii')

    @staticmethod
    def decode(encoded: str) -> bytes:
        """Decode base64-encoded string to bytes."""
        return base64.urlsafe_b64decode(encoded + '==')


# RequestId descriptor class
class RequestId:
    def __init__(self, config: RequestIdConfig = RequestIdConfig()):
        self._config = config
        self._private_name = None
        self._lock = threading.Lock()

        # Encoder and decoder strategies
        self._encoders = {
            'hex': HexEncoder,
            'base64': Base64Encoder
        }
        self._decoders = {
            'hex': HexEncoder,
            'base64': Base64Encoder
        }
        # Unique identifier for this descriptor instance
        self._descriptor_uuid = uuid.uuid4()

    def __set_name__(self, owner, name):
        """Set the name of the attribute this descriptor will manage."""
        self._private_name = f"_{owner.__name__}__{name}"

    def __get__(self, instance: object, owner: type) -> bytes:
        """Get the RequestId for an instance."""
        if instance is None:
            # Return descriptor's own UUID when accessed on class
            return self._descriptor_uuid

        # If ID doesn't exist, generate a new one
        if not hasattr(instance, self._private_name):
            with self._lock:
                new_id = self._generate_id()
                setattr(instance, self._private_name, new_id)
                if self._config.debug:
                    logger.debug("[RequestId] Generated new ID for %s: %s", instance, new_id)

        return getattr(instance, self._private_name)

    def __set__(self, instance: object, value: Optional[bytes]):
        # Prevent direct assignment of request_id
        raise AttributeError("Cannot set request ID directly.")

    def __delete__(self, instance: object):
        """Prevent deletion of the RequestId."""
        raise RequestIdError("RequestId cannot be deleted.")

    def _generate_id(self) -> bytes:
        """Generate a random ID with optional prefix."""
        # Generate a new UUID for each instance
        return uuid.uuid4()

    def get_encoded(self, instance: object, encoding: str = 'hex') -> str:
        """Get the encoded version of the RequestId."""
        self._ensure_instance(instance)
        raw = self.__get__(instance, instance.__class__)
        try:
            return self._encoders[encoding].encode(raw)
        except KeyError:
            raise EncodingError(f"Unsupported encoding '{encoding}'")

    def to_json(self, instance: object) -> str:
        """Return the base64-encoded RequestId."""
        return self.get_encoded(instance, encoding='base64')

    def from_encoded(self, instance: object, encoded: str, encoding: str = 'hex'):
        """Set the ID from an encoded string."""
        self._ensure_instance(instance)
        try:
            decode_fn = self._decoders[encoding].decode
            value = decode_fn(encoded)
        except (KeyError, ValueError) as e:
            raise EncodingError(f"Invalid encoded ID or unsupported encoding '{encoding}'.") from e
        self.inject(instance, value)

    def inject(self, instance: object, value: bytes):
        """Inject an ID directly into an instance."""
        self._ensure_instance(instance)
        self.__set__(instance, value)

    def is_equal(self, instance_a: object, instance_b: object) -> bool:
        """Compare two instances' RequestIds."""
        return self.__get__(instance_a, instance_a.__class__) == self.__get__(instance_b, instance_b.__class__)

    @property
    def length(self) -> int:
        """Return the length of the RequestId."""
        return self._config.length

    def _repr_(self):
        """String representation for debugging."""
        return f"<RequestId(length={self._config.length}, prefix={self._config.prefix}, debug={self._config.debug})>"

    def _ensure_instance(self, instance: object):
        """Ensure the instance is valid."""
        if instance is None:
            raise RequestIdError("Instance must not be None.")

    def _reset(self, instance: object):
        """Reset the ID for testing purposes (without changing immutability)."""
        if hasattr(instance, self._private_name):
            delattr(instance, self._private_name)

    def __eq__(self, other: object) -> bool:
        """Compare equality of two RequestId descriptors based on their unique UUID."""
        if not isinstance(other, RequestId):
            return False
        return getattr(self, '_descriptor_uuid', None) == getattr(other, '_descriptor_uuid', None)

    def __ne__(self, other: object) -> bool:
        """Inequality comparison for RequestId descriptors."""
        return not self.__eq__(other)

