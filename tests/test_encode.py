"""
Test encode.
"""
from jsonablr import encode, encode_output
from datetime import datetime
from pydantic import BaseModel, AwareDatetime, RootModel


def test_custom_encoder():

    def custom_encoder(obj):
        return 'custom_encoder'

    assert encode('test', encoders={str: custom_encoder}) == 'custom_encoder'


def test_datetime():

    date = datetime(2020, 1, 1, 13, 30, 0)
    assert encode(date) == '2020-01-01T12:30:00.000Z'


def test_datetime_in_dict():

    data = {
        'when': datetime(2020, 1, 1, 13, 30, 0)
    }
    assert encode(data) == {'when': '2020-01-01T12:30:00.000Z'}


def test_preserve_set():

    assert encode(set([1, 2, 3]), preserve_set=True) == {1, 2, 3}


def test_pydantic_model():

    class TestModel(BaseModel):
        a: int
        b: str
        c: set

    item = TestModel.model_validate({
        'a': 1,
        'b': 'test',
        'c': [1, 2, 3, 3, 4]
    })

    assert encode(item) == {'a': 1, 'b': 'test', 'c': [1, 2, 3, 4]}


def test_pydantic_model_preserve_set():

    class TestModel(BaseModel):

        class SubModel(BaseModel):
            z: set

        a: int
        b: str
        c: set
        d: SubModel

    item = TestModel.model_validate({
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


def test_datetime_types():

    AwareDatetimeT = RootModel[AwareDatetime]

    dt = AwareDatetimeT.model_validate('2020-01-01T12:30:00.000Z')

    assert encode(dt) == '2020-01-01T12:30:00.000Z'
