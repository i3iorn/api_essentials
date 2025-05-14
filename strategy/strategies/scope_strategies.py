from dataclasses import dataclass
from enum import Enum
from typing import List, Union

from strategy.interface import SimpleStrategy


class ScopeStrategyError(Exception):...
class ScopeStrategyInvalid(ScopeStrategyError):...
class ScopeStrategyNotFound(ScopeStrategyError):...
class ScopeStrategyAlreadyExists(ScopeStrategyError):...
class ScopeStrategyExecutionError(ScopeStrategyError):...
class ScopeModeStrategyError(ScopeStrategyError):...


class ScopeExecutionMode(Enum):
    """
    Enum to represent the execution mode of the scope strategy.
    """
    SPLIT = "split"
    MERGE = "merge"
    DUAL = "dual"


class ScopeStrategy(SimpleStrategy):
    """
    Base class for scope strategies.
    """

    def __init__(self, delimiter: str):
        """
        Initialize the scope strategy with a delimiter.
        :param delimiter: The delimiter to use for splitting scopes.
        """
        self.delimiter = delimiter

    @property
    def delimiter(self) -> str:
        """
        Get the delimiter used for splitting scopes.
        :return: The delimiter.
        """
        return self._delimiter

    @delimiter.setter
    def delimiter(self, value: str):
        """
        Set the delimiter used for splitting scopes.
        :param value: The delimiter to set.
        """
        if not isinstance(value, str):
            raise ScopeStrategyError("Delimiter must be a string.")
        self._delimiter = value

    def split_scopes(self, scopes: str) -> list:
        """
        Split the scopes string into a list of scopes.
        :param scopes: The scopes to be split.
        :return: A list of scopes.
        """
        try:
            return scopes.split(self.delimiter)
        except AttributeError as e:
            raise ScopeStrategyExecutionError(f"Error splitting scopes: {e}.") from e

    def merge_scopes(self, scopes: List[str]) -> str:
        """
        Merge a list of scopes into a single string.
        :param scopes: The list of scopes to be merged.
        :return: A string of merged scopes.
        """
        try:
            return self.delimiter.join(set(scopes))
        except AttributeError as e:
            raise ScopeStrategyExecutionError(f"Error merging scopes: {e}.") from e

    def execute(self, scopes: Union[str, List[str]], mode: ScopeExecutionMode = ScopeExecutionMode.DUAL) -> Union[str, List[str]]:
        """
        Execute the strategy.
        :param scopes: The scopes to be processed.
        :param mode: The execution mode (SPLIT, MERGE, DUAL).
        :return: The processed scopes.
        """
        try:
            if mode == ScopeExecutionMode.SPLIT:
                return self.split_scopes(scopes)
            elif mode == ScopeExecutionMode.MERGE:
                return self.merge_scopes(scopes)
            elif mode == ScopeExecutionMode.DUAL:
                if isinstance(scopes, str):
                    return self.split_scopes(scopes)
                elif isinstance(scopes, list):
                    return self.merge_scopes(scopes)
        except Exception as e:
            if isinstance(e, ScopeStrategyError):
                raise e
            raise ScopeStrategyExecutionError(f"Error executing strategy: {e}.") from e

        raise ScopeModeStrategyError(f"Invalid execution mode: {mode}.")