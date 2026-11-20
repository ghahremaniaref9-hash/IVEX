// IVEX Medya - "Nasıl çalışıyoruz?" arayüz animasyonu (EffectCraft / After Effects script modeli).
// Higgsfield ArtCraft kutusunda çalışır:  effectcraft-cli script /project/ivex-panel.jsx
// Girdi: /project/assets (logo, Montserrat fontları, img/*.jpg, audio/vo0-4.mp3)
// Çıktı: /project/ivex-panel.ecproj (katmanları düzenlenebilir proje)
// 1080x1920, 30 fps, 26,8 sn. Müzik yok; yalnızca Harrison seslendirmesi.
// Tüm metinler yerel metin katmanı, kartlar ve butonlar şekil katmanı; her ekran ayrı bir precomp.

var A = "/project/assets/";
var W = 1080, H = 1920, FPS = 30, DUR = 26.8;
var SCENES = [[0.0, 4.95], [4.95, 10.85], [10.85, 15.85], [15.85, 21.4]];
var BODY = [60, 716];          // window body origin in the main comp
var SW = 960, SH = 824;        // screen precomp size (= window body)

function rgb(r, g, b) { return [r / 255, g / 255, b / 255]; }
var C = {
    bg: rgb(5, 22, 11), win: rgb(8, 30, 14), card: rgb(10, 40, 18), field: rgb(16, 56, 27),
    line: rgb(70, 120, 60), lime: rgb(218, 255, 46), white: [1, 1, 1], soft: rgb(214, 226, 214),
    muted: rgb(150, 178, 150), ink: rgb(10, 24, 14)
};
var F = { med: "Montserrat-Medium", semi: "Montserrat-SemiBold", bold: "Montserrat-Bold",
          xb: "Montserrat-ExtraBold", black: "Montserrat-Black" };

// ------------------------------------------------------------------ helpers
function T(l) { return l.property("ADBE Transform Group"); }
function P(l) { return T(l).property("ADBE Position"); }
function O(l) { return T(l).property("ADBE Opacity"); }
function S(l) { return T(l).property("ADBE Scale"); }
function G(x, y) { return [BODY[0] + x, BODY[1] + y]; }

function easeAll(prop, inf) {
    inf = inf || 70;
    for (var i = 1; i <= prop.numKeys; i++) {
        for (var n = 1; n <= 3; n++) {
            var e = [];
            for (var d = 0; d < n; d++) e.push(new KeyframeEase(0, inf));
            try { prop.setTemporalEaseAtKey(i, e, e); break; } catch (err) {}
        }
    }
}
function keys(prop, list, inf) {
    for (var i = 0; i < list.length; i++) prop.setValueAtTime(list[i][0], list[i][1]);
    easeAll(prop, inf);
}
function linearKeys(prop, list) {
    for (var i = 0; i < list.length; i++) prop.setValueAtTime(list[i][0], list[i][1]);
}

function text(comp, name, str, font, size, color, x, y, just, tracking, leading) {
    var l = comp.layers.addText(str);
    l.name = name;
    var sp = l.property("ADBE Text Properties").property("ADBE Text Document");
    var td = sp.value;
    try { td.resetCharStyle(); } catch (e1) {}
    td.text = str;
    td.font = font; td.fontSize = size;
    td.applyFill = true; td.fillColor = color; td.applyStroke = false;
    td.justification = just === "L" ? ParagraphJustification.LEFT_JUSTIFY :
        (just === "R" ? ParagraphJustification.RIGHT_JUSTIFY : ParagraphJustification.CENTER_JUSTIFY);
    td.tracking = tracking || 0;
    try { td.allCaps = false; td.smallCaps = false; } catch (e2) {}
    if (leading) { td.autoLeading = false; td.leading = leading; }
    sp.setValue(td);
    P(l).setValue([x, y]);
    return l;
}

