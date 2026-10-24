"""Minah Tekstil - Trendyol toplu ürün şablonunu düzeltip yüklemeye hazır hale getirir.

Kullanım:  python3 duzelt.py urunler.json
Kaynak dosyada bütün ürünler tek bir kategori sayfasına girilmişti. Betik her ürünü urunler.json'daki
kategori sayfasına taşır ve ürün bazında şunları yapar:
- Kategori kodunu sayfanın koduna eşitler.
- Barkodu sade bir biçime çevirir: MNH-MODEL-RENK-BEDEN, yalnızca A-Z, 0-9 ve tire.
- Stok Kodu sütununa barkodu yazar.
- Ürün adını tek satıra indirir.
- İlk bedenin görsellerini diğer bedenlere kopyalar.
- Zorunlu özellikleri, şablondaki izinli değerlere göre kontrol eder.
İndirilen şablonda olmayan kategoriler için "yeni_kategoriler" sayfası açılır: Trendyol'un sayfa düzeninde,
temel sütunlar + bilinen bütün kategorilerde ortak olan özellikler + "ek" ile verilenler. Bu sayfalarda bir
değer ancak bilinen bütün kategorilerin listesinde varsa kabul edilir.
Trendyol bir dosyada en fazla 8 sayfa kabul ettiği için çıktı "dosyalar" listesine göre bölünür; her dosyada
yalnızca o dosyanın kategori sayfaları kalır.
"""
import io
import json
import re
import sys
from copy import copy
from pathlib import Path

import openpyxl

HERE = Path(__file__).resolve().parent
TR = str.maketrans("ÇĞİIÖŞÜçğıiöşü", "CGIIOSUCGIIOSU")
SIZES = {"STANDART": "Standart", "XXL": "2XL"}
BASE_REQUIRED = ["Barkod", "Model Kodu", "Marka", "Kategori", "Para Birimi", "Ürün Adı", "Ürün Açıklaması",
                 "Piyasa Satış Fiyatı (KDV Dahil)", "Trendyol'da Satılacak Fiyat (KDV Dahil)", "Ürün Stok Adedi",
                 "KDV Oranı", "Görsel 1"]
BASE_COLUMNS = 24  # Barkod ... Sevkiyat Süresi; the category's attributes follow
# mandatory in every category of the downloaded template
COMMON_REQUIRED = ["Beden", "Renk", "Web Color", "Yaş Grubu", "Cinsiyet", "Menşei", "Kumaş Tipi", "Boy"]


def one_line(v):
    return " ".join(str(v).split())


def size(v):
    s = one_line(v).upper()
    return SIZES.get(s, s)


def code(text):
    return re.sub(r"[^A-Z0-9]+", "-", text.translate(TR).upper()).strip("-")


def sheet_for(wb, kategori):
    return next(wb[n] for n in wb.sheetnames if n.endswith(f"({kategori})"))


def category_sheets(wb):
    return [wb[n] for n in wb.sheetnames if re.search(r"\(\d+\)$", n)]


def add_category_sheet(wb, kategori, spec):
    """A sheet for a category the downloaded template lacks, laid out and styled like Trendyol's own."""
    known = category_sheets(wb)
    tpl = known[0]
    headers = [[c.value for c in ws[1]] for ws in known]
    common = [h for h in headers[0][BASE_COLUMNS:] if all(h in hs for hs in headers) and h != "Beden"]
    attrs = ["Beden"] + common + spec.get("ek", [])
    required = set(COMMON_REQUIRED + spec.get("ek", []))
    tpl_attrs = tpl[1][BASE_COLUMNS:]
    styles = {
        "Beden": next(c for c in tpl_attrs if c.value == "Beden"),
        True: next(c for c in tpl_attrs if c.font.b and c.value != "Beden"),
        False: next(c for c in tpl_attrs if not c.font.b),
    }
    ws = wb.create_sheet(f"{spec['ad']}({kategori})", index=wb.sheetnames.index("Menşei Ülke Kısaltmaları"))
    for j, h in enumerate(headers[0][:BASE_COLUMNS] + attrs, start=1):
        src = tpl[1][j - 1] if j <= BASE_COLUMNS else styles["Beden" if h == "Beden" else h in required]
        c = ws.cell(row=1, column=j, value=h)
        c._style = copy(src._style)
        ws.column_dimensions[c.column_letter].width = tpl.column_dimensions[src.column_letter].width or 20
    return ws


def allowed_values(wb, kategori):
    name = f"Urun_Ozellik_Bilgileri_{kategori}"
    if name not in wb.sheetnames:
        # a category we added has no list: accept only values that every known category allows
        lists = [allowed_values(wb, n.rsplit("_", 1)[1]) for n in wb.sheetnames
                 if n.startswith("Urun_Ozellik_Bilgileri_")]
        return {h: set.intersection(*[l[h] for l in lists if h in l]) for h in set().union(*lists)}
    at = wb[name]
    cols = [c.value for c in at[1]]
    vals = {h: set() for h in cols}
    for row in at.iter_rows(min_row=2, values_only=True):
        for h, v in zip(cols, row):
            if v is not None:
                vals[h].add(str(v))
    return vals


def required_attributes(ws):
    """Bold headers on the green/blue attribute columns are the category's mandatory attributes."""
    return [c.value for c in ws[1] if c.font.b and c.fill.fgColor.rgb in ("FFB1CE95", "FFA1C2E2")]


