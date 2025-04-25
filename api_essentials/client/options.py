from dataclasses import dataclass, field
from typing import Optional, Dict, Any, Union

HttpMethod = Union["get", "post", "put", "patch", "delete", "head", "options"]


@dataclass
class RequestOptions:
    method: HttpMethod
    path: str
    params: Optional[Dict[str, Any]] = None
    json: Optional[Dict[str, Any]] = None
    headers: Optional[Dict[str, str]] = None
    verify: Optional[bool] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    def as_dict(self):
        """
        Convert the RequestOptions instance to a dictionary if the value is not None.
        This is useful for logging or debugging purposes.
        """
        return {k: v for k, v in self.__dict__.items() if v is not None and k not in ["method", "path", "extra"]}