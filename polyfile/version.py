import os
import subprocess


def git_branch():
    branch = subprocess.check_output(
        ['git', 'symbolic-ref', '-q', 'HEAD'],
        cwd=os.path.dirname(os.path.realpath(__file__)),
        stderr=subprocess.DEVNULL
    )
    branch = branch.decode('utf-8').strip().split('/')[-1]
    return branch


# Change DEV_BUILD to False when deploying to PyPI
DEV_BUILD = True


__version__ = (0, 1, 5)

if DEV_BUILD:
    __version__ = __version__ + ('git', git_branch())

VERSION_STRING = ''

for element in __version__:
    if isinstance(element, int):
        if VERSION_STRING:
            VERSION_STRING += f'.{element}'
        else:
            VERSION_STRING = str(element)
    else:
        if VERSION_STRING:
            VERSION_STRING += f'-{element!s}'
        else:
            VERSION_STRING += str(element)


if __name__ == '__main__':
    print(VERSION_STRING)