function shape(comp, name) { var s = comp.layers.addShape(); s.name = name; return s; }
function addRect(s, w, h, r, fill, stroke, sw, offset) {
    var g = s.property("ADBE Root Vectors Group").addProperty("ADBE Vector Group");
    var v = g.property("ADBE Vectors Group");
    var rc = v.addProperty("ADBE Vector Shape - Rect");
    rc.property("ADBE Vector Rect Size").setValue([w, h]);
    rc.property("ADBE Vector Rect Roundness").setValue(r);
    if (offset) rc.property("ADBE Vector Rect Position").setValue(offset);
    if (stroke) {
        var st = v.addProperty("ADBE Vector Graphic - Stroke");
        st.property("ADBE Vector Stroke Color").setValue(stroke);
        st.property("ADBE Vector Stroke Width").setValue(sw || 2);
    }
    if (fill) {
        var f = v.addProperty("ADBE Vector Graphic - Fill");
        f.property("ADBE Vector Fill Color").setValue(fill);
    }
    return g;
}
function rect(comp, name, w, h, r, fill, stroke, sw, x, y) {
    var s = shape(comp, name);
    addRect(s, w, h, r, fill, stroke, sw);
    P(s).setValue([x, y]);
    return s;
}
function ellipse(comp, name, d, fill, stroke, sw, x, y) {
    var s = shape(comp, name);
    var g = s.property("ADBE Root Vectors Group").addProperty("ADBE Vector Group");
    var v = g.property("ADBE Vectors Group");
    v.addProperty("ADBE Vector Shape - Ellipse").property("ADBE Vector Ellipse Size").setValue([d, d]);
    if (stroke) {
        var st = v.addProperty("ADBE Vector Graphic - Stroke");
        st.property("ADBE Vector Stroke Color").setValue(stroke);
        st.property("ADBE Vector Stroke Width").setValue(sw || 2);
    }
    if (fill) v.addProperty("ADBE Vector Graphic - Fill").property("ADBE Vector Fill Color").setValue(fill);
    P(s).setValue([x, y]);
    return s;
}
function pathLayer(comp, name, pts, closed, fill, stroke, sw, x, y) {
    var s = shape(comp, name);
    var g = s.property("ADBE Root Vectors Group").addProperty("ADBE Vector Group");
    var v = g.property("ADBE Vectors Group");
    var p = v.addProperty("ADBE Vector Shape - Group");
    var sh = new Shape(); sh.vertices = pts; sh.closed = closed;
    p.property("ADBE Vector Shape").setValue(sh);
    if (stroke) {
        var st = v.addProperty("ADBE Vector Graphic - Stroke");
        st.property("ADBE Vector Stroke Color").setValue(stroke);
        st.property("ADBE Vector Stroke Width").setValue(sw || 2);
        try { st.property("ADBE Vector Stroke Line Cap").setValue(2); st.property("ADBE Vector Stroke Line Join").setValue(2); } catch (e) {}
    }
    if (fill) v.addProperty("ADBE Vector Graphic - Fill").property("ADBE Vector Fill Color").setValue(fill);
    P(s).setValue([x, y]);
    return s;
}
function rrShape(x, y, w, h, r) {
    var k = 0.5523 * r, s = new Shape();
    s.vertices = [[x + r, y], [x + w - r, y], [x + w, y + r], [x + w, y + h - r], [x + w - r, y + h], [x + r, y + h], [x, y + h - r], [x, y + r]];
    s.inTangents = [[-k, 0], [0, 0], [0, -k], [0, 0], [k, 0], [0, 0], [0, k], [0, 0]];
    s.outTangents = [[0, 0], [k, 0], [0, 0], [0, k], [0, 0], [-k, 0], [0, 0], [0, -k]];
    s.closed = true;
    return s;
}
var FOOT = {};
function footage(path) {
    if (!FOOT[path]) FOOT[path] = app.project.importFile(new ImportOptions(File(path)));
    return FOOT[path];
}
function image(comp, name, path, w, h, r, x, y) {
    var f = footage(path);
    var l = comp.layers.add(f);
    l.name = name;
    var k = Math.max(w / f.width, h / f.height);
    S(l).setValue([k * 100, k * 100]);
    var vw = w / k, vh = h / k;
    var m = l.property("ADBE Mask Parade").addProperty("ADBE Mask Atom");
    m.property("ADBE Mask Shape").setValue(rrShape((f.width - vw) / 2, (f.height - vh) / 2, vw, vh, r / k));
    P(l).setValue([x, y]);
    return l;
}
function child(kid, parent) { kid.parent = parent; return kid; }
function fadeKids(kids, t0, t1, from, to) { for (var i = 0; i < kids.length; i++) fade(kids[i], t0, t1, from, to); }
function fade(l, t0, t1, from, to) { keys(O(l), [[t0, from], [t1, to]]); }
function pop(l, t, peak) {
    peak = peak || 108;
    keys(S(l), [[t, [0, 0]], [t + 0.18, [peak, peak]], [t + 0.3, [100, 100]]]);
}
function press(l, t) { keys(S(l), [[t, [100, 100]], [t + 0.1, [95, 95]], [t + 0.25, [100, 100]]]); }
function show(l, t, dy) {   // fade + small rise
    var p = P(l).value;
    keys(P(l), [[t, [p[0], p[1] + (dy || 18)]], [t + 0.3, p]]);
    fade(l, t, t + 0.3, 0, 100);
}
function span(l, a, b) { l.inPoint = a; l.outPoint = b; }

