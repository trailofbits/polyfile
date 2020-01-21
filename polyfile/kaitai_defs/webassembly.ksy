# -*- mode: yaml -*-
meta:
    id: webassembly
    title: Web Assembly parser
    file-extension: wasm
    endian: le
    license: CC0-1.0
    file-extension:
      - wasm
    imports:
      - vlq_base128_le

doc: |
  WebAssembly is a web standard that defines a binary format and a corresponding
  assembly-like text format for executable code in Web pages. It is meant to
  enable executing code nearly as fast as running native machine code.

doc-ref: https://github.com/WebAssembly/design/blob/master/BinaryEncoding.md

#####################################################################################################

seq:
    - id: magic
      size: 4
      contents: [0x00, "asm"]
    - id: version
      type: u4
    - id: sections
      type: sections

#####################################################################################################

types:

  func_type:
    seq:
      - id: form
        type: u1
        enum: constructor_type
      - id: param_count
        type: u1
      - id: param_types
        type: u1
        enum: value_type
        repeat: expr
        repeat-expr: param_count
        if: param_count > 0
      - id: return_count
        type: u1
      - id: return_type
        type: u1
        enum: value_type
        if: return_count==1

  resizable_limits_type:
    seq:
      - id: flags
        type: u1
      - id: initial
        type: vlq_base128_le
      - id: maximum
        type: vlq_base128_le
        if: flags == 1

  table_type:
    seq:
      - id: element_type
        type: u1
        enum: elem_type
      - id: limits
        type: resizable_limits_type

  memory_type:
    seq:
      - id: limits
        type: resizable_limits_type

  global_type:
    seq:
      - id: content_type
        type: u1
        enum: value_type
      - id: mutability
        type: u1
        enum: mutability_flag

  global_variable_type:
    seq:
      - id: type
        type: global_type
      - id: init
        type: u1
        repeat: until
        repeat-until: _ == 0x0b

  export_entry_type:
    seq:
      - id: field_len
        type: vlq_base128_le
      - id: field_str
        type: str
        encoding: UTF-8
        size: field_len.value
      - id: kind
        type: u1
        enum: kind_type
      - id: index
        type: vlq_base128_le

  elem_segment_type:
    seq:
      - id: index
        type: vlq_base128_le
      - id: offset
        type: u1
        repeat: until
        repeat-until: _ == 0x0b
      - id: num_elem
        type: vlq_base128_le
      - id: elems
        type: vlq_base128_le
        repeat: expr
        repeat-expr: num_elem.value

  function_body_type:
    seq:
      - id: body_size
        type: vlq_base128_le
      - id: data
        type: function_body_data_type
        size: body_size.value

  function_body_data_type:
    seq:
      - id: local_count
        type: vlq_base128_le
      - id: locals
        type: local_entry_type
        repeat: expr
        repeat-expr: local_count.value
      - id: code
        size-eos: true

  local_entry_type:
    seq:
      - id: count
        type: vlq_base128_le
      - id: type
        type: u1
        enum: value_type

  data_segment_type:
    seq:
      - id: index
        type: vlq_base128_le
      - id: offset
        type: u1
        repeat: until
        repeat-until: _ == 0x0b
      - id: size
        type: vlq_base128_le
      - id: data
        type: u1
        repeat: expr
        repeat-expr: size.value

  section_header:
    seq:
      - id: id
        type: u1
        enum: payload_type
      - id: payload_len
        type: vlq_base128_le
      - id: name_len
        type: vlq_base128_le
        #type: u4
        if: id == payload_type::custom_payload
      - id: name
        size: name_len
        if: id == payload_type::custom_payload

  section:
    seq:
      - id: header
        type: section_header

      - id: payload_data
        type:
          switch-on: header.id
          cases:
            # https://github.com/WebAssembly/design/blob/master/BinaryEncoding.md#high-level-structure
            'payload_type::custom_payload':    unimplemented_section
            'payload_type::type_payload':      type_section
            'payload_type::import_payload':    import_section
            'payload_type::function_payload':  function_section
            'payload_type::table_payload':     table_section
            'payload_type::memory_payload':    memory_section
            'payload_type::global_payload':    global_section
            'payload_type::export_payload':    export_section
            'payload_type::start_payload':     start_section
            'payload_type::element_payload':   element_section
            'payload_type::code_payload':      code_section
            'payload_type::data_payload':      data_section


  sections:
    seq:
      - id: sections
        type: section
        repeat: eos

  type_section:
    # https://github.com/WebAssembly/design/blob/master/BinaryEncoding.md#type-section
    seq:
      - id: count
        type: u1
      - id: entries
        type: func_type
        repeat: expr
        repeat-expr: count

  import_section:
    # https://github.com/WebAssembly/design/blob/master/BinaryEncoding.md#import-section
    seq:
      - id: count
        type: u1
      - id: entries
        type: import_entry
        if: count > 0
        repeat: expr
        repeat-expr: count

  import_entry:
    # https://github.com/WebAssembly/design/blob/master/BinaryEncoding.md#import-entry
    seq:
      - id: module_len
        type: vlq_base128_le
      - id: module_str
        type: str
        size: module_len.value
        encoding: UTF-8
      - id: field_len
        type: vlq_base128_le
      - id: field_str
        type: str
        size: field_len.value
        encoding: UTF-8
      - id: kind
        type: u1
        enum: kind_type
      - id: type
        type:
          switch-on: kind
          cases:
            'kind_type::function_kind':  vlq_base128_le
            'kind_type::table_kind':     table_type
            'kind_type::memory_kind':    memory_type
            'kind_type::global_kind':    global_type

  function_section:
    # https://github.com/WebAssembly/design/blob/master/BinaryEncoding.md#function-section
    seq:
      - id: count
        type: vlq_base128_le
      - id: types
        type: vlq_base128_le
        repeat: expr
        repeat-expr: count.value

  table_section:
    # https://github.com/WebAssembly/design/blob/master/BinaryEncoding.md#table-section
    seq:
      - id: count
        type: vlq_base128_le
      - id: entries
        type: table_type
        repeat: expr
        repeat-expr: count.value

  memory_section:
    # https://github.com/WebAssembly/design/blob/master/BinaryEncoding.md#memory-section
    seq:
      - id: count
        type: vlq_base128_le
      - id: entries
        type: memory_type
        repeat: expr
        repeat-expr: count.value

  global_section:
    # https://github.com/WebAssembly/design/blob/master/BinaryEncoding.md#global-section
    seq:
      - id: count
        type: vlq_base128_le
      - id: globals
        type: global_variable_type
        repeat: expr
        repeat-expr: count.value

  export_section:
    # https://github.com/WebAssembly/design/blob/master/BinaryEncoding.md#export-section
    seq:
      - id: count
        type: vlq_base128_le
      - id: entries
        type: export_entry_type
        repeat: expr
        repeat-expr: count.value

  start_section:
    # https://github.com/WebAssembly/design/blob/master/BinaryEncoding.md#start-section
    seq:
      - id: index
        type: vlq_base128_le

  element_section:
    # https://github.com/WebAssembly/design/blob/master/BinaryEncoding.md#element-section
    seq:
      - id: count
        type: vlq_base128_le
      - id: entries
        type: elem_segment_type
        repeat: expr
        repeat-expr: count.value

  code_section:
    # https://github.com/WebAssembly/design/blob/master/BinaryEncoding.md#code-section
    seq:
      - id: count
        type: vlq_base128_le
      - id: bodies
        type: function_body_type
        repeat: expr
        repeat-expr: count.value

  data_section:
    # https://github.com/WebAssembly/design/blob/master/BinaryEncoding.md#data-section
    seq:
      - id: count
        type: vlq_base128_le
      - id: entries
        type: data_segment_type
        repeat: expr
        repeat-expr: count.value

  unimplemented_section:
      seq:
        - id: raw
          type: u1
          repeat: expr
          repeat-expr: _parent.header.payload_len.value - _parent.header.name_len.value - 1

#####################################################################################################

enums:

  constructor_type:
    0x7f: i32
    0x7e: i64
    0x7d: f32
    0x7c: f64
    0x70: anyfunc
    0x60: func
    0x40: empty_block

  value_type:
    0x7f: i32
    0x7e: i64
    0x7d: f32
    0x7c: f64

  kind_type:
    0: function_kind
    1: table_kind
    2: memory_kind
    3: global_kind

  payload_type:
    0: custom_payload
    1: type_payload
    2: import_payload
    3: function_payload
    4: table_payload
    5: memory_payload
    6: global_payload
    7: export_payload
    8: start_payload
    9: element_payload
    10: code_payload
    11: data_payload

  elem_type:
    0x70: anyfunc

  mutability_flag:
    0: immutable
    1: mutable
