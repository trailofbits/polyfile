import os
from pathlib import Path
from setuptools import setup, find_packages

import compile_kaitai_parsers


POLYFILE_DIR: Path = Path(__file__).absolute().parent
README_PATH: Path = POLYFILE_DIR / "README.md"

compile_kaitai_parsers.rebuild()

with open(README_PATH, "r", encoding="utf8") as readme:
    README = readme.read()

setup(
    name='polyfile',
    description='A utility to recursively map the structure of a file.',
    long_description=README,
    long_description_content_type="text/markdown",
    url='https://github.com/trailofbits/polyfile',
    author='Trail of Bits',
    version="0.5.4",
    packages=find_packages(exclude=("tests",)),
    python_requires='>=3.8',
    install_requires=[
        "abnf~=2.2.0",
        "chardet~=5.0.0",
        "cint>=1.0.0",
        "fickling>=0.0.8",
        "graphviz>=0.20.1",
        "intervaltree>=2.4.0",
        "jinja2>=2.1.0",
        "kaitaistruct~=0.10",
        "networkx>=2.6.3",
        "pdfminer.six==20220524",
        "Pillow>=5.0.0",
        "pyreadline3;platform_system=='Windows'",
        "pyyaml>=3.13",
        "setuptools>=65.5.1"
    ],
    extras_require={
        'demangle': ['cxxfilt'],
        "dev": ["mypy", "pytest", "flake8"]
    },
    entry_points={
        'console_scripts': [
            'polyfile = polyfile.__main__:main'
        ]
    },
    package_data={"polyfile": [
        os.path.join("templates", "*"),
        os.path.join("kaitai", "parsers", "*.py"),
        os.path.join("kaitai", "parsers", "manifest.json"),
        os.path.join("magic_defs", "*")
    ]},
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