// ------------------------------------------------------------------ project
var proj = app.project;
var main = proj.items.addComp("IVEX_Panel_Reels", W, H, 1, DUR, FPS);

var bg = main.layers.addSolid(C.bg, "Arka plan", W, H, 1, DUR);
var glow = ellipse(main, "Arka plan ışığı", 1500, C.lime, null, 0, 820, 380);
O(glow).setValue(9);
try {
    var bl = glow.property("ADBE Effect Parade").addProperty("ADBE Gaussian Blur 2");
    bl.property(1).setValue(260);
} catch (eBlur) { O(glow).setValue(5); }

// ------------------------------------------------------------------ window frame
var win = rect(main, "Pencere", 960, 900, 36, C.win, C.line, 2, 540, 1090);
var bar = rect(main, "Pencere çizgisi", 960, 2, 0, C.line, null, 0, 540, 716);
var dots = [];
for (var d = 0; d < 3; d++) {
    var dot = ellipse(main, "Nokta " + (d + 1), 14, C.soft, null, 0, 102 + d * 26, 678);
    O(dot).setValue(45);
    dots.push(dot);
}
var winTitles = ["IVEX · Yeni proje", "IVEX · Senaryo", "IVEX · İçerik takvimi", "IVEX · Reklam paneli"];

// ------------------------------------------------------------------ screens (precomps)
function screen(name) { return proj.items.addComp(name, SW, SH, 1, DUR, FPS); }
function header(c, title, sub) {
    text(c, "Başlık", title, F.bold, 40, C.white, 48, 74, "L");
    if (sub) text(c, "Alt başlık", sub, F.med, 26, C.muted, 48, 114, "L");
}

