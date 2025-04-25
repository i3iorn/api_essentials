from api_essentials.flags import FORCE_HTTPS


def validate_url(url: str, *_flags) -> str:
    if not isinstance(url, str):
        raise TypeError("Base URL must be a string.")
    if not url.startswith("http"):
        raise ValueError("Base URL must start with 'http' or 'https'.")
    if FORCE_HTTPS in _flags and not url.startswith("https://"):
        raise ValueError("HTTPS required under FORCE_HTTPS flag.")
    return url