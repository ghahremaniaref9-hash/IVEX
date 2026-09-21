#!/usr/bin/env python3
"""
IVEX Lead Finder
Sektör + mahalle bazlı Google Maps taramasından esnaf listesi çıkarır;
her işletme için website'in aktif olup olmadığını ve website üzerinden
bulunabilen sosyal medya linklerini otomatik kontrol eder.

Kullanım:
    python3 lead_finder.py --config config.json
    python3 lead_finder.py --dry-run   (API anahtarı olmadan, örnek veriyle test)
"""

import argparse
import csv
import json
import os
import re
import sys
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

PLACES_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
FIELD_MASK = ",".join(
    [
        "places.id",
        "places.displayName",
        "places.formattedAddress",
        "places.nationalPhoneNumber",
        "places.internationalPhoneNumber",
        "places.websiteUri",
        "places.googleMapsUri",
        "places.rating",
        "places.businessStatus",
        "nextPageToken",
    ]
)
SOCIAL_DOMAINS = {
    "instagram.com": "Instagram",
    "facebook.com": "Facebook",
    "tiktok.com": "TikTok",
    "twitter.com": "Twitter/X",
    "x.com": "Twitter/X",
    "linkedin.com": "LinkedIn",
    "youtube.com": "YouTube",
}
SOCIAL_LINK_RE = re.compile(
    r"https?://(?:www\.)?(" + "|".join(re.escape(d) for d in SOCIAL_DOMAINS) + r")/[^\s\"'<>)]+",
    re.IGNORECASE,
)
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36 IVEXLeadFinder/1.0"
)


def load_config(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def google_text_search(query, api_key, max_results, session):
    """Google Places API (New) Text Search - sayfalama ile max_results'a kadar sonuç çeker."""
    results = []
    page_token = None
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": FIELD_MASK,
    }

    while len(results) < max_results:
        body = {"textQuery": query, "languageCode": "tr"}
        if page_token:
            body["pageToken"] = page_token
            # Google: yeni page token birkaç saniye gecikmeyle aktif olur
            time.sleep(2)

        resp = session.post(PLACES_SEARCH_URL, headers=headers, json=body, timeout=15)
        if resp.status_code != 200:
            print(f"  [HATA] '{query}' aramasi basarisiz: {resp.status_code} {resp.text[:200]}", file=sys.stderr)
            break

        data = resp.json()
        places = data.get("places", [])
        results.extend(places)
        page_token = data.get("nextPageToken")
        if not page_token or not places:
            break
        time.sleep(0.3)

    return results[:max_results]


def check_website(url, session):
    """Website'e istek atip aktif/pasif oldugunu ve sayfada gecen sosyal medya linklerini bulur."""
    if not url:
        return "Yok", []

    try:
        resp = session.get(
            url,
            headers={"User-Agent": USER_AGENT},
            timeout=8,
            allow_redirects=True,
        )
        if resp.status_code < 400:
            status = "Aktif"
            socials = sorted(set(SOCIAL_DOMAINS[m.group(1).lower()] for m in SOCIAL_LINK_RE.finditer(resp.text)))
        else:
            status = f"Pasif (HTTP {resp.status_code})"
            socials = []
    except requests.exceptions.SSLError:
        status = "Pasif (SSL hatasi)"
        socials = []
    except requests.exceptions.Timeout:
        status = "Pasif (zaman asimi)"
        socials = []
    except requests.exceptions.RequestException:
        status = "Pasif (erisilemiyor)"
        socials = []

    return status, socials


def manual_check_link(name, location):
    q = f'"{name}" {location} instagram'
    return "https://www.google.com/search?q=" + urllib.parse.quote(q)


def score_priority(website_status, socials_found):
    if website_status == "Yok":
        return "Yüksek"
    if website_status.startswith("Pasif"):
        return "Yüksek"
    if not socials_found:
        return "Orta"
    return "Düşük"


def should_call(website_status):
    return "Evet" if (website_status == "Yok" or website_status.startswith("Pasif")) else "Hayır"


