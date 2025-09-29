from datetime import date, datetime
from typing import List, Set
import requests
from bs4 import BeautifulSoup, Tag

BASE_URL = "https://prada3d.ru/"


def _build_url(day: date) -> str:
    return f"{BASE_URL}?date={day.isoformat()}&city=balashiha&facility=prada-3d"


def _is_selected(el: Tag) -> bool:
    cls = " ".join(el.get("class", [])).lower() if el.has_attr("class") else ""
    if "active" in cls or "selected" in cls or "is-active" in cls:
        return True
    if el.get("aria-selected") in ("true", True) or el.get("aria-current") in ("date", "page", "true"):
        return True
    if el.name == "input" and (el.get("checked") in ("", "checked", True)):
        return True
    return False


def _available_dates(soup: BeautifulSoup) -> Set[str]:
    dates: Set[str] = set()
    # Collect ISO dates from links like ?date=YYYY-MM-DD
    for a in soup.select("a[href*='date=']"):
        href = a.get("href")
        if not href:
            continue
        # simple parse
        if "date=" in href:
            part = href.split("date=")[-1]
            iso = part.split("&")[0].split("#")[0]
            if len(iso) == 10:
                dates.add(iso)
    # Inputs with value ISO date
    for inp in soup.find_all("input", {"value": True}):
        val = inp.get("value")
        if isinstance(val, str) and len(val) == 10 and val[4] == "-" and val[7] == "-":
            dates.add(val)
    return dates


def _page_matches_date_or_listed(soup: BeautifulSoup, day: date) -> bool:
    iso = day.isoformat()
    # Selected/active explicitly
    for a in soup.select(f"a[href*='date={iso}']"):
        if isinstance(a, Tag) and _is_selected(a):
            return True
    for inp in soup.find_all("input", {"value": iso}):
        if isinstance(inp, Tag) and _is_selected(inp):
            return True
    # If requested date is among available dates shown on the page, accept
    if iso in _available_dates(soup):
        return True
    return False


def fetch_prada_titles(day: date) -> List[str]:
    url = _build_url(day)
    resp = requests.get(url, timeout=20, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        "Accept-Language": "ru-RU,ru;q=0.9",
    })
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")

    today = date.today()
    if day != today and not _page_matches_date_or_listed(soup, day):
        return []

    titles: List[str] = []
    for tag in soup.find_all(["h1", "h2", "h3"]):
        text = (tag.get_text(strip=True) or "").strip()
        if text:
            titles.append(text)
    return titles
