import logging
from abc import abstractmethod, ABC
from typing import Optional, Callable

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, RetryCallState

from api_essentials.logging_decorator import log_method_calls


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