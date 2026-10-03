"""HID-v1 shared constants: envelope magic, codec identifiers, DAG opcodes.

Constants only. The serializer (wire.py) and the search import this module.
The independent decoder (decode.py) deliberately does NOT import it and keeps
its own copy, so that a wrong constant here cannot be silently mirrored by the
decoder; tests/test_wire.py asserts the two copies agree.
"""
from __future__ import annotations

MAGIC = b"ISD1"
MAX_U = 2 ** 63 - 1

# W2 codec identifiers.
CODEC_LITERAL = 0
CODEC_HID = 1
CODEC_RLE = 2
CODEC_GAPS = 3
CODEC_PERIOD = 4
CODEC_BERNOULLI = 5
CODEC_CONTEXT = 6
CODEC_ZLIB = 7
CODEC_LZMA = 8
CODEC_PAIR = 9

CODEC_NAMES = {
    CODEC_LITERAL: "raw", CODEC_HID: "hid", CODEC_RLE: "rle", CODEC_GAPS: "gaps",
    CODEC_PERIOD: "period", CODEC_BERNOULLI: "bernoulli", CODEC_CONTEXT: "context",
    CODEC_ZLIB: "zlib", CODEC_LZMA: "lzma", CODEC_PAIR: "pair_grammar",
}

# W3 DAG opcodes.
OP_LITERAL = 0
OP_CONCAT = 1
OP_REPEAT = 2
OP_AP_UNION = 3
OP_SCHEMA_UNION = 4
OP_PATCH = 5
OP_XFORM = 6

OP_NAMES = {
    OP_LITERAL: "LITERAL", OP_CONCAT: "CONCAT", OP_REPEAT: "REPEAT",
    OP_AP_UNION: "AP_UNION", OP_SCHEMA_UNION: "SCHEMA_UNION", OP_PATCH: "PATCH",
    OP_XFORM: "XFORM",
}

XFORM_COMPLEMENT = 1
XFORM_REVERSE = 2

# W6 standard-library compressor parameters.
ZLIB_LEVEL = 9
LZMA_PRESET = 6

# W7 pair grammar.
PAIR_MAX_RULES = 4096
