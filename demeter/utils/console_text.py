from enum import Enum
from typing import Dict


class ForColorEnum(Enum):
    """
    foreground color in console
    """

    default = 0
    black = 30
    red = 31
    green = 32
    yellow = 33
    blue = 34
    purple = 35
    cyan = 36
    white = 37


class BackColorEnum(Enum):
    """
    background color in console
    """

    default = 0
    black = 40
    red = 41
    green = 42
    yellow = 43
    blue = 44
    purple = 45
    cyan = 46
    white = 47


class ModeEnum(Enum):
    """
    font mode in console
    """

    normal = 0
    bold = 1
    underline = 4
    blink = 5
    invert = 7
    hide = 8


DEFAULT_END = 0

STYLE = {
    "header1": {
        "mode": ModeEnum.invert,
        "fore": ForColorEnum.red,
        "back": BackColorEnum.default,
        "width": 50,
    },
    "header2": {
        "mode": ModeEnum.invert,
        "fore": ForColorEnum.purple,
        "back": BackColorEnum.default,
        "width": 30,
    },
    "header3": {
        "mode": ModeEnum.underline,
        "fore": ForColorEnum.yellow,
        "back": BackColorEnum.default,
        "width": -1,
    },
    "key": {
        "mode": ModeEnum.normal,
        "fore": ForColorEnum.blue,
        "back": BackColorEnum.default,
        "width": 10,
    },
    "value": {
        "mode": ModeEnum.normal,
        "fore": ForColorEnum.default,
        "back": BackColorEnum.default,
        "width": 25,
    },
}


def get_formatted(
    string: str,
    mode: ModeEnum = ModeEnum.normal,
    fore: ForColorEnum = ForColorEnum.default,
    back: BackColorEnum = BackColorEnum.default,
    width=-1,
) -> str:
    """
    Get formatted string to display in console

    :param string: text to convert
    :type string: str
    :param mode: text mode
    :type mode: ModeEnum
    :param fore: forground color
    :type fore: ForColorEnum
    :param back: background color
    :type back: BackColorEnum
    :param width: text width
    :type width: int
    :return: string with console format
    :rtype: str
    """
    mode = "{}".format(mode.value if mode != mode.normal else "")
    fore = "{}".format(fore.value if fore != ForColorEnum.default else "")
    back = "{}".format(back.value if back != BackColorEnum.default else "")
    style = ";".join([s for s in [mode, fore, back] if s])
    end = ""
    if style != "":
        style = """\033[{}m""".format(style)
        end = """\033[0m"""
    if width > 0:
        string = "{}{:<{}}{}".format(style, string, width, end)
    else:
        string = "{}{}{}".format(style, string, end)

    return string


def get_formatted_predefined(string: str, style: Dict)->str:
    """
    Get formatted string with predefined rule

    :param string: text to convert
    :type string: str
    :param style: style defined in STYLE dictionary
    :type style: Dict
    :return: string with console format
    :rtype: str
    """
    return get_formatted(string, style["mode"], style["fore"], style["back"], style["width"])


def get_formatted_from_dict(values: Dict[str, str]) -> str:
    """
    Get formatted string of key:value pair with predefined rule

    :param values: dict to convert, e.g. name: Eric.
    :type values: Dict[str, str]
    :return: string with console format
    :rtype: str
    """
    str_array = []
    for k, v in values.items():
        str_array.append(f"{get_formatted_predefined(k, STYLE['key'])}:{get_formatted_predefined(str(v), STYLE['value'])}")
    return "".join(str_array)
