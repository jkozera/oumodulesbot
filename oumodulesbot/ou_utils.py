import re
from typing import Iterable

MODULE_CODE_RE_TEMPLATE = r"[a-zA-Z]{1,6}[0-9]{1,3}(?:-[a-zA-Z]{1,5})?"
# QD = Open Degree:
QUALIFICATION_CODE_RE_TEMPLATE = r"[a-zA-Z][0-9]{2}(?:-[a-zA-Z]{1,5})?|QD"
QUALIFICATION_CODE_RE = re.compile(fr"^({QUALIFICATION_CODE_RE_TEMPLATE})$")
MODULE_OR_QUALIFICATION_CODE_RE_TEMPLATE = (
    fr"{MODULE_CODE_RE_TEMPLATE}|{QUALIFICATION_CODE_RE_TEMPLATE}"
)


def get_possible_qualification_urls(code: str) -> Iterable[str]:
    return [
        f"http://www.open.ac.uk/courses/qualifications/{code}",
        f"http://www.open.ac.uk/postgraduate/qualifications/{code}",
    ]


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


def get_possible_urls_from_code(code: str) -> Iterable[str]:
    code = code.lower()
    if QUALIFICATION_CODE_RE.match(code):
        return get_possible_qualification_urls(code)
    return [get_module_url(code)]
