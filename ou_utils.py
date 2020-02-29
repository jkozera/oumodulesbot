def get_module_level(module_code):
    for c in module_code:
        if c.isdigit():
            return int(c)


def get_module_url(module_code):
    if get_module_level(module_code) == 0:
        template = "http://www.open.ac.uk/courses/short-courses/{}"
    elif get_module_level(module_code) == 8:
        template = "http://www.open.ac.uk/postgraduate/modules/{}"
    else:
        template = "http://www.open.ac.uk/courses/modules/{}"
    return template.format(module_code.lower())