// 1 - new project form
var s1 = screen("Ekran 1 · Yeni proje");
header(s1, "Markanı anlat", null);
text(s1, "Etiket sektör", "Sektör", F.semi, 26, C.muted, 48, 142, "L");
rect(s1, "Alan sektör", 864, 84, 18, C.field, C.line, 2, 480, 192);
var ph1 = text(s1, "Sektör boş", "Sektör seç", F.med, 30, C.muted, 76, 203, "L");
var v1 = text(s1, "Sektör değer", "Giyim mağazası", F.semi, 30, C.white, 76, 203, "L");
pathLayer(s1, "Açılır ok", [[-11, -5], [0, 6], [11, -5]], false, null, C.soft, 3, 890, 192);
fade(ph1, 1.1, 1.2, 100, 0); fade(v1, 1.1, 1.3, 0, 100);
text(s1, "Etiket hedef", "Hedef", F.semi, 26, C.muted, 48, 284, "L");
var chips = [["Satış", 140, 120], ["Bilinirlik", 210, 330], ["Mesaj", 150, 530]];
for (var c = 0; c < chips.length; c++) {
    rect(s1, "Seçenek " + chips[c][0], chips[c][1], 66, 33, C.card, C.line, 2, chips[c][2], 334);
    text(s1, "Seçenek yazı " + chips[c][0], chips[c][0], F.semi, 28, C.white, chips[c][2], 344, "C");
}
var sel = rect(s1, "Seçili Satış", 140, 66, 33, C.lime, null, 0, 120, 334);
var selT = text(s1, "Seçili Satış yazı", "Satış", F.bold, 28, C.ink, 120, 344, "C");
fade(sel, 2.0, 2.15, 0, 100); fade(selT, 2.0, 2.15, 0, 100); pop(sel, 2.0, 106);
text(s1, "Etiket müşteri", "Hedef müşteri", F.semi, 26, C.muted, 48, 426, "L");
rect(s1, "Alan müşteri", 864, 84, 18, C.field, C.line, 2, 480, 476);
text(s1, "Müşteri değer", "25–40 yaş, İstanbul", F.semi, 30, C.white, 76, 487, "L");
var cover = shape(s1, "Yazma örtüsü");
addRect(cover, 360, 62, 0, C.field, null, 0, [180, 0]);
P(cover).setValue([72, 476]);
linearKeys(P(cover), [[2.8, [72, 476]], [3.4, [430, 476]]]);
fade(cover, 3.4, 3.45, 100, 0);
var caret = rect(s1, "İmleç çizgisi", 3, 40, 0, C.lime, null, 0, 76, 476);
linearKeys(P(caret), [[2.8, [74, 476]], [3.4, [428, 476]]]);
fade(caret, 2.7, 2.75, 0, 100); fade(caret, 3.6, 3.65, 100, 0);
var btn1 = rect(s1, "Buton Gönder", 864, 96, 24, C.lime, null, 0, 480, 640);
child(text(s1, "Buton Gönder yazı", "Gönder", F.bold, 34, C.ink, 480, 652, "C"), btn1);
press(btn1, 3.85);
var toast1 = rect(s1, "Bildirim", 400, 64, 32, C.card, C.lime, 2, 480, 764);
var t1k = [child(ellipse(s1, "Bildirim işaret", 30, C.lime, null, 0, 330, 764), toast1),
           child(pathLayer(s1, "Bildirim tik", [[-7, 0], [-2, 5], [7, -5]], false, null, C.ink, 3, 330, 764), toast1),
           child(text(s1, "Bildirim yazı", "Brif alındı", F.semi, 28, C.white, 500, 774, "C"), toast1)];
show(toast1, 4.15, 24); fadeKids(t1k, 4.15, 4.45, 0, 100);

// 2 - scenario document
var s2 = screen("Ekran 2 · Senaryo");
header(s2, "Senaryo", "Kış koleksiyonu · Reels · 12 sn");
var rows2 = [["0–3 sn", "KANCA", "Soğuk bir vapur sabahı.\rElinde çay, üstünde kırmızı kazak."],
             ["3–8 sn", "HİKÂYE", "Rüzgâr, martılar ve\rsıcacık bir an."],
             ["8–12 sn", "ÇAĞRI", "“Profildeki linkten\rsipariş ver.”"]];
