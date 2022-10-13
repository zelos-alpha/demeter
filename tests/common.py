def assert_equal_with_error(a, b, allowed_error=0.005):
    if a == b == 0:
        return True
    base = a if a != 0 else b
    error = (a - b) / base
    return error < allowed_error


def assert_equal(a, b, msg=""):
    if a != b:
        raise RuntimeError(f"{a} not equal to {b}, {msg}")
