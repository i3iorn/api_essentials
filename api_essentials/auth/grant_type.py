from enum import Enum


class OAuth2GrantType(Enum):
    """
    Enum to represent the OAuth2 grant types.
    """
    AUTHORIZATION_CODE = "authorization_code"
    CLIENT_CREDENTIALS = "client_credentials"
    PASSWORD = "password"
    IMPLICIT = "implicit"
    REFRESH_TOKEN = "refresh_token"
    DEVICE_CODE = "device_code"