var mark = null;
for (var r2 = 0; r2 < rows2.length; r2++) {
    var yc = 236 + r2 * 190;
    var row = rect(s2, "Satır " + (r2 + 1), 864, 170, 22, C.card, C.line, 2, 480, yc);
    child(rect(s2, "Süre " + (r2 + 1), 128, 44, 22, null, C.lime, 2, 112, yc - 45), row);
    child(text(s2, "Süre yazı " + (r2 + 1), rows2[r2][0], F.bold, 22, C.lime, 112, yc - 37, "C"), row);
    child(text(s2, "Bölüm " + (r2 + 1), rows2[r2][1], F.xb, 22, C.soft, 196, yc - 37, "L", 150), row);
    if (r2 === 0) {
        mark = shape(s2, "Vurgu");
        addRect(mark, 400, 40, 6, C.lime, null, 0, [200, 0]);
        P(mark).setValue([66, yc + 2]);
        O(mark).setValue(32);
        keys(S(mark), [[6.2, [0, 100]], [6.8, [100, 100]]], 55);
    }
    child(text(s2, "Metin " + (r2 + 1), rows2[r2][2], F.semi, 30, C.white, 72, yc + 12, "L", 0, 40), row);
}
var hl = rect(s2, "Seçili satır çerçeve", 864, 170, 22, null, C.lime, 4, 480, 236);
fade(hl, 7.85, 8.0, 0, 100);
var badge = rect(s2, "Rozet", 236, 48, 24, C.lime, null, 0, 760, 151);
var bt = child(text(s2, "Rozet yazı", "İLK 3 SANİYE", F.xb, 22, C.ink, 760, 159, "C", 80), badge);
fade(badge, 7.95, 8.05, 0, 100); fade(bt, 7.95, 8.05, 0, 100); pop(badge, 7.95, 112);

// 3 - content calendar
var s3 = screen("Ekran 3 · Takvim");
header(s3, "İçerik takvimi", "Bu hafta");
var days = ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"];
for (var i3 = 0; i3 < 7; i3++) {
    var cx = 108 + i3 * 124;
    rect(s3, "Gün " + days[i3], 116, 250, 16, C.card, C.line, 2, cx, 285);
    text(s3, "Gün yazı " + days[i3], days[i3], F.semi, 22, C.muted, cx, 190, "C");
}
text(s3, "Hazır içerikler", "Hazır içerikler", F.semi, 26, C.muted, 48, 478, "L");
var cards3 = [["Reels", "vapur.jpg", 180, 1, 11.45, 12.2], ["Hikâye", "hikaye.jpg", 480, 3, 12.8, 13.45],
              ["Gönderi", "askida.jpg", 780, 6, 14.0, 14.65]];
var card3 = [];
for (var k3 = 0; k3 < cards3.length; k3++) {
    var cd = cards3[k3];
    var base = rect(s3, "Kart " + cd[0], 264, 300, 20, C.card, C.line, 2, cd[2], 650);
    child(image(s3, "Kart görsel " + cd[0], A + "img/" + cd[1], 240, 200, 14, cd[2], 612), base);
    child(text(s3, "Kart yazı " + cd[0], cd[0], F.bold, 28, C.white, cd[2], 758, "C"), base);
    var tx = 108 + cd[3] * 124;
    keys(P(base), [[cd[4], [cd[2], 650]], [cd[5], [tx, 290]]], 65);
    keys(S(base), [[cd[4], [100, 100]], [cd[4] + 0.12, [104, 104]], [cd[5], [40, 40]]], 65);
    card3.push(base);
}
var stat3 = rect(s3, "Durum", 300, 52, 26, C.lime, null, 0, 762, 84);
var st3 = child(text(s3, "Durum yazı", "3 içerik planlandı", F.bold, 24, C.ink, 762, 93, "C"), stat3);
fade(stat3, 14.85, 14.95, 0, 100); fade(st3, 14.85, 14.95, 0, 100); pop(stat3, 14.85, 108);

// 4 - ad panel
var s4 = screen("Ekran 4 · Reklam");
header(s4, "Reklam paneli", "Önce organik, sonra reklam");
var rows4 = [["Vapur sabahı", "Reels · 12 sn", "vapur.jpg", "Organik ilgi: Yüksek", true],
             ["Mağaza turu", "Reels · 15 sn", "butik.jpg", "Organik ilgi: Orta", false],
             ["İndirim duyurusu", "Gönderi", null, "Organik ilgi: Düşük", false]];
