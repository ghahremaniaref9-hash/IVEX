"""Trendyol şablonunu XML düzeyinde yazar. Yalnızca ürün satırları değişir; indirilen dosyanın geri kalanı
olduğu gibi kalır: stiller, açılır listeler, özellik sayfaları, yardım sayfası.

openpyxl metinleri satır içi (inlineStr) yazıyor. Trendyol'un yükleme ekranı bu hücreleri boş okuyup
"Excel dosyasında kayıt edilecek satır bulunamadı" hatası veriyor. Bu yüzden burada bütün metinler, Excel'in
kendi yaptığı gibi, paylaşılan metin tablosuna (sharedStrings.xml) yazılır.
"""
import re
import zipfile
from html import unescape
from xml.sax.saxutils import escape

from openpyxl.utils import get_column_letter

MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
WS_TYPE = REL + "/worksheet"
WS_CT = "application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"
# header styles used by Trendyol's template
BEDEN, ATTR_OPTIONAL, ATTR_REQUIRED, LIST_HEADER = "40", "41", "42", "43"
BASE_REQUIRED, BASE_OPTIONAL = "36", "37"


class Package:
    def __init__(self, path):
        with zipfile.ZipFile(path) as z:
            self.names = z.namelist()
            self.parts = {n: z.read(n) for n in self.names}
        sst = self.text("xl/sharedStrings.xml")
        self.sst_head = sst[:sst.index("<si>")]
        self.si = re.findall(r"<si>.*?</si>", sst, re.S)
        self.index = {}
        for i, si in enumerate(self.si):
            m = re.fullmatch(r'<si><t(?: xml:space="preserve")?>(.*?)</t></si>', si, re.S)
            if m:
                self.index.setdefault(unescape(m.group(1)), i)

    def text(self, name):
        return self.parts[name].decode("utf-8")

    def put(self, name, text):
        if name not in self.parts:
            self.names.append(name)
        self.parts[name] = text.encode("utf-8")

    def drop(self, name):
        self.parts.pop(name, None)
        if name in self.names:
            self.names.remove(name)

    # --- workbook structure -------------------------------------------------------------------------
    def sheets(self):
        """[(name, rId, part)] in tab order."""
        rels = dict(re.findall(r'<Relationship Id="([^"]+)" Type="[^"]+/worksheet" Target="([^"]+)"',
                               self.text("xl/_rels/workbook.xml.rels")))
        return [(unescape(n), rid, "xl/" + rels[rid])
                for n, rid in re.findall(r'<sheet name="([^"]+)" sheetId="\d+" r:id="([^"]+)"/>',
                                         self.text("xl/workbook.xml"))]

    def part(self, name):
        return next(p for n, _, p in self.sheets() if n == name)

    def remove_sheet(self, name):
        _, rid, part = next(s for s in self.sheets() if s[0] == name)
        wb = re.sub(rf'<sheet name="[^"]+" sheetId="\d+" r:id="{rid}"/>', "", self.text("xl/workbook.xml"))
        self.put("xl/workbook.xml", wb)
        rels = re.sub(rf'<Relationship Id="{rid}" [^>]*/>', "", self.text("xl/_rels/workbook.xml.rels"))
        self.put("xl/_rels/workbook.xml.rels", rels)
        ct = self.text("[Content_Types].xml").replace(f'<Override PartName="/{part}" ContentType="{WS_CT}"/>', "")
        self.put("[Content_Types].xml", ct)
        self.drop(part)
        self.drop(part.replace("worksheets/", "worksheets/_rels/") + ".rels")

    def add_sheet(self, name, xml, before):
        wb = self.text("xl/workbook.xml")
        rels = self.text("xl/_rels/workbook.xml.rels")
        n = 1 + max(int(x) for x in re.findall(r"worksheets/sheet(\d+)\.xml", " ".join(self.names)))
        rid = "rId" + str(1 + max(int(x) for x in re.findall(r'Id="rId(\d+)"', rels)))
        sheet_id = 1 + max(int(x) for x in re.findall(r'sheetId="(\d+)"', wb))
        part = f"xl/worksheets/sheet{n}.xml"
        self.put(part, xml)
        _, before_rid, _ = next(s for s in self.sheets() if s[0] == before)
        anchor = re.search(rf'<sheet name="[^"]+" sheetId="\d+" r:id="{before_rid}"/>', wb).group(0)
        self.put("xl/workbook.xml", wb.replace(
            anchor, f'<sheet name="{escape(name)}" sheetId="{sheet_id}" r:id="{rid}"/>' + anchor))
        self.put("xl/_rels/workbook.xml.rels", rels.replace(
            "</Relationships>", f'<Relationship Id="{rid}" Type="{WS_TYPE}" Target="worksheets/sheet{n}.xml"/>'
                                "</Relationships>"))
        self.put("[Content_Types].xml", self.text("[Content_Types].xml").replace(
            "</Types>", f'<Override PartName="/{part}" ContentType="{WS_CT}"/></Types>'))

    # --- cells --------------------------------------------------------------------------------------
    def string(self, text):
        if text not in self.index:
            space = ' xml:space="preserve"' if text != text.strip() or "\n" in text else ""
            self.si.append(f"<si><t{space}>{escape(text)}</t></si>")
            self.index[text] = len(self.si) - 1
        return self.index[text]

    def row(self, r, values, styles):
        cells = []
        for j, v in enumerate(values, start=1):
            col = get_column_letter(j)
            s = f' s="{styles[col]}"' if styles.get(col) else ""
            if v is None or v == "":
                continue
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                cells.append(f'<c r="{col}{r}"{s}><v>{v}</v></c>')
            else:
                cells.append(f'<c r="{col}{r}"{s} t="s"><v>{self.string(str(v))}</v></c>')
        return f'<row r="{r}">{"".join(cells)}</row>'

    def sheet_data(self, header, header_styles, rows, data_styles):
        body = [self.row(1, header, header_styles)]
        body += [self.row(i, values, data_styles) for i, values in enumerate(rows, start=2)]
        return "<sheetData>" + "".join(body) + "</sheetData>"

    def fill_sheet(self, name, header, header_styles, rows, data_styles):
        """Replace a template sheet's rows, keeping its validations; drop the old image hyperlinks."""
        part = self.part(name)
        xml = self.text(part)
        xml = re.sub(r"<sheetData>.*?</sheetData>|<sheetData/>",
                     lambda _: self.sheet_data(header, header_styles, rows, data_styles), xml, count=1, flags=re.S)
        xml = re.sub(r'<dimension ref="[^"]*"/>',
                     f'<dimension ref="A1:{get_column_letter(len(header))}{len(rows) + 1}"/>', xml, count=1)
        xml = re.sub(r"<hyperlinks>.*?</hyperlinks>", "", xml, flags=re.S)
        self.put(part, xml)
        rels = part.replace("worksheets/", "worksheets/_rels/") + ".rels"
        if rels in self.parts:
            kept = [r for r in re.findall(r"<Relationship [^>]*/>", self.text(rels)) if "/hyperlink" not in r]
            if kept:
                self.put(rels, re.sub(r"<Relationship [^>]*/>", "", self.text(rels)).replace(
                    "</Relationships>", "".join(kept) + "</Relationships>"))
            else:
                self.drop(rels)

    def new_sheet(self, name, header, header_styles, rows, data_styles, cols, before):
        xml = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
               f'<worksheet xmlns="{MAIN}" xmlns:r="{REL}">'
               f'<dimension ref="A1:{get_column_letter(len(header))}{len(rows) + 1}"/>'
               '<sheetViews><sheetView workbookViewId="0"/></sheetViews><sheetFormatPr defaultRowHeight="15"/>'
               f"{cols}{self.sheet_data(header, header_styles, rows, data_styles)}"
               '<pageMargins left="0.7" right="0.7" top="0.75" bottom="0.75" header="0.3" footer="0.3"/>'
               "</worksheet>")
        self.add_sheet(name, xml, before)

    def save(self, path):
        refs = sum(len(re.findall(r't="s"', self.text(n))) for n in self.names if n.startswith("xl/worksheets/s"))
        head = re.sub(r'count="\d+" uniqueCount="\d+"', f'count="{refs}" uniqueCount="{len(self.si)}"',
                      self.sst_head)
        self.put("xl/sharedStrings.xml", head + "".join(self.si) + "</sst>")
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
            for n in self.names:
                z.writestr(n, self.parts[n])


def header_styles(pkg, name):
    """Column letter -> style id of the header row in a template sheet."""
    xml = pkg.text(pkg.part(name))
    row = re.search(r'<row r="1"[^>]*>(.*?)</row>', xml, re.S).group(1)
    return dict(re.findall(r'<c r="([A-Z]+)1" s="(\d+)"', row))


def cols_xml(pkg, name):
    m = re.search(r"<cols>.*?</cols>", pkg.text(pkg.part(name)), re.S)
    return m.group(0) if m else ""


def row_styles(pkg, name):
    """Column letter -> style id of the first product row; every image column takes Görsel 1's style."""
    xml = pkg.text(pkg.part(name))
    row = re.search(r'<row r="2"[^>]*>(.*?)</row>', xml, re.S).group(1)
    styles = dict(re.findall(r'<c r="([A-Z]+)2" s="(\d+)"', row))
    if "P" in styles:  # Görsel 1 ... Görsel 8 are P ... W
        styles.update({get_column_letter(j): styles["P"] for j in range(16, 24)})
    return styles
