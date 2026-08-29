"""Scrape + download Kill Team team-rules PDFs from warhammer-community."""
from __future__ import annotations

import logging
import os
from pathlib import Path
import re
import shutil

import requests
from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)

DOWNLOADS_URL = "https://www.warhammer-community.com/en-gb/downloads/kill-team/"
DEFAULT_LOCALE = "en-gb"
SEARCH_API_URL = "https://www.warhammer-community.com/api/search/"
SEARCH_API_INDEX = "downloads_v2_date_desc"

# Files that live in the Team Rules section but are not a single team's rules.
_EXCLUDE_PATTERNS = (
    "key_download", "key-download",
    "mission_pack", "missionpack", "mission-pack", "mission pack",
    "ctesiphus_expedition", "ctesiphus-expedition",
    "core_rules", "core-rules",
    "update_log", "update-log",
    "universal_equipment", "universal-equipment",
    "lite_rules", "lite-rules",
    "sniper_rules", "sniper-rules",
    "key rule", "critical operation",
    "gallowdark", "into the dark",
    "shadowvaults", "chalnath", "octarius",
)

DOWNLOAD_LANGUAGE_QUERY_LABELS = {
    "en-gb": "english",
    "de-de": "german",
    "fr-fr": "french",
    "it-it": "italian",
    "es-es": "spanish",
    "ja-jp": "japanese",
    "ko-kr": "korean",
}

LOCALE_FILENAME_PREFIXES = {
    "en-gb": ("eng_",),
    "de-de": ("deu_", "ger_"),
    "fr-fr": ("fra_", "fre_"),
    "it-it": ("ita_",),
    "es-es": ("spa_", "esp_"),
    "ja-jp": ("jpn_", "jap_"),
    "ko-kr": ("kor_", "korean_"),
}


def _absolute_url(href: str) -> str:
    if href.startswith("http"):
        return href
    if href.startswith("/"):
        return f"https://www.warhammer-community.com{href}"
    return f"https://assets.warhammer-community.com/{href}"


def _is_team_rules_file(filename: str, link_text: str) -> bool:
    filename = filename.lower()
    link_text = link_text.lower()
    return not any(p in filename or p in link_text for p in _EXCLUDE_PATTERNS)


def _current_locale() -> str:
    return (os.environ.get("KT_WARCOM_LOCALE") or DEFAULT_LOCALE).strip().lower()


def _matches_section(filename: str, section: str) -> bool:
    lower = filename.lower()
    if section == "Team Rules":
        return "team_rules" in lower or "teamrules" in lower or "_online_rules" in lower
    return True


def _infer_team_slug_from_filename(filename: str) -> str:
    stem = Path(filename).stem.lower().replace("_", "-")
    stem = re.sub(r"^(?:kor|eng|deu|ger|fra|fre|ita|spa|esp|jpn|jap|korean)-", "", stem)
    stem = re.sub(r"^\d{2}-\d{2}-", "", stem)
    stem = re.sub(r"^kill-team-team-rules-", "", stem)
    stem = re.sub(r"^kt-teamrules-", "", stem)
    stem = re.sub(r"^kt-", "", stem)
    stem = re.sub(r"^kill-team-", "", stem)
    stem = re.sub(r"^killteam-", "", stem)
    stem = re.sub(r"^team-rules-", "", stem)
    stem = re.sub(r"-(?:[a-z0-9]{10})-(?:[a-z0-9]{10})$", "", stem)
    stem = re.sub(r"-team-rules$", "", stem)
    stem = re.sub(r"-teamrules$", "", stem)
    stem = re.sub(r"-online-rules$", "", stem)
    return stem.strip("-")


def _detect_asset_locale(filename: str) -> str:
    lower = filename.lower()
    for locale, prefixes in LOCALE_FILENAME_PREFIXES.items():
        if lower.startswith(prefixes):
            return locale
    return DEFAULT_LOCALE


def _asset_priority(url: str, requested_locale: str) -> tuple[int, int, int, str]:
    filename = Path(url).name.lower()
    asset_locale = _detect_asset_locale(filename)
    is_team_rules = "team_rules" in filename or "teamrules" in filename
    is_online_rules = "_online_rules" in filename or "-online-rules" in filename
    locale_score = 2 if asset_locale == requested_locale else 1 if asset_locale == DEFAULT_LOCALE else 0
    completeness_score = 2 if is_team_rules else 1 if is_online_rules else 0
    fallback_bonus = 1 if asset_locale == DEFAULT_LOCALE and is_team_rules else 0
    return (completeness_score, locale_score, fallback_bonus, filename)


def _select_best_team_assets(urls: list[str], requested_locale: str) -> list[str]:
    grouped: dict[str, list[str]] = {}
    for url in list(dict.fromkeys(urls)):
        team_slug = _infer_team_slug_from_filename(Path(url).name)
        if not team_slug:
            continue
        grouped.setdefault(team_slug, []).append(url)

    selected: list[str] = []
    for team_slug in sorted(grouped):
        candidates = grouped[team_slug]
        best = sorted(candidates, key=lambda candidate: _asset_priority(candidate, requested_locale), reverse=True)[0]
        selected.append(best)
    return selected


