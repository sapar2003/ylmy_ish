"""Goşmaça kitaphanasyz ýönekeý .docx ýazyjy: paragraflar, tablisalar (birleşdirilen öýjükler bilen),
sahypa bölüjiler, kese A4 sahypa. Diňe raspisaniýe resminamalary üçin gerek bolan zatlar bar."""
import io
import zipfile
from dataclasses import dataclass, field
from xml.sax.saxutils import escape

FONT = "Times New Roman"


@dataclass
class Run:
    text: str
    bold: bool = False
    size: float | None = None  # punkt
    underline: bool = False
    superscript: bool = False

    def xml(self, default_size: float) -> str:
        size = self.size or default_size
        props = [f'<w:rFonts w:ascii="{FONT}" w:hAnsi="{FONT}" w:cs="{FONT}"/>']
        if self.bold:
            props.append("<w:b/><w:bCs/>")
        if self.underline:
            props.append('<w:u w:val="single"/>')
        if self.superscript:
            props.append('<w:vertAlign w:val="superscript"/>')
        props.append(f'<w:sz w:val="{round(size * 2)}"/><w:szCs w:val="{round(size * 2)}"/>')
        return f'<w:r><w:rPr>{"".join(props)}</w:rPr><w:t xml:space="preserve">{escape(self.text)}</w:t></w:r>'


@dataclass
class Para:
    runs: list[Run]
    align: str | None = None  # "center", "left", "right"
    size: float = 11
    space_after: int = 0  # twip
    page_break_before: bool = False

    def xml(self) -> str:
        ppr = [f'<w:spacing w:before="0" w:after="{self.space_after}" w:line="240" w:lineRule="auto"/>']
        if self.page_break_before:
            ppr.insert(0, "<w:pageBreakBefore/>")
        if self.align:
            ppr.append(f'<w:jc w:val="{"both" if self.align == "justify" else self.align}"/>')
        runs = "".join(r.xml(self.size) for r in self.runs)
        return f'<w:p><w:pPr>{"".join(ppr)}</w:pPr>{runs}</w:p>'


def p(text: str = "", *, bold=False, size=11, align=None, after=0, **run_kw) -> Para:
    return Para([Run(text, bold=bold, size=size, **run_kw)] if text else [], align=align, size=size, space_after=after)


@dataclass
class Cell:
    paras: list[Para] = field(default_factory=list)
    span: int = 1  # gridSpan
    vmerge: str | None = None  # "restart" / "continue"
    vertical: bool = False  # tekst aşakdan ýokary
    valign: str = "center"


@dataclass
class Row:
    cells: list[Cell]
    height: int | None = None  # twip, iň az
    header: bool = False  # her sahypada gaýtalansyn


@dataclass
class Table:
    widths: list[int]  # twip
    rows: list[Row]
    borders: bool = True

    def xml(self) -> str:
        border = (
            "<w:tblBorders>"
            + "".join(f'<w:{s} w:val="single" w:sz="4" w:space="0" w:color="000000"/>'
                      for s in ("top", "left", "bottom", "right", "insideH", "insideV"))
            + "</w:tblBorders>"
            if self.borders else
            "<w:tblBorders>" + "".join(f'<w:{s} w:val="nil"/>' for s in ("top", "left", "bottom", "right",
                                                                         "insideH", "insideV")) + "</w:tblBorders>"
        )
        out = [
            f'<w:tbl><w:tblPr><w:tblW w:w="{sum(self.widths)}" w:type="dxa"/><w:jc w:val="center"/>{border}'
            '<w:tblLayout w:type="fixed"/><w:tblCellMar><w:left w:w="40" w:type="dxa"/>'
            '<w:right w:w="40" w:type="dxa"/></w:tblCellMar></w:tblPr><w:tblGrid>',
            "".join(f'<w:gridCol w:w="{w}"/>' for w in self.widths),
            "</w:tblGrid>",
        ]
        for row in self.rows:
            trpr = "<w:trPr><w:cantSplit/></w:trPr>"  # setir iki sahypa bölünmesin
            if row.height or row.header:
                trpr = "<w:trPr><w:cantSplit/>" + (
                    f'<w:trHeight w:val="{row.height}"/>' if row.height else "") + (
                    "<w:tblHeader/>" if row.header else "") + "</w:trPr>"
            out.append(f"<w:tr>{trpr}")
            col = 0
            for c in row.cells:
                width = sum(self.widths[col:col + c.span])
                col += c.span
                tcpr = [f'<w:tcW w:w="{width}" w:type="dxa"/>']
                if c.span > 1:
                    tcpr.append(f'<w:gridSpan w:val="{c.span}"/>')
                if c.vmerge:
                    tcpr.append(f'<w:vMerge w:val="{c.vmerge}"/>' if c.vmerge == "restart" else "<w:vMerge/>")
                if c.vertical:
                    tcpr.append('<w:textDirection w:val="btLr"/>')
                tcpr.append(f'<w:vAlign w:val="{c.valign}"/>')
                paras = c.paras if c.paras and c.vmerge != "continue" else [Para([])]
                out.append(f'<w:tc><w:tcPr>{"".join(tcpr)}</w:tcPr>{"".join(x.xml() for x in paras)}</w:tc>')
            out.append("</w:tr>")
        out.append("</w:tbl>")
        return "".join(out)


@dataclass
class Page:
    """Sahypa sözlügi: margins twip (ýokary, aşaky, çep, sag)."""
    margins: tuple[int, int, int, int] = (568, 1135, 709, 720)
    landscape: bool = True


def build_docx(blocks: list, page: Page = Page()) -> bytes:
    """`blocks`: Para, Table ýa-da "PAGE_BREAK" setirleri."""
    body = []
    for b in blocks:
        if b == "PAGE_BREAK":
            body.append('<w:p><w:r><w:br w:type="page"/></w:r></w:p>')
        else:
            body.append(b.xml())
    w, h = (16838, 11906) if page.landscape else (11906, 16838)
    top, bottom, left, right = page.margins
    sect = (
        f'<w:sectPr><w:pgSz w:w="{w}" w:h="{h}"{" w:orient=\"landscape\"" if page.landscape else ""}/>'
        f'<w:pgMar w:top="{top}" w:right="{right}" w:bottom="{bottom}" w:left="{left}" w:header="709" '
        'w:footer="709" w:gutter="0"/></w:sectPr>'
    )
    document = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f'<w:body>{"".join(body)}{sect}</w:body></w:document>'
    )
    styles = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f'<w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="{FONT}" w:hAnsi="{FONT}" w:cs="{FONT}" '
        f'w:eastAsia="{FONT}"/><w:sz w:val="22"/><w:szCs w:val="22"/><w:lang w:val="tk-TM"/></w:rPr></w:rPrDefault>'
        '<w:pPrDefault><w:pPr><w:spacing w:after="0" w:line="240" w:lineRule="auto"/></w:pPr></w:pPrDefault>'
        '</w:docDefaults></w:styles>'
    )
    files = {
        "[Content_Types].xml": (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/word/document.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
            '<Override PartName="/word/styles.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
            "</Types>"
        ),
        "_rels/.rels": (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/'
            'officeDocument" Target="word/document.xml"/></Relationships>'
        ),
        "word/_rels/document.xml.rels": (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/'
            'styles" Target="styles.xml"/></Relationships>'
        ),
        "word/document.xml": document,
        "word/styles.xml": styles,
    }
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name, content in files.items():
            z.writestr(name, content)
    return buf.getvalue()
