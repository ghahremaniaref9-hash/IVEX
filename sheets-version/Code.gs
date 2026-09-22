/**
 * IVEX Lead Finder - Google Sheets / Apps Script sürümü.
 * Python/terminal gerekmez; her şey tarayıcıda, Google Sheets içinde çalışır.
 *
 * Akış: her sektör kendi bölge listesinde taranır, adaylar Google puanına göre
 * ön elenir ("en doğru" / gerçek işletmeleri öne almak için), kalan havuzda
 * website durumu kontrol edilip önce web sitesi olmayan/pasif olanlar öne
 * alınarak sektör başına günlük en iyi N işletme seçilir. Daha önce aynı
 * sektör için gösterilmiş işletmeler bir daha önerilmez (_Görülenler sayfası).
 */

var FIELD_MASK = [
  'places.id',
  'places.displayName',
  'places.formattedAddress',
  'places.nationalPhoneNumber',
  'places.internationalPhoneNumber',
  'places.websiteUri',
  'places.googleMapsUri',
  'places.rating',
  'places.businessStatus',
  'nextPageToken'
].join(',');

var SOCIAL_DOMAINS = {
  'instagram.com': 'Instagram',
  'facebook.com': 'Facebook',
  'tiktok.com': 'TikTok',
  'twitter.com': 'Twitter/X',
  'x.com': 'Twitter/X',
  'linkedin.com': 'LinkedIn',
  'youtube.com': 'YouTube'
};

var SOCIAL_LINK_RE = /https?:\/\/(?:www\.)?(instagram\.com|facebook\.com|tiktok\.com|twitter\.com|x\.com|linkedin\.com|youtube\.com)\/[^\s"'<>)]+/gi;

var HEADERS = [
  'Tarih', 'Sektör', 'Bölge', 'Marka Adı', 'Telefon', 'Adres', 'Google Puanı',
  'Website', 'Website Durumu', "Sosyal Medya (Website'den Bulunan)",
  'Sosyal Medya Manuel Kontrol Linki', 'Google Maps Linki', 'Öncelik', 'Aranmalı mı?'
];

var SUMMARY_HEADERS = ['Tarih', 'Çalışma Türü', 'Toplam Yeni İşletme', 'Sektör Dağılımı'];
var SEEN_HEADERS = ['Anahtar', 'Sektör', 'PlaceID', 'Tarih'];
var DAILY_TRIGGER_HANDLER = 'dailyAutoRun';

function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu('IVEX Lead Finder')
    .addItem('0) Sayfaları Hazırla (İlk Kurulum)', 'setupSheets')
    .addItem('1) API Anahtarını Kaydet', 'saveApiKey')
    .addItem('2) Taramayı Şimdi Çalıştır', 'runLeadSearch')
    .addSeparator()
    .addItem('3) Otomatik Günlük Taramayı Aç', 'enableDailyAutoRun')
    .addItem('4) Otomatik Günlük Taramayı Kapat', 'disableDailyAutoRun')
    .addSeparator()
    .addItem('Örnek Veriyle Test Et (Dry Run)', 'runDryRun')
    .addToUi();
}

