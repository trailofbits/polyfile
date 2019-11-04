__version__ = (0, 1, 4)

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
