"""Versa Aura - üretim organizasyonu belgesi (A4 PDF).

Kullanım:  python3 plan.py [veri.json]
veri.json'daki roller, iş akışı ve koleksiyon adetlerinden bir HTML belge kurar, Chromium ile A4 PDF'e basar ve
her sayfanın PNG önizlemesini `sayfalar/` klasörüne kaydeder. Toplamlar, beden dağılımları ve takip çizelgesi
veriden hesaplanır; her desenin beden toplamı desen adediyle tutmazsa betik durur.
Sayfalar: kapak, organizasyon şeması, iş akışı, bikini & mayo, pareo, şal, üretim özeti, takip çizelgesi.
"""
import html
import json
import math
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
FONTS = os.path.join(REPO, "ivex-icerik", "uretim", "fonts")

NAVY, AQUA, SAND, SHELL, CORAL, GOLD = "#2B2A22", "#8A7A4A", "#E8DCCB", "#FBF8F3", "#B5704A", "#5E7C7A"
LOGO = os.path.join(REPO, "versa-aura", "marka", "versa-aura-logo.png")
SAL = "#C4A35A"  # shawl collection
LANES = [("creative", "Creative Direction", NAVY), ("stilist1", "Stilist 1 · Bikini & Mayo", AQUA),
         ("stilist2", "Stilist 2 · Pareo & Şal", CORAL), ("koordinator", "Üretim Koordinatörü", GOLD)]


def e(text):
    return html.escape(str(text))


def tr_upper(text):
    return str(text).replace("i", "İ").replace("ı", "I").upper()


def num(n):
    return f"{n:,}".replace(",", ".")