function setupSheets() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();

  var ayarlar = ss.getSheetByName('Ayarlar');
  var isEmpty = !ayarlar || ayarlar.getLastRow() < 2;
  if (!ayarlar) ayarlar = ss.insertSheet('Ayarlar');

  if (isEmpty) {
    ayarlar.clear();
    ayarlar.getRange('A1:D1').setValues([[
      'Sektör', 'Bölge', 'Bölge Başına Ham Tarama Limiti', 'Sektör Başına Günlük Sonuç'
    ]]);
    ayarlar.getRange('A1:D1').setFontWeight('bold');
    ayarlar.getRange('A2:B9').setValues([
      ['kuaför', 'Kadıköy, İstanbul'],
      ['kuaför', 'Üsküdar, İstanbul'],
      ['kuaför', 'Beşiktaş, İstanbul'],
      ['kuaför', 'Şişli, İstanbul'],
      ['galerici', 'Kadıköy, İstanbul'],
      ['galerici', 'Üsküdar, İstanbul'],
      ['galerici', 'Beşiktaş, İstanbul'],
      ['galerici', 'Şişli, İstanbul']
    ]);
    ayarlar.getRange('C2').setValue(20);
    ayarlar.getRange('D2').setValue(10);
    ayarlar.getRange('F1').setValue(
      'Her satır bir arama demektir. C2: her bölgede kaç ham sonuç taransın (seçim havuzunu ' +
      'büyütmek için ihtiyacınızdan biraz fazla olsun, örn. 20). D2: bu havuzdan sektör başına ' +
      'günlük olarak en iyi kaç işletme seçilip listeye eklensin (örn. 10). Aynı işletme bir ' +
      'sektör için bir daha önerilmez, her çalıştırmada gerçekten yeni işletmeler gelir.'
    );
    ayarlar.getRange('F1').setFontStyle('italic').setFontColor('#666666');
    ayarlar.setFrozenRows(1);
    ayarlar.autoResizeColumns(1, 4);
    ayarlar.autoResizeColumn(6);
  } else {
    ayarlar.getRange('A1:D1').setValues([[
      'Sektör', 'Bölge', 'Bölge Başına Ham Tarama Limiti', 'Sektör Başına Günlük Sonuç'
    ]]);
    ayarlar.getRange('A1:D1').setFontWeight('bold');
    if (!ayarlar.getRange('C2').getValue()) ayarlar.getRange('C2').setValue(20);
    if (!ayarlar.getRange('D2').getValue()) ayarlar.getRange('D2').setValue(10);
  }

  ensureSheetWithHeader('Tüm Sonuçlar', HEADERS);
  ensureSheetWithHeader('Günlük Özet', SUMMARY_HEADERS);
  ensureSheetWithHeader('_Görülenler', SEEN_HEADERS);

  SpreadsheetApp.getUi().alert(
    'Sayfalar hazır.\n\n' +
    '"Ayarlar" sayfasında sektör/bölge listenizi düzenleyin; C2 (bölge başına ham tarama limiti) ve ' +
    'D2 (sektör başına günlük sonuç) hücrelerini kontrol edin.\n\n' +
    'Sonra "1) API Anahtarını Kaydet" ve "2) Taramayı Şimdi Çalıştır" ile deneyin, ya da ' +
    '"3) Otomatik Günlük Taramayı Aç" ile her gün kendiliğinden çalışmasını sağlayın.\n\n' +
    'Mevcut verileriniz varsa dokunulmadı, sadece eksik ayarlar tamamlandı.'
  );
}

function saveApiKey() {
  var ui = SpreadsheetApp.getUi();
  var resp = ui.prompt(
    'Google Places API Anahtarı',
    'Google Cloud Console\'dan aldığınız anahtarı yapıştırın (AIza... ile başlar):',
    ui.ButtonSet.OK_CANCEL
  );
  if (resp.getSelectedButton() !== ui.Button.OK) return;
  var key = resp.getResponseText().trim();
  if (!key) {
    ui.alert('Anahtar boş olamaz.');
    return;
  }
  PropertiesService.getScriptProperties().setProperty('GOOGLE_MAPS_API_KEY', key);
  ui.alert('Anahtar kaydedildi. Artık "2) Taramayı Şimdi Çalıştır" ile devam edebilirsiniz.');
}

function getSettings() {
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName('Ayarlar');
  if (!sheet) throw new Error('"Ayarlar" sayfası bulunamadı. Önce "0) Sayfaları Hazırla" çalıştırın.');
  var data = sheet.getDataRange().getValues();
  var pairs = [];
  for (var i = 1; i < data.length; i++) {
    var sector = (data[i][0] || '').toString().trim();
    var location = (data[i][1] || '').toString().trim();
    if (sector && location) {
      pairs.push({ sector: sector, location: location });
    }
  }
  var rawLimit = Number(sheet.getRange('C2').getValue()) || 20;
  var dailyPerSector = Number(sheet.getRange('D2').getValue()) || 10;
  return { pairs: pairs, rawLimit: rawLimit, dailyPerSector: dailyPerSector };
}

function textSearch(query, apiKey, maxResults) {
  var results = [];
  var pageToken = null;

  while (results.length < maxResults) {
    var body = { textQuery: query, languageCode: 'tr' };
    if (pageToken) {
      body.pageToken = pageToken;
      Utilities.sleep(2000);
    }
    var resp = UrlFetchApp.fetch('https://places.googleapis.com/v1/places:searchText', {
      method: 'post',
      contentType: 'application/json',
      headers: {
        'X-Goog-Api-Key': apiKey,
        'X-Goog-FieldMask': FIELD_MASK
      },
      payload: JSON.stringify(body),
      muteHttpExceptions: true
    });

    if (resp.getResponseCode() !== 200) {
      Logger.log('Arama hatasi: ' + query + ' -> ' + resp.getContentText());
      break;
    }

    var data = JSON.parse(resp.getContentText());
    var places = data.places || [];
    results = results.concat(places);
    pageToken = data.nextPageToken;
    if (!pageToken || places.length === 0) break;
    Utilities.sleep(300);
  }

  return results.slice(0, maxResults);
}

