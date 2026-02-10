#!/usr/bin/env python3
# technical_seo_auditor.py
# Agency-Grade Technical SEO Auditor V2 (Recursive Sitemap Support)

import argparse
import csv
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Dict, List, Tuple
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

# --- CONSTANTS ---
THIN_CONTENT_THRESHOLD = 300
TITLE_MIN_LEN = 30
TITLE_MAX_LEN = 60
DESC_MIN_LEN = 50
DESC_MAX_LEN = 160

# --- HELPERS ---
WORD_RE = re.compile(r"[A-Za-z0-9']+")

def _normalize_space(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())

def _count_words(text: str) -> int:
    return len(WORD_RE.findall(text or ""))

def _get_domain(href: str) -> str:
    try:
        p = urlparse(href)
        host = (p.netloc or "").lower()
        if host.startswith("www."):
            host = host[4:]
        return host
    except Exception:
        return ""

def _fetch_text(url: str, timeout: int, ua: str) -> Tuple[int, str]:
    headers = {"User-Agent": ua}
    try:
        r = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
        return r.status_code, r.text
    except requests.RequestException:
        return 0, ""

def parse_sitemap(sitemap_input: str, timeout: int, ua: str) -> List[str]:
    """
    Robust sitemap parser that handles nested sitemapindex and urlset.
    """
    seen = set()
    final_urls = []
    queue = [sitemap_input]

    while queue:
        current_url = queue.pop(0)
        if current_url in seen:
            continue
        seen.add(current_url)

        print(f"Reading sitemap: {current_url}...")
        code, xml_text = _fetch_text(current_url, timeout, ua)
        if code != 200 or not xml_text:
            print(f"  [!] Failed to fetch {current_url} (Status: {code})")
            continue

        try:
            root = ET.fromstring(xml_text)
            
            # Remove namespaces (e.g. {http://www.sitemaps.org/schemas/sitemap/0.9})
            # to make findall simpler
            for elem in root.iter():
                if '}' in elem.tag:
                    elem.tag = elem.tag.split('}', 1)[1]

            # Case 1: Sitemap Index (Nested sitemaps)
            if root.tag.lower() == 'sitemapindex':
                for sitemap in root.findall('sitemap'):
                    loc = sitemap.find('loc')
                    if loc is not None and loc.text:
                        nested_url = loc.text.strip()
                        if nested_url not in seen:
                            queue.append(nested_url)
            
            # Case 2: URL Set (Actual pages)
            elif root.tag.lower() == 'urlset':
                for url_tag in root.findall('url'):
                    loc = url_tag.find('loc')
                    if loc is not None and loc.text:
                        final_urls.append(loc.text.strip())
            
            else:
                # Fallback: try to find any <loc> tag
                for loc in root.findall(".//loc"):
                    if loc.text:
                        txt = loc.text.strip()
                        if txt.endswith('.xml'):
                            queue.append(txt)
                        else:
                            final_urls.append(txt)

        except ET.ParseError:
            print(f"  [!] Invalid XML in {current_url}")
            continue

    # Filter out duplicates
    return list(set(final_urls))

@dataclass
class SeoMetrics:
    url: str
    http_status: int
    severity: str  # ERROR, WARN, OK
    
    # Content
    word_count: int
    is_thin_content: int
    
    # Metadata
    title: str
    title_len: int
    title_status: str
    meta_desc: str
    meta_desc_len: int
    meta_desc_status: str
    
    # Technical
    h1_count: int
    canonical_link: str
    canonical_status: str
    
    # Links
    internal_links: int
    external_links: int
    broken_anchors: int
    img_missing_alt: int

