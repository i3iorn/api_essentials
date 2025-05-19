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

    def add_request(self):
        """
        Add a request to the rate limit tracker.
        """
        pass

    def reset(self):
        """
        Reset the rate limit tracker.
        """
        pass


class RateLimit(RateLimitStrategyProtocol):
    """
    Rate limit strategy for controlling the number of requests to a resource.
    """

    def __init__(self, max_requests: int, time_window: int):
        """
        Initialize the rate limit strategy.
        :param max_requests: Maximum number of requests allowed in the time window.
        :param time_window: Time window in seconds.
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests: List[datetime] = []

    def is_rate_limited(self) -> bool:
        """
        Check if the rate limit has been exceeded.
        """
        now = datetime.now()
        self.requests = [req for req in self.requests if (now - req).seconds < self.time_window]
        return len(self.requests) >= self.max_requests

    def add_request(self):
        """
        Add a request to the rate limit tracker.
        """
        self.requests.append(datetime.now())

    def reset(self):
        """
        Reset the rate limit tracker.
        """
        self.requests = []
