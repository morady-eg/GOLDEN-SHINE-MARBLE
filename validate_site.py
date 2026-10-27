from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
errors = []

def fail(message):
    errors.append(message)

required = [
    "index.html", "en/index.html", "commercial-projects.html",
    "en/commercial-projects.html", "service-areas.html", "en/service-areas.html",
    "robots.txt", "sitemap.xml", "404.html", "assets/gallery/README.md",
]
for rel in required:
    if not (ROOT / rel).is_file():
        fail(f"Missing required file: {rel}")

ar_home = (ROOT / "index.html").read_text(encoding="utf-8") if (ROOT / "index.html").exists() else ""
en_home = (ROOT / "en/index.html").read_text(encoding="utf-8") if (ROOT / "en/index.html").exists() else ""
projects = (ROOT / "commercial-projects.html").read_text(encoding="utf-8") if (ROOT / "commercial-projects.html").exists() else ""

if len(re.findall(r"<li>", projects)) != 64:
    fail("Project register must contain exactly 64 entries.")
if re.search(r"<b>28</b>", projects):
    fail("Project register should preserve the source numbering gap at item 28.")
for label, html in (("Arabic", ar_home), ("English", en_home)):
    gallery_match = re.search(r"const\s+galleryImages\s*=\[(.*?)\];", html, re.S)
    image_names = re.findall(r'"([^"]+\.webp)"', gallery_match.group(1)) if gallery_match else []
    if len(image_names) != 93:
        fail(f"{label} homepage must reference exactly 93 finished-work images.")
    if not ("encodeURIComponent(filename)" in html or "encodeURI('/assets/gallery/'+filename)" in html):
        fail(f"{label} homepage must build gallery image URLs from the actual filenames.")
    if "unsplash" in html.lower():
        fail(f"{label} homepage must not use stock Unsplash images as company work.")

service_slugs = [
    "marble-polishing", "granite-polishing", "joint-treatment",
    "crystal-polishing", "marble-protection", "staircase-polishing",
]
for slug in service_slugs:
    for rel in (f"services/{slug}.html", f"en/services/{slug}.html"):
        if not (ROOT / rel).is_file():
            fail(f"Missing service page: {rel}")

# Check local links in every HTML file. Gallery photos are user-supplied later.
for html_path in ROOT.rglob("*.html"):
    source = html_path.read_text(encoding="utf-8")
    for raw in re.findall(r'(?:href|src)="([^"]+)"', source):
        if raw.startswith(("#", "https://", "http://", "mailto:", "tel:", "javascript:", "data:")):
            continue
        # JavaScript-generated URLs are templates, not literal files on disk.
        if (re.search(r"""['"]\s*\+\s*[A-Za-z_$][\w$]*\s*\+\s*['"]""", raw)
                or "${" in raw or "encodeURI('/assets/gallery/'" in raw
                or ("assets/gallery/" in raw and "encodeURIComponent(filename)" in raw)):
            continue
        url = urlsplit(raw)
        target = url.path
        if not target:
            continue
        if re.fullmatch(r"/assets/gallery/work-\d{2}\.jpg", target):
            continue
        if target.startswith("/"):
            candidate = ROOT / target.lstrip("/")
        else:
            candidate = html_path.parent / target
        if candidate.is_dir():
            candidate = candidate / "index.html"
        if not candidate.exists() and not (not candidate.suffix and (candidate / "index.html").exists()):
            fail(f"Broken local link in {html_path.relative_to(ROOT)}: {raw}")

try:
    sitemap = ET.parse(ROOT / "sitemap.xml")
    for loc in sitemap.findall(".//{*}loc"):
        url = urlsplit(loc.text or "")
        path = url.path.lstrip("/")
        candidate = ROOT / path if path else ROOT / "index.html"
        if path.endswith("/"):
            candidate = candidate / "index.html"
        if not candidate.exists():
            fail(f"Sitemap URL has no matching file: {url.path}")
except (FileNotFoundError, ET.ParseError) as exc:
    fail(f"Invalid or missing sitemap.xml: {exc}")

if errors:
    print("FAIL: static website validation found issues:")
    for error in errors:
        print(f"- {error}")
    sys.exit(1)

print("PASS: required pages, 64 project entries, 93-image gallery setup, local links, service pages and sitemap validated.")
