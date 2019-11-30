# -*- mode: yaml -*-
meta:
  id: vlq_base128_le
  title: Variable length quantity, unsigned integer, base128, little-endian
  license: CC0-1.0
  ks-version: 0.7
doc: |
  A variable-length unsigned integer using base128 encoding. 1-byte groups
  consists of 1-bit flag of continuation and 7-bit value, and are ordered
  least significant group first, i.e. in little-endian manner
  (https://github.com/kaitai-io/kaitai_struct_formats/blob/master/common/vlq_base128_le.ksy)

seq:
  - id: groups
    type: group
    repeat: until
    repeat-until: not _.has_next
types:
  group:
    doc: |
      One byte group, clearly divided into 7-bit "value" and 1-bit "has continuation
      in the next byte" flag.
    seq:
      - id: b
        type: u1
    instances:
      has_next:
        value: (b & 0b1000_0000) != 0
        doc: If true, then we have more bytes to read
      value:
        value: b & 0b0111_1111
        doc: The 7-bit (base128) numeric value of this group
instances:
  len:
    value: groups.size
  value:
    value: >-
      groups[0].value
      + (len >= 2 ? (groups[1].value << 7) : 0)
      + (len >= 3 ? (groups[2].value << 14) : 0)
      + (len >= 4 ? (groups[3].value << 21) : 0)
      + (len >= 5 ? (groups[4].value << 28) : 0)
      + (len >= 6 ? (groups[5].value << 35) : 0)
      + (len >= 7 ? (groups[6].value << 42) : 0)
      + (len >= 8 ? (groups[7].value << 49) : 0)
    doc: Resulting value as normal integer
