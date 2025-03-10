from pathlib import Path

from .fileutils import ExactNamedTempfile
from .magic import MagicMatcher, TestType

with ExactNamedTempfile(b"""# The default libmagic test for NITF does not associate a MIME type,
# and does not support NITF 02.10
0       string  NITF       NITF
>4      string  02.10      \\ version 2.10 (ISO/IEC IS 12087-5)
>25     string  >\\0     dated %.14s
!:mime application/vnd.nitf
!:ext ntf
""", name="NITFMatcher") as t:
    nitf_matcher = MagicMatcher.DEFAULT_INSTANCE.add(Path(t), test_type=TestType.BINARY)[0]
    assert nitf_matcher.test_type == TestType.BINARY
