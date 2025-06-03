# API Essentials

A collection of essentials for various API functionalities.

## RequestId Descriptor

The `RequestId` descriptor provides a per-instance, immutable UUID4 for your classes. It is thread-safe and supports hex and base64 encoding.

### Usage Example

```python
from api_essentials.models.request import RequestId


class MyRequest:
    request_id = RequestId()


req = MyRequest()
print(req.request_id)  # uuid.UUID instance

# Get hex/base64 encoding
hex_val = MyRequest.__dict__['request_id']._get_encoded(req, encoding='hex')
b64_val = MyRequest.__dict__['request_id']._get_encoded(req, encoding='base64')
print(hex_val, b64_val)
```

### Features
- Per-instance UUID4, immutable after creation
- Thread-safe
- Hex and base64 encoding utilities
- Raises `AttributeError` if you try to set or delete the ID

### Testing
Run all tests:

```bash
pytest
```

## OAuth2 Configuration

The `OAuth2Config` class provides a flexible way to manage OAuth2 configurations, including client credentials, token URLs, and more.

### Features
- Supports client credentials, access tokens, and refresh tokens
- Configurable timeout, redirects, and SSL verification
- Scope and grant type management
- Built-in validation for configuration values

### Usage Example

```python
from api_essentials.auth.config import OAuth2Config
from httpx import URL

config = OAuth2Config(
    client_id="your_client_id",
    client_secret="your_client_secret",
    token_url=URL("https://example.com/oauth/token"),
)

print(config.client_id)
```

## Logging Utilities

The `api_essentials.utils.log` module provides utilities for consistent and structured logging across your application.

### Features
- Configurable log levels
- Support for structured logging
- Easy integration with existing Python logging

### Usage Example

```python
from api_essentials.utils.log import setup_logging

setup_logging(level="DEBUG")
```

## Strategies

The `api_essentials.strategy` module provides interfaces and implementations for various strategies, such as rate limiting and scope management.

### Features
- Flexible strategy interfaces
- Built-in implementations for common use cases

### Usage Example

```python
from api_essentials.strategy.strategies.scope_strategies import ScopeStrategy

strategy = ScopeStrategy(delimiter=",")
scopes = strategy.split_scopes("read,write")
print(scopes)
```

## Examples

Check the `examples/` directory for more usage examples, including how to integrate these utilities into your projects.

## Contributing

Contributions are welcome! Please follow the guidelines in `CONTRIBUTING.md` and ensure all tests pass before submitting a pull request.

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.
