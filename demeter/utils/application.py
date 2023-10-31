import json
from decimal import Decimal
from enum import Enum
from functools import wraps
from types import SimpleNamespace
from typing import Any, Dict

OUTPUT_WIDTH = 30


def to_decimal(value: Any) -> Decimal:
    """
    convert value to decimal

    :param value: any value
    :type value: Any
    :return: Decimal value
    :rtype: Decimal

    """
    return Decimal(value)


def object_to_decimal(num: Any) -> Any:
    """
    If number is float or int, return Decimal, else return original value

    :param value: any value
    :type value: Any
    :return: Decimal value
    :rtype: Any
    """
    return Decimal(str(num)) if (isinstance(num, float) or type(num) == int) else num


def dict_to_object(dict_entity: Dict) -> Any:
    """
    convert dict to object via json

    :param dict_entity: dict instance
    :type dict_entity: Dict
    :return: object
    :rtype: Any
    """
    return json.loads(json.dumps(dict_entity), object_hook=lambda d: SimpleNamespace(**d))


def float_param_formatter(func):
    """
    decorator to convert param to float

    :param func: any function
    :return: function execute result
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


def get_enum_by_name(me: Enum, name: str):
    """
    get enum by name

    :param me: enum class
    :param name: enum item name
    :return: get value in enum
    """
    for e in me:
        if e.name.lower() == name.lower():
            return e
    raise RuntimeError(f"cannot found {name} in {me}, allow value is " + str([x.name for x in me]))


def require(condition: bool, error_msg: str):
    """
    Checking whether the condition is True, if not, will raise a AssertionError

    :param condition: condition
    :type condition: bool
    :param error_msg: error message contains in AssertionError
    :param error_msg: str
    """
    if not condition:
        raise AssertionError(error_msg)
