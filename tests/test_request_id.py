from copy import copy

import pytest
import uuid

from pydantic import UUID4

from api_essentials.request.request_id import RequestIdDescriptor


class SampleClass:
    request_id = RequestIdDescriptor()


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
    assert isinstance(SampleClass.__dict__['request_id'], RequestIdDescriptor)
    assert isinstance(SampleClass.request_id, uuid.UUID)


def test_setting_request_id_raises_attribute_error():
    instance = SampleClass()
    with pytest.raises(AttributeError, match="Cannot set request ID directly."):
        instance.request_id = uuid.uuid4()

def test_multiple_request_ids():
    id1 = RequestIdDescriptor()
    id2 = RequestIdDescriptor()
    id3 = copy(id1)
    assert id1 != id2, "Each call to RequestIdDescriptor should return a unique UUID."
    assert id1 == id3, ("id3 should be the same as id1 since it's assigned directly.")
