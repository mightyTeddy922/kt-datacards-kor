"""
Step 1: Scrape Kill Team PDFs from Warhammer Community downloads page.
Uses Playwright to render JavaScript and extract PDF links from collapsible sections.
"""

import requests
import os
from pathlib import Path
import argparse
import time
import asyncio
import logging
from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)

DEFAULT_LOCALE = 'en-gb'
SEARCH_API_URL = 'https://www.warhammer-community.com/api/search/'
SEARCH_API_INDEX = 'downloads_v2_date_desc'
DOWNLOADS_URLS = {
    'en-gb': 'https://www.warhammer-community.com/en-gb/downloads/kill-team/',
    'de-de': 'https://www.warhammer-community.com/de-de/downloads/kill-team/',
    'fr-fr': 'https://www.warhammer-community.com/fr-fr/downloads/kill-team/',
    'it-it': 'https://www.warhammer-community.com/it-it/downloads/kill-team/',
    'es-es': 'https://www.warhammer-community.com/es-es/downloads/kill-team/',
    'ja-jp': 'https://www.warhammer-community.com/ja-jp/downloads/kill-team/',
    # Kill Team downloads stay on the en-gb page and swap PDFs via the in-page language filter.
    'ko-kr': 'https://www.warhammer-community.com/en-gb/downloads/kill-team/',
}

SECTION_LABELS = {
    'Team Rules': {
        'en-gb': ['Team Rules'],
        'de-de': ['Team-Regeln', 'Team Rules'],
        'fr-fr': ["Règles d'équipe", 'Team Rules'],
        'it-it': ['Regole della squadra', 'Team Rules'],
        'es-es': ['Reglas de comando', 'Team Rules'],
        'ja-jp': ['チームルール', 'Team Rules'],
        'ko-kr': ['팀 규칙', 'Team Rules'],
    },
    'Recently Added': {
        'en-gb': ['Recently Added'],
        'de-de': ['Neueste Regelupdates', 'Recently Added'],
        'fr-fr': ['Ajouts récents', 'Recently Added'],
        'it-it': ['Aggiunti di recente', 'Recently Added'],
        'es-es': ['Añadidos recientemente', 'Recently Added'],
        'ja-jp': ['最近追加されたコンテンツ', 'Recently Added'],
        'ko-kr': ['최신 규칙 업데이트', 'Recently Added'],
    },
}

DOWNLOAD_LANGUAGE_LABELS = {
    'en-gb': ['English'],
    'de-de': ['Deutsch', 'German'],
    'fr-fr': ['Français', 'French'],
    'it-it': ['Italiano', 'Italian'],
    'es-es': ['Español', 'Spanish'],
    'ja-jp': ['日本語', 'Japanese'],
    'ko-kr': ['한국어', 'Korean'],
}

DOWNLOAD_LANGUAGE_QUERY_LABELS = {
    'en-gb': 'english',
    'de-de': 'german',
    'fr-fr': 'french',
    'it-it': 'italian',
    'es-es': 'spanish',
    'ja-jp': 'japanese',
    'ko-kr': 'korean',
}

LOCALE_FILENAME_PREFIXES = {
    'en-gb': ('eng_',),
    'de-de': ('deu_', 'ger_'),
    'fr-fr': ('fra_', 'fre_'),
    'it-it': ('ita_',),
    'es-es': ('spa_', 'esp_'),
    'ja-jp': ('jpn_', 'jap_'),
    'ko-kr': ('kor_', 'korean_'),
}

EXCLUDE_PATTERNS = [
    'key_download', 'key-download',
    'mission_pack', 'missionpack', 'mission-pack',
    'mission pack',
    'ctesiphus_expedition', 'ctesiphus-expedition',
    'core_rules', 'core-rules',
    'update_log', 'update-log',
    'universal_equipment', 'universal-equipment',
    'lite_rules', 'lite-rules',
    'sniper_rules', 'sniper-rules',
    'key rule', 'critical operation',
    'gallowdark', 'into the dark',
    'shadowvaults', 'chalnath', 'octarius',
]

LOCAL_BROWSER_CANDIDATES = [
    Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
    Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
    Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
    Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
]


def _locale_url(locale: str) -> str:
    return DOWNLOADS_URLS.get(locale, DOWNLOADS_URLS[DEFAULT_LOCALE])


def _locale_labels(section: str, locale: str) -> list[str]:
    labels = SECTION_LABELS.get(section, {}).get(locale, [])
    return labels or [section]


def _filter_locale_pdfs(urls: list[str], locale: str) -> list[str]:
    urls = list(dict.fromkeys(urls))
    prefixes = LOCALE_FILENAME_PREFIXES.get(locale, ())
    if not prefixes:
        return urls
    preferred = [url for url in urls if Path(url).name.lower().startswith(prefixes)]
    return preferred or urls


