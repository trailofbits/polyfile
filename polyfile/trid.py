from collections import defaultdict
import glob
import os
from xml.etree import ElementTree

from . import logger
from .fileutils import make_stream, FileStream
from .search import MultiSequenceSearch

log = logger.getStatusLogger("TRiD")

TRID_DEFS_URL = 'http://mark0.net/download/triddefs_xml.7z'

DEF_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), "defs")

DEFS = None

# These are the file formats that don't have to start at byte offset zero of the file:
CAN_BE_OFFSET = {'adobe_pdf', 'zip'}


class TRiDDef:
    def __init__(self, name, filetype, ext, mime, patterns, strings=()):
        self.name = name
        self.filetype = filetype
        self.ext = ext
        self.mime = mime
        self.patterns = patterns
        self.strings = strings
        self.can_be_offset = False
        for cbo in CAN_BE_OFFSET:
            if self.name.startswith(cbo):
                self.can_be_offset = True
                break

    @staticmethod
    def load(xml_path):
        xml = ElementTree.parse(xml_path).getroot()
        filetype = xml.findtext("Info/FileType").strip()
        ext = xml.findtext("Info/Ext", default="").split("/")
        mime = xml.findtext("Info/Mime", default="").strip()
        patterns = []
        for pattern in xml.findall("FrontBlock/Pattern"):
            for data in pattern:
                ppos = 0
                if data.tag == "Pos":
                    ppos = int(data.text)
                elif data.tag == "Bytes":
                    if len(data.text) % 2:
                        data.text = '0' + data.text
                    pbytes = bytes.fromhex(data.text)
            patterns.append((ppos, pbytes))
        if xml.findtext("General/CheckStrings", default="False").strip() == "True":
            strings = tuple(string.text.replace("'", "\x00").encode('utf-8') for string in xml.findall("GlobalStrings/String"))
        else:
            strings = ()
        return TRiDDef(os.path.split(xml_path)[-1], filetype, ext, mime, patterns, strings)

    def match(self, file_stream, try_all_offsets=False):
        with make_stream(file_stream) as fs:
            if try_all_offsets and self.can_be_offset:
                offset_range = range(len(fs))
            else:
                offset_range = (0,)
            for global_offset in offset_range:
                for offset, pattern in self.patterns:
                    if global_offset + offset >= len(fs):
                        break
                    fs.seek(global_offset + offset)
                    if fs.read(len(pattern)) != pattern:
                        break
                else:
                    if FileStream(fs, start=global_offset).contains_all(*self.strings):
                        yield global_offset

    def __repr__(self):
        return f"{self.__class__.__name__}(name={self.name!r}, filetype={self.filetype!r}, ext={self.ext!r}, mime={self.mime!r}, patterns={self.patterns!r}, strings={self.strings!r})"


class Matcher:
    def __init__(self):
        load()
        self.patterns = defaultdict(set)
        log.status("Building multi-string search data structures...")
        for tdef in DEFS:
            if tdef.can_be_offset:
                if not tdef.patterns:
                    log.clear_status()
                    raise ValueError("TRiDDefs must have at least one pattern for multi-sequence matching")
                for pos, seq in tdef.patterns:
                    self.patterns[seq].add((pos, tdef))
                for string in tdef.strings:
                    self.patterns[string].add((None, tdef))
        self.search = MultiSequenceSearch(*self.patterns.keys())
        log.clear_status()

    def match(self, file_stream):
        with make_stream(file_stream) as fs:
            found_strings = defaultdict(set)
            partial_tdefs = set()
            yielded = defaultdict(set)
            for offset, source in self.search.search(fs):
                log.debug(f"Found byte sequence {source!r} at offset {offset} potentially matching "
                          f"{''.join(set(tdef.filetype for _, tdef in self.patterns[source]))}")
                found_strings[source].add(offset)
                # see if this constitutes the potential start of a tdef
                for expected_offset, tdef in self.patterns[source]:
                    if expected_offset is None or expected_offset <= offset:
                        partial_tdefs.add(tdef)
                # see if this completes any partial tdefs
                for tdef in partial_tdefs:
                    first_pattern_offset, first_pattern_seq = tdef.patterns[0]
                    for match_pos in found_strings[first_pattern_seq]:
                        if match_pos in yielded[tdef]:
                            # We already found this match
                            continue
                        if first_pattern_offset > match_pos:
                            continue
                        potential_start = match_pos - first_pattern_offset
                        for pos, seq in tdef.patterns[1:]:
                            if pos + potential_start not in found_strings[seq]:
                                # We haven't found this other required pattern yet
                                break
                        else:
                            # Check that all of the strings have been found
                            if all(
                                any(
                                    pos >= potential_start for pos in found_strings[string]
                                ) for string in tdef.strings
                            ):
                                yield potential_start, tdef
                                yielded[tdef].add(potential_start)


def download_defs():
    import subprocess
    import urllib.request
    log.status('Downloading TRiD file definitions...')
    trid_defs_zip = os.path.join(os.path.dirname(os.path.realpath(__file__)), "triddefs_xml.7z")
    urllib.request.urlretrieve(TRID_DEFS_URL, trid_defs_zip)
    log.status('Extracting TRiD file definitions...')
    subprocess.check_call(['7za', 'x', trid_defs_zip], cwd=os.path.dirname(os.path.realpath(__file__)))
    log.clear_status()


def download_defs_if_necessary():
    if not os.path.exists(DEF_DIR):
        download_defs()


def load():
    global DEFS
    if DEFS is not None:
        return

    download_defs_if_necessary()

    log.status('Loading TRiD file definitions...')

    DEFS = []

    for xml_path in glob.glob(os.path.join(DEF_DIR, '**', '*.xml')):
        DEFS.append(TRiDDef.load(xml_path))
        log.status(f'Loading TRiD file definitions... {DEFS[-1].name}')

    log.clear_status()
