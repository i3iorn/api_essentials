import httpx
from typing import Optional, Union, AsyncIterator
import io


def _is_reusable_stream(stream: Union[bytes, bytearray, io.BytesIO]) -> bool:
    return isinstance(stream, (bytes, bytearray, io.BytesIO))


async def _buffer_stream(stream: AsyncIterator[bytes]) -> bytes:
    """
    Fully consumes an async byte stream and returns the content as bytes.
    Use with caution for large uploads.
    """
    chunks = []
    async for chunk in stream:
        chunks.append(chunk)
    return b"".join(chunks)


async def rebuild_request(
    request: httpx.Request,
    content: Optional[bytes] = None,
    headers: Optional[httpx.Headers] = None,
    buffer_streams: bool = True,
) -> httpx.Request:
    """
    Rebuilds an `httpx.Request` for retrying, handling both buffered and streamed bodies.

    Args:
        request (httpx.Request): Original request to rebuild.
        content (Optional[bytes]): Override the content body if desired.
        headers (Optional[httpx.Headers]): Optionally override headers.
        buffer_streams (bool): If True, attempt to read and buffer streaming bodies in memory.

    Returns:
        httpx.Request: A new request instance suitable for reuse/retry.
    """
    # If content is explicitly provided, use it.
    if content is None:
        # Attempt to extract buffered content if available
        if request._content is not None:
            content = request._content
        elif request.stream is not None and buffer_streams:
            # Buffer the stream into memory
            content = await _buffer_stream(request.stream)
        else:
            raise ValueError("Cannot rebuild request: content is missing and stream buffering is disabled.")

    return httpx.Request(
        method=request.method,
        url=request.url,
        headers=headers or request.headers,
        content=content,
        extensions=request.extensions.copy(),  # prevent mutability side-effects
    )


