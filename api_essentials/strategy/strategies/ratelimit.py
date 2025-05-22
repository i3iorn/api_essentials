from datetime import datetime
from typing import List

from api_essentials.strategy.interface import Strategy


class RateLimitStrategyProtocol(Strategy):
    """
    Protocol for rate limit strategies.
    """
    def is_rate_limited(self) -> bool:
        """
        Check if the rate limit has been exceeded.
        """
        pass

    def add_request(self) -> None:
        """
        Add a request to the rate limit tracker.
        """
        pass

    def reset(self) -> None:
        """
        Reset the rate limit tracker.
        """
        pass


class RateLimit(RateLimitStrategyProtocol):
    """
    Rate limit strategy for controlling the number of requests to a resource.
    """
    def __init__(self, max_requests: int, time_window: int) -> None:
        """
        Initialize the rate limit strategy.

        Attributes:
            max_requests (int): Maximum number of requests allowed in the time window.
            time_window (int): Time window in seconds.
        Raises:
            ValueError: If max_requests or time_window is less than or equal to 0.
        """
        super().__init__()
        self._validate(max_requests, time_window)
        self.max_requests: int = max_requests
        self.time_window: int = time_window
        self.requests: List[datetime] = []

    def _validate(self, max_requests: int, time_window: int) -> None:
        """
        Validate the rate limit parameters.

        Attributes:
            max_requests (int): Maximum number of requests allowed in the time window.
            time_window (int): Time window in seconds.
        Raises:
            ValueError: If max_requests or time_window is less than or equal to 0.
        """
        if max_requests <= 0:
            raise ValueError("max_requests must be greater than 0")
        if time_window <= 0:
            raise ValueError("time_window must be greater than 0")

    def is_rate_limited(self) -> bool:
        """
        Check if the rate limit has been exceeded.

        Returns:
            bool: True if the rate limit has been exceeded, False otherwise.
        """
        now = datetime.now()
        self.requests = [req for req in self.requests if (now - req).seconds < self.time_window]
        return len(self.requests) >= self.max_requests

    def add_request(self) -> None:
        """
        Add a request to the rate limit tracker.

        This method appends the current timestamp to the requests list.
        It should be called each time a request is made.
        Raises:
            ValueError: If the rate limit has been exceeded.
        """
        self.requests.append(datetime.now())

    def reset(self) -> None:
        """
        Reset the rate limit tracker.
        This method clears the requests list, effectively resetting the rate limit.
        It can be used to manually reset the rate limit tracker.
        This is useful in scenarios where the rate limit needs to be reset
        before the time window expires, such as when a user is granted a higher
        rate limit.
        """
        self.requests = []
