from typing import Callable

import httpx

ResponseHook = Callable[[httpx.Response], None]