CSS = """
@font-face{font-family:M;font-weight:300;src:url(FONTS/Montserrat_300Light.ttf)}
@font-face{font-family:M;font-weight:400;src:url(FONTS/Montserrat_500Medium.ttf)}
@font-face{font-family:M;font-weight:500;src:url(FONTS/Montserrat_500Medium.ttf)}
@font-face{font-family:M;font-weight:600;src:url(FONTS/Montserrat_600SemiBold.ttf)}
@font-face{font-family:M;font-weight:700;src:url(FONTS/Montserrat_700Bold.ttf)}
@font-face{font-family:M;font-weight:800;src:url(FONTS/Montserrat_800ExtraBold.ttf)}
@page{size:A4;margin:0}
*{box-sizing:border-box}
body{margin:0;font-family:M,sans-serif;color:#2A2820;-webkit-print-color-adjust:exact;print-color-adjust:exact}
.page{width:210mm;height:297mm;position:relative;overflow:hidden;background:#FBF8F3;padding:24mm 18mm 20mm;
  break-after:page}
.page:last-child{break-after:auto}
.top{position:absolute;top:10mm;left:18mm;right:18mm;display:flex;justify-content:space-between;
  font-size:7pt;letter-spacing:.3em;font-weight:600;color:#9A9482}
.top{align-items:center;top:7mm}
.top img{height:12mm;display:block}
.foot{position:absolute;bottom:9mm;left:18mm;right:18mm;display:flex;justify-content:space-between;
  font-size:7pt;color:#9A9482;border-top:1px solid #E3DACD;padding-top:3mm;letter-spacing:.04em}
.eyebrow{font-size:7.5pt;letter-spacing:.32em;color:#8A7A4A;font-weight:700;margin:0 0 2.5mm}
h1{font-size:23pt;line-height:1.12;margin:0 0 3.5mm;color:#2B2A22;font-weight:800}
h2{font-size:11pt;margin:0 0 3mm;color:#2B2A22;font-weight:700}
p.lead{font-size:9.5pt;line-height:1.6;color:#6B665A;max-width:150mm;margin:0 0 7mm}
.small{font-size:7.5pt;color:#9A9482;line-height:1.5}

/* cover */
.cover{background:#2B2A22;color:#fff;padding:0}
.cover .inner{position:absolute;left:20mm;right:20mm;top:46mm}
.cover .logo{width:74mm;display:block;margin:0 0 0 -2mm}
.cover .rule{width:34mm;height:2px;background:#C4C07D;margin:10mm 0 8mm}
.cover .title{font-size:25pt;font-weight:800;letter-spacing:.02em;margin:0}
.cover .sub{font-size:11pt;font-weight:500;color:#D3CDB4;margin:3mm 0 0;letter-spacing:.06em}
.cover .waves{position:absolute;left:0;right:0;bottom:66mm}
.cover .figs{position:absolute;left:20mm;right:20mm;bottom:26mm;display:grid;grid-template-columns:repeat(4,1fr);
  gap:6mm;border-top:1px solid rgba(232,220,203,.25);padding-top:7mm}
.cover .fig b{display:block;font-size:20pt;font-weight:800;color:#fff}
.cover .fig span{font-size:7.5pt;letter-spacing:.14em;color:#D3CDB4;font-weight:600}
.cover .by{position:absolute;left:20mm;right:20mm;bottom:12mm;display:flex;justify-content:space-between;
  font-size:7.5pt;letter-spacing:.2em;color:#AFA88E;font-weight:600}

/* org chart */
.org{width:174mm;margin:2mm auto 0}
.node{background:#fff;border:1px solid #E3DACD;border-radius:14px;padding:10px 14px 11px;text-align:center;
  box-shadow:0 8px 22px rgba(43,42,34,.07)}
.node .role{font-size:7pt;letter-spacing:.26em;font-weight:700}
.node h3{margin:4px 0 9px;font-size:12pt;color:#2B2A22;font-weight:700}
.node.navy{background:#2B2A22;border:none}
.node.navy h3{color:#fff}
.chips{display:flex;flex-wrap:wrap;gap:5px;justify-content:center}
.chip{font-size:7.8pt;padding:4px 10px;border-radius:999px;background:#F1E9DD;color:#2B2A22;font-weight:600}
.node.navy .chip{background:rgba(232,220,203,.16);color:#E8DCCB}
.pair{display:grid;grid-template-columns:1fr 1fr;gap:24px}
.mid{width:62%;margin:0 auto}
.conn{display:block}
.roles{display:grid;grid-template-columns:repeat(4,1fr);gap:4.5mm;margin-top:6mm}
.roles div{border-top:3px solid var(--c);padding-top:3mm}
.roles b{display:block;font-size:8pt;color:#2B2A22;margin-bottom:1.5mm}
.roles p{margin:0;font-size:7.4pt;line-height:1.5;color:#6B665A}

/* swimlane */
.lanes{display:grid;grid-template-columns:9mm repeat(4,1fr);column-gap:2.5mm;row-gap:2mm}
.lh{font-size:7pt;font-weight:700;letter-spacing:.06em;color:#fff;padding:3mm 2.5mm;border-radius:8px;text-align:center;
  line-height:1.3}
.phase{grid-column:1/-1;font-size:7pt;letter-spacing:.3em;font-weight:700;color:#9A9482;margin-top:3mm;
  display:flex;align-items:center;gap:3mm}
.phase:after{content:"";flex:1;height:1px;background:#E3DACD}
.no{width:7mm;height:7mm;border-radius:50%;background:#2B2A22;color:#fff;font-size:7.5pt;font-weight:700;display:flex;
  align-items:center;justify-content:center;align-self:center}
.cell{min-height:13mm;border-radius:9px;background:rgba(43,42,34,.025);display:flex;align-items:center;padding:0 2mm}
.step{width:100%;background:#fff;border:1px solid #E3DACD;border-left:4px solid var(--c);border-radius:8px;
  padding:2.6mm 2.6mm;font-size:8.3pt;font-weight:600;color:#2B2A22;display:flex;justify-content:space-between;
  align-items:center;gap:2mm;box-shadow:0 3px 10px rgba(43,42,34,.05)}
.ok{font-size:6.2pt;letter-spacing:.12em;font-weight:700;color:#fff;background:var(--c);border-radius:999px;
  padding:1.2mm 2mm;white-space:nowrap}
.legend{display:flex;gap:6mm;margin-top:7mm;font-size:7.5pt;color:#6B665A;align-items:center}
.legend .ok{background:#2B2A22}

/* collections */
.kpis{display:grid;grid-template-columns:repeat(3,1fr);gap:5mm;margin-bottom:7mm}
.kpi{background:#fff;border:1px solid #E3DACD;border-radius:12px;padding:5mm}
.kpi b{display:block;font-size:22pt;font-weight:800;color:#2B2A22;line-height:1}
.kpi span{display:block;margin-top:2mm;font-size:7.5pt;letter-spacing:.12em;font-weight:600;color:#9A9482}
.kpi.dark{background:#2B2A22;border:none}
.kpi.dark b{color:#fff}
.kpi.dark span{color:#D3CDB4}
.two{display:grid;grid-template-columns:1fr 1fr;gap:6mm}
.card{background:#fff;border:1px solid #E3DACD;border-radius:12px;padding:5mm}
.card .t{font-size:7pt;letter-spacing:.24em;font-weight:700;color:var(--c)}
.card h3{margin:1.5mm 0 1mm;font-size:13pt;color:#2B2A22}
.card .f{font-size:8.5pt;color:#6B665A;margin-bottom:3mm}
.bars{display:flex;flex-direction:column;gap:2.2mm}
.bar{display:grid;grid-template-columns:9mm 1fr 18mm;align-items:center;gap:2.5mm;font-size:8pt}
.bar .k{font-weight:700;color:#2B2A22}
.bar .track{height:4.2mm;background:#F1E9DD;border-radius:99px;overflow:hidden}
.bar .fill{height:100%;background:var(--c);border-radius:99px}
.bar .v{text-align:right;font-weight:600;color:#2B2A22}
.bar .v i{font-style:normal;color:#9A9482;font-weight:500;margin-left:1mm}
table.t{width:100%;border-collapse:separate;border-spacing:0;font-size:8.5pt;background:#fff;border:1px solid #E3DACD;
  border-radius:12px;overflow:hidden}
table.t th{background:#2B2A22;color:#fff;font-weight:600;font-size:7.5pt;letter-spacing:.08em;padding:2.6mm 3mm;
  text-align:right}
table.t th:first-child,table.t td:first-child{text-align:left}
table.t td{padding:2.6mm 3mm;border-top:1px solid #EFE7DB;text-align:right;color:#2B2A22}
table.t tr.sum td{background:#F6F0E6;font-weight:800}
.grid10{display:grid;grid-template-columns:repeat(5,1fr);gap:2.6mm}
.sw{border-radius:9px;overflow:hidden;background:#fff;border:1px solid #E3DACD}
.sw .pat{height:12mm}
.sw .lab{padding:1.6mm 2.2mm;display:flex;justify-content:space-between;font-size:7pt;font-weight:700;color:#2B2A22}
.sw .lab i{font-style:normal;color:#9A9482;font-weight:600}
.note{margin-top:4mm;font-size:7.5pt;color:#9A9482}
.strip{display:grid;grid-template-columns:repeat(10,1fr);gap:1.8mm}
.strip .sw .pat{height:9mm}
.strip .sw .lab{justify-content:center;font-size:6.2pt;padding:1.3mm 0}
.pat.plain{display:flex;align-items:flex-end;justify-content:flex-end;padding:1mm 1.4mm}
.pat.plain span{font-size:5.2pt;font-weight:700;letter-spacing:.14em;color:rgba(255,255,255,.85)}
.pat.plain.light span{color:rgba(43,42,34,.6)}
.keys{display:flex;gap:5mm;font-size:7pt;color:#6B665A;margin:1.5mm 0 2.5mm;align-items:center}
.keys i{display:inline-block;width:3mm;height:3mm;border-radius:1px;margin-right:1.5mm;vertical-align:-.4mm}
.strip7{display:grid;grid-template-columns:repeat(7,1fr);gap:2.4mm}
.load{margin-top:9mm;background:#2B2A22;border-radius:14px;padding:6mm 7mm;display:flex;justify-content:space-between;
  align-items:center;color:#fff}
.load span{display:block;font-size:6.8pt;letter-spacing:.22em;font-weight:700;color:#C4C07D}
.load b{font-size:13pt}
.sum3{display:flex;align-items:center;gap:5mm}
.sum3 div{text-align:center}
.sum3 b{display:block;font-size:19pt;font-weight:800}
.sum3 span{color:#D3CDB4;letter-spacing:.1em}
.sum3 i{font-style:normal;font-size:15pt;color:#C4C07D}
.strip7 .sw .pat{height:16mm}
.strip7 .sw .lab{flex-direction:column;align-items:center;font-size:7pt;gap:.6mm;padding:1.8mm 0}
.strip7 .sw .pat{height:26mm}
.models{display:flex;flex-direction:column;gap:2.4mm}
.models div{display:flex;justify-content:space-between;align-items:baseline;border-bottom:1px solid #EFE7DB;padding-bottom:2.6mm}
.models b{font-size:10.5pt;color:#2B2A22}
.models span{font-size:8.5pt;color:#6B665A}
.models span strong{color:#2B2A22}
table.resp{width:100%;border-collapse:separate;border-spacing:0;font-size:7.6pt;background:#fff;border:1px solid #E3DACD;
  border-radius:12px;overflow:hidden}
table.resp th{background:#2B2A22;color:#fff;font-weight:600;font-size:6.8pt;letter-spacing:.06em;padding:2mm 2mm;text-align:center}
table.resp th:first-child{text-align:left;padding-left:3mm}
table.resp td{border-top:1px solid #EFE7DB;padding:0.95mm 2mm;text-align:center}
table.resp td:first-child{text-align:left;padding-left:3mm;font-weight:600;color:#2B2A22}
table.resp .dot{display:inline-block;width:2.6mm;height:2.6mm;border-radius:50%}

/* summary */
.big{display:grid;grid-template-columns:62mm 1fr;gap:8mm;align-items:center;margin-bottom:8mm}
.donut{position:relative;width:62mm;height:62mm}
.donut .c{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center}
.donut .c b{font-size:24pt;font-weight:800;color:#2B2A22;line-height:1}
.donut .c span{font-size:7pt;letter-spacing:.18em;font-weight:700;color:#9A9482;margin-top:1.5mm}
.split > .key{display:flex;align-items:center;gap:3mm;margin:0 0 4mm}
.split i{width:4mm;height:4mm;border-radius:2px;display:inline-block}
.split b{font-size:15pt;color:#2B2A22;font-weight:800}
.split span{font-size:8.5pt;color:#6B665A}
.stack{display:flex;height:100%;border-radius:99px;overflow:hidden}
.mini{display:grid;grid-template-columns:repeat(4,1fr);gap:4mm;margin-top:7mm}
.mini div{background:#fff;border:1px solid #E3DACD;border-radius:12px;padding:4mm}
.mini b{display:block;font-size:16pt;font-weight:800;color:#2B2A22}
.mini span{font-size:7.2pt;color:#9A9482;font-weight:600;letter-spacing:.06em}

/* tracking */
table.track{width:100%;border-collapse:collapse;font-size:6.6pt;table-layout:fixed}
table.track th{background:#2B2A22;color:#fff;font-weight:600;padding:2mm 1mm;font-size:6.4pt;line-height:1.25;
  text-align:center;border:1px solid #2B2A22}
table.track th.l{text-align:left;padding-left:2mm}
table.track td{border:1px solid #E3DACD;height:4.75mm;text-align:center;color:#2B2A22;background:#fff}
table.track td.l{text-align:left;padding-left:2mm;font-weight:600}
table.track td.m{color:#6B665A;text-align:left;padding-left:2mm}
table.track tr.g td{background:#F6F0E6;font-weight:700;letter-spacing:.18em;font-size:6.4pt;color:#9A9482;
  text-align:left;padding-left:2mm;height:4.3mm}
.box{display:inline-block;width:3mm;height:3mm;border:1px solid #D3CDB4;border-radius:1px}
"""


