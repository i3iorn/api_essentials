from abc import ABC, abstractmethod
from typing import Protocol


class Strategy(Protocol):
    """
    Base class for all strategies.
    """
    pass


class SimpleStrategy(Strategy):
    """
    A simple strategy that does not require any additional configuration.
    """
    @abstractmethod
    def execute(self, *args, **kwargs):
        """
        Execute the strategy.
        """
        pass