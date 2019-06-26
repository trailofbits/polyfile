from . import pdfparser


def parse_pdf(file_stream):
    with file_stream.tempfile(suffix='.pdf') as pdf_path:
        parser = pdfparser.cPDFParser(pdf_path, True)
        while True:
            object = parser.GetObject()
            if object is None:
                break
            elif object.type == pdfparser.PDF_ELEMENT_COMMENT:
                print('PDF Comment %s' % pdfparser.FormatOutput(object.comment, False))
                print('')
