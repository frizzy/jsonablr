"""
Test Options
"""
from jsonablr import Options


def test_options():

    options = Options.parse_obj({
        'include': ['a', 'b'],
        'exclude': {
            'c:': [
                'd',
                'e'
            ]
        }
    })

    assert type(options.include) is set
