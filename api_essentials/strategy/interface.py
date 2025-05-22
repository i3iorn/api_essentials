from abc import abstractmethod
from typing import Protocol, Any


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
    def execute(self, *args: Any, **kwargs: Any) -> Any:
        """
        Execute the strategy.
        """
        pass

