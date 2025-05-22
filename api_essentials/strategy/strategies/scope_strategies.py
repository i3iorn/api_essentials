import os
from dataclasses import dataclass
from enum import Enum, IntEnum, auto
from typing import List, Union, Any

from api_essentials.strategy.interface import SimpleStrategy


class ScopeStrategyError(Exception):...
class ScopeStrategyInvalid(ScopeStrategyError):...
class ScopeStrategyNotFound(ScopeStrategyError):...
class ScopeStrategyAlreadyExists(ScopeStrategyError):...
class ScopeStrategyExecutionError(ScopeStrategyError):...
class ScopeModeStrategyError(ScopeStrategyError):...


DELIMITER_MAX_LENGTH = os.getenv("AE_DELIMITER_MAX_LENGTH", 1)
SCOPE_LENGTH_BACKSTOP = os.getenv("AE_SCOPE_LENGTH_BACKSTOP", 255)
MAXIMUM_SCOPES = os.getenv("AE_MAXIMUM_SCOPES", 16)


class ScopeExecutionMode(IntEnum):
    """
    Enum to represent the execution mode of the scope strategy.
    """
    SPLIT = auto()
    MERGE = auto()
    DUAL = auto()


class ScopeStrategy(SimpleStrategy):
    """
    Base class for scope strategies.
    """
    _delimiter: str

    def __init__(self, delimiter: str) -> None:
        """
        Initialize the scope strategy with a delimiter.
        Arguments:
            delimiter (str): The delimiter used for splitting scopes.
        Raises:
            ScopeStrategyError: If the delimiter is not a string or if it is empty.
        Returns:
            None
        """
        self.delimiter = delimiter

    @property
    def delimiter(self) -> str:
        """
        Get the delimiter used for splitting scopes.

        Returns:
            str: The delimiter.
        """
        return self._delimiter

    @delimiter.setter
    def delimiter(self, value: str) -> None:
        """
        Set the delimiter used for splitting scopes. Max length of the delimiter is 
        controlled by the AE_DELIMITER_MAX_LENGTH environment variable. It defaults to
        1 character.

        Arguments:
            value (str): The delimiter to set.
        Raises:
            ScopeStrategyError: If the delimiter is not a string or if it is empty.
        Returns:
            None
        """
        if not isinstance(value, str):
            raise ScopeStrategyError("Delimiter must be a string.")
        if not value:
            raise ScopeStrategyError("Delimiter cannot be empty.")
        if len(value) > DELIMITER_MAX_LENGTH:
            raise ScopeStrategyError("Delimiter must be a single character.")
        self._delimiter = value

    def split_scopes(self, scopes: str) -> List[str]:
        """
        Split the scopes string into a list of scopes.
        
        1. The input string is checked to ensure it is a string and not empty.
        2. The length of the string is checked against a backstop value to prevent
              excessively long strings. The backstop value is controlled by the
              AE_SCOPE_LENGTH_BACKSTOP environment variable, which defaults to 255.

        Arguments:
            scopes (str): The scopes string to be split.
        Returns:
            List[str]: The list of scopes.
        Raises:
            ScopeStrategyError: If the input is not a string or if it is empty.
            ScopeStrategyExecutionError: If an error occurs during splitting.
        """
        if not isinstance(scopes, str):
            raise ScopeStrategyError("Scopes must be a string.")
        if len(scopes) > SCOPE_LENGTH_BACKSTOP:
            raise ScopeStrategyError("Scopes string is too long.")
        try:
            return scopes.split(self.delimiter)
        except AttributeError as e:
            raise ScopeStrategyExecutionError(f"Error splitting scopes: {e}.") from e

    def merge_scopes(self, scopes: List[str]) -> str:
        """
        Merge a list of scopes into a single string.
        
        1. The input is checked to ensure it is a list and not empty.
        2. The length of the list is checked against a maximum value to prevent
                excessively long lists. The maximum value is controlled by the
                AE_MAXIMUM_SCOPES environment variable, which defaults to 16.

        Arguments:
            scopes (List[str]): The list of scopes to be merged.
        Returns:
            str: The merged scopes as a string.
        Raises:
            ScopeStrategyError: If the input is not a list or if it contains non-string elements.
            ScopeStrategyExecutionError: If an error occurs during merging.
        """
        if not isinstance(scopes, list):
            raise ScopeStrategyError("Scopes must be a list.")
        if len(scopes) > MAXIMUM_SCOPES:
            raise ScopeStrategyError("Too many scopes to merge.")
        if not all(isinstance(scope, str) for scope in scopes):
            raise ScopeStrategyError("All scopes must be strings.")

        try:
            # Remove duplicates and join with the delimiter
            return self.delimiter.join(set(scopes))
        except AttributeError as e:
            raise ScopeStrategyExecutionError(f"Error merging scopes: {e}.") from e

    def execute(self, scopes: Union[str, List[str]], mode: ScopeExecutionMode = ScopeExecutionMode.DUAL) -> Union[str, List[str]]:
        """
        Execute the strategy.

        Arguments:
            scopes (Union[str, List[str]]): The scopes to be processed.
            mode (ScopeExecutionMode): The execution mode (SPLIT, MERGE, DUAL).
        Returns:
            Union[str, List[str]]: The processed scopes as a string or a list.
        Raises:
            ScopeStrategyError: If the input is not a string or list, or if it contains invalid elements.
            ScopeStrategyExecutionError: If an error occurs during execution.
            ScopeModeStrategyError: If the execution mode is invalid.
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

