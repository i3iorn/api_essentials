import base64
from copy import copy

import pytest
import uuid

from api_essentials.models.request import RequestId


class SampleClass:
    request_id = RequestId()


def test_request_id_is_uuid():
    instance = SampleClass()
    rid = instance.request_id
    assert isinstance(rid, uuid.UUID)


def test_request_id_is_unique_per_instance():
    instance1 = SampleClass()
    instance2 = SampleClass()
    assert instance1.request_id != instance2.request_id


def test_request_id_descriptor_access_from_class():
    # Accessing request_id from the class should return the descriptor itself
    assert isinstance(SampleClass.__dict__['request_id'], RequestId)
    assert isinstance(SampleClass.request_id, uuid.UUID)


def test_setting_request_id_raises_attribute_error():
    instance = SampleClass()
    with pytest.raises(AttributeError, match="Cannot set request ID directly."):
        instance.request_id = uuid.uuid4()

def test_multiple_request_ids():
    id1 = RequestId()
    id2 = RequestId()
    id3 = copy(id1)
    print(f"ID1: {id1}, ID2: {id2}, ID3: {id3}")
    assert id1 != id2, "Each call to RequestIdDescriptor should return a unique UUID."
    assert id1 == id3, ("id3 should be the same as id1 since it's assigned directly.")

def test_request_id_hex_encoding():
    instance = SampleClass()
    hex_val = SampleClass.__dict__['request_id'].to_hex()
    assert isinstance(hex_val, str)
    assert len(hex_val) == 32  # UUID in hex is 32 characters long
    assert all(c in '0123456789abcdef' for c in hex_val)

def test_request_id_base64_encoding():
    instance = SampleClass()
    b64_val = SampleClass.__dict__['request_id'].to_base64()
    assert isinstance(b64_val, str)

def test_request_id_to_json():
    b64_val = SampleClass.__dict__['request_id'].to_json()
    assert isinstance(b64_val, str)

def test_request_id_from_encoded_raises():
    instance = SampleClass()
    with pytest.raises(AttributeError):
        SampleClass.__dict__['request_id'].from_encoded(instance, 'deadbeef', encoding='hex')

def test_request_id_inject_raises():
    instance = SampleClass()
    with pytest.raises(AttributeError):
        SampleClass.__dict__['request_id'].inject(instance, uuid.uuid4())

def test_request_id_thread_safety():
    import threading
    ids = []
    def get_id():
        instance = SampleClass()
        ids.append(instance.request_id)
    threads = [threading.Thread(target=get_id) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(set(ids)) == 10