function findSocialLinks(html) {
  var found = {};
  var m;
  SOCIAL_LINK_RE.lastIndex = 0;
  while ((m = SOCIAL_LINK_RE.exec(html)) !== null) {
    found[SOCIAL_DOMAINS[m[1].toLowerCase()]] = true;
  }
  return Object.keys(found).sort();
}

function checkWebsite(url) {
  if (!url) return { status: 'Yok', socials: [] };
  try {
    var resp = UrlFetchApp.fetch(url, {
      muteHttpExceptions: true,
      followRedirects: true,
      headers: { 'User-Agent': 'Mozilla/5.0 IVEXLeadFinder/1.0' }
    });
    var code = resp.getResponseCode();
    if (code < 400) {
      return { status: 'Aktif', socials: findSocialLinks(resp.getContentText()) };
    }
    return { status: 'Pasif (HTTP ' + code + ')', socials: [] };
  } catch (e) {
    return { status: 'Pasif (erişilemiyor)', socials: [] };
  }
}

function manualCheckLink(name, location) {
  var q = '"' + name + '" ' + location + ' instagram';
  return 'https://www.google.com/search?q=' + encodeURIComponent(q);
}

function scorePriority(status, socials) {
  if (status === 'Yok') return 'Yüksek';
  if (status.indexOf('Pasif') === 0) return 'Yüksek';
  if (socials.length === 0) return 'Orta';
  return 'Düşük';
}

function priorityRank(priority) {
  if (priority === 'Yüksek') return 0;
  if (priority === 'Orta') return 1;
  return 2;
}

function shouldCall(status) {
  return (status === 'Yok' || status.indexOf('Pasif') === 0) ? 'Evet' : 'Hayır';
}

function sheetNameForSector(sector) {
  var name = 'Liste - ' + sector;
  name = name.replace(/[:\\\/\?\*\[\]]/g, '-');
  if (name.length > 100) name = name.substring(0, 100);
  return name;
}

function ensureSheetWithHeader(sheetName, headers) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName(sheetName);
  if (!sheet) {
    sheet = ss.insertSheet(sheetName);
  }
  if (sheet.getLastRow() === 0) {
    sheet.appendRow(headers);
    sheet.getRange(1, 1, 1, headers.length).setFontWeight('bold');
    sheet.setFrozenRows(1);
  }
  return sheet;
}

function appendRows(sheetName, headers, rows) {
  var sheet = ensureSheetWithHeader(sheetName, headers);
  if (rows.length) {
    var startRow = sheet.getLastRow() + 1;
    sheet.getRange(startRow, 1, rows.length, headers.length).setValues(rows);
  }
  sheet.autoResizeColumns(1, headers.length);
}

function getSeenSet() {
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName('_Görülenler');
  var set = {};
  if (!sheet) return set;
  var lastRow = sheet.getLastRow();
  if (lastRow < 2) return set;
  var keys = sheet.getRange(2, 1, lastRow - 1, 1).getValues();
  for (var i = 0; i < keys.length; i++) {
    var k = keys[i][0];
    if (k) set[k] = true;
  }
  return set;
}

function markSeen(entries) {
  if (!entries.length) return;
  appendRows('_Görülenler', SEEN_HEADERS, entries);
}

