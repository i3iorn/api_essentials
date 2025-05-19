import logging
from threading import Lock
from typing import Tuple

_secret_lock = Lock()
_secrets: Tuple[str, ...] = ()

def register_secret(secret: str) -> None:
    """Add a secret to the global mask registry."""
    global _secrets
    with _secret_lock:
        # dedupe and grow tuple
        if secret and secret not in _secrets:
            _secrets = _secrets + (secret,)

def _mask(text: str) -> str:
    """Replace any occurrence of a registered secret with asterisks."""
    for s in _secrets:
        if s and s in text:
            text = text.replace(s, "*" * len(s))
    return text

class SecretFilter(logging.Filter):
    """Mask all registered secrets in every log record."""
    def filter(self, record: logging.LogRecord) -> bool:
        # Sanitize the format string
        record.msg = _mask(str(record.msg))
        # Sanitize each argument
        if record.args:
            # record.args might be a tuple or dict; handle both
            if isinstance(record.args, tuple):
                record.args = tuple(_mask(str(a)) for a in record.args)
            elif isinstance(record.args, dict):
                record.args = {k: _mask(str(v)) for k, v in record.args.items()}
        return True

def setup_secret_filter() -> None:
    """Attach the SecretFilter to the root logger once."""
    root = logging.getLogger()
    # Avoid adding multiple times
    if not any(isinstance(f, SecretFilter) for f in root.filters):
        root.addFilter(SecretFilter())
