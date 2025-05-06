import inspect
import json
from typing import Union, Any, Dict

import httpx

from api_essentials.auth.flow import AUTHORIZATION_HEADER_NAME
from api_essentials.logging_decorator import log_method_calls


@log_method_calls()
class HTTPFormatter:
    @classmethod
    def _format_request_line(cls, request: httpx.Request, http_version: str) -> str:
        """
        Build the start-line of the HTTP request, e.g.:
            GET /path?query=1 HTTP/1.1
        """
        url = request.url
        # Use raw_path to preserve percent-encoding; fallback to .path if needed
        try:
            path = url.raw_path.decode("utf-8")
        except (AttributeError, UnicodeDecodeError):
            path = url.path
        if url.query:
            path = f"{path}?{url.query}"
        return f"{request.method} {path} HTTP/{http_version}"

    @classmethod
    def _format_headers(cls, headers: httpx.Headers) -> str:
        """
        Join all headers into the canonical "Name: value" form, one per line.
        """
        return "\r\n".join(f"{name}: {value}" if name.lower() != AUTHORIZATION_HEADER_NAME.lower() else f"{name}: [secure]" for name, value in headers.items())

    @classmethod
    def _format_body(cls, body: Union[bytes, str, None]) -> str:
        """
        Decode bytes to UTF-8 (with replacement), or pass through string bodies.
        Returns an empty string if there's no body.
        """
        if body is None:
            return ""
        if isinstance(body, bytes):
            return body.decode("utf-8", errors="replace")

        body_dict = json.loads(body)
        for key, value in body_dict.items():
            if any(
                ["token" in key.lower(),
                "secret" in key.lower(),
                "password" in key.lower()]
            ):
                body_dict[key] = "[secure]"
        body = json.dumps(body_dict, indent=4, ensure_ascii=False)
        return body

    @classmethod
    def format_raw_http_request(cls, request: httpx.Request) -> str:
        """
        Convert an httpx.Response into the full raw HTTP request text, including:
          1. Request-Line (method, path+query, version)
          2. All request headers
          3. A blank line, then the request body (if any)

        :param response: The httpx.Response whose underlying request we want to reconstruct.
        :return: A single string containing the raw HTTP request.
        """
        # Use the negotiated HTTP version from the response (e.g. "1.1" or "2")
        http_version = getattr(request, "http_version", "1.1")

        request_line = cls._format_request_line(request, http_version)
        headers = cls._format_headers(request.headers)
        body = cls._format_body(request.content)

        # Assemble parts, ensuring CRLF separation
        parts = [request_line, headers, "", body]
        return "\r\n".join(parts)

    @classmethod
    def format_raw_http_response(cls, response: httpx.Response) -> str:
        """
        Convert an httpx.Response into the full raw HTTP response text, including:
          1. Status-Line (version, status code, reason)
          2. All response headers
          3. A blank line, then the response body (if any)

        :param response: The httpx.Response to format.
        :return: A single string containing the raw HTTP response.
        """
        # Use the negotiated HTTP version from the response (e.g. "1.1" or "2")
        http_version = getattr(response, "http_version", "1.1")

        status_line = f"HTTP/{http_version} {response.status_code} {response.reason_phrase}"
        headers = cls._format_headers(response.headers)
        body = cls._format_body(response.content)

        # Assemble parts, ensuring CRLF separation
        parts = [status_line, headers, "", body]
        return "\r\n".join(parts)


@log_method_calls()
class Response(httpx.Response):
    def __init__(self, response: httpx.Response, request_time: float) -> None:
        self._response = response
        self._request_time = request_time

    @property
    def perf_request_time(self) -> float:
        """
        Get the time taken for the request in milliseconds.
        """
        return self._request_time

    def as_http_format(self) -> Dict[str, str]:
        """
        Convert the httpx.Response into a formatted string representation.
        This includes both the request and response in raw HTTP format.
        """
        return {
            "request": HTTPFormatter.format_raw_http_request(self._response.request),
            "response": HTTPFormatter.format_raw_http_response(self._response),
            "token_request": HTTPFormatter.format_raw_http_request(self._response.request.extensions.get("token_request", None)),
            "token_response": HTTPFormatter.format_raw_http_response(self._response.request.extensions.get("token_response", None)),
        }

    def print_http(self):
        print(
            HTTPFormatter.format_raw_http_request(self._response.request),
            HTTPFormatter.format_raw_http_response(self._response),
            sep="\n\n",
        )

    def __getattr__(self, name: str) -> Any:
        return getattr(self._response, name)