def _matches_section(filename: str, section: str) -> bool:
    lower = filename.lower()
    if section == 'Team Rules':
        return (
            'team_rules' in lower
            or 'teamrules' in lower
            or '_online_rules' in lower
        )
    return True


def _build_asset_url(file_path: str) -> str:
    if file_path.startswith('http://') or file_path.startswith('https://'):
        return file_path
    return f"https://assets.warhammer-community.com/{file_path.lstrip('/')}"


def extract_pdf_urls_from_api(
    section: str = 'Team Rules',
    locale: str = DEFAULT_LOCALE,
) -> list[str]:
    """Extract PDF URLs via Warhammer Community's downloads search API."""
    requested_locale = (locale or DEFAULT_LOCALE).lower()
    language_label = DOWNLOAD_LANGUAGE_QUERY_LABELS.get(requested_locale)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json',
        'Content-Type': 'application/json',
    }

    page = 0
    nb_pages = None
    team_pdfs: list[str] = []

    while nb_pages is None or page < nb_pages:
        payload = {
            'index': SEARCH_API_INDEX,
            'searchTerm': 'kill team',
            'page': page,
            'locale': DEFAULT_LOCALE,
        }
        response = requests.post(
            SEARCH_API_URL,
            json=payload,
            headers=headers,
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()
        nb_pages = data.get('nbPages', 0)

        for hit in data.get('hits', []):
            hit_language = str(hit.get('download_languages') or '').lower()
            if language_label and hit_language != language_label:
                continue

            if 'kill-team' not in str(hit.get('game_systems') or ''):
                continue

            filename = str(hit.get('id', {}).get('file') or '')
            if not filename or not _matches_section(filename, section):
                continue

            filename_lower = filename.lower()
            if any(pattern in filename_lower for pattern in EXCLUDE_PATTERNS):
                continue

            team_pdfs.append(_build_asset_url(filename))

        page += 1

    team_pdfs = _filter_locale_pdfs(team_pdfs, requested_locale)
    logger.info(
        f"Search API returned {len(team_pdfs)} PDFs in section '{section}' for locale '{requested_locale}'"
    )
    return team_pdfs


def _resolve_browser_executable() -> str | None:
    env_browser = os.environ.get("KT_WARCOM_BROWSER")
    if env_browser and Path(env_browser).exists():
        return env_browser

    for candidate in LOCAL_BROWSER_CANDIDATES:
        if candidate.exists():
            return str(candidate)

    return None


async def _expand_section(page, headings: list[str]):
    for heading in headings:
        selectors_to_try = [
            f'h2:has-text("{heading}")',
            f'h3:has-text("{heading}")',
            f'h4:has-text("{heading}")',
            f'button:has-text("{heading}")',
            f'summary:has-text("{heading}")',
            f'[aria-label*="{heading}"]',
        ]

        for selector in selectors_to_try:
            try:
                elem = page.locator(selector).first
                if await elem.count() == 0:
                    continue

                logger.info(f"Found section '{heading}' with: {selector}")

                toggle = elem.locator('xpath=ancestor-or-self::button[1]').first
                if await toggle.count() == 0:
                    toggle = elem

                aria_expanded = await toggle.get_attribute('aria-expanded')
                if aria_expanded == 'false':
                    logger.info(f"Expanding section '{heading}'...")
                    await toggle.click(timeout=3000)
                    await page.wait_for_timeout(2000)

                container = elem.locator("xpath=ancestor::div[contains(@class,'border-b')][1]").first
                if await container.count() > 0:
                    return container

                container = elem.locator(
                    "xpath=ancestor::div[contains(@class, 'accordion')][1] | ancestor::details[1]"
                ).first
                if await container.count() > 0:
                    return container

                sibling = elem.locator('xpath=following-sibling::*[1]').first
                if await sibling.count() > 0:
                    return sibling
            except Exception:
                continue

    return None


async def _switch_download_language(page, locale: str) -> bool:
    labels = DOWNLOAD_LANGUAGE_LABELS.get(locale, [])
    if not labels or locale == DEFAULT_LOCALE:
        return True

    container = page.locator('.downloads-languageFilter').first
    if await container.count() == 0:
        logger.warning("Downloads language filter not found")
        return False

    trigger = container.locator('button').first
    if await trigger.count() == 0:
        logger.warning("Downloads language filter trigger not found")
        return False

    trigger_text = ((await trigger.inner_text()) or '').strip()
    if any(label.lower() == trigger_text.lower() for label in labels):
        logger.info(f"Downloads language already set to {trigger_text}")
        return True

    logger.info(f"Switching downloads language to locale '{locale}'")
    await trigger.click(timeout=5000)
    await page.wait_for_timeout(750)

    for label in labels:
        option = container.locator(f'button:has-text(\"{label}\")').last
        if await option.count() == 0:
            continue
        await option.click(timeout=5000)
        await page.wait_for_timeout(2500)
        return True

    logger.warning(f"Could not find downloads language option for locale '{locale}'")
    return False


async def extract_pdf_urls_from_page(
    url: str | None = None,
    section: str = 'Team Rules',
    locale: str = DEFAULT_LOCALE,
) -> list[str]:
    """
    Extract PDF URLs from the Warhammer Community Kill Team page.
    Uses Playwright to render JavaScript and expand collapsible sections.
    """
    requested_locale = (locale or DEFAULT_LOCALE).lower()
    primary_url = url or _locale_url(requested_locale)
    fallback_url = _locale_url(DEFAULT_LOCALE)
    labels = _locale_labels(section, requested_locale)

    logger.info("Launching browser to fetch Kill Team downloads page...")

    async with async_playwright() as p:
        executable_path = _resolve_browser_executable()
        launch_kwargs = {"headless": True}
        if executable_path:
            logger.info(f"Using local browser executable: {executable_path}")
            launch_kwargs["executable_path"] = executable_path
        else:
            logger.info("Using Playwright-managed Chromium")

        browser = await p.chromium.launch(**launch_kwargs)
        try:
            team_pdfs = []
            pages_to_try = [primary_url]
            if primary_url != fallback_url:
                pages_to_try.append(fallback_url)

            for current_url in pages_to_try:
                page = await browser.new_page()
                try:
                    logger.info(f"Loading page: {current_url}")
                    response = await page.goto(current_url, wait_until='networkidle')
                    if response and response.status >= 400:
                        logger.warning(f"Skipping {current_url}: HTTP {response.status}")
                        continue

                    await page.wait_for_timeout(2000)

                    try:
                        await page.evaluate("document.getElementById('onetrust-consent-sdk')?.remove()")
                        await page.wait_for_timeout(500)
                    except Exception:
                        pass

                    await _switch_download_language(page, requested_locale)

                    container = await _expand_section(page, labels)

                    if container is not None:
                        logger.info(f"Extracting PDFs from '{section}' section...")
                        pdf_links = await container.locator('a[href*=".pdf"]').all()

                        for link in pdf_links:
                            href = await link.get_attribute('href')
                            text = (await link.inner_text()) or ''
                            if not href:
                                continue

                            if href.startswith('http'):
                                full_url = href
                            elif href.startswith('/'):
                                full_url = f"https://www.warhammer-community.com{href}"
                            else:
                                full_url = f"https://assets.warhammer-community.com/{href}"

                            filename = Path(full_url).name.lower()
                            text_lower = text.lower()
                            if not any(pattern in filename or pattern in text_lower for pattern in EXCLUDE_PATTERNS):
                                team_pdfs.append(full_url)
                    elif section == 'Team Rules':
                        logger.warning("Could not locate Team Rules container, falling back to filename filtering...")
                        pdf_links = await page.locator('a[href*=".pdf"]').all()
                        for link in pdf_links:
                            href = await link.get_attribute('href')
                            text = (await link.inner_text()) or ''
                            if not href:
                                continue

                            if href.startswith('http'):
                                full_url = href
                            elif href.startswith('/'):
                                full_url = f"https://www.warhammer-community.com{href}"
                            else:
                                full_url = f"https://assets.warhammer-community.com/{href}"

                            filename = Path(full_url).name.lower()
                            text_lower = text.lower()
                            is_team_rules = (
                                'team_rules' in filename
                                or 'teamrules' in filename
                                or '_online_rules' in filename
                            )
                            if is_team_rules and not any(
                                pattern in filename or pattern in text_lower for pattern in EXCLUDE_PATTERNS
                            ):
                                team_pdfs.append(full_url)
                    else:
                        logger.warning(f"'{section}' section not found on {current_url}")

                    team_pdfs = _filter_locale_pdfs(team_pdfs, requested_locale)
                    if team_pdfs:
                        break
                finally:
                    await page.close()

            team_pdfs = list(dict.fromkeys(team_pdfs))
            logger.info(
                f"Found {len(team_pdfs)} PDFs in section '{section}' for locale '{requested_locale}'"
            )
            return team_pdfs
        finally:
            await browser.close()


def download_pdf(url: str, output_path: Path, chunk_size: int = 8192) -> bool:
    """Download a PDF file."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, stream=True, timeout=60)
        response.raise_for_status()
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)
        
        return True
    except Exception as e:
        logger.error(f"    x Error: {e}")
        return False


def run(
    output_dir: Path = None,
    url: str = None,
    delay: float = 1.0,
    locale: str = DEFAULT_LOCALE,
) -> dict:
    """
    Main function to scrape and download Kill Team PDFs.
    
    Args:
        output_dir: Directory to save PDFs (default: layers/warcom/staging/)
        url: Warhammer Community downloads page URL
        delay: Delay between downloads in seconds
        
    Returns:
        dict with 'success', 'downloaded', 'skipped', 'failed' counts
    """
    if output_dir is None:
        output_dir = Path('layers/warcom/staging')
    
    requested_locale = (locale or DEFAULT_LOCALE).lower()
    if url is None:
        url = _locale_url(requested_locale)
    
    logger.info("=" * 70)
    logger.info("Step 1: Scrape Warhammer Community Kill Team Downloads")
    logger.info("=" * 70)
    logger.info("")
    
    # Prefer the official search API; fall back to Playwright page scraping if needed.
    try:
        team_pdf_urls = extract_pdf_urls_from_api(
            section='Team Rules',
            locale=requested_locale,
        )
    except Exception as e:
        logger.warning(f"Search API extraction failed: {e}")
        team_pdf_urls = []

    if not team_pdf_urls:
        logger.info("Falling back to Playwright page scraping...")
        try:
            team_pdf_urls = asyncio.run(
                extract_pdf_urls_from_page(
                    url=url,
                    section='Team Rules',
                    locale=requested_locale,
                )
            )
        except Exception as e:
            logger.error(f"Error extracting PDF URLs: {e}")
            import traceback
            traceback.print_exc()
            return {'success': False, 'downloaded': 0, 'skipped': 0, 'failed': 0}
    
    if not team_pdf_urls:
        logger.error("No team PDFs found!")
        return {'success': False, 'downloaded': 0, 'skipped': 0, 'failed': 0}
    
    logger.info("")
    logger.info(f"Output: {output_dir}")
    logger.info(f"Downloading {len(team_pdf_urls)} PDFs:")
    logger.info("-" * 70)
    
    # Download each PDF
    downloaded_count = 0
    skipped_count = 0
    failed_count = 0
    
    for idx, pdf_url in enumerate(team_pdf_urls, 1):
        # Extract filename from URL
        filename = Path(pdf_url).name
        output_path = output_dir / filename
        
        # Skip if already exists
        if output_path.exists():
            logger.info(f"  [{idx}/{len(team_pdf_urls)}] {filename}")
            logger.info(f"    * Already exists, skipping")
            skipped_count += 1
            continue
        
        logger.info(f"  [{idx}/{len(team_pdf_urls)}] {filename}")
        logger.info(f"    Downloading...")
        
        if download_pdf(pdf_url, output_path):
            file_size_mb = output_path.stat().st_size / (1024 * 1024)
            logger.info(f"    + Downloaded: {file_size_mb:.2f} MB")
            downloaded_count += 1
        else:
            logger.error(f"    x Failed to download")
            failed_count += 1
        
        # Delay between downloads to be respectful
        if idx < len(team_pdf_urls):
            time.sleep(delay)
    
    logger.info("")
    logger.info("=" * 70)
    logger.info(f"Download complete!")
    logger.info(f"  Downloaded: {downloaded_count}")
    logger.info(f"  Skipped: {skipped_count}")
    logger.info(f"  Failed: {failed_count}")
    logger.info(f"  Output: {output_dir}")
    logger.info("=" * 70)
    
    return {
        'success': failed_count == 0,
        'downloaded': downloaded_count,
        'skipped': skipped_count,
        'failed': failed_count
    }


def main():
    parser = argparse.ArgumentParser(
        description='Step 1: Scrape and download Kill Team PDFs from Warhammer Community'
    )
    parser.add_argument('--url', type=str,
                       default='https://www.warhammer-community.com/en-gb/downloads/kill-team/',
                       help='Kill Team downloads page URL')
    parser.add_argument('--output', type=Path, default=Path('layers/warcom/staging'),
                       help='Output directory (default: layers/warcom/staging)')
    parser.add_argument('--delay', type=float, default=1.0,
                       help='Delay between downloads in seconds (default: 1.0)')
    parser.add_argument('--locale', type=str, default=DEFAULT_LOCALE,
                       help='Warhammer Community locale to prefer (default: en-gb)')
    
    args = parser.parse_args()
    
    result = run(output_dir=args.output, url=args.url, delay=args.delay, locale=args.locale)
    
    # Exit with error code if failed
    if not result['success']:
        exit(1)


if __name__ == '__main__':
    main()
