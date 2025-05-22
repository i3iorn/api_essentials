import httpx

from api_essentials.request.request_id import RequestIdDescriptor


class Request(httpx.Request):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.extensions["token_request"]    = None
        self.extensions["token_response"]   = None
        self.extensions["request_id"]       = RequestIdDescriptor()
        self.extensions["perf_request_time"]= None
        self.extensions["http_version"]     = None
