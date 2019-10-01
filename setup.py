import os
from setuptools import setup, find_packages

VERSION_MODULE_PATH = os.path.join(os.path.realpath(os.path.dirname(__file__)), "polyfile", "version.py")


def get_version_string():
    version = {}
    with open(VERSION_MODULE_PATH) as f:
        exec(f.read(), version)
    return version['VERSION_STRING']


setup(
    name='polyfile',
    description='A utility to recursively map the structure of a file.',
    url='https://github.com/trailofbits/polyfile',
    author='Trail of Bits',
    version=get_version_string(),
    packages=find_packages(),
    python_requires='>=3.6',
    install_requires=[
        'jinja2',
        'kaitaistruct>=0.7',
        'Pillow>=5.0.0',
        'pyyaml>=3.13',
        'setuptools'
    ],
    entry_points={
        'console_scripts': [
            'polyfile = polyfile.__main__:main'
        ]
    },
    package_data={'polyfile': ['defs.json.gz', os.path.join('templates', '*')]},
    include_package_data=True,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU Affero General Public License v3',
        'Topic :: Security',
        'Topic :: Software Development :: Testing'
    ]
)