def page(section, body, number, total, cls=""):
    top = (f'<div class="top"><img src="file://{LOGO}" alt="Versa Aura"><span>{e(section)}</span></div>'
           if section else "")
    foot = (f'<div class="foot"><span>Versa Aura · Üretim Organizasyonu</span><span>{number:02d} / {total:02d}</span>'
            f'</div>') if section else ""
    return f'<section class="page {cls}">{top}{body}{foot}</section>'


def waves():
    paths = []
    for i in range(7):
        amp, y0, ph = 9 + i * 1.6, 40 + i * 13, i * 0.7
        pts = [f"{x:.1f},{y0 + amp * math.sin(x / 95 + ph) + 4 * math.sin(x / 37 + ph * 2):.1f}"
               for x in range(0, 801, 10)]
        col = "#C4C07D" if i % 2 == 0 else "#8A7A4A"
        op = 0.55 - i * 0.06
        paths.append(f'<polyline points="{" ".join(pts)}" fill="none" stroke="{col}" stroke-width="1.4" '
                     f'stroke-opacity="{op:.2f}"/>')
    return f'<svg class="waves" viewBox="0 0 800 140" width="100%" height="140">{"".join(paths)}</svg>'


def cover(d, t):
    figs = [(num(t["toplam"]), "TOPLAM ADET"), ("3", "KOLEKSİYON"), (str(t["tasarim"]), "TASARIM / MODEL"),
            ("2", "FABRİKA")]
    fig_html = "".join(f'<div class="fig"><b>{a}</b><span>{b}</span></div>' for a, b in figs)
    body = (f'<div class="inner"><img class="logo" src="file://{LOGO}" alt="{e(d["marka"])}"><div class="rule"></div>'
            f'<p class="title">{e(d["baslik"])}</p><p class="sub">{e(d["alt_baslik"])}</p></div>'
            f'{waves()}<div class="figs">{fig_html}</div>'
            f'<div class="by"><span>HAZIRLAYAN · {e(tr_upper(d["hazirlayan"]))}</span><span>{e(tr_upper(d["tarih"]))}</span>'
            f'</div>')
    return page("", body, 1, 1, "cover")


