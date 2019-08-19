# PolyFile
A utility to identify and map the semantic structure of files, including polyglots, chimeras, and schizophrenic files.

## Quickstart

In the same directory as this README, run:
```
pip3 install -e .
```

This will automatically install the `polyfile` executable in your path.

## Usage

```
$ polyfile --help
usage: polyfile [-h] [--debug] [--quiet] FILE

A utility to recursively map the structure of a file.

positional arguments:
  FILE         The file to analyze

optional arguments:
  -h, --help   show this help message and exit
  --debug, -d  Print debug information
  --quiet, -q  Suppress all log output (overrides --debug)
```

To generate a JSON mapping of a file, run:

```
polyfile INPUT_FILE > output.json
```

## License

PolyFile was created by Trail of Bits under subcontract to Galois on the DARPA SafeDocs project. Licensing TBD.