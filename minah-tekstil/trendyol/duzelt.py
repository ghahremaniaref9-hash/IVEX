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
Trendyol bir dosyada en fazla 8 kategori kabul ettiği için çıktı "dosyalar" listesine göre bölünür. Her dosya,
"sablon" ile verilen (verilmezse kaynak) Trendyol şablonunun kendisidir (paket.py): sütunlar, zorunlu alanlar ve
izinli değerler doğrudan şablondan gelir, dosyada kullanılmayan kategoriler çıkarılır.
"""
import json
import re
import sys
from pathlib import Path

import openpyxl

import paket

HERE = Path(__file__).resolve().parent
TR = str.maketrans("ÇĞİIÖŞÜçğıiöşü", "CGIIOSUCGIIOSU")
SIZES = {"STANDART": "Standart", "XXL": "2XL"}
BASE_REQUIRED = ["Barkod", "Model Kodu", "Marka", "Kategori", "Para Birimi", "Ürün Adı", "Ürün Açıklaması",
                 "Piyasa Satış Fiyatı (KDV Dahil)", "Trendyol'da Satılacak Fiyat (KDV Dahil)", "Ürün Stok Adedi",
                 "KDV Oranı", "Görsel 1"]


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


def allowed_values(wb, kategori):
    at = wb[f"Urun_Ozellik_Bilgileri_{kategori}"]
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

    # each category is read from the template of the file it goes into
    templates = {cfg["kaynak"]: wb}
    template_of = {}
    for spec in cfg["dosyalar"]:
        name = spec.get("sablon", cfg["kaynak"])
        if name not in templates:
            templates[name] = openpyxl.load_workbook(base / name)
        template_of.update(dict.fromkeys(spec["kategoriler"], name))

    if cfg.get("marka"):  # must be written exactly as the brand is defined on Trendyol
        for item in cfg["urunler"]:
            item["ozellik"] = {**item.get("ozellik", {}), "Marka": cfg["marka"]}
    by_category = {}
    for item in cfg["urunler"]:
        ws = sheet_for(templates[template_of[item["kategori"]]], item["kategori"])
        tgt_hdr = [c.value for c in ws[1]]
        by_category.setdefault(item["kategori"], (ws, []))[1].extend(build_rows(src_hdr, src_rows, item, tgt_hdr))

    problems, barcodes = [], []
    for kategori, (ws, rows) in by_category.items():
        problems += check(templates[template_of[kategori]], kategori, ws, rows)
        barcodes += [r[0] for r in rows]
    dup = {b for b in barcodes if barcodes.count(b) > 1}
    problems += [f"{b}: barkod tekrar ediyor" for b in sorted(dup)]
    if problems:
        print("\n".join(problems))
        sys.exit("Düzeltilmesi gereken alanlar var, dosya kaydedilmedi.")

    # Trendyol takes at most 8 categories per upload. Each file is its template package itself, with the
    # categories it does not use (and their attribute lists) taken out.
    for spec in cfg["dosyalar"]:
        name = spec.get("sablon", cfg["kaynak"])
        pkg = paket.Package(base / name)
        # style ids index the package's own styles.xml; only the source template has product-row styles
        data_styles = paket.row_styles(pkg, src.title) if name == cfg["kaynak"] else {}
        for ws in category_sheets(templates[name]):
            kategori = ws.title.rsplit("(", 1)[1][:-1]
            if kategori not in spec["kategoriler"]:
                pkg.remove_sheet(ws.title)
                pkg.remove_sheet(f"Urun_Ozellik_Bilgileri_{kategori}")
        for kategori in spec["kategoriler"]:
            ws, rows = by_category[kategori]
            styles = paket.header_styles(pkg, ws.title)
            if ws is src:
                styles["K"] = paket.BASE_OPTIONAL
            pkg.fill_sheet(ws.title, [c.value for c in ws[1]], styles, rows, data_styles)
            print(f"{ws.title}: {len(rows)} satır")
        out = base / spec["cikti"]
        pkg.save(out)
        n = sum(len(by_category[k][1]) for k in spec["kategoriler"])
        print("kaydedildi:", out, f"({len(spec['kategoriler'])} kategori, {n} ürün satırı)")

if __name__ == "__main__":
    main()
