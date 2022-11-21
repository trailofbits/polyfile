# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild

from pkg_resources import parse_version
import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO
import collections


if parse_version(kaitaistruct.__version__) < parse_version('0.9'):
    raise Exception("Incompatible Kaitai Struct Python API: 0.9 or later is required, but you have %s" % (kaitaistruct.__version__))

class DosDatetime(KaitaiStruct):
    """MS-DOS date and time are packed 16-bit values that specify local date/time.
    The time is always stored in the current UTC time offset set on the computer
    which created the file. Note that the daylight saving time (DST) shifts
    also change the UTC time offset.
    
    For example, if you pack two files A and B into a ZIP archive, file A last modified
    at 2020-03-29 00:59 UTC+00:00 (GMT) and file B at 2020-03-29 02:00 UTC+01:00 (BST),
    the file modification times saved in MS-DOS format in the ZIP file will vary depending
    on whether the computer packing the files is set to GMT or BST at the time of ZIP creation.
    
      - If set to GMT:
          - file A: 2020-03-29 00:59 (UTC+00:00)
          - file B: 2020-03-29 01:00 (UTC+00:00)
      - If set to BST:
          - file A: 2020-03-29 01:59 (UTC+01:00)
          - file B: 2020-03-29 02:00 (UTC+01:00)
    
    It follows that you are unable to determine the actual last modified time
    of any file stored in the ZIP archive, if you don't know the locale time
    setting of the computer at the time it created the ZIP.
    
    This format is used in some data formats from the MS-DOS era, for example:
    
      - [zip](/zip/)
      - [rar](/rar/)
      - [vfat](/vfat/) (FAT12)
      - [lzh](/lzh/)
      - [cab](http://justsolve.archiveteam.org/wiki/Cabinet)
    
    .. seealso::
       Source - https://docs.microsoft.com/en-us/windows/win32/sysinfo/ms-dos-date-and-time
    
    
    .. seealso::
       Source - https://docs.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-dosdatetimetofiletime
    
    
    .. seealso::
       DosDateTimeToFileTime - https://github.com/reactos/reactos/blob/c6b6444/dll/win32/kernel32/client/time.c#L82-L87
    
    
    .. seealso::
       page 25/34 - https://download.microsoft.com/download/0/8/4/084c452b-b772-4fe5-89bb-a0cbf082286a/fatgen103.doc
    """
    SEQ_FIELDS = ["time", "date"]
    def __init__(self, _io, _parent=None, _root=None):
        self._io = _io
        self._parent = _parent
        self._root = _root if _root else self
        self._debug = collections.defaultdict(dict)

    def _read(self):
        self._debug['time']['start'] = self._io.pos()
        self.time = DosDatetime.Time(self._io, self, self._root)
        self.time._read()
        self._debug['time']['end'] = self._io.pos()
        self._debug['date']['start'] = self._io.pos()
        self.date = DosDatetime.Date(self._io, self, self._root)
        self.date._read()
        self._debug['date']['end'] = self._io.pos()

    class Time(KaitaiStruct):
        SEQ_FIELDS = ["second_div_2", "minute", "hour"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['second_div_2']['start'] = self._io.pos()
            self.second_div_2 = self._io.read_bits_int_le(5)
            self._debug['second_div_2']['end'] = self._io.pos()
            if not self.second_div_2 <= 29:
                raise kaitaistruct.ValidationGreaterThanError(29, self.second_div_2, self._io, u"/types/time/seq/0")
            self._debug['minute']['start'] = self._io.pos()
            self.minute = self._io.read_bits_int_le(6)
            self._debug['minute']['end'] = self._io.pos()
            if not self.minute <= 59:
                raise kaitaistruct.ValidationGreaterThanError(59, self.minute, self._io, u"/types/time/seq/1")
            self._debug['hour']['start'] = self._io.pos()
            self.hour = self._io.read_bits_int_le(5)
            self._debug['hour']['end'] = self._io.pos()
            if not self.hour <= 23:
                raise kaitaistruct.ValidationGreaterThanError(23, self.hour, self._io, u"/types/time/seq/2")

        @property
        def second(self):
            if hasattr(self, '_m_second'):
                return self._m_second if hasattr(self, '_m_second') else None

            self._m_second = (2 * self.second_div_2)
            return self._m_second if hasattr(self, '_m_second') else None

        @property
        def padded_second(self):
            if hasattr(self, '_m_padded_second'):
                return self._m_padded_second if hasattr(self, '_m_padded_second') else None

            self._m_padded_second = (u"0" if self.second <= 9 else u"") + str(self.second)
            return self._m_padded_second if hasattr(self, '_m_padded_second') else None

        @property
        def padded_minute(self):
            if hasattr(self, '_m_padded_minute'):
                return self._m_padded_minute if hasattr(self, '_m_padded_minute') else None

            self._m_padded_minute = (u"0" if self.minute <= 9 else u"") + str(self.minute)
            return self._m_padded_minute if hasattr(self, '_m_padded_minute') else None

        @property
        def padded_hour(self):
            if hasattr(self, '_m_padded_hour'):
                return self._m_padded_hour if hasattr(self, '_m_padded_hour') else None

            self._m_padded_hour = (u"0" if self.hour <= 9 else u"") + str(self.hour)
            return self._m_padded_hour if hasattr(self, '_m_padded_hour') else None


    class Date(KaitaiStruct):
        SEQ_FIELDS = ["day", "month", "year_minus_1980"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['day']['start'] = self._io.pos()
            self.day = self._io.read_bits_int_le(5)
            self._debug['day']['end'] = self._io.pos()
            if not self.day >= 1:
                raise kaitaistruct.ValidationLessThanError(1, self.day, self._io, u"/types/date/seq/0")
            self._debug['month']['start'] = self._io.pos()
            self.month = self._io.read_bits_int_le(4)
            self._debug['month']['end'] = self._io.pos()
            if not self.month >= 1:
                raise kaitaistruct.ValidationLessThanError(1, self.month, self._io, u"/types/date/seq/1")
            if not self.month <= 12:
                raise kaitaistruct.ValidationGreaterThanError(12, self.month, self._io, u"/types/date/seq/1")
            self._debug['year_minus_1980']['start'] = self._io.pos()
            self.year_minus_1980 = self._io.read_bits_int_le(7)
            self._debug['year_minus_1980']['end'] = self._io.pos()

        @property
        def year(self):
            """only years from 1980 to 2107 (1980 + 127) can be represented."""
            if hasattr(self, '_m_year'):
                return self._m_year if hasattr(self, '_m_year') else None

            self._m_year = (1980 + self.year_minus_1980)
            return self._m_year if hasattr(self, '_m_year') else None

        @property
        def padded_day(self):
            if hasattr(self, '_m_padded_day'):
                return self._m_padded_day if hasattr(self, '_m_padded_day') else None

            self._m_padded_day = (u"0" if self.day <= 9 else u"") + str(self.day)
            return self._m_padded_day if hasattr(self, '_m_padded_day') else None

        @property
        def padded_month(self):
            if hasattr(self, '_m_padded_month'):
                return self._m_padded_month if hasattr(self, '_m_padded_month') else None

            self._m_padded_month = (u"0" if self.month <= 9 else u"") + str(self.month)
            return self._m_padded_month if hasattr(self, '_m_padded_month') else None

        @property
        def padded_year(self):
            if hasattr(self, '_m_padded_year'):
                return self._m_padded_year if hasattr(self, '_m_padded_year') else None

            self._m_padded_year = (u"0" + (u"0" + (u"0" if self.year <= 9 else u"") if self.year <= 99 else u"") if self.year <= 999 else u"") + str(self.year)
            return self._m_padded_year if hasattr(self, '_m_padded_year') else None



