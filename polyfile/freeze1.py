"""Freeze 1.x adaptive Huffman decoding, adapted from Ancient 2.3.0.

BSD 2-Clause License

Copyright (c) 2017-2025, Teemu Suutari
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

* Redistributions of source code must retain the above copyright notice, this
  list of conditions and the following disclaimer.
* Redistributions in binary form must reproduce the above copyright notice,
  this list of conditions and the following disclaimer in the documentation
  and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

from array import array

from polyfile.compression import DecodeError, DecodeResult, OutputBuffer, RawRegion
from polyfile.fileutils import FileStream

FREEZE_MAGIC = b"\x1f\x9e"
FREEZE_MEMORY = 64 * 1024
_SYMBOLS = 315
_ROOT = _SYMBOLS * 2 - 2
_WINDOW = 4096
_DISTANCE_COUNTS = (0, 0, 1, 3, 8, 12, 24, 16)


class _Bits:
    def __init__(self, stream: FileStream) -> None:
        self.stream = stream
        self.value = 0
        self.remaining = 0

    def read(self, count: int = 1) -> int:
        result = 0
        for _ in range(count):
            if not self.remaining:
                data = self.stream.read(1)
                if not data:
                    raise DecodeError(
                        "truncated freeze 1.x bitstream before end marker"
                    )
                self.value, self.remaining = data[0], 8
            self.remaining -= 1
            result = (result << 1) | ((self.value >> self.remaining) & 1)
        return result


class _AdaptiveHuffman:
    def __init__(self) -> None:
        self.frequency = array("I", [0]) * (_ROOT + 1)
        self.index = array("I", range(_ROOT + 1))
        self.parent = array("I", [0]) * (_ROOT + 1)
        self.left = array("I", [0]) * (_ROOT + 1)
        self.right = array("I", [0]) * (_ROOT + 1)
        self.order = array("I", range(_ROOT + 1))
        for code in range(_SYMBOLS):
            self.frequency[code] = 1
            self.parent[code] = _SYMBOLS + (code >> 1)
        for code in range(_SYMBOLS, _ROOT + 1):
            child = (code - _SYMBOLS) * 2
            self._join(code, child, child + 1)

    def _join(self, code: int, left: int, right: int) -> None:
        self.frequency[code] = self.frequency[left] + self.frequency[right]
        self.index[code] = code
        self.parent[code] = _SYMBOLS + (code >> 1)
        self.left[code], self.right[code] = left, right
        self.order[code] = code

    def decode(self, bits: _Bits) -> int:
        code = _ROOT
        while code >= _SYMBOLS:
            code = self.right[code] if bits.read() else self.left[code]
        if self.frequency[_ROOT] == 0x8000:
            self._halve()
        self._update(code)
        return code

    def _swap(self, code: int, other: int) -> None:
        first, second = self.index[code], self.index[other]
        self.order[first], self.order[second] = other, code
        self.index[code], self.index[other] = second, first
        parent, other_parent = self.parent[code], self.parent[other]
        side = self.left if self.left[parent] == code else self.right
        other_side = self.left if self.left[other_parent] == other else self.right
        side[parent], other_side[other_parent] = other, code
        self.parent[code], self.parent[other] = other_parent, parent

    def _update(self, code: int) -> None:
        while code != _ROOT:
            self.frequency[code] += 1
            position = self.index[code]
            destination = position
            while (
                destination != _ROOT
                and self.frequency[code] > self.frequency[self.order[destination + 1]]
            ):
                destination += 1
            if position != destination:
                self._swap(code, self.order[destination])
            code = self.parent[code]
        self.frequency[_ROOT] += 1

    def _halve(self) -> None:
        position = 0
        for code in self.order:
            if code < _SYMBOLS:
                self.index[code] = position
                position += 1
        for code in range(_SYMBOLS):
            self.frequency[code] = (self.frequency[code] + 1) >> 1
            self.parent[code] = _SYMBOLS + (self.index[code] >> 1)
            self.order[self.index[code]] = code
        for code in range(_SYMBOLS, _ROOT + 1):
            child = (code - _SYMBOLS) * 2
            self._join(code, self.order[child], self.order[child + 1])
            self._reorder(code)

    def _reorder(self, code: int) -> None:
        position = code
        while self.frequency[code] < self.frequency[self.order[position - 1]]:
            other = self.order[position - 1]
            self.index[code], self.index[other] = self.index[other], self.index[code]
            self.parent[code], self.parent[other] = (
                self.parent[other],
                self.parent[code],
            )
            self.order[position], self.order[position - 1] = other, code
            position -= 1


def _distance(bits: _Bits) -> int:
    value = first = symbol = 0
    for count in _DISTANCE_COUNTS[:-1]:
        value = (value << 1) | bits.read()
        if value < first + count:
            return ((symbol + value - first) << 6) + bits.read(6) + 1
        symbol += count
        first = (first + count) << 1
    value = (value << 1) | bits.read()
    return ((symbol + value - first) << 6) + bits.read(6) + 1


def _expand(stream: FileStream, output: OutputBuffer) -> None:
    bits = _Bits(stream)
    tree = _AdaptiveHuffman()
    history = bytearray(b" " * _WINDOW)
    position = 0
    while (code := tree.decode(bits)) != 256:
        if code < 256:
            data = bytes((code,))
            history[position] = code
            position = (position + 1) % _WINDOW
        else:
            distance = _distance(bits)
            copied = bytearray()
            for _ in range(code - 254):
                value = history[(position - distance) % _WINDOW]
                copied.append(value)
                history[position] = value
                position = (position + 1) % _WINDOW
            data = bytes(copied)
        output.append(data)


def decode_freeze1(
    stream: FileStream, *, max_output: int | None = None
) -> DecodeResult:
    """Decodes one freeze 1.x stream, requiring its end marker and complete consumption.

    Args:
        stream: Encoded bytes positioned at the two-byte freeze signature.
        max_output: Optional decoded byte allowance.

    Returns:
        Validated bytes and physical signature/body regions.

    Raises:
        DecodeError: If the signature, bitstream, or output allowance is invalid.
    """
    start = stream.tell()
    header = stream.read(2)
    regions = (
        RawRegion("freeze_1_header", start, len(header), header),
        RawRegion(
            "adaptive_huffman_data", start + len(header), len(stream) - stream.tell()
        ),
    )
    try:
        if header != FREEZE_MAGIC:
            raise DecodeError("invalid or truncated freeze 1.x signature")
        output = OutputBuffer(max_output)
        _expand(stream, output)
        if stream.tell() != len(stream):
            raise DecodeError("trailing bytes after freeze 1.x end marker")
    except DecodeError as error:
        raise DecodeError(str(error), status=error.status, regions=regions) from error
    return DecodeResult(output.finish(), regions)
