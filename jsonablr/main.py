"""
Encoders
"""
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union
from datetime import datetime, date, timezone
import dataclasses
from enum import Enum
from pathlib import PurePath
from types import GeneratorType
from pydantic import BaseModel
from pydantic.json import ENCODERS_BY_TYPE


def datetime_encoder(dateval: datetime) -> str:
    datestr = dateval.astimezone(tz=timezone.utc).isoformat(
        sep='T',
        timespec='milliseconds'
    )
    return f'{datestr[:-6]}Z'


default_encoders = {
    datetime: datetime_encoder,
    date: str
}


SetIntStr = Set[Union[int, str]]
DictIntStrAny = Dict[Union[int, str], Union[SetIntStr, Any]]


class Options(BaseModel):
    include: Optional[Union[SetIntStr, DictIntStrAny]] = None
    exclude: Optional[Union[SetIntStr, DictIntStrAny]] = None
    by_alias: bool = True
    exclude_unset: bool = False
    exclude_none: bool = False
    exclude_defaults: bool = False
    sqlalchemy_safe: bool = True
    preserve_set: bool = False


def encode(data: Any, **options) -> dict:
    encoder = JsonAblr(
        encoders=options.pop('encoders', {}),
        **Options.parse_obj(options).dict()
    )
    return encoder(data)


def encode_output(func=None, **options):
    encoder = JsonAblr(
        encoders=options.pop('encoders', {}),
        **Options.parse_obj(options).dict()
    )

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            return encoder.encode(func(*args, **kwargs))
        return wrapper

    return decorator if func is None else decorator(func)


encoder_map:  Dict[Callable[[Any], Any], Tuple[Any, ...]] = {}
for type_, encoder in ENCODERS_BY_TYPE.items():
    encoder_map.setdefault(encoder, tuple())
    encoder_map[encoder] += (type_,)


class JsonAblr:

    def __init__(self, encoders: Optional[Dict[Any, Callable]] = None, **options) -> None:
        self.encoders = {
            **default_encoders,
            **(encoders or {})
        }
        self._options = Options.parse_obj(options)
        self._override_options = None

    @property
    def options(self) -> Options:
        return Options.parse_obj({
            **self._options.dict(),
            **(self._override_options.dict() if self._override_options else {})
        })

    def __call__(self, obj: Any, **options) -> Any:
        return self.encode(obj, **options)

    def encode(self, obj: Any, **options) -> Any:
        if options:
            self._override_options = Options.parse_obj(options)
        encoded = self._encode(obj)
        self._override_options = None
        return encoded

    def _encode(self, obj: Any) -> Any:

        custom_encoder = self.get_encoder(self.encoders, obj)
        if custom_encoder:
            return custom_encoder(obj)

        if isinstance(obj, BaseModel):
            return self.handle_pydantic_model(obj)

        if dataclasses.is_dataclass(obj):
            return self.handle_dataclass(obj)

        if isinstance(obj, dict):
            return self.handle_dict(obj)

        if isinstance(obj, Enum):
            return obj.value

        if isinstance(obj, PurePath):
            return str(obj)

        if isinstance(obj, (str, int, float, type(None))):
            return obj

        if self.options.preserve_set and isinstance(obj, (set, frozenset)):
            return self.handle_set(obj)

        if isinstance(obj, (list, set, frozenset, GeneratorType, tuple)):
            return self.handle_list_type(obj)

        encoder = ENCODERS_BY_TYPE.get(type(obj))
        if encoder:
            return encoder(obj)

        for encoder, types in encoder_map.items():
            if isinstance(obj, types):
                return encoder(obj)

        try:
            data = dict(obj)
        except Exception as e:
            errors: List[Exception] = []
            errors.append(e)
            try:
                data = vars(obj)
            except Exception as e:
                errors.append(e)
                raise ValueError(errors) from e

        return data

    @staticmethod
    def get_encoder(encoders: Dict[Any, Callable], obj: Any) -> Optional[Callable]:
        if not encoders:
            return None
        if type(obj) in encoders:
            return encoders[type(obj)]
        for type_, encoder in encoders.items():
            if isinstance(obj, type_):
                return encoder

    def handle_pydantic_model(self, obj: BaseModel) -> dict:

        obj_dict = obj.dict(**self.options.dict(include={
            'include',
            'exclude',
            'by_alias',
            'exclude_unset',
            'exclude_none',
            'exclude_defaults'
        }))

        json_encoders = getattr(obj.__config__, 'json_encoders', {})

        if '__root__' in obj_dict:
            obj_dict = obj_dict['__root__']

        encoder = self.__class__(
            encoders={**json_encoders, **(self.encoders or {})},
            **self.options.dict(include={
                'exclude_none',
                'exclude_defaults',
                'sqlalchemy_safe',
                'preserve_set'
            })
        )
        return encoder.encode(obj_dict)

    def handle_dataclass(self, obj: Any) -> Any:
        obj_dict = dataclasses.asdict(obj)
        return self.encode(obj_dict)

    def handle_dict(self, obj: dict) -> dict:

        encoded_dict = {}
        allowed_keys = set(obj.keys())

        if self.options.include is not None:
            allowed_keys &= set(self.options.include)
        if self.options.exclude is not None:
            allowed_keys -= set(self.options.exclude)

        encoder = self.__class__(
            self.encoders,
            **self.options.dict(
                include={
                    'by_alias',
                    'exclude_unset',
                    'exclude_none',
                    'exclude_defaults',
                    'sqlalchemy_safe',
                    'preserve_set'
                }
            )
        )

        for key, value in obj.items():
            if key not in allowed_keys:
                continue
            if value is None and self.options.exclude_none:
                continue
            if self.options.sqlalchemy_safe and isinstance(key, str) and key.startswith('_sa'):
                continue
            encoded_dict[encoder(key)] = encoder(value)
        return encoded_dict

    def handle_list_type(self, obj: Union[list, set, frozenset, GeneratorType, tuple]):
        encoded_list = []
        for item in obj:
            encoded_list.append(self(item))
        return encoded_list

    def handle_set(self, obj: Union[set, frozenset]):
        encoded_set = set()
        for item in obj:
            encoded_set.add(self(item))
        return encoded_set