for (var r4 = 0; r4 < rows4.length; r4++) {
    var y4 = 214 + r4 * 150, rw = rows4[r4];
    var row4 = rect(s4, "Satır " + (r4 + 1), 864, 130, 20, C.card, C.line, 2, 480, y4);
    if (rw[2]) child(image(s4, "Görsel " + (r4 + 1), A + "img/" + rw[2], 100, 100, 14, 110, y4), row4);
    else {
        child(rect(s4, "Görsel " + (r4 + 1), 100, 100, 14, C.field, C.line, 2, 110, y4), row4);
        child(text(s4, "Görsel yazı " + (r4 + 1), "%20", F.black, 30, C.lime, 110, y4 + 11, "C"), row4);
    }
    child(text(s4, "Başlık " + (r4 + 1), rw[0], F.bold, 30, C.white, 184, y4 - 6, "L"), row4);
    child(text(s4, "Bilgi " + (r4 + 1), rw[1], F.med, 24, C.muted, 184, y4 + 30, "L"), row4);
    var tag = rect(s4, "Etiket " + (r4 + 1), 304, 52, 26, rw[4] ? C.lime : null, rw[4] ? null : C.line, 2, 736, y4);
    child(text(s4, "Etiket yazı " + (r4 + 1), rw[3], F.xb, 22, rw[4] ? C.ink : C.soft, 736, y4 + 8, "C"), tag);
}
var hl4 = rect(s4, "Seçili içerik çerçeve", 864, 130, 20, null, C.lime, 4, 480, 214);
fade(hl4, 17.05, 17.2, 0, 100);
var btn4 = rect(s4, "Buton Reklama çıkar", 864, 92, 24, C.lime, null, 0, 480, 650);
child(text(s4, "Buton Reklama çıkar yazı", "Reklama çıkar", F.bold, 34, C.ink, 480, 662, "C"), btn4);
press(btn4, 18.5);
var toast4 = rect(s4, "Bildirim", 640, 62, 31, C.card, C.lime, 2, 480, 764);
var t4k = [child(ellipse(s4, "Bildirim işaret", 30, C.lime, null, 0, 196, 764), toast4),
           child(pathLayer(s4, "Bildirim tik", [[-7, 0], [-2, 5], [7, -5]], false, null, C.ink, 3, 196, 764), toast4),
           child(text(s4, "Bildirim yazı", "Bütçe bu içeriğe yönlendirildi", F.semi, 26, C.white, 498, 773, "C"), toast4)];
show(toast4, 18.75, 24); fadeKids(t4k, 18.75, 19.05, 0, 100);

// ------------------------------------------------------------------ place screens in the window
var screens = [s1, s2, s3, s4];
for (var q = 0; q < 4; q++) {
    var L = main.layers.add(screens[q]);
    L.name = screens[q].name;
    var cxy = [BODY[0] + SW / 2, BODY[1] + SH / 2];
    var a = SCENES[q][0], b = SCENES[q][1];
    var pin = q === 0 ? [[0.25, [cxy[0], cxy[1] + 30]], [0.7, cxy]] : [[a, [cxy[0] + 90, cxy[1]]], [a + 0.4, cxy]];
    var pout = [[b - 0.3, cxy], [b, [cxy[0] - 90, cxy[1]]]];
    keys(P(L), pin.concat(pout), 70);
    keys(O(L), [[pin[0][0], 0], [pin[1][0], 100], [b - 0.3, 100], [b, 0]], 60);
    span(L, Math.max(0, a - 0.05), b + 0.05);
    var wt = text(main, "Pencere başlığı " + (q + 1), winTitles[q], F.semi, 24, C.muted, 540, 687, "C");
    keys(O(wt), [[a + (q === 0 ? 0.3 : 0.1), 0], [a + 0.4, 100], [b - 0.2, 100], [b, 0]], 60);
    span(wt, a, b + 0.05);
}
// window entrance and exit (parent first, while the window is still at 100 %, so children keep their size)
var frameParts = [win, bar].concat(dots);
for (var fp = 0; fp < frameParts.length; fp++) {
    if (frameParts[fp] !== win) frameParts[fp].parent = win;
}
keys(S(win), [[0.0, [94, 94]], [0.55, [100, 100]]], 75);
var dotOp = [45, 45, 45];
keys(O(win), [[0.0, 0], [0.45, 100], [21.2, 100], [21.6, 0]], 60);
keys(O(bar), [[0.0, 0], [0.45, 100], [21.2, 100], [21.6, 0]], 60);
for (var dd = 0; dd < dots.length; dd++) keys(O(dots[dd]), [[0.0, 0], [0.45, dotOp[dd]], [21.2, dotOp[dd]], [21.6, 0]], 60);
keys(S(win), [[21.2, [100, 100]], [21.6, [92, 92]]], 70);

