"""Object identity and wire bytes survive serialization type corrections."""

from polyfile import serialization


LEGACY_VALUES = bytes.fromhex(
    "a784856669727374a684867365636f6e64a581a48280a38281a28380a183ffa0830180"
    "9f83020000000000000000809e8482c3a99d858200ff9c84857475706c659b879c809a"
    "838199838298899a9980978383968384958a9796809486a5a4a3a2a1a09f9e9d9b98"
    "95808188a794a69480"
)


def test_repeated_values_keep_the_existing_wire_format() -> None:
    value = [1, b"ab", 1]
    encoded = serialization.dumps(value)
    assert encoded.hex() == "8483818385826162818684838480"
    assert serialization.loads(encoded) == value


def test_shared_children_are_restored_as_one_object() -> None:
    child = ["shared", b"content"]
    value = {"first": child, "second": child}
    restored = serialization.loads(serialization.dumps(value))
    assert isinstance(restored, dict)
    assert restored == value
    assert restored["first"] is restored["second"]


def test_legacy_supported_values_and_sharing_remain_readable() -> None:
    """Read bytes produced by the serializer before PR3766 polishing."""
    child = [
        None,
        False,
        True,
        0,
        127,
        128,
        2**64,
        "é",
        b"\0\xff",
        ("tuple",),
        {1, 2},
        frozenset({3, 4}),
    ]
    restored = serialization.loads(LEGACY_VALUES)

    assert isinstance(restored, dict)
    assert restored == {"first": child, "second": child}
    assert restored["first"] is restored["second"]
