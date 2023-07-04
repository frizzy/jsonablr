"""
Encoders
"""
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Set, Union
from datetime import datetime, date, timezone
import dataclasses
from enum import Enum
from pathlib import PurePath
from types import GeneratorType
from pydantic import BaseModel, create_model


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
        **Options.model_validate(options).model_dump()
    )
    return encoder(data)


def encode_output(func=None, **options):
    encoder = JsonAblr(
        encoders=options.pop('encoders', {}),
        **Options.model_validate(options).model_dump()
    )

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            return encoder.encode(func(*args, **kwargs))
        return wrapper

    return decorator if func is None else decorator(func)


class JsonAblr:

    def __init__(self, encoders: Optional[Dict[Any, Callable]] = None, **options) -> None:
        self.encoders = {
            **default_encoders,
            **(encoders or {})
        }
        self._options = Options.model_validate(options)
        self._override_options = None

    @property
    def options(self) -> Options:
        return Options.model_validate({
            **self._options.model_dump(),
            **(self._override_options.model_dump() if self._override_options else {})
        })

    def __call__(self, obj: Any, **options) -> Any:
        return self.encode(obj, **options)

    def encode(self, obj: Any, **options) -> Any:
        if options:
            self._override_options = Options.model_validate(options)
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

        try:
            ObjModel = create_model('ObjModel', obj=(type(obj), ...))
            return ObjModel(obj=obj).model_dump(mode='json')['obj']
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

        obj_dict = obj.model_dump(**self.options.model_dump(include={
            'include',
            'exclude',
            'by_alias',
            'exclude_unset',
            'exclude_none',
            'exclude_defaults'
        }))

        encoder = self.__class__(
            encoders=self.encoders,
            **self.options.model_dump(include={
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
            **self.options.model_dump(
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