def collect_leads(config, api_key, dry_run=False):
    session = requests.Session()
    all_places = {}  # place id -> (place dict, sector, location)

    if dry_run:
        fixture_path = os.path.join(os.path.dirname(__file__), "fixtures", "dryrun_places.json")
        with open(fixture_path, "r", encoding="utf-8") as f:
            fixture = json.load(f)
        for sector in config["sectors"]:
            for location in config["locations"]:
                for place in fixture:
                    key = f"{place['id']}-{sector}-{location}"
                    all_places[key] = (place, sector, location)
        print(f"[DRY-RUN] {len(all_places)} ornek kayit yuklendi (gercek API cagrisi yapilmadi).")
    else:
        for sector in config["sectors"]:
            for location in config["locations"]:
                query = f"{sector} {location}"
                print(f"Araniyor: {query} ...")
                places = google_text_search(query, api_key, config.get("max_results_per_query", 40), session)
                print(f"  -> {len(places)} sonuc bulundu")
                for place in places:
                    pid = place.get("id")
                    if pid and pid not in all_places:
                        all_places[pid] = (place, sector, location)

    leads = []
    website_checks = {}

    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_pid = {}
        for pid, (place, sector, location) in all_places.items():
            website = place.get("websiteUri")
            if dry_run:
                # dry-run'da gercek network cagrisi yapma, fixture'daki durumu kullan
                future = executor.submit(lambda p=place: (p.get("_dryrun_status", "Yok"), p.get("_dryrun_socials", [])))
            else:
                future = executor.submit(check_website, website, session)
            future_to_pid[future] = pid

        for future in as_completed(future_to_pid):
            pid = future_to_pid[future]
            website_checks[pid] = future.result()

    skipped_closed = 0
    for pid, (place, sector, location) in all_places.items():
        if place.get("businessStatus") == "CLOSED_PERMANENTLY":
            skipped_closed += 1
            continue
        status, socials = website_checks[pid]
        name = place.get("displayName", {}).get("text", "")
        leads.append(
            {
                "Sektör": sector,
                "Bölge": location,
                "Marka Adı": name,
                "Telefon": place.get("nationalPhoneNumber") or place.get("internationalPhoneNumber") or "",
                "Adres": place.get("formattedAddress", ""),
                "Google Puanı": place.get("rating", ""),
                "Website": place.get("websiteUri", ""),
                "Website Durumu": status,
                "Sosyal Medya (Website'den Bulunan)": ", ".join(socials) if socials else "-",
                "Sosyal Medya Manuel Kontrol Linki": manual_check_link(name, location),
                "Google Maps Linki": place.get("googleMapsUri", ""),
                "Öncelik": score_priority(status, socials),
                "Aranmalı mı?": should_call(status),
            }
        )

    if skipped_closed:
        print(f"  ({skipped_closed} kalici kapali isletme listeden cikarildi)")

    return leads


def write_csv(leads, out_path):
    fieldnames = [
        "Sektör",
        "Bölge",
        "Marka Adı",
        "Telefon",
        "Adres",
        "Google Puanı",
        "Website",
        "Website Durumu",
        "Sosyal Medya (Website'den Bulunan)",
        "Sosyal Medya Manuel Kontrol Linki",
        "Google Maps Linki",
        "Öncelik",
        "Aranmalı mı?",
    ]
    # utf-8-sig: Excel'de Turkce karakterlerin dogru gorunmesi icin BOM ekler
    with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for lead in leads:
            writer.writerow(lead)


def main():
    parser = argparse.ArgumentParser(description="IVEX Lead Finder - Google Maps'ten esnaf listesi cikarir")
    parser.add_argument("--config", default="config.json", help="Config dosyasi (varsayilan: config.json)")
    parser.add_argument("--out", default=None, help="Cikti CSV dosyasi (config'teki output_csv'yi gecersiz kilar)")
    parser.add_argument("--dry-run", action="store_true", help="API anahtari olmadan ornek veriyle test et")
    args = parser.parse_args()

    if not os.path.exists(args.config):
        print(f"[HATA] Config dosyasi bulunamadi: {args.config}")
        print("Once config.example.json dosyasini kopyalayip config.json olarak duzenleyin.")
        sys.exit(1)

    config = load_config(args.config)

    api_key = os.environ.get("GOOGLE_MAPS_API_KEY")
    if not args.dry_run and not api_key:
        print("[HATA] GOOGLE_MAPS_API_KEY ortam degiskeni bulunamadi.")
        print("Once .env.example dosyasini .env olarak kopyalayip API anahtarinizi girin,")
        print("sonra: export GOOGLE_MAPS_API_KEY=... (veya .env dosyasini yukleyen bir arac kullanin)")
        sys.exit(1)

    leads = collect_leads(config, api_key, dry_run=args.dry_run)

    out_path = args.out or config.get("output_csv", "leads.csv")
    write_csv(leads, out_path)

    high = sum(1 for l in leads if l["Öncelik"] == "Yüksek")
    print(f"\nToplam {len(leads)} benzersiz isletme bulundu.")
    print(f"  Yuksek oncelik (website yok/pasif -> aranmali): {high}")
    print(f"Sonuc dosyasi: {out_path}")


if __name__ == "__main__":
    main()
