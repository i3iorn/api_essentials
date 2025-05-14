import httpx
from httpx import Auth


class NoAuth(Auth):
    """
    No authentication class for httpx.
    This class does not perform any authentication and is used when no authentication is required.
    """
    def __call__(self, request: httpx.Request) -> httpx.Request:
        return request
