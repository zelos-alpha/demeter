from enum import Enum
from typing import Dict


class ForColorEnum(Enum):
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


def get_formatted_predefined(string: str, style):
    return get_formatted(string, style["mode"], style["fore"], style["back"], style["width"])


def get_formatted_from_dict(values: Dict[str, str]) -> str:
    str_array = []
    for k, v in values.items():
        str_array.append(f"{get_formatted_predefined(k, STYLE['key'])}:{get_formatted_predefined(str(v), STYLE['value'])}")
    return "".join(str_array)


# def TestColor():
#     print(get_formatted('正常显示'))
#     print('')
#     print("测试显示模式")
#     print(get_formatted('高亮', mode=ModeEnum.bold), )
#     print(get_formatted('下划线', mode=ModeEnum.underline), )
#     print(get_formatted('闪烁', mode=ModeEnum.blink), )
#     print(get_formatted('反白', mode=ModeEnum.invert), )
#     print(get_formatted('不可见', mode=ModeEnum.hide))
#     print('')
#     print("测试前景色")
#     print(get_formatted('黑色', fore=ForColorEnum.black), )
#     print(get_formatted('红色', fore=ForColorEnum.red), )
#     print(get_formatted('绿色', fore=ForColorEnum.green), )
#     print(get_formatted('黄色', fore=ForColorEnum.yellow), )
#     print(get_formatted('蓝色', fore=ForColorEnum.blue), )
#     print(get_formatted('紫红色', fore=ForColorEnum.purple), )
#     print(get_formatted('青蓝色', fore=ForColorEnum.cyan), )
#     print(get_formatted('白色', fore=ForColorEnum.white))
#     print('')
#     print("测试背景色")
#     print(get_formatted('黑色', back=BackColorEnum.black), )
#     print(get_formatted('红色', back=BackColorEnum.red), )
#     print(get_formatted('绿色', back=BackColorEnum.green), )
#     print(get_formatted('黄色', back=BackColorEnum.yellow), )
#     print(get_formatted('蓝色', back=BackColorEnum.blue), )
#     print(get_formatted('紫红色', back=BackColorEnum.purple), )
#     print(get_formatted('青蓝色', back=BackColorEnum.cyan), )
#     print(get_formatted('白色', back=BackColorEnum.white))
#     print('')
#     print(get_formatted("综合", ModeEnum.invert, ForColorEnum.red))
#
#
# if __name__ == '__main__':
#     TestColor()