// ------------------------------------------------------------------ top: logo, step pill, two-line headline
var logoF = footage(A + "logo/ivex-logo.png");
var logoL = main.layers.add(logoF);
logoL.name = "Logo";
var lk = 42 / (logoF.height - 12) * 100;
S(logoL).setValue([lk, lk]);
P(logoL).setValue([540, 300]);
keys(O(logoL), [[0.1, 0], [0.5, 100], [21.2, 100], [21.5, 0]], 60);
var heads = [["Markanı", "dinliyoruz."], ["Durduran", "senaryo yazıyoruz."], ["Planlıyor, üretiyor,", "paylaşıyoruz."],
             ["Bütçeyi", "işe yarayana veriyoruz."]];
for (var h = 0; h < 4; h++) {
    var a2 = SCENES[h][0] + (h === 0 ? 0.25 : 0.15), b2 = SCENES[h][1];
    var pill = rect(main, "Adım " + (h + 1), 190, 50, 25, C.lime, null, 0, 540, 392);
    var pt = child(text(main, "Adım yazı " + (h + 1), "ADIM " + (h + 1) + " / 4", F.xb, 22, C.ink, 540, 400, "C", 100), pill);
    var l1 = text(main, "Başlık " + (h + 1) + " a", heads[h][0], F.black, 54, C.white, 540, 484, "C");
    var l2 = text(main, "Başlık " + (h + 1) + " b", heads[h][1], F.black, 54, C.lime, 540, 548, "C");
    var parts = [pill, l1, l2];
    for (var pp = 0; pp < parts.length; pp++) {
        var at = a2 + pp * 0.07;
        var base0 = P(parts[pp]).value;
        keys(P(parts[pp]), [[at, [base0[0], base0[1] + 22]], [at + 0.35, base0]], 70);
        keys(O(parts[pp]), [[at, 0], [at + 0.3, 100], [b2 - 0.25, 100], [b2, 0]], 60);
        span(parts[pp], a2 - 0.05, b2 + 0.05);
    }
    // child text of the pill needs its own opacity
    keys(O(pt), [[a2, 0], [a2 + 0.3, 100], [b2 - 0.25, 100], [b2, 0]], 60);
    span(pt, a2 - 0.05, b2 + 0.05);
}

// ------------------------------------------------------------------ end card
var E0 = 21.75;
var endLogo = main.layers.add(logoF);
endLogo.name = "Kapanış logo";
var ek = 112 / (logoF.height - 12) * 100;
S(endLogo).setValue([ek, ek]);
P(endLogo).setValue([540, 620]);
var e1 = text(main, "Kapanış satır 1", "Önce organik,", F.black, 66, C.white, 540, 820, "C");
var e2 = text(main, "Kapanış satır 2", "sonra doğru reklam.", F.black, 66, C.lime, 540, 902, "C");
var eb = rect(main, "Kapanış buton", 640, 78, 39, C.lime, null, 0, 540, 1010);
var ebt = text(main, "Kapanış buton yazı", "DM'DEN “OPERASYON” YAZ", F.xb, 30, C.ink, 540, 1021, "C", 60);
ebt.parent = eb;
var es = text(main, "Kapanış alt yazı", "Markana özel senaryoyu birlikte kuralım.", F.med, 28, C.soft, 540, 1120, "C");
var ew = text(main, "Kapanış site", "WWW.İVEX.COM.TR", F.bold, 22, C.muted, 540, 1200, "C", 250);
var endParts = [endLogo, e1, e2, eb, ebt, es, ew];
for (var ep = 0; ep < endParts.length; ep++) {
    var t0 = E0 + ep * 0.08;
    if (endParts[ep] !== ebt) {
        var bp = P(endParts[ep]).value;
        keys(P(endParts[ep]), [[t0, [bp[0], bp[1] + 26]], [t0 + 0.4, bp]], 70);
    }
    keys(O(endParts[ep]), [[t0, 0], [t0 + 0.35, 100]], 60);
    span(endParts[ep], E0 - 0.05, DUR);
}
keys(S(eb), [[24.6, [100, 100]], [24.8, [107, 107]], [25.05, [100, 100]]], 60);

