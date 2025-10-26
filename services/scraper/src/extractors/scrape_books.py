import re
import time, random
import requests
from pathlib import Path
from urllib.parse import urljoin, urlparse
import pandas as pd
from bs4 import BeautifulSoup

BASE           = "https://books.toscrape.com/"
START_URL      = urljoin(BASE, "index.html")
MAX_PAGES_GUARD = 200 

REPO_ROOT  = Path(__file__).resolve().parents[4]
BRONZE_DIR = REPO_ROOT / "data" / "bronze"
IMAGES_DIR = BRONZE_DIR / "images"
BRONZE_DIR.mkdir(parents=True, exist_ok=True)
IMAGES_DIR.mkdir(parents=True, exist_ok=True)

OUT_PATH = BRONZE_DIR / "books.csv"

W2D = {"One":1, "Two":2, "Three":3, "Four":4, "Five":5}

session = requests.Session()
session.headers.update({"User-Agent": "books-scraper/0.1"})


def download_image(image_url: str, book_id: str) -> str | None:
    if not image_url:
        return None
    
    try:
        r = session.get(image_url, timeout=30, stream=True)

        if not r.encoding or r.encoding.lower() != "utf-8":
            r.encoding = "utf-8"

        r.raise_for_status()
        ext = Path(urlparse(image_url).path).suffix.lower()

        if ext not in {".jpg",".jpeg",".png",".gif",".webp"}:
            ctype = r.headers.get("Content-Type","").lower()
            if "png" in ctype:
                ext = ".png"
            elif "webp" in ctype:
                ext = ".webp"
            else:
                ext = ".jpg"

        out = IMAGES_DIR / f"{book_id}{ext}"

        with open(out, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        return f"data/bronze/images/{book_id}{ext}"
    
    except Exception:
        return None

def fetch_more_info(prod_url: str) -> tuple[dict, str | None]:
    r = session.get(prod_url, timeout=30)

    if not r.encoding or r.encoding.lower() != "utf-8":
        r.encoding = "utf-8"

    r.raise_for_status()
    sp = BeautifulSoup(r.text, "html.parser")

    product_info = {}
    table = sp.select_one("table.table.table-striped")

    if table:
        for tr in table.select("tr"):
            th = tr.find("th").get_text(strip=True)
            td = tr.find("td").get_text(strip=True)
            product_info[th] = td

    if "Availability" in product_info:
        m = re.search(r"(\d+)", product_info["Availability"])
        if m:
            product_info["Availability"] = m.group(1)

    full_img = sp.select_one(".item.active img, #product_gallery img, .thumbnail img")
    full_img_url = urljoin(prod_url, full_img["src"]) if full_img and full_img.get("src") else None

    return product_info, full_img_url

def iterate_category(category_name: str, first_page_url: str, rows: list[dict]):
    url = first_page_url
    guard = 0

    while url and guard < MAX_PAGES_GUARD:
        guard += 1
        r = session.get(url, timeout=30)

        if not r.encoding or r.encoding.lower() != "utf-8":
            r.encoding = "utf-8"

        r.raise_for_status()
        sp = BeautifulSoup(r.text, "html.parser")

        items = sp.select("ol.row li")

        for li in items:
            a = li.select_one("h3 a")

            if not a:
                continue

            title = a.get("title", "").strip()
            rating_words = li.select_one("p.star-rating")
            rating = 0

            if rating_words:
                classes = rating_words.get("class", [])
                rating = next((W2D[c] for c in classes if c in W2D), 0)

            raw_price = (li.select_one("p.price_color").get_text(strip=True)
                         if li.select_one("p.price_color") else "")

            href = a.get("href", "").strip()
            prod_url = urljoin(url, href).replace("index.html", "")
            prod_url = prod_url if prod_url.endswith(".html") else prod_url + "index.html"

            p = Path(urlparse(prod_url).path)
            book_id = p.parent.name if p.name == "index.html" else p.stem

            product_info, full_img_url = fetch_more_info(prod_url)

            thumb = li.select_one("img")
            thumb_url = urljoin(url, thumb["src"]) if thumb and thumb.get("src") else None
            image_url = full_img_url or thumb_url

            image_path_rel = None

            rows.append({
                "id": book_id,                                  # string
                "book_title": title,                            # string
                "category": category_name,                      # string
                "raw_price": raw_price,                         # string
                "rating": rating,                               # integer
                "instock": product_info.get("Availability"),    # integer
                "UPC": product_info.get("UPC"),                 # string
                "link": prod_url,                               # string
                "image_url": image_url,                         # string
                "image_path": image_path_rel,                   # string
            })

        next_a = sp.select_one("li.next > a")

        if next_a and next_a.get("href"):
            url = urljoin(r.url, next_a["href"])
            time.sleep(random.uniform(0.2, 0.5))
        else:
            break

def main():
    r = session.get(START_URL, timeout=30)

    if not r.encoding or r.encoding.lower() != "utf-8":
        r.encoding = "utf-8"

    r.raise_for_status()
    sp = BeautifulSoup(r.text, "html.parser")

    cats = sp.select("ul.nav.nav-list > li > ul > li > a")
    rows: list[dict] = []

    for a in cats:
        category_name = a.get_text(strip=True)
        category_url = urljoin(BASE, a.get("href"))
        iterate_category(category_name, category_url, rows)

    df = pd.DataFrame(rows).drop_duplicates(subset=["id"], keep="first").reset_index(drop=True)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_PATH, index=False, encoding="utf-8-sig")

    print(f"[OK] Categorias: {len(cats)} | Livros únicos: {len(df)}")
    print(f"[OK] CSV: {OUT_PATH.resolve()}")
    print(f"[OK] Imagens em: {IMAGES_DIR.resolve()}")

if __name__ == "__main__":
    main()