def _is_online_rules_filename(filename: str) -> bool:
    lower = filename.lower()
    return "_online_rules" in lower or "-online-rules" in lower


def _is_full_team_rules_filename(filename: str) -> bool:
    lower = filename.lower()
    return ("team_rules" in lower or "teamrules" in lower) and not _is_online_rules_filename(lower)


def _archive_roots() -> list[Path]:
    value = (os.environ.get("KT_WARCOM_ARCHIVE_ROOTS") or "").strip()
    if not value:
        return []
    roots: list[Path] = []
    for raw in value.split(os.pathsep):
        raw = raw.strip()
        if not raw:
            continue
        roots.append(Path(raw))
    return roots


def _pdf_page_count(pdf: Path) -> int:
    try:
        import fitz  # type: ignore

        with fitz.open(pdf) as doc:
            return len(doc)
    except Exception:
        return 0


def _find_archived_full_pdf(team_slug: str) -> Path | None:
    """Return the best archived English PDF when WarCom only exposes a locale stub."""
    best_candidate: Path | None = None
    best_score: tuple[int, int, int, str] | None = None

    for archive_root in _archive_roots():
        team_archive_dir = archive_root / team_slug / "warcom"
        if not team_archive_dir.exists():
            continue

        for candidate in sorted(team_archive_dir.glob("*.pdf")):
            if _detect_asset_locale(candidate.name) != DEFAULT_LOCALE:
                continue
            page_count = _pdf_page_count(candidate)
            score = (
                1 if page_count > 2 else 0,
                1 if _is_full_team_rules_filename(candidate.name) else 0,
                page_count,
                str(candidate),
            )
            if best_score is None or score > best_score:
                best_candidate = candidate
                best_score = score

    if best_candidate is not None and best_score is not None and best_score[0] == 1:
        return best_candidate
    return None


def maybe_restore_archived_full_pdf(output_dir: Path, source_url: str) -> Path | None:
    """Copy an archived English full-rules PDF into staging for online-rules-only teams."""
    filename = Path(source_url).name
    if not _is_online_rules_filename(filename):
        return None

    team_slug = _infer_team_slug_from_filename(filename)
    if not team_slug:
        return None

    archived_full_pdf = _find_archived_full_pdf(team_slug)
    if archived_full_pdf is None:
        return None

    restored_path = output_dir / archived_full_pdf.name
    output_dir.mkdir(parents=True, exist_ok=True)
    if restored_path.exists():
        restored_path.unlink()
    shutil.copy2(archived_full_pdf, restored_path)
    logger.info(
        "  restored archived full team rules for %s: %s",
        team_slug,
        archived_full_pdf.name,
    )
    return restored_path


def should_skip_incomplete_online_rules_pdf(pdf_path: Path, source_url: str) -> bool:
    """Skip locale-only online-rules stubs when no archived full-rules fallback exists."""
    filename = Path(source_url).name
    if not _is_online_rules_filename(filename):
        return False

    team_slug = _infer_team_slug_from_filename(filename)
    if not team_slug:
        return False
    if _find_archived_full_pdf(team_slug) is not None:
        return False

    return _pdf_page_count(pdf_path) <= 2


def _build_asset_url(file_path: str) -> str:
    if file_path.startswith("http://") or file_path.startswith("https://"):
        return file_path
    return f"https://assets.warhammer-community.com/{file_path.lstrip('/')}"


def extract_pdf_urls_from_api(section: str = "Team Rules", locale: str | None = None) -> list[str]:
    requested_locale = (locale or _current_locale() or DEFAULT_LOCALE).lower()
    locales_to_collect = [requested_locale]
    if requested_locale != DEFAULT_LOCALE:
        locales_to_collect.append(DEFAULT_LOCALE)

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    team_pdfs: list[str] = []
    for source_locale in locales_to_collect:
        language_label = DOWNLOAD_LANGUAGE_QUERY_LABELS.get(source_locale)
        page = 0
        nb_pages = None

        while nb_pages is None or page < nb_pages:
            payload = {
                "index": SEARCH_API_INDEX,
                "searchTerm": "kill team",
                "page": page,
                "locale": DEFAULT_LOCALE,
            }
            response = requests.post(SEARCH_API_URL, json=payload, headers=headers, timeout=60)
            response.raise_for_status()
            data = response.json()
            nb_pages = data.get("nbPages", 0)

            for hit in data.get("hits", []):
                hit_language = str(hit.get("download_languages") or "").lower()
                if language_label and hit_language != language_label:
                    continue
                if "kill-team" not in str(hit.get("game_systems") or ""):
                    continue

                filename = str(hit.get("id", {}).get("file") or "")
                if not filename or not _matches_section(filename, section):
                    continue
                if not _is_team_rules_file(filename, ""):
                    continue

                team_pdfs.append(_build_asset_url(filename))
            page += 1

    team_pdfs = _select_best_team_assets(team_pdfs, requested_locale)
    logger.info(
        f"Search API returned {len(team_pdfs)} best-match PDFs in section '{section}' for locale '{requested_locale}'"
    )
    return team_pdfs


