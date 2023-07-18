"""
Test encode.
"""
from jsonablr import encode, encode_output
from datetime import datetime, timezone


def test_custom_encoder():

    def custom_encoder(obj):
        return 'custom_encoder'

    assert encode('test', encoders={str: custom_encoder}) == 'custom_encoder'


def test_datetime():

    date = datetime(2020, 1, 1, 13, 30, 0).replace(tzinfo=timezone.utc)
    assert encode(date) == '2020-01-01T13:30:00.000Z'


def test_datetime_in_dict():

    data = {
        'when': datetime(2020, 1, 1, 14, 30, 0).replace(tzinfo=timezone.utc)
    }
    assert encode(data) == {'when': '2020-01-01T14:30:00.000Z'}


def test_preserve_set():

    assert encode(set([1, 2, 3]), preserve_set=True) == {1, 2, 3}


def test_pydantic_model():

    from pydantic import BaseModel

    class TestModel(BaseModel):
        a: int
        b: str
        c: set

    item = TestModel.parse_obj({
        'a': 1,
        'b': 'test',
        'c': [1, 2, 3, 3, 4]
    })

    assert encode(item) == {'a': 1, 'b': 'test', 'c': [1, 2, 3, 4]}


def test_pydantic_model_preserve_set():

    from pydantic import BaseModel

    class TestModel(BaseModel):

        class SubModel(BaseModel):
            z: set

        a: int
        b: str
        c: set
        d: SubModel

    item = TestModel.parse_obj({
        'a': 1,
        'b': 'test',
        'c': [1, 2, 3, 3, 4],
        'd': {
            'z': [1, 2, 3, 3, 4]
        }
    })

    assert encode(item, preserve_set=True) == {
        'a': 1, 'b': 'test', 'c': {1, 2, 3, 4}, 'd': {'z': {1, 2, 3, 4}}
    }


def test_decorator():

    @encode_output(encoders={datetime: lambda obj: obj.isoformat(sep=' ', timespec='seconds')})
    def my_func():
        return datetime(2020, 1, 1, 13, 30, 0)

    assert my_func() == '2020-01-01 13:30:00'