def build_rows(src_hdr, src_rows, item, tgt_hdr):
    first, last = item["satirlar"]
    rows = [src_rows[n] for n in range(first, last + 1)]
    pick = {h: i for i, h in reversed(list(enumerate(src_hdr)))}  # first column wins on duplicate headers
    with_img = next(r for r in rows if r[pick["Görsel 1"]])
    images = {f"Görsel {k}": with_img[pick[f"Görsel {k}"]] for k in range(1, 9)}
    out = []
    for r in rows:
        beden = size(r[pick["Beden"]])
        barkod = "-".join([item["model"], item["renk_kodu"], "STD" if beden == "Standart" else code(beden)])
        fixed = {
            "Barkod": barkod, "Stok Kodu": barkod, "Model Kodu": item["model"], "Kategori": item["kategori"],
            "Ürün Adı": item.get("ad") or one_line(r[pick["Ürün Adı"]]), "Ürün Açıklaması": item["aciklama"],
            "Beden": beden, "Renk": item["renk"], "Web Color": item["web_color"], **images, **item.get("ozellik", {}),
        }
        row = []
        for h in tgt_hdr:
            if h in fixed:
                v = fixed[h]
            elif h in pick:
                v = r[pick[h]]
                v = one_line(v) if isinstance(v, str) else v
            else:
                v = None
            row.append(v if v != "" else None)
        out.append(row)
    return out


def check(wb, kategori, ws, rows):
    hdr = [c.value for c in ws[1]]
    allowed = allowed_values(wb, kategori)
    problems = []
    for row in rows:
        rec = dict(zip(hdr, row))
        for h in BASE_REQUIRED + required_attributes(ws):
            if rec.get(h) in (None, ""):
                problems.append(f"{rec['Barkod']}: '{h}' boş")
        for h, v in rec.items():
            if v is not None and allowed.get(h) and str(v) not in allowed[h]:
                problems.append(f"{rec['Barkod']}: '{h}' = {v!r} şablondaki listede yok")
        if not re.fullmatch(r"[A-Z0-9-]{1,40}", rec["Barkod"]):
            problems.append(f"{rec['Barkod']}: barkod biçimi")
        if len(rec["Ürün Adı"]) > 100 or "\n" in rec["Ürün Adı"]:
            problems.append(f"{rec['Barkod']}: ürün adı")
    return problems


def main():
    cfg_path = Path(sys.argv[1]).resolve()
    with open(cfg_path, encoding="utf-8") as fh:
        cfg = json.load(fh)
    base = cfg_path.parent
    wb = openpyxl.load_workbook(base / cfg["kaynak"])
    src = wb[cfg["kaynak_sayfa"]]
    src_hdr = [c.value for c in src[1]]
    src_rows = {n: [c.value for c in row] for n, row in enumerate(src.iter_rows(min_row=1), start=1)}

    # the template's 11th column is "Stok Kodu"; it had been renamed to a second "Ürün Stok Adedi"
    src.cell(row=1, column=11, value="Stok Kodu")
    for kategori, spec in cfg.get("yeni_kategoriler", {}).items():
        add_category_sheet(wb, kategori, spec)

    by_sheet = {}
    for item in cfg["urunler"]:
        ws = sheet_for(wb, item["kategori"])
        tgt_hdr = [c.value for c in ws[1]]
        by_sheet.setdefault(ws.title, (item["kategori"], ws, []))[2].extend(
            build_rows(src_hdr, src_rows, item, tgt_hdr))

    problems, barcodes = [], []
    for title, (kategori, ws, rows) in by_sheet.items():
        problems += check(wb, kategori, ws, rows)
        barcodes += [r[0] for r in rows]
    dup = {b for b in barcodes if barcodes.count(b) > 1}
    problems += [f"{b}: barkod tekrar ediyor" for b in sorted(dup)]
    if problems:
        print("\n".join(problems))
        sys.exit("Düzeltilmesi gereken alanlar var, dosya kaydedilmedi.")

    # write: clear every product row of the sheets that receive products (the stray '"' row included);
    # image links were stored as hyperlinks too, which would bring the old URL back on save
    for title, (kategori, ws, rows) in by_sheet.items():
        for row in ws.iter_rows(min_row=2, max_row=max(ws.max_row, 2)):
            for c in row:
                c.value = None
                c.hyperlink = None
        for i, values in enumerate(rows, start=2):
            for j, v in enumerate(values, start=1):
                ws.cell(row=i, column=j, value=v)
        print(f"{title}: {len(rows)} satır")
    if src.title not in by_sheet:  # products moved away entirely: leave the sheet as downloaded
        for row in src.iter_rows(min_row=2, max_row=src.max_row):
            for c in row:
                c.value = None
                c.hyperlink = None
        src.cell(row=2, column=4, value=src.title.split("(")[1].rstrip(")"))
        src.cell(row=2, column=5, value="TRY")

    # Trendyol takes at most 8 sheets per upload: each file keeps only its own category sheets
    # (the attribute lists, country codes and help sheets are reference only)
    full = io.BytesIO()
    wb.save(full)
    for spec in cfg["dosyalar"]:
        part = openpyxl.load_workbook(io.BytesIO(full.getvalue()))
        keep = [sheet_for(part, k).title for k in spec["kategoriler"]]
        for name in part.sheetnames:
            if name not in keep:
                del part[name]
        part.active = 0
        out = base / spec["cikti"]
        part.save(out)
        n = sum(len(by_sheet[t][2]) for t in keep)
        print("kaydedildi:", out, f"({len(keep)} sayfa, {n} ürün satırı)")


if __name__ == "__main__":
    main()
