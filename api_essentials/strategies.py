import base64
import json
import logging
from abc import abstractmethod, ABC
from typing import Optional, Callable, Any, Type

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, RetryCallState

from api_essentials.logging_decorator import log_method_calls


@log_method_calls()
class Strategy(ABC):
    """
    Base class for strategies.
    """
    @abstractmethod
    def apply(self, *args, **kwargs):
        """
        Apply the strategy.
        """
        pass


@log_method_calls()
class CredentialEncodingStrategy(Strategy):
    """
    Strategy for encoding credentials.
    """
    def apply(self, client_id: str, client_secret: str) -> str:
        """
        Apply the encoding strategy.
        """
        if not client_id or not client_secret:
            raise ValueError("Client ID and Client Secret must be provided.")
        if not isinstance(client_id, str) or not isinstance(client_secret, str):
            raise TypeError("Client ID and Client Secret must be strings.")

        auth_str = f"{client_id}:{client_secret}"
        return base64.b64encode(auth_str.encode()).decode()


@log_method_calls()
class StandardScopeStrategy(Strategy):
    """
    Standard scope strategy for OAuth2 authentication.
    """
    def apply(self, scopes: list) -> str:
        """
        Apply the standard scope strategy.
        """
        if not isinstance(scopes, list):
            raise ValueError("Scopes must be a list.")
        return " ".join(scopes)



@log_method_calls()
class ErrorStrategy(Strategy):
    """
    Optional injectable strategy to handle or transform HTTP errors.
    """
    def apply(self, response: httpx.Response) -> None:
        if response.status_code >= 400:
            raise httpx.HTTPStatusError(
                f"[{response.status_code}] Error for {response.request.method.upper()} {response.request.url}",
                request=response.request,
                response=response
            )


@log_method_calls()
class RetryStrategy(Strategy):
    """
    Retry strategy wrapper using tenacity, customizable per instance.
    """

    def __init__(
        self,
        retries: int = 3,
        wait_multiplier: float = 1.0,
        wait_max: float = 10.0,
        retry_on: Optional[Callable[[Exception], bool]] = None,
    ):
        self.logger = logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}")
        self.retries = retries
        self.wait_multiplier = wait_multiplier
        self.wait_max = wait_max
        self._retry_on = retry_on or self._default_retry_condition

    def _default_retry_condition(self, exc: Exception) -> bool:
        return isinstance(exc, (httpx.RequestError, httpx.TimeoutException))

    def apply(self, func: Callable) -> Callable:
        return retry(
            stop=stop_after_attempt(self.retries),
            wait=wait_exponential(multiplier=self.wait_multiplier, max=self.wait_max),
            retry=retry_if_exception_type(httpx.RequestError),
            before_sleep=self._log_retry,
        )(func)

    def _log_retry(self, retry_state: RetryCallState):
        exc = retry_state.outcome.exception()
        if exc:
            self.logger.warning(
                f"Retrying {retry_state.fn.__name__} due to {exc.__class__.__name__}: {exc}. "
                f"Attempt {retry_state.attempt_number}/{self.retries}."
            )


@log_method_calls()
class NoRetries(RetryStrategy):
    """
    No retry strategy.
    """
    def __init__(self):
        super().__init__(retries=0, wait_multiplier=0, wait_max=0)


@log_method_calls()
class CoercionStrategy(Strategy, ABC):
    @abstractmethod
    def apply(self, raw: Any) -> Any:
        ...


@log_method_calls()
class SimpleCoercion(CoercionStrategy):
    def __init__(self, target: Type):
        self.target = target

    def apply(self, raw: Any) -> Any:
        if isinstance(raw, self.target):
            return raw
        try:
            return self.target(raw)
        except Exception as e:
            raise TypeError(f"Cannot coerce {raw!r} to {self.target.__name__}") from e


@log_method_calls()
class JSONCoercion(CoercionStrategy):
    def apply(self, raw: Any) -> Any:
        if isinstance(raw, str):
            try:
                return json.loads(raw)
            except json.JSONDecodeError as e:
                if raw.startswith("{") or raw.startswith("[") or raw.endswith("}") or raw.endswith("]"):
                    raise ValueError(f"Invalid JSON: {raw!r}") from e
                else:
                    return raw
        elif isinstance(raw, (dict, list)):
            return raw
        raise TypeError(f"Cannot coerce {raw!r} to JSON")
