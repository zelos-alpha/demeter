import json
from decimal import Decimal
from types import SimpleNamespace
from functools import wraps

OUTPUT_WIDTH = 30


def to_decimal(value):
    return Decimal(value)


def object_to_decimal(num):
    return Decimal(str(num)) if (isinstance(num, float) or type(num) == int) else num


def dict_to_object(dict_entity):
    return json.loads(json.dumps(dict_entity), object_hook=lambda d: SimpleNamespace(**d))


def float_param_formatter(func):
    @wraps(func)
    def wrapper_func(*args, **kwargs):
        new_args = ()
        for arg in args:
            new_args += (object_to_decimal(arg),)
        for k, v in kwargs.items():
            kwargs[k] = object_to_decimal(v)
        return func(*new_args, **kwargs)

    return wrapper_func


def get_enum_by_name(me, name):
    for e in me:
        if e.name.lower() == name.lower():
            return e
    raise RuntimeError(f"cannot found {name} in {me}, allow value is " + str([x.name for x in me]))