def node(r, color, cls=""):
    chips = "".join(f'<span class="chip">{e(g)}</span>' for g in r["gorevler"])
    return (f'<div class="node {cls}"><div class="role" style="color:{color}">{e(r["etiket"])}</div>'
            f'<h3>{e(r["ad"])}</h3><div class="chips">{chips}</div></div>')


def connector(down):
    """Lines between one centred box and the two boxes of a pair (650 px wide, 24 px gap)."""
    w, h, gap = 658, 34, 24
    c1, c2 = (w - gap) / 4, (w - gap) / 4 * 3 + gap
    mid = h / 2
    if down:  # one -> two
        dpath = f"M{w / 2} 0 V{mid} M{c1} {mid} H{c2} M{c1} {mid} V{h} M{c2} {mid} V{h}"
    else:  # two -> one
        dpath = f"M{c1} 0 V{mid} M{c2} 0 V{mid} M{c1} {mid} H{c2} M{w / 2} {mid} V{h}"
    dot = f'<circle cx="{w / 2}" cy="{mid}" r="3.2" fill="{NAVY}"/>'
    return (f'<svg class="conn" viewBox="0 0 {w} {h}" width="100%" height="{h}"><path d="{dpath}" fill="none" '
            f'stroke="{NAVY}" stroke-width="1.4" stroke-opacity=".55"/>{dot}</svg>')


def org_page(d, n, total):
    r = d["roller"]
    roles = "".join(f'<div style="--c:{c}"><b>{e(name)}</b><p>{e(r[k]["aciklama"])}</p></div>'
                    for k, name, c in LANES)
    tasks = []
    for phase in d["akis"]:
        for s in phase["adimlar"]:
            if s.get("creative"):
                tasks.append((s["creative"], {"creative"}))
            if s.get("stilist"):
                tasks.append((s["stilist"], {"stilist1", "stilist2"}))
            if s.get("koordinator"):
                tasks.append((s["koordinator"], {"koordinator"}))
    head = "<tr><th>Görev</th>" + "".join(f"<th>{e(name)}</th>" for _, name, _ in LANES) + "</tr>"
    body_rows = "".join(
        f'<tr><td>{e(task)}</td>' + "".join(
            f'<td>{f"<span class=dot style=background:{c}></span>" if key in who else ""}</td>' for key, _, c in LANES)
        + "</tr>" for task, who in tasks)
    matrix = (f'<h2 style="margin-top:5mm">Sorumluluk tablosu</h2><table class="resp">{head}{body_rows}</table>')
    body = (f'<p class="eyebrow">01 · ORGANİZASYON YAPISI</p><h1>Kim, neyden sorumlu?</h1>'
            f'<p class="lead">Koleksiyon tek bir yaratıcı yönden çıkar, iki uzman fabrikada üretilir ve tek bir '
            f'koordinatör üzerinden kontrol edilip teslim edilir. Her aşamanın sahibi bellidir.</p>'
            f'<div class="org"><div class="mid">{node(r["creative"], AQUA, "navy")}</div>{connector(True)}'
            f'<div class="pair">{node(r["stilist1"], AQUA)}{node(r["stilist2"], CORAL)}</div>{connector(False)}'
            f'<div class="mid">{node(r["koordinator"], GOLD)}</div></div>'
            f'<div class="roles">{roles}</div>{matrix}')
    return page("ORGANİZASYON YAPISI", body, n, total)


def flow_page(d, n, total):
    head = '<div></div>' + "".join(f'<div class="lh" style="background:{c}">{e(name)}</div>' for _, name, c in LANES)
    rows = []
    for phase in d["akis"]:
        rows.append(f'<div class="phase">{e(phase["faz"])}</div>')
        for s in phase["adimlar"]:
            cells = [f'<div class="no">{s["no"]}</div>']
            for key, _, color in LANES:
                text = s.get(key) or (s.get("stilist") if key.startswith("stilist") else None)
                if text:
                    gate = ""
                    if s.get("onay") and (key in ("creative", "koordinator") and s.get(key)):
                        gate = '<span class="ok">ONAY</span>'
                    cells.append(f'<div class="cell"><div class="step" style="--c:{color}"><span>{e(text)}</span>'
                                 f'{gate}</div></div>')
                else:
                    cells.append('<div class="cell"></div>')
            rows.append("".join(cells))
    legend = ('<div class="legend"><span class="ok" style="--c:#2B2A22">ONAY</span><span>Bir sonraki adıma '
              'geçmeden önce onay verilmesi gereken nokta</span></div>')
    body = (f'<p class="eyebrow">02 · İŞ AKIŞI</p><h1>Tasarımdan sevkiyata 9 adım</h1>'
            f'<p class="lead">İki fabrika aynı adımları paralel yürütür. Üretim koordinatörü kumaş, numune ve kalite '
            f'aşamalarında devreye girer; sevkiyatı tek elden yönetir.</p>'
            f'<div class="lanes">{head}{"".join(rows)}</div>{legend}')
    return page("İŞ AKIŞI", body, n, total)


def bars(beden, color):
    total = sum(beden.values())
    peak = max(beden.values())
    out = []
    for k, v in beden.items():
        out.append(f'<div class="bar"><span class="k">{k}</span><div class="track"><div class="fill" '
                   f'style="width:{v / peak * 100:.1f}%;background:{color}"></div></div>'
                   f'<span class="v">{v}<i>%{round(v / total * 100)}</i></span></div>')
    return f'<div class="bars">{"".join(out)}</div>'


