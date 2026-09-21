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
    'Sektörler (her satıra bir tane)',
    'Bölgeler (her satıra bir tane)',
    'Sorgu Başına Maks. Sonuç'
  ]]);
  ayarlar.getRange('A1:C1').setFontWeight('bold');
  ayarlar.getRange('A2:B4').setValues([
    ['kuaför', 'Kadıköy, İstanbul'],
    ['berber', 'Üsküdar, İstanbul'],
    ['eczane', '']
  ]);
  ayarlar.getRange('C2').setValue(40);
  ayarlar.setFrozenRows(1);
  ayarlar.autoResizeColumns(1, 3);

  var leads = ss.getSheetByName('Leads');
  if (!leads) leads = ss.insertSheet('Leads');
  leads.clearContents();
  leads.appendRow(HEADERS);
  leads.setFrozenRows(1);

  SpreadsheetApp.getUi().alert(
    'Sayfalar hazırlandı.\n\n' +
    '"Ayarlar" sayfasındaki örnek sektör/bölgeleri kendi listenizle değiştirin, ' +
    'sonra menüden "1) API Anahtarını Kaydet" ve ardından "2) Taramayı Başlat" adımlarına geçin.'
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
  var sectors = [];
  var locations = [];
  for (var i = 1; i < data.length; i++) {
    var sector = (data[i][0] || '').toString().trim();
    var location = (data[i][1] || '').toString().trim();
    if (sector) sectors.push(sector);
    if (location) locations.push(location);
  }
  var maxResults = Number(sheet.getRange('C2').getValue()) || 40;
  return { sectors: sectors, locations: locations, maxResults: maxResults };
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

function writeLeads(rows) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName('Leads');
  if (!sheet) sheet = ss.insertSheet('Leads');
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
  if (!settings.sectors.length || !settings.locations.length) {
    ui.alert('"Ayarlar" sayfasında en az bir sektör ve bir bölge girin.');
    return;
  }

  var allPlaces = {};
  for (var s = 0; s < settings.sectors.length; s++) {
    for (var l = 0; l < settings.locations.length; l++) {
      var sector = settings.sectors[s];
      var location = settings.locations[l];
      var query = sector + ' ' + location;
      var places = textSearch(query, apiKey, settings.maxResults);
      for (var p = 0; p < places.length; p++) {
        var place = places[p];
        if (place.id && !allPlaces[place.id]) {
          allPlaces[place.id] = { place: place, sector: sector, location: location };
        }
      }
    }
  }

  var rows = [];
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
    rows.push([
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
    ]);
  }

  writeLeads(rows);

  var high = 0;
  for (var r = 0; r < rows.length; r++) {
    if (rows[r][11] === 'Yüksek') high++;
  }

  ui.alert(
    'Tamamlandı.\n\n' +
    rows.length + ' benzersiz işletme bulundu.\n' +
    high + ' tanesi yüksek öncelikli (website yok/pasif -> aranmalı).\n' +
    skippedClosed + ' kalıcı kapalı işletme listeden çıkarıldı.\n\n' +
    'Sonuçlar "Leads" sayfasında.'
  );
}

function runDryRun() {
  var rows = [
    ['kuaför', 'Kadıköy, İstanbul', 'Güzellik Salonu Aylin', '(0216) 123 45 67',
      'Caferağa Mah. Moda Cad. No:12, Kadıköy/İstanbul', 4.6, '', 'Yok', '-',
      manualCheckLink('Güzellik Salonu Aylin', 'Kadıköy, İstanbul'),
      'https://maps.google.com/?cid=1', 'Yüksek', 'Evet'],
    ['kuaför', 'Kadıköy, İstanbul', 'Berber Mert', '(0216) 234 56 78',
      'Osmanağa Mah. Söğütlüçeşme Cad. No:5, Kadıköy/İstanbul', 4.2,
      'http://berbermert-eskisite.com', 'Pasif (HTTP 404)', '-',
      manualCheckLink('Berber Mert', 'Kadıköy, İstanbul'),
      'https://maps.google.com/?cid=2', 'Yüksek', 'Evet'],
    ['kuaför', 'Kadıköy, İstanbul', 'Kırtasiye Dünyası', '(0216) 345 67 89',
      'Fenerbahçe Mah. Bağdat Cad. No:88, Kadıköy/İstanbul', 4.8,
      'https://kirtasiyedunyasi.com.tr', 'Aktif', 'Instagram, Facebook',
      manualCheckLink('Kırtasiye Dünyası', 'Kadıköy, İstanbul'),
      'https://maps.google.com/?cid=3', 'Düşük', 'Hayır'],
    ['kuaför', 'Kadıköy, İstanbul', 'Eczane Yıldız', '(0216) 456 78 90',
      'Rasimpaşa Mah. Rıhtım Cad. No:3, Kadıköy/İstanbul', 4.5,
      'https://eczaneyildiz.com', 'Aktif', '-',
      manualCheckLink('Eczane Yıldız', 'Kadıköy, İstanbul'),
      'https://maps.google.com/?cid=4', 'Orta', 'Hayır']
  ];
  writeLeads(rows);
  SpreadsheetApp.getUi().alert('Örnek veri "Leads" sayfasına yazıldı. Gerçek taramayı başlatmak için önce API anahtarınızı girin.');
}
