from polyfile import pdf
from polyfile.fileutils import make_stream
from polyfile.pdf import PDFDictionary
from polyfile.polyfile import Matcher


class PDFInfo:
    def __init__(self, pdf_path: str):
        self.matcher = Matcher()
        self.objs: [] = None
        self.path: str = pdf_path
        self.dicts = []

        attrs_before = frozenset(self.__dict__.keys())

        # BEGIN PROPERTIES
        self.is_signed = False
        self.usf = False  # Universal Signature Forgery
        self.encrypted = False
        self.has_forms = False
        self.has_hyperlinks = False
        self.has_javascript = False
        # END PROPERTIES

        self.properties = tuple(frozenset(self.__dict__.keys()) - attrs_before) + ('might_have_encryption_exfil',)

    @property
    def might_have_encryption_exfil(self):
        return self.encrypted and (self.has_hyperlinks or self.has_forms or self.has_javascript)

    def to_obj(self):
        return {p: getattr(self, p) for p in self.properties}

    def process(self):
        if self.objs is not None:
            return
        with make_stream(self.path) as f:
            self.objs = [submatch for submatch in pdf.PDF('PDF', None, matcher=self.matcher).submatch(f)]

        for obj in self.objs:
            if isinstance(obj, PDFDictionary):
                self.dicts.append(obj)
                is_signature = False
                usf = False
                for k, v in obj.items():
                    if k.match == '/Subfilter' and v.match == 'adbe.pkcs7':
                        self.is_signed = True
                        is_signature = True
                    elif (k.match == '/Contents' or k.match == '/ByteRange') and \
                            (v.match == 'null'
                             or v.match is None
                             or v.match == 0
                             or v.match == '0'
                             or '0x0' in v.match):
                        usf = True
                    elif k.match == '/Encrypt':
                        self.encrypted = True
                    elif k.match == '/AcroForm':
                        self.has_forms = True
                    elif k.match == '/OpenAction':
                        self.has_hyperlinks = True
                    elif k.match == '/JS':
                        self.has_javascript = True

                self.usf = self.usf or (is_signature and usf)


if __name__ == '__main__':
    import json
    import sys
    info = PDFInfo(sys.argv[1])
    info.process()
    print(json.dumps(info.to_obj()))
