MODULE_CODE_RE_TEMPLATE = r"[a-zA-Z]{1,6}[0-9]{1,3}(?:-[a-zA-Z]{1,5})?"


def get_module_level(module_code: str) -> int:
    for c in module_code:
        if c.isdigit():
            return int(c)
    raise ValueError(f"Invalid module code: {module_code}")


def get_module_url(module_code: str) -> str:
    if get_module_level(module_code) == 0:
        template = "http://www.open.ac.uk/courses/short-courses/{}"
    elif get_module_level(module_code) == 8:
        template = "http://www.open.ac.uk/postgraduate/modules/{}"
    else:
        template = "http://www.open.ac.uk/courses/modules/{}"
    return template.format(module_code.lower())
