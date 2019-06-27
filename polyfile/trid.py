import glob
import os
from xml.etree import ElementTree

from . import logger
from .fileutils import make_stream, FileStream

log = logger.getStatusLogger("TRiD")

TRID_DEFS_URL = 'http://mark0.net/download/triddefs_xml.7z'

DEF_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), "defs")

DEFS = None

# These are the file formats that don't have to start at byte offset zero of the file:
CAN_BE_OFFSET = {'adobe_pdf', 'zip'}


class TridDef:
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
                    pbytes = bytearray.fromhex(data.text)
            patterns.append((ppos, pbytes))
        if xml.findtext("General/CheckStrings", default="False").strip() == "True":
            strings = tuple(string.text.replace("'", "\x00").encode('utf-8') for string in xml.findall("GlobalStrings/String"))
        else:
            strings = ()
        return TridDef(os.path.split(xml_path)[-1], filetype, ext, mime, patterns, strings)

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


def match(*args, **kwargs):
    load()
    for tdef in DEFS:
        for offset in tdef.match(*args, **kwargs):
            yield offset, tdef


def download_defs():
    import subprocess
    import urllib.request
    log.status('Downloading TRiD file definitions...')
    trid_defs_zip = os.path.join(os.path.dirname(os.path.realpath(__file__)), "triddefs_xml.7z")
    urllib.request.urlretrieve(TRID_DEFS_URL, trid_defs_zip)
    log.status('Extracting TRiD file definitions...')
    subprocess.check_call(['7za', 'x', trid_defs_zip], cwd=os.path.dirname(os.path.realpath(__file__)))
    log.clear_status()


def load():
    global DEFS
    if DEFS is not None:
        return

    if not os.path.exists(DEF_DIR):
        download_defs()

    log.status('Loading TRiD file definitions...')

    DEFS = []

    for xml_path in glob.glob(os.path.join(DEF_DIR, '**', '*.xml')):
        DEFS.append(TridDef.load(xml_path))
        log.status(f'Loading TRiD file definitions... {DEFS[-1].name}')

    log.clear_status()
