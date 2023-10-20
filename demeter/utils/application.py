import json
from decimal import Decimal
from functools import wraps
from types import SimpleNamespace


OUTPUT_WIDTH = 30


def to_decimal(value):
    """
    decimal value
    :param value:
    :return:
    """
    return Decimal(value)


def object_to_decimal(num):
    """
    convert object to decimal
    :param num:
    :return:
    """
    return Decimal(str(num)) if (isinstance(num, float) or type(num) == int) else num


def dict_to_object(dict_entity):
    """
    convert dict to object
    :param dict_entity:
    :return:
    """
    return json.loads(json.dumps(dict_entity), object_hook=lambda d: SimpleNamespace(**d))


def float_param_formatter(func):
    """
    decorator to convert param to float
    :param func:
    :return:
    """

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
    """
    get enum by name
    :param me: enum
    :param name: key
    :return: get value in enum
    """
    for e in me:
        if e.name.lower() == name.lower():
            return e
    raise RuntimeError(f"cannot found {name} in {me}, allow value is " + str([x.name for x in me]))


def require(condition: bool, error_msg: str):
    """
    Checking whether the condition is True, if not, will raise a AssertionError
    """
    if not condition:
        raise AssertionError(error_msg)
