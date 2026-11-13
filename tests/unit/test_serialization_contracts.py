"""Object identity and wire bytes survive serialization type corrections."""

from polyfile import serialization


def test_repeated_values_keep_the_existing_wire_format() -> None:
    value = [1, b"ab", 1]
    encoded = serialization.dumps(value)
    assert encoded.hex() == "8483818385826162818684838480"
    assert serialization.loads(encoded) == value


def test_shared_children_are_restored_as_one_object() -> None:
    child = ["shared", b"content"]
    value = {"first": child, "second": child}
    restored = serialization.loads(serialization.dumps(value))
    assert restored == value
    assert restored["first"] is restored["second"]