def swatch(i, color, code, qty, kind):
    """A placeholder pattern tile; the real artwork replaces it once designs are approved."""
    a = (i * 37) % 180
    styles = [
        f"repeating-linear-gradient({a}deg,{color} 0 3px,#fff 3px 9px)",
        f"radial-gradient(circle at 30% 40%,{color} 0 18%,transparent 19%),radial-gradient(circle at 75% 70%,"
        f"{color}99 0 14%,transparent 15%),#F7F1E8",
        f"repeating-linear-gradient(90deg,{color} 0 6px,#F7F1E8 6px 12px)",
        f"linear-gradient({a}deg,{color},{color}55)",
        f"repeating-linear-gradient(45deg,{color}aa 0 2px,transparent 2px 7px),repeating-linear-gradient(-45deg,"
        f"{color}66 0 2px,#fff 2px 7px)",
    ]
    return (f'<div class="sw"><div class="pat" style="background:{styles[i % 5]}"></div>'
            f'<div class="lab"><span>{code}</span><i>{qty} {kind}</i></div></div>')


def solid(color, code):
    return (f'<div class="sw"><div class="pat plain" style="background:{color}"><span>DÜZ</span></div>'
            f'<div class="lab"><span>{code}</span></div></div>')


def bikini_page(d, t, n, total):
    b = d["bikini"]
    size = b["beden"]
    rows = []
    sums = {k: 0 for k in size}
    for m in b["modeller"]:
        line = "".join(f"<td>{num(v * m['desen'])}</td>" for v in size.values())
        rows.append(f'<tr><td>{e(m["ad"])}</td>{line}<td><b>{num(m["desen"] * m["adet"])}</b></td></tr>')
        for k, v in size.items():
            sums[k] += v * m["desen"]
    sum_row = "".join(f"<td>{num(v)}</td>" for v in sums.values())
    table = (f'<table class="t"><tr><th>Model</th>{"".join(f"<th>{k}</th>" for k in size)}<th>Toplam</th></tr>'
             f'{"".join(rows)}<tr class="sum"><td>Toplam</td>{sum_row}<td>{num(t["bikini"])}</td></tr></table>')
    per = sum(size.values())
    dist = (f'<div class="card" style="--c:{AQUA}"><div class="t">BEDEN DAĞILIMI</div><h3>Her tasarımda</h3>'
            f'<div class="f">{per} {b["birim"]}, dört bedene dağılır.</div>{bars(size, AQUA)}</div>')
    lines = "".join(
        f'<div><b>{e(m["ad"])}</b><span>{m["desenli"]} desenli · {m["duz"]} düz · '
        f'<strong>{num(m["desen"] * m["adet"])} {b["birim"]}</strong></span></div>' for m in b["modeller"])
    patterned = sum(m["desenli"] * m["adet"] for m in b["modeller"])
    plain = sum(m["duz"] * m["adet"] for m in b["modeller"])
    models = (f'<div class="card" style="--c:{NAVY}"><div class="t">MODELLER</div><h3>2 takım modeli</h3>'
              f'<div class="f">Her modelde 10 tasarım: 7 desenli, 3 düz renk.</div>'
              f'<div class="models">{lines}<div><b>Desenli</b><span><strong>{num(patterned)} {b["birim"]}</strong>'
              f'</span></div><div style="border:none"><b>Düz renk</b><span><strong>{num(plain)} {b["birim"]}</strong>'
              f'</span></div></div></div>')
    plains = {"IP": [("#8A7A4A", ""), ("#C4C07D", "light"), ("#E8DCCB", "light")],
              "BY": [("#2B2A22", ""), ("#6B665A", ""), ("#D3CDB4", "light")]}
    grid = ""
    for m, c in zip(b["modeller"], (AQUA, NAVY)):
        tiles = "".join(swatch(i, c, f"VA-{m['kod']}-{i + 1:02d}", "", "").replace("<i> </i>", "")
                        for i in range(m["desenli"]))
        for k in range(m["duz"]):
            col, tone = plains.get(m["kod"], [(c, "")] * m["duz"])[k % 3]
            tiles += solid(col, f"VA-{m['kod']}-{m['desenli'] + k + 1:02d}").replace('class="pat plain"',
                                                                                    f'class="pat plain {tone}"')
        grid += (f'<h2 style="margin-top:4mm">{e(m["ad"])} <span class="small">· {m["desenli"]} desenli, '
                 f'{m["duz"]} düz renk · her tasarımdan {m["adet"]} {b["birim"]}</span></h2>'
                 f'<div class="strip">{tiles}</div>')
    keys = (f'<div class="keys"><span><i style="background:repeating-linear-gradient(45deg,{AQUA} 0 2px,#fff 2px 4px)">'
            f'</i>Desenli</span><span><i style="background:{AQUA}"></i>Düz renk</span></div>')
    total_designs = sum(m["desen"] for m in b["modeller"])
    kpis = (f'<div class="kpis"><div class="kpi"><b>{len(b["modeller"])}</b><span>TAKIM MODELİ</span></div>'
            f'<div class="kpi"><b>{total_designs}</b><span>TASARIM · {sum(m["desenli"] for m in b["modeller"])} DESENLİ, '
            f'{sum(m["duz"] for m in b["modeller"])} DÜZ</span></div>'
            f'<div class="kpi dark"><b>{num(t["bikini"])}</b><span>TOPLAM {tr_upper(b["birim"])}</span></div></div>')
    sizes = ", ".join(f"{k}&nbsp;{v}" for k, v in size.items())
    body = (f'<p class="eyebrow">03 · KOLEKSİYON</p><h1>{e(b["ad"])}</h1>'
            f'<p class="lead">İki takım modeli, her modelde 10 tasarım: 7\'si desenli, 3\'ü düz renk. Her tasarımdan '
            f'50 takım üretilir; beden dağılımı hepsinde aynıdır: {sizes}.</p>{kpis}<div class="two">{dist}{models}</div>'
            f'<h2 style="margin-top:5mm">Beden bazında üretim adedi</h2>{table}{grid}{keys}'
            f'<p class="note" style="margin-top:1mm">Kodlar öneridir; desen ve renk görselleri tasarım onayından sonra '
            f'eklenir.</p>')
    return page("BİKİNİ & MAYO", body, n, total)