def audit_html(url: str, html: str, domain: str) -> Dict:
    soup = BeautifulSoup(html, "html.parser")
    text_all = _normalize_space(soup.get_text(" "))
    word_count = _count_words(text_all)
    
    # 1. Title
    title_tag = soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else ""
    t_len = len(title)
    if t_len == 0: t_status = "MISSING"
    elif t_len < TITLE_MIN_LEN: t_status = "TOO_SHORT"
    elif t_len > TITLE_MAX_LEN: t_status = "TOO_LONG"
    else: t_status = "OK"

    # 2. Description
    meta_desc = ""
    d_tag = soup.find("meta", attrs={"name": "description"})
    if d_tag and d_tag.get("content"):
        meta_desc = d_tag["content"].strip()
    
    d_len = len(meta_desc)
    if d_len == 0: d_status = "MISSING"
    elif d_len < DESC_MIN_LEN: d_status = "TOO_SHORT"
    elif d_len > DESC_MAX_LEN: d_status = "TOO_LONG"
    else: d_status = "OK"

    # 3. Canonical
    canon_href = ""
    c_tag = soup.find("link", rel="canonical")
    if c_tag and c_tag.get("href"):
        canon_href = c_tag["href"].strip()
    
    c_status = "MISSING"
    if canon_href:
        if canon_href.rstrip('/') == url.rstrip('/'):
            c_status = "SELF"
        else:
            c_status = "OTHER"

    # 4. Headings
    h1_count = len(soup.find_all("h1"))

    # 5. Links
    internal = 0
    external = 0
    broken_anchors = 0
    ids = {tag.get("id") for tag in soup.find_all(True) if tag.get("id")}

    for a in soup.find_all("a"):
        href = a.get("href") or ""
        if not href or href.startswith(("mailto:", "tel:", "javascript:")): continue
        
        if href.startswith("#"):
            if len(href) > 1 and href[1:] not in ids:
                broken_anchors += 1
            continue

        link_domain = _get_domain(href)
        if not link_domain: 
            internal += 1
        elif link_domain == domain or link_domain.endswith("." + domain):
            internal += 1
        else:
            external += 1

    # 6. Images
    img_missing_alt = sum(1 for img in soup.find_all("img") if not img.get("alt"))

    return {
        "word_count": word_count,
        "is_thin_content": 1 if word_count < THIN_CONTENT_THRESHOLD else 0,
        "title": title,
        "title_len": t_len,
        "title_status": t_status,
        "meta_desc": meta_desc,
        "meta_desc_len": d_len,
        "meta_desc_status": d_status,
        "h1_count": h1_count,
        "canonical_link": canon_href,
        "canonical_status": c_status,
        "internal_links": internal,
        "external_links": external,
        "broken_anchors": broken_anchors,
        "img_missing_alt": img_missing_alt
    }

def compute_severity(m: Dict) -> str:
    if m["http_status"] >= 400: return "ERROR"
    if m["h1_count"] == 0: return "ERROR"
    if m["canonical_status"] == "MISSING": return "ERROR"
    if m["title_status"] == "MISSING": return "ERROR"
    
    if m["is_thin_content"]: return "WARN"
    if m["meta_desc_status"] != "OK": return "WARN"
    if m["title_status"] != "OK": return "WARN"
    if m["broken_anchors"] > 0: return "WARN"
    if m["img_missing_alt"] > 0: return "WARN"
    
    return "OK"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sitemap", required=True)
    ap.add_argument("--out", default="technical_audit.csv")
    args = ap.parse_args()

    parsed = urlparse(args.sitemap)
    domain = (parsed.netloc or "").replace("www.", "")
    
    # Use a real browser UA to avoid 403 blocks
    UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

    print(f"--- Starting Audit for: {domain} ---")
    
    urls = parse_sitemap(args.sitemap, 20, UA)
    if not urls:
        print("No page URLs found. Check your sitemap format.")
        return

    print(f"Found {len(urls)} pages to audit.")
    
    rows = []
    for idx, url in enumerate(urls, 1):
        print(f"[{idx}/{len(urls)}] Auditing: {url}")
        status, html = _fetch_text(url, 20, UA)
        
        if status >= 400 or not html:
            data = {
                "word_count": 0, "is_thin_content": 0, "title": "", "title_len": 0,
                "title_status": "MISSING", "meta_desc": "", "meta_desc_len": 0,
                "meta_desc_status": "MISSING", "h1_count": 0, "canonical_link": "",
                "canonical_status": "MISSING", "internal_links": 0, "external_links": 0,
                "broken_anchors": 0, "img_missing_alt": 0
            }
        else:
            data = audit_html(url, html, domain)
        
        data["http_status"] = status
        sev = compute_severity(data)
        rows.append(SeoMetrics(url=url, severity=sev, **data))

    # Save
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        headers = [
            "severity", "http_status", "url", 
            "title_status", "title_len", "title",
            "meta_desc_status", "meta_desc_len", "meta_desc",
            "canonical_status", "canonical_link",
            "h1_count", "word_count", "is_thin_content",
            "internal_links", "external_links", "broken_anchors", "img_missing_alt"
        ]
        writer.writerow(headers)
        
        # Sort: ERROR > WARN > OK
        rows.sort(key=lambda x: (0 if x.severity=="ERROR" else 1 if x.severity=="WARN" else 2))
        
        for r in rows:
            writer.writerow([getattr(r, h) for h in headers])

    print(f"\nDone! Report saved to {args.out}")

if __name__ == "__main__":
    main()