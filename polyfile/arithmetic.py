from typing import Callable, Dict, Tuple

import cint


CStyleInt = cint.Cint


INT_TYPES: Dict[Tuple[int, bool], Callable[[int], CStyleInt]] = {
    (1, False): cint.U8,
    (1, True): cint.I8,
    (2, False): cint.U16,
    (2, True): cint.I16,
    (4, False): cint.U32,
    (4, True): cint.I32,
    (8, False): cint.U64,
    (8, True): cint.I64
}


def make_c_style_int(value: int, num_bytes: int, signed: bool):
    if (num_bytes, signed) not in INT_TYPES:
        raise NotImplementedError(f"{num_bytes*8}-bit {['un',''][signed]}signed integers are not yet supported")
    return INT_TYPES[(num_bytes, signed)](value)


setattr(CStyleInt, "new", make_c_style_int)