def pareo_page(d, t, n, total):
    p = d["pareo"]
    size = p["beden"]
    sums = {k: v * p["model"] for k, v in size.items()}
    table = (f'<table class="t"><tr><th>Koleksiyon</th>{"".join(f"<th>{k}</th>" for k in size)}<th>Toplam</th></tr>'
             f'<tr><td>Model başına</td>{"".join(f"<td>{v}</td>" for v in size.values())}<td><b>{p["adet"]}</b></td></tr>'
             f'<tr class="sum"><td>{p["model"]} model toplam</td>{"".join(f"<td>{num(v)}</td>" for v in sums.values())}'
             f'<td>{num(t["pareo"])}</td></tr></table>')
    tiles = "".join(swatch(i + 2, CORAL, f"VA-{p['kod']}-{i + 1:02d}", p["adet"], p["birim"]) for i in range(p["model"]))
    kpis = (f'<div class="kpis"><div class="kpi"><b>{p["model"]}</b><span>FARKLI MODEL</span></div>'
            f'<div class="kpi"><b>{p["adet"]}</b><span>MODEL BAŞINA ADET</span></div>'
            f'<div class="kpi dark"><b>{num(t["pareo"])}</b><span>TOPLAM ADET</span></div></div>')
    card = (f'<div class="card" style="--c:{CORAL}"><div class="t">BEDEN DAĞILIMI</div><h3>Her modelde</h3>'
            f'<div class="f">{p["adet"]} adet, beş bedene dağılır.</div>{bars(size, CORAL)}</div>')
    side = (f'<div class="card" style="--c:{CORAL}"><div class="t">ÖZET</div><h3>10 model, 10 desen</h3>'
            f'<div class="f" style="line-height:1.65">Her model kendine özgü desenle üretilir. Pareo ve şal fabrikası '
            f'özel kalıp, kumaş ve astar seçimini yapar; numune onayından sonra üretime geçilir.</div>'
            f'<div class="f" style="margin:0">En çok üretilen bedenler <b>S ve M</b> (model başına 7\'şer adet).</div>'
            f'</div>')
    body = (f'<p class="eyebrow">04 · KOLEKSİYON</p><h1>{e(p["ad"])}</h1>'
            f'<p class="lead">On farklı model, her biri farklı desende. Her modelden 25 adet üretilir; beden dağılımı '
            f'{", ".join(f"{k}&nbsp;{v}" for k, v in size.items())}.</p>{kpis}<div class="two">{card}{side}</div>'
            f'<h2 style="margin-top:7mm">Beden bazında üretim adedi</h2>{table}'
            f'<h2 style="margin-top:6mm">Modeller</h2><div class="grid10">{tiles}</div>'
            f'<p class="note">Model kodları öneridir. {e(p["not"])}</p>')
    return page("PAREO", body, n, total)


def sal_page(d, t, n, total):
    s_ = d["sal"]
    w, h = s_["olcu"]
    # the shawl drawn to scale (180 x 60) with dimension lines
    W, H, pad = 420, 140, 28
    sw, sh = W - 2 * pad, (W - 2 * pad) * h / w
    svg = (f'<svg viewBox="0 0 {W} {H + 40}" width="100%">'
           f'<defs><pattern id="p" width="14" height="14" patternUnits="userSpaceOnUse" patternTransform="rotate(35)">'
           f'<rect width="14" height="14" fill="#F4EDDC"/><rect width="5" height="14" fill="{SAL}" opacity=".55"/>'
           f'</pattern></defs>'
           f'<rect x="{pad}" y="12" width="{sw}" height="{sh}" rx="4" fill="url(#p)" stroke="{SAL}" stroke-width="1.5"/>'
           + "".join(f'<line x1="{pad + sw * k / 24:.1f}" y1="{12 + sh}" x2="{pad + sw * k / 24:.1f}" y2="{20 + sh}" '
                     f'stroke="{SAL}" stroke-width="1.2"/>' for k in range(25)) +
           f'<line x1="{pad}" y1="{sh + 34}" x2="{pad + sw}" y2="{sh + 34}" stroke="#2B2A22" stroke-width="1"/>'
           f'<line x1="{pad}" y1="{sh + 28}" x2="{pad}" y2="{sh + 40}" stroke="#2B2A22"/>'
           f'<line x1="{pad + sw}" y1="{sh + 28}" x2="{pad + sw}" y2="{sh + 40}" stroke="#2B2A22"/>'
           f'<rect x="{pad + sw / 2 - 30}" y="{sh + 26}" width="60" height="16" fill="#fff"/>'
           f'<text x="{pad + sw / 2}" y="{sh + 38}" text-anchor="middle" font-family="M" font-weight="700" '
           f'font-size="11" fill="#2B2A22">{w} cm</text>'
           f'<line x1="{pad - 14}" y1="12" x2="{pad - 14}" y2="{12 + sh}" stroke="#2B2A22" stroke-width="1"/>'
           f'<line x1="{pad - 20}" y1="12" x2="{pad - 8}" y2="12" stroke="#2B2A22"/>'
           f'<line x1="{pad - 20}" y1="{12 + sh}" x2="{pad - 8}" y2="{12 + sh}" stroke="#2B2A22"/>'
           f'<text x="{pad - 18}" y="{12 + sh / 2}" text-anchor="middle" font-family="M" font-weight="700" font-size="11" '
           f'fill="#2B2A22" transform="rotate(-90 {pad - 18} {12 + sh / 2})">{h} cm</text></svg>')
    size_card = (f'<div class="card" style="--c:{SAL}"><div class="t">ÖLÇÜ</div><h3>{w} × {h} cm</h3>'
                 f'<div class="f">Tüm şallar tek ölçüde üretilir, beden yoktur.</div>{svg}</div>')
    info = (f'<div class="card" style="--c:{SAL}"><div class="t">ÜRETİM</div><h3>{s_["desen"]} desenli kumaş</h3>'
            f'<div class="models"><div><b>Desen sayısı</b><span><strong>{s_["desen"]}</strong></span></div>'
            f'<div><b>Desen başına</b><span><strong>{s_["adet"]} {s_["birim"]}</strong></span></div>'
            f'<div><b>Ölçü</b><span><strong>{w} × {h} cm</strong></span></div>'
            f'<div style="border:none"><b>Toplam</b><span><strong>{num(t["sal"])} {s_["birim"]}</strong></span></div>'
            f'</div><div class="f" style="margin:4mm 0 0">Pareo & şal fabrikasında, Stilist 2 sorumluluğunda üretilir.'
            f'</div></div>')
    rows = "".join(f'<tr><td>VA-{s_["kod"]}-{i + 1:02d}</td><td style="text-align:left">Desenli kumaş {i + 1:02d}</td>'
                   f'<td>{w} × {h} cm</td><td><b>{s_["adet"]}</b></td></tr>' for i in range(s_["desen"]))
    table = (f'<table class="t"><tr><th>Kod</th><th style="text-align:left">Kumaş</th><th>Ölçü</th><th>Adet</th></tr>'
             f'{rows}<tr class="sum"><td>Toplam</td><td></td><td></td><td>{num(t["sal"])}</td></tr></table>')
    tiles = "".join(swatch(i + 1, SAL, f"VA-{s_['kod']}-{i + 1:02d}", s_["adet"], s_["birim"])
                    for i in range(s_["desen"]))
    kpis = (f'<div class="kpis"><div class="kpi"><b>{s_["desen"]}</b><span>DESENLİ KUMAŞ</span></div>'
            f'<div class="kpi"><b>{s_["adet"]}</b><span>DESEN BAŞINA ADET</span></div>'
            f'<div class="kpi dark"><b>{num(t["sal"])}</b><span>TOPLAM ADET</span></div></div>')
    body = (f'<p class="eyebrow">05 · KOLEKSİYON</p><h1>{e(s_["ad"])}</h1>'
            f'<p class="lead">Yedi farklı desenli kumaştan, her desenden {s_["adet"]} adet şal. Tüm şallar tek ölçüde '
            f'üretilir: {w}&nbsp;×&nbsp;{h}&nbsp;cm.</p>{kpis}<div class="two">{size_card}{info}</div>'
            f'<h2 style="margin-top:7mm">Desenler <span class="small">· her desenden {s_["adet"]} {s_["birim"]}, '
            f'{w}&nbsp;×&nbsp;{h}&nbsp;cm</span></h2><div class="strip7">{tiles}</div>'
            f'<p class="note">Kumaş kodları öneridir; desen görselleri kumaş onayından sonra eklenir.</p>'
            f'<div class="load"><div><span>STİLİST 2 · PAREO & ŞAL FABRİKASI</span><b>Toplam üretim yükü</b></div>'
            f'<div class="sum3"><div><b>{num(t["pareo"])}</b><span>pareo</span></div><i>+</i>'
            f'<div><b>{num(t["sal"])}</b><span>şal</span></div><i>=</i>'
            f'<div><b>{num(t["pareo"] + t["sal"])}</b><span>adet</span></div></div></div>')
    return page("ŞAL", body, n, total)


