/**
 * IVEX Lead Finder - Google Sheets / Apps Script sürümü.
 * Python/terminal gerekmez; her şey tarayıcıda, Google Sheets içinde çalışır.
 * Kurulum: sheets-version/README.md dosyasına bakın.
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
  'Sektör', 'Bölge', 'Marka Adı', 'Telefon', 'Adres', 'Google Puanı',
  'Website', 'Website Durumu', "Sosyal Medya (Website'den Bulunan)",
  'Sosyal Medya Manuel Kontrol Linki', 'Google Maps Linki', 'Öncelik', 'Aranmalı mı?'
];

function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu('IVEX Lead Finder')
    .addItem('0) Sayfaları Hazırla (İlk Kurulum)', 'setupSheets')
    .addItem('1) API Anahtarını Kaydet', 'saveApiKey')
    .addItem('2) Taramayı Başlat', 'runLeadSearch')
    .addSeparator()
    .addItem('Örnek Veriyle Test Et (Dry Run)', 'runDryRun')
    .addToUi();
}

function setupSheets() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();

  var ayarlar = ss.getSheetByName('Ayarlar');
  if (!ayarlar) ayarlar = ss.insertSheet('Ayarlar');
  ayarlar.clear();
  ayarlar.getRange('A1:C1').setValues([[
    'Sektör',
    'Bölge',
    'Sorgu Başına Maks. Sonuç'
  ]]);
  ayarlar.getRange('A1:C1').setFontWeight('bold');
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
  ayarlar.getRange('C2').setValue(40);
  ayarlar.setFrozenRows(1);
  ayarlar.autoResizeColumns(1, 3);
  ayarlar.getRange('E1').setValue(
    'Her satır bir arama demektir: o satırdaki sektörü, o satırdaki bölgede arar. ' +
    'Aynı sektörü birden fazla bölgede aramak için sektörü tekrar tekrar yeni satırlara yazın. ' +
    'Farklı sektörler farklı bölge setlerinde aranabilir, hepsi aynı olmak zorunda değil.'
  );
  ayarlar.getRange('E1').setFontStyle('italic').setFontColor('#666666');
  ayarlar.autoResizeColumn(5);

  var tumSonuclar = ss.getSheetByName('Tüm Sonuçlar');
  if (!tumSonuclar) tumSonuclar = ss.insertSheet('Tüm Sonuçlar');
  tumSonuclar.clearContents();
  tumSonuclar.appendRow(HEADERS);
  tumSonuclar.setFrozenRows(1);

  SpreadsheetApp.getUi().alert(
    'Sayfalar hazırlandı.\n\n' +
    '"Ayarlar" sayfasındaki örnek sektör/bölgeleri kendi listenizle değiştirin, ' +
    'sonra menüden "1) API Anahtarını Kaydet" ve ardından "2) Taramayı Başlat" adımlarına geçin.\n\n' +
    'Tarama bitince her sektör için ayrı bir sayfa ("Liste - <sektör adı>") ve hepsini bir arada ' +
    'gösteren bir "Tüm Sonuçlar" sayfası otomatik oluşacak.'
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
  ui.alert('Anahtar kaydedildi. Artık "2) Taramayı Başlat" ile devam edebilirsiniz.');
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
  var maxResults = Number(sheet.getRange('C2').getValue()) || 40;
  return { pairs: pairs, maxResults: maxResults };
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

function shouldCall(status) {
  return (status === 'Yok' || status.indexOf('Pasif') === 0) ? 'Evet' : 'Hayır';
}

function sheetNameForSector(sector) {
  var name = 'Liste - ' + sector;
  name = name.replace(/[:\\\/\?\*\[\]]/g, '-');
  if (name.length > 100) name = name.substring(0, 100);
  return name;
}

function writeToSheet(sheetName, rows) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName(sheetName);
  if (!sheet) sheet = ss.insertSheet(sheetName);
  sheet.clearContents();
  sheet.appendRow(HEADERS);
  if (rows.length) {
    sheet.getRange(2, 1, rows.length, HEADERS.length).setValues(rows);
  }
  sheet.setFrozenRows(1);
  sheet.autoResizeColumns(1, HEADERS.length);
}

function runLeadSearch() {
  var ui = SpreadsheetApp.getUi();
  var apiKey = PropertiesService.getScriptProperties().getProperty('GOOGLE_MAPS_API_KEY');
  if (!apiKey) {
    ui.alert('Önce menüden "1) API Anahtarını Kaydet" ile anahtarınızı girin.');
    return;
  }

  var settings = getSettings();
  if (!settings.pairs.length) {
    ui.alert('"Ayarlar" sayfasında en az bir sektör-bölge satırı girin (her ikisi de dolu olmalı).');
    return;
  }

  var allPlaces = {};
  for (var i = 0; i < settings.pairs.length; i++) {
    var sector = settings.pairs[i].sector;
    var location = settings.pairs[i].location;
    var query = sector + ' ' + location;
    var places = textSearch(query, apiKey, settings.maxResults);
    for (var p = 0; p < places.length; p++) {
      var place = places[p];
      if (place.id && !allPlaces[place.id]) {
        allPlaces[place.id] = { place: place, sector: sector, location: location };
      }
    }
  }

  var allRows = [];
  var bySector = {};
  var sectorOrder = [];
  var skippedClosed = 0;
  var ids = Object.keys(allPlaces);
  for (var i = 0; i < ids.length; i++) {
    var entry = allPlaces[ids[i]];
    var place = entry.place;
    if (place.businessStatus === 'CLOSED_PERMANENTLY') {
      skippedClosed++;
      continue;
    }
    var website = place.websiteUri || '';
    var check = checkWebsite(website);
    var name = (place.displayName && place.displayName.text) || '';
    var row = [
      entry.sector,
      entry.location,
      name,
      place.nationalPhoneNumber || place.internationalPhoneNumber || '',
      place.formattedAddress || '',
      place.rating || '',
      website,
      check.status,
      check.socials.length ? check.socials.join(', ') : '-',
      manualCheckLink(name, entry.location),
      place.googleMapsUri || '',
      scorePriority(check.status, check.socials),
      shouldCall(check.status)
    ];
    allRows.push(row);
    if (!bySector[entry.sector]) {
      bySector[entry.sector] = [];
      sectorOrder.push(entry.sector);
    }
    bySector[entry.sector].push(row);
  }

  writeToSheet('Tüm Sonuçlar', allRows);
  for (var s = 0; s < sectorOrder.length; s++) {
    var sector = sectorOrder[s];
    writeToSheet(sheetNameForSector(sector), bySector[sector]);
  }

  var high = 0;
  for (var r = 0; r < allRows.length; r++) {
    if (allRows[r][11] === 'Yüksek') high++;
  }

  var sectorSummary = sectorOrder.map(function (sector) {
    return '- ' + sector + ': ' + bySector[sector].length + ' işletme (sayfa: "' + sheetNameForSector(sector) + '")';
  }).join('\n');

  ui.alert(
    'Tamamlandı.\n\n' +
    allRows.length + ' benzersiz işletme bulundu.\n' +
    high + ' tanesi yüksek öncelikli (website yok/pasif -> aranmalı).\n' +
    skippedClosed + ' kalıcı kapalı işletme listeden çıkarıldı.\n\n' +
    'Sektöre göre dağılım:\n' + sectorSummary + '\n\n' +
    'Hepsi bir arada: "Tüm Sonuçlar" sayfasında.'
  );
}

function runDryRun() {
  var bySector = {
    'kuaför': [
      ['kuaför', 'Kadıköy, İstanbul', 'Güzellik Salonu Aylin', '(0216) 123 45 67',
        'Caferağa Mah. Moda Cad. No:12, Kadıköy/İstanbul', 4.6, '', 'Yok', '-',
        manualCheckLink('Güzellik Salonu Aylin', 'Kadıköy, İstanbul'),
        'https://maps.google.com/?cid=1', 'Yüksek', 'Evet'],
      ['kuaför', 'Kadıköy, İstanbul', 'Berber Mert', '(0216) 234 56 78',
        'Osmanağa Mah. Söğütlüçeşme Cad. No:5, Kadıköy/İstanbul', 4.2,
        'http://berbermert-eskisite.com', 'Pasif (HTTP 404)', '-',
        manualCheckLink('Berber Mert', 'Kadıköy, İstanbul'),
        'https://maps.google.com/?cid=2', 'Yüksek', 'Evet']
    ],
    'galerici': [
      ['galerici', 'Üsküdar, İstanbul', 'Oto Galeri Can', '(0216) 345 67 89',
        'Altunizade Mah. Kısıklı Cad. No:88, Üsküdar/İstanbul', 4.8,
        'https://otogaleriscan.com.tr', 'Aktif', 'Instagram, Facebook',
        manualCheckLink('Oto Galeri Can', 'Üsküdar, İstanbul'),
        'https://maps.google.com/?cid=3', 'Düşük', 'Hayır'],
      ['galerici', 'Beşiktaş, İstanbul', 'Star Galeri', '(0212) 456 78 90',
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
    writeToSheet(sheetNameForSector(sector), bySector[sector]);
    allRows = allRows.concat(bySector[sector]);
  }
  writeToSheet('Tüm Sonuçlar', allRows);

  SpreadsheetApp.getUi().alert(
    'Örnek veri yazıldı: her sektör kendi sayfasına ("Liste - kuaför", "Liste - galerici"), ' +
    'hepsi bir arada "Tüm Sonuçlar" sayfasına.\n\n' +
    'Gerçek taramayı başlatmak için önce API anahtarınızı girin.'
  );
}
