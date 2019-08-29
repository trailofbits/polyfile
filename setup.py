import os
from setuptools import setup, find_packages

from polyfile.trid import build_defs_cache_if_necessary

build_defs_cache_if_necessary()

setup(
    name='polyfile',
    description='A utility to recursively map the structure of a file.',
    url='https://github.com/trailofbits/polyfile',
    author='Trail of Bits',
    version='0.0.1',
    packages=find_packages(),
    python_requires='>=3.6',
    install_requires=[
        'jinja2',
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
