# JsonAblr

JsonAblr is a Python library that allows you to encode variables into a format that represents a JSON object. It provides a simple and intuitive way to convert variables into a JSON-like structure, making it easier to store and transmit data.

This was heavily inspired by FastAPI's `jsonable_encoder`.

## Features

- Encode variables into a JSON-like format
- Supports various data types including strings, numbers, lists, dictionaries, dates, Pydantic models, dataclasses and more
- Easy to use
- Customizable for your own types

## Installation

You can install Jsonablr using pip:

```shell
pip install jsonablr
```

## Usage

### `encode` helper function:

```python
from jsonablr import encode
from datetime import datetime, timezone

my_date = datetime.now(tz=timezone.utc)

print(encode(my_date))
```

#### Output:

```
2023-06-26T12:30:00.000Z
```

### `JsonAblr` class:

```python
from typing import Set
from datetime import datetime
from jsonablr import JsonAblr
from pydantic import BaseModel

class DynamoDbItem(BaseModel):
    partition_key: str
    sort_key: str
    games: Set[str]
    when: datetime

encoder = JsonAblr(
    encoders={
        datetime: lambda x: x.isoformat(sep=' ', timespec='seconds')
    },
    preserve_set=True
)

item = DynamoDbItem(
    partition_key='foo',
    sort_key='bar',
    games=['minecraft', 'terraria'],
    when=datetime.now()
)

print(encoder.encode(item))

```

This example demonstrates using a Pydantic model to be used as AWS DynamoDB item and not to be used as JSON. The `games` attribute is returned as a set (when using the `preserve_set=True` option) to support the DynamoDB SET type.
Serialising a set with `json.dumps` will cause an error.

#### Output:

```
{
    'partition_key': 'foo',
    'sort_key': 'bar',
    'games': {'minecraft', 'terraria'},
    'when': '2023-06-26 12:30:00'
}
```
