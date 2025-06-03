import httpx

from api_essentials.models.request.request_id import RequestId


class Request(httpx.Request):
    """
    A custom HTTP request class that extends httpx.Request to include
    additional extensions for tracking request metadata such as token requests,
    token responses, request IDs, performance request time, and HTTP version.

    Attributes:
        extensions (dict): A dictionary to hold custom extensions for the request.
            - token_request: The token request associated with this request.
            - token_response: The token response associated with this request.
            - request_id: A unique identifier for the request, generated using RequestId.
            - perf_request_time: Performance timing for the request. Is set when
                the request is sent and can be used to measure the time taken for the request.
            - http_version: The HTTP version used for the request. Is set when
                the request is sent and can be used to determine the protocol version.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.extensions["token_request"]    = None
        self.extensions["token_response"]   = None
        self.extensions["request_id"]       = RequestId()._get_encoded("hex")
        self.extensions["perf_request_time"]= None
        self.extensions["http_version"]     = None
