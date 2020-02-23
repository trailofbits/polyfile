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
        'graphviz',
        'intervaltree',
        'jinja2',
        'kaitaistruct>=0.7',
        'networkx',
        'Pillow>=5.0.0',
        'pyyaml>=3.13',
        'setuptools'
    ],
    extras_require={
        'demangle': ['cxxfilt'],
    },
    entry_points={
        'console_scripts': [
            'polyfile = polyfile.__main__:main',
            'polymerge = polymerge.__main__:main'
        ]
    },
    package_data={'polyfile': ['defs.json.gz', os.path.join('templates', '*')]},
    include_package_data=True,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python :: 3 :: Only',
        'Topic :: Security',
        'Topic :: Software Development :: Testing',
        'Topic :: Utilities'
    ]
)
