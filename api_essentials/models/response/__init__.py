import typing

import httpx
from httpx._types import HeaderTypes, ResponseContent, SyncByteStream, AsyncByteStream
from api_essentials.models.request import Request, RequestId


class Response(httpx.Response):
    """
    Response class that extends httpx.Response.
    """
    def __init__(
        self,
        status_code: int,
        *,
        headers: HeaderTypes = None,
        content: ResponseContent = None,
        text: str = None,
        html: str = None,
        json: typing.Any = None,
        stream: typing.Union[SyncByteStream, AsyncByteStream] = None,
        request: Request = None,
        extensions: dict = None,
        history: typing.List["Response"] = None,
        request_id: RequestId = None
    ):
        super().__init__(
            status_code,
            headers=headers,
            content=content,
            text=text,
            html=html,
            json=json,
            stream=stream,
            request=request,
            extensions=extensions,
            history=history
        )
        self.request_id = request_id