async def _expand_section(page, heading: str) -> object | None:
    """Find + expand a named download section and return its container locator.

    ``heading`` is the section title as shown on the page (e.g. ``"Team Rules"``
    or ``"Recently Added"``); matching is case-insensitive substring.
    """
    selectors = [
        f'h2:has-text("{heading}")',
        f'h3:has-text("{heading}")',
        f'h4:has-text("{heading}")',
        f'button:has-text("{heading}")',
        f'summary:has-text("{heading}")',
        f'[aria-label*="{heading}"]',
    ]
    for selector in selectors:
        try:
            elem = page.locator(selector).first
            if await elem.count() == 0:
                continue
            logger.info(f"Found '{heading}' section with: {selector}")
            # The accordion toggle is the heading's enclosing button; expand if collapsed.
            toggle = elem.locator("xpath=ancestor-or-self::button[1]").first
            toggle = toggle if await toggle.count() > 0 else elem
            if await toggle.get_attribute("aria-expanded") == "false":
                await toggle.click(timeout=3000)
                await page.wait_for_timeout(2000)
            # This section's links live in its OWN accordion item (nearest ancestor
            # div with the item border class), NOT the outer <section> that wraps
            # every accordion (which would mix Recently Added + Team Rules + …).
            container = elem.locator(
                "xpath=ancestor::div[contains(@class,'border-b')][1]"
            ).first
            if await container.count() > 0:
                return container
            container = elem.locator(
                "xpath=ancestor::div[contains(@class, 'accordion')][1] | ancestor::details[1]"
            ).first
            if await container.count() > 0:
                return container
            sibling = elem.locator("xpath=following-sibling::*[1]").first
            if await sibling.count() > 0:
                return sibling
        except Exception:
            continue
    return None


async def extract_pdf_urls_from_page(
    url: str = DOWNLOADS_URL, section: str = "Team Rules", locale: str | None = None
) -> list[str]:
    """Return team-rules PDF URLs from a named section of the Kill Team downloads page.

    ``section`` selects which page accordion to read: the default ``"Team Rules"``
    (all teams) or ``"Recently Added"`` (only the PDFs updated in the latest
    balance dataslate / release). Non-team files (update logs, mission packs,
    companions, …) are filtered out of either section by ``_is_team_rules_file``.
    """
    requested_locale = (locale or _current_locale() or DEFAULT_LOCALE).lower()
    logger.info("Launching browser to fetch Kill Team downloads page...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            logger.info(f"Loading page: {url}")
            await page.goto(url, wait_until="networkidle")
            await page.wait_for_timeout(2000)

            # Dismiss cookie consent overlay if present.
            try:
                await page.evaluate(
                    "document.getElementById('onetrust-consent-sdk')?.remove()"
                )
                await page.wait_for_timeout(500)
            except Exception:
                pass

            container = await _expand_section(page, section)

            team_pdfs: list[str] = []
            if container is not None:
                for link in await container.locator('a[href*=".pdf"]').all():
                    href = await link.get_attribute("href")
                    text = (await link.inner_text()) or ""
                    if not href:
                        continue
                    full_url = _absolute_url(href)
                    if _is_team_rules_file(Path(full_url).name, text):
                        team_pdfs.append(full_url)
            elif section == "Team Rules":
                logger.warning(
                    "Team Rules container not found; falling back to filename filter"
                )
                for link in await page.locator('a[href*=".pdf"]').all():
                    href = await link.get_attribute("href")
                    if not href:
                        continue
                    full_url = _absolute_url(href)
                    name = Path(full_url).name.lower()
                    if ("team_rules" in name or "teamrules" in name or "_online_rules" in name) \
                            and _is_team_rules_file(name, ""):
                        team_pdfs.append(full_url)
            else:
                logger.warning(
                    f"'{section}' section not found; no reliable filename fallback"
                )
        finally:
            await browser.close()

    team_pdfs = _select_best_team_assets(list(dict.fromkeys(team_pdfs)), requested_locale)
    logger.info(f"Found {len(team_pdfs)} PDFs in section '{section}' for locale '{requested_locale}'")
    return team_pdfs


def extract_pdf_urls(url: str = DOWNLOADS_URL, section: str = "Team Rules", locale: str | None = None) -> list[str]:
    requested_locale = (locale or _current_locale() or DEFAULT_LOCALE).lower()
    try:
        return extract_pdf_urls_from_api(section=section, locale=requested_locale)
    except Exception as exc:
        logger.warning(f"Search API scrape failed, falling back to page scrape: {exc}")
        return asyncio.run(extract_pdf_urls_from_page(url=url, section=section, locale=requested_locale))


def download_pdf(url: str, output_path: Path, chunk_size: int = 8192) -> bool:
    """Download a PDF to ``output_path``. Returns True on success."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        response = requests.get(url, headers=headers, stream=True, timeout=60)
        response.raise_for_status()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)
        return True
    except Exception as e:
        logger.error(f"  download failed: {e}")
        return False