// ------------------------------------------------------------------ cursor and clicks
var CLICKS = [[1.05, G(600, 192)], [1.95, G(120, 334)], [2.7, G(560, 476)], [3.85, G(560, 640)], [7.85, G(840, 160)],
              [11.45, G(180, 650)], [12.2, G(232, 290)], [12.8, G(480, 650)], [13.45, G(480, 290)],
              [14.0, G(780, 650)], [14.65, G(852, 290)], [17.0, G(400, 214)], [18.5, G(560, 650)]];
for (var ci = 0; ci < CLICKS.length; ci++) {
    var ct = CLICKS[ci][0];
    var rip = ellipse(main, "Tık " + (ci + 1), 64, null, C.lime, 4, CLICKS[ci][1][0], CLICKS[ci][1][1]);
    keys(S(rip), [[ct, [30, 30]], [ct + 0.45, [190, 190]]], 40);
    keys(O(rip), [[ct, 90], [ct + 0.45, 0]], 40);
    span(rip, ct, ct + 0.5);
}
var cur = pathLayer(main, "İmleç", [[0, 0], [0, 46], [12, 35], [21, 54], [29, 50], [20, 32], [35, 32]], true,
                    C.white, C.ink, 3, 0, 0);
var CUR = [[0.3, G(860, 760)], [1.0, G(600, 192)], [1.9, G(120, 334)], [2.65, G(560, 476)], [3.75, G(560, 640)],
           [4.5, G(700, 760)], [5.9, G(66, 238)], [6.2, G(66, 238)], [6.8, G(470, 238)], [7.6, G(840, 160)],
           [9.0, G(700, 760)], [11.45, G(180, 650)], [12.2, G(232, 290)], [12.8, G(480, 650)], [13.45, G(480, 290)],
           [14.0, G(780, 650)], [14.65, G(852, 290)], [15.4, G(700, 430)], [16.8, G(400, 214)], [18.3, G(560, 650)],
           [19.4, G(780, 780)]];
keys(P(cur), CUR, 65);
var CS = 130;
var sk = [[0, [CS, CS]]];
for (var cc = 0; cc < CLICKS.length; cc++) {
    var tt = CLICKS[cc][0];
    sk.push([tt - 0.06, [CS, CS]]); sk.push([tt, [CS * 0.85, CS * 0.85]]); sk.push([tt + 0.12, [CS, CS]]);
}
keys(S(cur), sk, 50);
keys(O(cur), [[0.3, 0], [0.5, 100], [21.1, 100], [21.4, 0]], 60);
span(cur, 0, 21.5);

// ------------------------------------------------------------------ narration (no music)
var VO = [0.35, 5.35, 11.25, 16.25, 21.85];
for (var vi = 0; vi < VO.length; vi++) {
    var al = main.layers.add(footage(A + "audio/vo" + vi + ".mp3"));
    al.name = "Seslendirme " + (vi + 1);
    al.startTime = VO[vi];
    try { al.property("ADBE Audio Group").property("ADBE Audio Levels").setValue([-1, -1]); } catch (eLvl) {}
    try { al.moveToEnd(); } catch (eMove) {}
}

try { main.openInViewer(); } catch (eV) {}
proj.save(File("/project/ivex-panel.ecproj"));
writeLn("kaydedildi: /project/ivex-panel.ecproj, katman: " + main.numLayers);
