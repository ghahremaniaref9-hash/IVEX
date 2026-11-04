// HTML belgeyi A4 PDF'e basar ve her sayfanın PNG önizlemesini kaydeder.
// Kullanım: node yazdir.js belge.html cikti.pdf sayfa-klasoru
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

(async () => {
  const [html, pdf, pagesDir] = process.argv.slice(2);
  const browser = await chromium.launch();
  const context = await browser.newContext({ deviceScaleFactor: 2, viewport: { width: 794, height: 1123 } });
  const page = await context.newPage();
  await page.goto('file://' + path.resolve(html));
  await page.evaluate(() => document.fonts.ready);
  await page.pdf({ path: pdf, preferCSSPageSize: true, printBackground: true });
  fs.mkdirSync(pagesDir, { recursive: true });
  const sections = await page.$$('section.page');
  for (let i = 0; i < sections.length; i++) {
    await sections[i].screenshot({ path: path.join(pagesDir, `sayfa-${String(i + 1).padStart(2, '0')}.png`) });
  }
  await browser.close();
})();
