# API Essentials

A collection of essentials for various API functionalities.

## RequestId Descriptor

The `RequestId` descriptor provides a per-instance, immutable UUID4 for your classes. It is thread-safe and supports hex and base64 encoding.

### Usage Example

```python
from api_essentials.request.request_id import RequestId

class MyRequest:
    request_id = RequestId()

req = MyRequest()
print(req.request_id)  # uuid.UUID instance

# Get hex/base64 encoding
hex_val = MyRequest.__dict__['request_id'].get_encoded(req, encoding='hex')
b64_val = MyRequest.__dict__['request_id'].get_encoded(req, encoding='base64')
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

### Code Quality
This project uses black, isort, flake8, mypy, and bandit. See `.pre-commit-config.yaml` for details.

