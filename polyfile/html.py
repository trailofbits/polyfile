import os

from jinja2 import Template

TEMPLATE_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'templates', 'template.html')
TEMPLATE = None


def assign_ids(matches):
    i = 0
    stack = list(matches)
    while stack:
        m = stack.pop()
        assert 'uid' not in m
        m['uid'] = i
        i += 1
        stack += list(m['children'])
    return matches


def generate(file_path, matches):
    global TEMPLATE
    if TEMPLATE is None:
        with open(TEMPLATE_PATH, 'r') as template:
            TEMPLATE = Template(template.read())

    matches = assign_ids(matches)

    return TEMPLATE.render(file_path=file_path, matches=matches)


if __name__ == '__main__':
    import json
    import sys

    with open(sys.argv[2], 'r') as f:
        print(generate(sys.argv[1], json.load(f)))
