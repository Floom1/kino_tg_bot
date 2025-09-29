from datetime import date
from typing import List
import asyncio
import re
import requests
from bs4 import BeautifulSoup

from ..filters import filter_movie_titles

BASE_YA = "https://afisha.yandex.ru/moscow/cinema/places/karo-10-reutov"


def _build_yandex_url(day: date) -> str:
    today = date.today()
    if day == today:
        return f"{BASE_YA}?place-schedule-preset=today"
    if day == date.fromordinal(today.toordinal() + 1):
        return f"{BASE_YA}?place-schedule-preset=tomorrow"
    return f"{BASE_YA}?place-schedule-date={day.isoformat()}"


def _parse_titles_from_html(html: str) -> List[str]:
    soup = BeautifulSoup(html, "lxml")
    titles: List[str] = []

    # Prefer explicit movie links
    for a in soup.select('a[href*="/movie/"]'):
        txt = (a.get_text(strip=True) or "").strip()
        if txt:
            titles.append(txt)

    # Headings inside movie cards
    for h in soup.select("h2, h3"):
        txt = (h.get_text(strip=True) or "").strip()
        if txt:
            titles.append(txt)

    return titles


def _has_smartcaptcha(html: str) -> bool:
    return ("SmartCaptcha" in html) or ("Я не робот" in html)


def _fetch_with_requests(url: str) -> str:
    resp = requests.get(
        url,
        timeout=25,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            "Accept-Language": "ru-RU,ru;q=0.9",
        },
    )
    resp.raise_for_status()
    return resp.text


async def _fetch_with_playwright_async(url: str) -> str:
    try:
        from playwright.async_api import async_playwright  # type: ignore
    except Exception:
        return ""

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            context = await browser.new_context(locale="ru-RU")
            page = await context.new_page()
            await page.goto(url, timeout=30000, wait_until="domcontentloaded")

            # Slow scroll to trigger lazy content
            for _ in range(6):
                await page.mouse.wheel(0, 1200)
                await page.wait_for_timeout(400)

            # Wait for movie cards/selectors heuristically
            try:
                await page.wait_for_selector('a[href*="/movie/"], h2, h3', timeout=5000)
            except Exception:
                await page.wait_for_timeout(800)

            return await page.content()
        finally:
            await browser.close()


async def fetch_karo_titles_quick(day: date) -> List[str]:
    url = _build_yandex_url(day)
    html = await asyncio.to_thread(_fetch_with_requests, url)
    if _has_smartcaptcha(html):
        html = await _fetch_with_playwright_async(url)
    titles = _parse_titles_from_html(html) if html else []
    return filter_movie_titles(titles)


async def fetch_karo_titles(day: date) -> List[str]:
    url = _build_yandex_url(day)
    # Go straight to Playwright to avoid captcha issues
    html = await _fetch_with_playwright_async(url)
    if not html:
        # Fallback to requests
        html = await asyncio.to_thread(_fetch_with_requests, url)
    titles = _parse_titles_from_html(html) if html else []
    return filter_movie_titles(titles)