function performLeadSearch(runType) {
  var apiKey = PropertiesService.getScriptProperties().getProperty('GOOGLE_MAPS_API_KEY');
  if (!apiKey) {
    if (runType === 'Manuel') {
      SpreadsheetApp.getUi().alert('Önce menüden "1) API Anahtarını Kaydet" ile anahtarınızı girin.');
    } else {
      Logger.log('GOOGLE_MAPS_API_KEY tanimli degil, otomatik tarama atlandi.');
    }
    return;
  }

  var settings = getSettings();
  if (!settings.pairs.length) {
    if (runType === 'Manuel') {
      SpreadsheetApp.getUi().alert('"Ayarlar" sayfasında en az bir sektör-bölge satırı girin (her ikisi de dolu olmalı).');
    } else {
      Logger.log('Ayarlar sayfasi bos, otomatik tarama atlandi.');
    }
    return;
  }

  var sectorLocations = {};
  var sectorOrder = [];
  for (var i = 0; i < settings.pairs.length; i++) {
    var pSector = settings.pairs[i].sector;
    var pLocation = settings.pairs[i].location;
    if (!sectorLocations[pSector]) {
      sectorLocations[pSector] = [];
      sectorOrder.push(pSector);
    }
    sectorLocations[pSector].push(pLocation);
  }

  var today = Utilities.formatDate(new Date(), Session.getScriptTimeZone(), 'yyyy-MM-dd');
  var seenSet = getSeenSet();
  var bufferMultiplier = 3;

  var allNewRows = [];
  var newSeenEntries = [];
  var summaryLines = [];

  for (var s = 0; s < sectorOrder.length; s++) {
    var sector = sectorOrder[s];
    var locations = sectorLocations[sector];

    var candidatesById = {};
    for (var l = 0; l < locations.length; l++) {
      var location = locations[l];
      var query = sector + ' ' + location;
      var places = textSearch(query, apiKey, settings.rawLimit);
      for (var p = 0; p < places.length; p++) {
        var place = places[p];
        if (!place.id || candidatesById[place.id]) continue;
        if (place.businessStatus === 'CLOSED_PERMANENTLY') continue;
        var key = sector + '||' + place.id;
        if (seenSet[key]) continue;
        candidatesById[place.id] = { place: place, location: location, key: key };
      }
    }

    var candidates = Object.keys(candidatesById).map(function (id) { return candidatesById[id]; });
    candidates.sort(function (a, b) {
      var ra = typeof a.place.rating === 'number' ? a.place.rating : -1;
      var rb = typeof b.place.rating === 'number' ? b.place.rating : -1;
      return rb - ra;
    });

    var bufferSize = settings.dailyPerSector * bufferMultiplier;
    var buffer = candidates.slice(0, bufferSize);

    var checked = [];
    for (var c = 0; c < buffer.length; c++) {
      var cand = buffer[c];
      var place = cand.place;
      var website = place.websiteUri || '';
      var check = checkWebsite(website);
      var name = (place.displayName && place.displayName.text) || '';
      var priority = scorePriority(check.status, check.socials);
      var row = [
        today,
        sector,
        cand.location,
        name,
        place.nationalPhoneNumber || place.internationalPhoneNumber || '',
        place.formattedAddress || '',
        place.rating || '',
        website,
        check.status,
        check.socials.length ? check.socials.join(', ') : '-',
        manualCheckLink(name, cand.location),
        place.googleMapsUri || '',
        priority,
        shouldCall(check.status)
      ];
      checked.push({ row: row, key: cand.key, rating: place.rating || -1, priority: priority });
    }

    checked.sort(function (a, b) {
      var pr = priorityRank(a.priority) - priorityRank(b.priority);
      if (pr !== 0) return pr;
      return b.rating - a.rating;
    });

    var picked = checked.slice(0, settings.dailyPerSector);
    var sectorRows = picked.map(function (item) { return item.row; });

    appendRows(sheetNameForSector(sector), HEADERS, sectorRows);
    allNewRows = allNewRows.concat(sectorRows);

    for (var k = 0; k < picked.length; k++) {
      newSeenEntries.push([picked[k].key, sector, picked[k].key.split('||')[1], today]);
    }

    var sectorHigh = 0;
    for (var r2 = 0; r2 < sectorRows.length; r2++) {
      if (sectorRows[r2][12] === 'Yüksek') sectorHigh++;
    }
    summaryLines.push('- ' + sector + ': ' + sectorRows.length + ' yeni işletme (' + sectorHigh + ' yüksek öncelikli)');
  }

  appendRows('Tüm Sonuçlar', HEADERS, allNewRows);
  markSeen(newSeenEntries);

  var summaryText = summaryLines.join('\n');
  appendRows('Günlük Özet', SUMMARY_HEADERS, [[today, runType, allNewRows.length, summaryText]]);

  if (runType === 'Manuel') {
    SpreadsheetApp.getUi().alert('Tamamlandı.\n\n' + allNewRows.length + ' yeni işletme eklendi.\n\n' + summaryText);
  } else {
    Logger.log('Otomatik tarama tamamlandi: ' + allNewRows.length + ' yeni isletme.\n' + summaryText);
  }
}

function runLeadSearch() {
  performLeadSearch('Manuel');
}

function dailyAutoRun() {
  performLeadSearch('Otomatik');
}