def donut(parts):
    total = sum(v for v, _ in parts)
    r, c = 80, 2 * math.pi * 80
    out, offset = [], 0
    for v, color in parts:
        seg = c * v / total
        out.append(f'<circle cx="110" cy="110" r="{r}" fill="none" stroke="{color}" stroke-width="30" '
                   f'stroke-dasharray="{seg:.2f} {c - seg:.2f}" stroke-dashoffset="{-offset:.2f}" '
                   f'transform="rotate(-90 110 110)"/>')
        offset += seg
    return f'<svg viewBox="0 0 220 220" width="100%" height="100%">{"".join(out)}</svg>'


def summary_page(d, t, n, total):
    b, p, s_ = d["bikini"], d["pareo"], d["sal"]
    rows_def = ["S", "M", "L", "XL", "XXL", "Tek ölçü"]
    designs = sum(m["desen"] for m in b["modeller"])
    col = {
        "bikini": {k: b["beden"].get(k, 0) * designs for k in rows_def},
        "pareo": {k: p["beden"].get(k, 0) * p["model"] for k in rows_def},
        "sal": {k: (t["sal"] if k == "Tek ölçü" else 0) for k in rows_def},
    }
    colors = {"bikini": AQUA, "pareo": CORAL, "sal": SAL}

    def cell(v):
        return num(v) if v else "–"

    rows = ""
    for k in rows_def:
        tot = sum(col[c][k] for c in col)
        label = f"Tek ölçü ({s_['olcu'][0]}×{s_['olcu'][1]} cm)" if k == "Tek ölçü" else k
        rows += (f'<tr><td>{label}</td>' + "".join(f"<td>{cell(col[c][k])}</td>" for c in col) +
                 f'<td><b>{num(tot)}</b></td><td>%{round(tot / t["toplam"] * 100)}</td></tr>')
    table = (f'<table class="t"><tr><th>Beden</th><th>Bikini & Mayo</th><th>Pareo</th><th>Şal</th><th>Toplam</th>'
             f'<th>Pay</th></tr>{rows}<tr class="sum"><td>Toplam</td><td>{num(t["bikini"])}</td><td>{num(t["pareo"])}</td>'
             f'<td>{num(t["sal"])}</td><td>{num(t["toplam"])}</td><td>%100</td></tr></table>')
    peak = max(sum(col[c][k] for c in col) for k in rows_def)
    stacks = ""
    for k in rows_def:
        tot = sum(col[c][k] for c in col)
        segs = "".join(f'<div style="width:{col[c][k] / tot * 100:.2f}%;background:{colors[c]}"></div>'
                       for c in col if col[c][k])
        stacks += (f'<div class="bar"><span class="k">{"Tek" if k == "Tek ölçü" else k}</span>'
                   f'<div class="track" style="background:transparent"><div class="stack" '
                   f'style="width:{tot / peak * 100:.1f}%">{segs}</div></div><span class="v">{num(tot)}</span></div>')
    parts = [("bikini", "bikini & mayo takımı"), ("pareo", "pareo"), ("sal", "şal")]
    keys = "".join(f'<div class="key"><i style="background:{colors[c]}"></i><b>{num(t[c])}</b>'
                   f'<span>{name} · %{round(t[c] / t["toplam"] * 100)}</span></div>' for c, name in parts)
    big = (f'<div class="big"><div class="donut">{donut([(t[c], colors[c]) for c, _ in parts])}'
           f'<div class="c"><b>{num(t["toplam"])}</b><span>TOPLAM ADET</span></div></div>'
           f'<div class="split">{keys}<div class="bars" style="margin-top:5mm;gap:2.4mm">{stacks}</div></div></div>')
    mini = (f'<div class="mini"><div><b>{t["tasarim"]}</b><span>tasarım / model</span></div>'
            f'<div><b>{t["varyant"]}</b><span>beden varyantı (stok kodu)</span></div>'
            f'<div><b>2</b><span>üretim fabrikası</span></div><div><b>1</b><span>üretim koordinatörü</span></div></div>')
    body = (f'<p class="eyebrow">06 · ÜRETİM ÖZETİ</p><h1>Toplam {num(t["toplam"])} adet</h1>'
            f'<p class="lead">Üç koleksiyonun toplam üretimi ve bedenlere dağılımı. Kumaş, astar ve aksesuar '
            f'siparişleri bu adetlere göre planlanır.</p>{big}<h2>Beden bazında toplam</h2>{table}{mini}')
    return page("ÜRETİM ÖZETİ", body, n, total)


