# 🕷️ Python Technical SEO Auditor

An "Agency-Grade" automated audit tool. This script recursively crawls XML sitemaps (handling nested `sitemapindex` files) to identify critical technical SEO issues and "Thin Content" risks across your entire site.

## 🚀 Key Features
1. **Recursive Sitemap Parsing:** Unlike basic scripts, this handles nested sitemaps (`sitemapindex`) and deep folder structures automatically.
2. **Smart Severity Scoring:** Automatically categorizes URLs as `ERROR`, `WARN`, or `OK` and sorts the final report so critical issues appear at the top.
3. **Thin Content Detection:** Identifies pages with less than 300 words to spot low-quality pages.
4. **Canonical Logic:** Checks if the canonical tag is self-referencing, missing, or pointing to another URL.
5. **On-Page Health:** Audits Title tags, Meta Descriptions, H1 presence, and Image Alt text.

## 🛠️ Installation
This tool requires `requests` and `beautifulsoup4`.

```bash
pip install requests beautifulsoup4

⚡ How to Run
Simply provide your sitemap URL. The script will handle the crawling and parsing.

python technical_seo_auditor.py --sitemap https://example.com/sitemap_index.xml

📊 The Output Report
The script generates a CSV with the following diagnostic columns:

Severity: ERROR (404s, Missing H1/Titles), WARN (Thin content, Missing Alts), or OK.

Status Code: Detects 4xx/5xx errors.

Word Count: Helps identify thin content.

Metadata: Length checks for Titles (30-60 chars) and Descriptions (50-160 chars).

Canonicals: Verifies canonical consistency.

📄 License
Open Source. Feel free to modify the THIN_CONTENT_THRESHOLD constant (default: 300 words) to fit your content strategy.