function enableDailyAutoRun() {
  var ui = SpreadsheetApp.getUi();
  var resp = ui.prompt(
    'Otomatik Günlük Tarama',
    'Her gün saat kaçta çalışsın? 0-23 arası bir saat girin (örn. 9 = sabah 09:00):',
    ui.ButtonSet.OK_CANCEL
  );
  if (resp.getSelectedButton() !== ui.Button.OK) return;
  var hour = parseInt(resp.getResponseText().trim(), 10);
  if (isNaN(hour) || hour < 0 || hour > 23) {
    ui.alert('Geçerli bir saat girin (0-23).');
    return;
  }

  var triggers = ScriptApp.getProjectTriggers();
  for (var i = 0; i < triggers.length; i++) {
    if (triggers[i].getHandlerFunction() === DAILY_TRIGGER_HANDLER) {
      ScriptApp.deleteTrigger(triggers[i]);
    }
  }

  ScriptApp.newTrigger(DAILY_TRIGGER_HANDLER)
    .timeBased()
    .everyDays(1)
    .atHour(hour)
    .create();

  ui.alert('Otomatik günlük tarama kuruldu. Her gün yaklaşık saat ' + hour + ':00 civarında kendiliğinden çalışacak.');
}

function disableDailyAutoRun() {
  var ui = SpreadsheetApp.getUi();
  var triggers = ScriptApp.getProjectTriggers();
  var removed = 0;
  for (var i = 0; i < triggers.length; i++) {
    if (triggers[i].getHandlerFunction() === DAILY_TRIGGER_HANDLER) {
      ScriptApp.deleteTrigger(triggers[i]);
      removed++;
    }
  }
  ui.alert(removed > 0 ? 'Otomatik günlük tarama kapatıldı.' : 'Zaten kurulu bir otomatik tarama yoktu.');
}

function runDryRun() {
  var today = Utilities.formatDate(new Date(), Session.getScriptTimeZone(), 'yyyy-MM-dd');
  var bySector = {
    'kuaför': [
      [today, 'kuaför', 'Kadıköy, İstanbul', 'Güzellik Salonu Aylin', '(0216) 123 45 67',
        'Caferağa Mah. Moda Cad. No:12, Kadıköy/İstanbul', 4.6, '', 'Yok', '-',
        manualCheckLink('Güzellik Salonu Aylin', 'Kadıköy, İstanbul'),
        'https://maps.google.com/?cid=1', 'Yüksek', 'Evet'],
      [today, 'kuaför', 'Kadıköy, İstanbul', 'Berber Mert', '(0216) 234 56 78',
        'Osmanağa Mah. Söğütlüçeşme Cad. No:5, Kadıköy/İstanbul', 4.2,
        'http://berbermert-eskisite.com', 'Pasif (HTTP 404)', '-',
        manualCheckLink('Berber Mert', 'Kadıköy, İstanbul'),
        'https://maps.google.com/?cid=2', 'Yüksek', 'Evet']
    ],
    'galerici': [
      [today, 'galerici', 'Üsküdar, İstanbul', 'Oto Galeri Can', '(0216) 345 67 89',
        'Altunizade Mah. Kısıklı Cad. No:88, Üsküdar/İstanbul', 4.8,
        'https://otogaleriscan.com.tr', 'Aktif', 'Instagram, Facebook',
        manualCheckLink('Oto Galeri Can', 'Üsküdar, İstanbul'),
        'https://maps.google.com/?cid=3', 'Düşük', 'Hayır'],
      [today, 'galerici', 'Beşiktaş, İstanbul', 'Star Galeri', '(0212) 456 78 90',
        'Levent Mah. Büyükdere Cad. No:3, Beşiktaş/İstanbul', 4.5,
        'https://stargaleri.com', 'Aktif', '-',
        manualCheckLink('Star Galeri', 'Beşiktaş, İstanbul'),
        'https://maps.google.com/?cid=4', 'Orta', 'Hayır']
    ]
  };

  var allRows = [];
  var sectorOrder = Object.keys(bySector);
  for (var s = 0; s < sectorOrder.length; s++) {
    var sector = sectorOrder[s];
    appendRows(sheetNameForSector(sector), HEADERS, bySector[sector]);
    allRows = allRows.concat(bySector[sector]);
  }
  appendRows('Tüm Sonuçlar', HEADERS, allRows);

  SpreadsheetApp.getUi().alert(
    'Örnek veri eklendi (mevcut verilerin altına, silmeden): her sektör kendi sayfasına, hepsi ' +
    '"Tüm Sonuçlar" sayfasına.\n\nGerçek taramayı başlatmak için önce API anahtarınızı girin.'
  );
}