def tracking_page(d, t, n, total):
    steps = d["takip"]
    head = ('<tr><th class="l" style="width:21mm">Kod</th><th class="l" style="width:33mm">Ürün</th>'
            '<th style="width:12mm">Adet</th>' + "".join(f"<th>{e(s)}</th>" for s in steps) + "</tr>")
    boxes = "".join('<td><span class="box"></span></td>' for _ in steps)
    span = 3 + len(steps)
    rows = []
    b = d["bikini"]
    for m in b["modeller"]:
        rows.append(f'<tr class="g"><td colspan="{span}">{e(tr_upper(m["ad"]))}</td></tr>')
        for i in range(m["desen"]):
            kind = "Desenli" if i < m["desenli"] else "Düz renk"
            rows.append(f'<tr><td class="l">VA-{m["kod"]}-{i + 1:02d}</td><td class="m">{kind}</td>'
                        f'<td>{m["adet"]}</td>{boxes}</tr>')
    p = d["pareo"]
    rows.append(f'<tr class="g"><td colspan="{span}">PAREO</td></tr>')
    for i in range(p["model"]):
        rows.append(f'<tr><td class="l">VA-{p["kod"]}-{i + 1:02d}</td><td class="m">Model {i + 1:02d}</td>'
                    f'<td>{p["adet"]}</td>{boxes}</tr>')
    s_ = d["sal"]
    rows.append(f'<tr class="g"><td colspan="{span}">ŞAL · {s_["olcu"][0]} × {s_["olcu"][1]} CM</td></tr>')
    for i in range(s_["desen"]):
        rows.append(f'<tr><td class="l">VA-{s_["kod"]}-{i + 1:02d}</td><td class="m">Desenli kumaş {i + 1:02d}</td>'
                    f'<td>{s_["adet"]}</td>{boxes}</tr>')
    body = (f'<p class="eyebrow">07 · TAKİP ÇİZELGESİ</p><h1 style="font-size:19pt">Üretim takip çizelgesi</h1>'
            f'<p class="lead" style="margin-bottom:4mm">Üretim koordinatörü her tasarım için tamamlanan adımı '
            f'işaretler. Çizelge yazdırılıp fabrikada da kullanılabilir.</p>'
            f'<table class="track">{head}{"".join(rows)}</table>')
    return page("TAKİP ÇİZELGESİ", body, n, total)


def totals(d):
    b, p, s_ = d["bikini"], d["pareo"], d["sal"]
    for m in b["modeller"]:
        if sum(b["beden"].values()) != m["adet"]:
            sys.exit(f"{m['ad']}: beden toplamı {sum(b['beden'].values())}, tasarım adedi {m['adet']}")
        if m["desenli"] + m["duz"] != m["desen"]:
            sys.exit(f"{m['ad']}: {m['desenli']} desenli + {m['duz']} düz, {m['desen']} tasarım etmiyor")
    if sum(p["beden"].values()) != p["adet"]:
        sys.exit(f"Pareo: beden toplamı {sum(p['beden'].values())}, model adedi {p['adet']}")
    bikini = sum(m["desen"] * m["adet"] for m in b["modeller"])
    pareo = p["model"] * p["adet"]
    sal = s_["desen"] * s_["adet"]
    designs = sum(m["desen"] for m in b["modeller"])
    return {"bikini": bikini, "pareo": pareo, "sal": sal, "toplam": bikini + pareo + sal,
            "tasarim": designs + p["model"] + s_["desen"],
            "varyant": designs * len(b["beden"]) + p["model"] * len(p["beden"]) + s_["desen"]}


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "veri.json")
    d = json.load(open(path, encoding="utf-8"))
    t = totals(d)
    total = 8
    pages = [cover(d, t), org_page(d, 2, total), flow_page(d, 3, total), bikini_page(d, t, 4, total),
             pareo_page(d, t, 5, total), sal_page(d, t, 6, total), summary_page(d, t, 7, total),
             tracking_page(d, t, 8, total)]
    doc = (f'<!doctype html><html lang="tr"><head><meta charset="utf-8"><title>{e(d["marka"])} · {e(d["baslik"])}'
           f'</title><style>{CSS.replace("FONTS", "file://" + FONTS)}</style></head><body>{"".join(pages)}</body></html>')
    html_path = os.path.join(HERE, "plan.html")
    open(html_path, "w", encoding="utf-8").write(doc)
    pdf = os.path.join(REPO, d["cikti"])
    subprocess.run(["node", os.path.join(HERE, "yazdir.js"), html_path, pdf, os.path.join(HERE, "sayfalar")], check=True)
    print("kaydedildi:", os.path.relpath(pdf, REPO))
    print(f"toplam {t['toplam']} adet: bikini & mayo {t['bikini']} takım, pareo {t['pareo']} adet, şal {t['sal']} adet")


if __name__ == "__main__":
    main()
