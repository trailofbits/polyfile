import base64
import codecs
from collections import defaultdict
import glob
import gzip
import json
import os
from xml.etree import ElementTree

from . import logger
from .fileutils import make_stream, FileStream
from .search import MultiSequenceSearch

log = logger.getStatusLogger("TRiD")

TRID_DEFS_URL = 'http://mark0.net/download/triddefs_xml.7z'

DEF_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), "defs")

SERIALIZED_DEFS_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), "defs.json.gz")

SERIALIZED_FULL_TRIE = os.path.join(os.path.dirname(os.path.realpath(__file__)), "trie_full.gz")
SERIALIZED_PARTIAL_TRIE = os.path.join(os.path.dirname(os.path.realpath(__file__)), "trie_partial.gz")

DEFS = None

# These are the file formats that don't have to start at byte offset zero of the file:
CAN_BE_OFFSET = {'adobe_pdf', 'zip', 'html'}


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
    def deserialize(json):
        patterns = [(ppos, base64.b64decode(pbytes)) for ppos, pbytes in json['patterns']]
        strings = tuple(base64.b64decode(s) for s in json['strings'])
        return TRiDDef(
            name=json['name'],
            filetype=json['filetype'],
            ext=json['ext'],
            mime=json['mime'],
            patterns=patterns,
            strings=strings
        )

    def serialize(self):
        return {
            'name': self.name,
            'filetype': self.filetype,
            'ext': self.ext,
            'mime': self.mime,
            'patterns': [[ppos, base64.b64encode(pbytes).decode('utf-8')] for ppos, pbytes in self.patterns],
            'strings': [base64.b64encode(s).decode('utf-8') for s in self.strings]
        }

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
    def __init__(self, try_all_offsets=False, defs=None):
        load()
        if defs is None:
            defs = DEFS
            self.custom_defs = False
        else:
            self.custom_defs = True
        self.patterns = defaultdict(set)
        self.try_all_offsets = try_all_offsets
        log.status("Building multi-string search data structures...")
        for tdef in defs:
            if not try_all_offsets and not tdef.can_be_offset:
                continue
            log.status(f"Building multi-string search data structures... {tdef.name}")
            for pos, seq in tdef.patterns:
                self.patterns[seq].add((pos, tdef))
            for string in tdef.strings:
                self.patterns[string].add((None, tdef))
        if try_all_offsets:
            trie_path = SERIALIZED_FULL_TRIE
        else:
            trie_path = SERIALIZED_PARTIAL_TRIE
        # This is currently slower than just building the Trie from scratch every time!
        #if os.path.exists(trie_path):
        #    log.status("Loading the Cached Aho-Corasick Trie...")
        #   with gzip.open(trie_path, 'rb') as f:
        #        self.search = MultiSequenceSearch.load(f)
        #else:
        log.status("Constructing the Aho-Corasick Trie...")
        self.search = MultiSequenceSearch(*self.patterns.keys())
            # Commented out the caching because it is slower than just rebuilding the Trie every time:
            #log.status("Caching the Aho-Corasick Trie...")
            #with gzip.open(trie_path, 'wb') as f:
            #    self.search.save(f)
        log.clear_status()

    def match(self, file_stream, progress_callback=None):
        with make_stream(file_stream) as fs:
            if progress_callback is not None:
                fslen = len(fs)

                def callback(stream, pos):
                    progress_callback(pos, fslen)
                fs.add_listener(callback)
            if not self.try_all_offsets:
                # See if any of the TDEFs occur at offset zero
                prev_pos = fs.tell()
                for tdef in DEFS:
                    if not tdef.can_be_offset:
                        for offset in tdef.match(fs):
                            yield offset, tdef
                fs.seek(prev_pos)
            found_strings = defaultdict(set)
            partial_tdefs = set()
            yielded = defaultdict(set)
            for offset, source in self.search.search(fs):
                log.debug(f"Found byte sequence {source!r} at offset {offset} potentially matching "
                          f"{''.join(set(tdef.filetype for _, tdef in self.patterns[source]))}")
                found_strings[source].add(offset)
                # see if this constitutes the potential start of a tdef
                for expected_offset, tdef in self.patterns[source]:
                    if expected_offset is None \
                        or (tdef.can_be_offset and expected_offset <= offset) \
                            or (not tdef.can_be_offset and expected_offset == offset):
                        partial_tdefs.add(tdef)
                # see if this completes any partial tdefs
                for tdef in partial_tdefs:
                    first_pattern_offset, first_pattern_seq = tdef.patterns[0]
                    for match_pos in found_strings[first_pattern_seq]:
                        if (tdef.can_be_offset and first_pattern_offset > match_pos)\
                                or (not tdef.can_be_offset and first_pattern_offset != match_pos):
                            continue
                        potential_start = match_pos - first_pattern_offset
                        if potential_start in yielded[tdef]:
                            # We already found this match
                            continue
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


def build_defs_cache_if_necessary():
    if not os.path.exists(SERIALIZED_DEFS_PATH):
        load()


def load():
    global DEFS
    if DEFS is not None:
        return

    if not os.path.exists(SERIALIZED_DEFS_PATH):
        download_defs_if_necessary()

        log.status('Loading TRiD file definitions...')

        DEFS = []

        for xml_path in glob.glob(os.path.join(DEF_DIR, '**', '*.xml')):
            DEFS.append(TRiDDef.load(xml_path))
            log.status(f'Loading TRiD file definitions... {DEFS[-1].name}')

        log.status('Serializing TRiD definitions...')

        with gzip.open(SERIALIZED_DEFS_PATH, 'wb') as f:
            json.dump([d.serialize() for d in DEFS], codecs.getwriter('utf-8')(f))

        log.clear_status()
    else:
        log.status('Loading cached TRiD file definitions...')
        with gzip.open(SERIALIZED_DEFS_PATH, 'rb') as f:
            DEFS = [TRiDDef.deserialize(tdef) for tdef in json.load(codecs.getreader('utf-8')(f))]
        log.clear_status()
