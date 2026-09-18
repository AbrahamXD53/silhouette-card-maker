"""Palworld TCG decks from palworldtcg.gg, a community deck builder.

The site has no deck API: a shared deck page (`/deck/<share id>`) is rendered
by Next.js, and the deck travels in the page's React Server Components stream as
`{"main": [...], "soul": [...], "maybe": [...], "art": {...}}`, where each entry
is `{"slug", "count"}` and `art` maps a card to the printing chosen for it.
Card images are `/img/card-thumbnails/<slug>.webp` (400x559, the same size as
the official images).
"""
import json
import os
import re
from time import sleep
from typing import Dict, List, Tuple

import requests

from utilities import guess_extension

SITE = 'https://palworldtcg.gg'
DECK_PAGE = SITE + '/deck/{deck_id}'
IMAGE_URL = SITE + '/img/card-thumbnails/{slug}.webp'

HEADERS = {'user-agent': 'silhouette-card-maker/0.1'}

DECK_URL_PATTERN = re.compile(r'palworldtcg\.gg/(?:[a-z]{2}/)?deck/([0-9a-f]{6,})', re.IGNORECASE)
BARE_ID_PATTERN = re.compile(r'^\s*([0-9a-f]{6,})\s*$', re.IGNORECASE)
PUSH_PATTERN = re.compile(r'self\.__next_f\.push\(\[1,"(.*?)"\]\)</script>', re.S)

def extract_deck_id(value: str) -> str:
    value = value or ''
    match = DECK_URL_PATTERN.search(value) or BARE_ID_PATTERN.match(value)
    if not match:
        raise ValueError(f'No Palworld TCG deck found in "{value.strip()}". Expected a link like '
                         'https://palworldtcg.gg/deck/6a5f62a083')
    return match.group(1).lower()

def rsc_rows(html: str) -> Dict[str, object]:
    """Parse the flight stream into its JSON rows.

    Rows are "<id>:<json>\\n", except text rows, "<id>:T<hex byte length>,<text>",
    which have no newline after them, so they are skipped by length.
    """
    data = ''.join(json.loads('"' + chunk + '"') for chunk in PUSH_PATTERN.findall(html)).encode('utf-8')
    rows, position, size = {}, 0, len(data)
    while position < size:
        colon = data.find(b':', position)
        if colon < 0:
            break
        key = data[position:colon].decode('ascii', 'replace').strip()
        position = colon + 1
        if data[position:position + 1] == b'T':
            comma = data.find(b',', position)
            position = comma + 1 + int(data[position + 1:comma], 16)
            continue
        end = data.find(b'\n', position)
        end = size if end < 0 else end
        text = data[position:end].decode('utf-8', 'replace')
        position = end + 1
        if text[:1] in '{[':
            try:
                rows[key] = json.loads(text)
            except ValueError:
                pass
    return rows

def resolve(value, rows: dict, depth: int = 0):
    """Follow "$<id>" references between rows."""
    if depth > 30:
        return value
    if isinstance(value, str) and value.startswith('$') and value[1:] in rows:
        return resolve(rows[value[1:]], rows, depth + 1)
    if isinstance(value, list):
        return [resolve(item, rows, depth + 1) for item in value]
    if isinstance(value, dict):
        return {key: resolve(item, rows, depth + 1) for key, item in value.items()}
    return value

def get_deck(deck_id: str) -> dict:
    response = requests.get(DECK_PAGE.format(deck_id=deck_id), headers=HEADERS, timeout=30)
    if response.status_code == 404:
        raise ValueError(f'Deck {deck_id} was not found, or it is private.')
    response.raise_for_status()

    rows = rsc_rows(response.text)
    for row in rows.values():
        if isinstance(row, dict) and 'main' in row and 'soul' in row:
            deck = resolve(row, rows)
            if isinstance(deck.get('main'), list):
                title = re.search(r'<title>(.*?)</title>', response.text, re.S)
                deck['title'] = title.group(1).split(' · ')[0].strip() if title else ''
                return deck
    raise ValueError(f'Deck {deck_id} was not found, or it is private.')

def entries(section) -> List[Tuple[str, int]]:
    return [(entry['slug'], int(entry.get('count') or 0))
            for entry in section or [] if isinstance(entry, dict) and entry.get('slug')]

def display_name(slug: str) -> str:
    # "bp01-028-pengullet-yearning-for-the-sky" -> "Pengullet Yearning For The Sky"
    words = [w for w in slug.split('-') if not re.fullmatch(r'(?:[a-z]{1,4}\d+|\d+|osr|ssp|sp|sr|tsp|ur|r|rr|u|c)', w)]
    return ' '.join(words).title() or slug

def fetch_card(index: int, quantity: int, slug: str, art: dict, front_img_dir: str) -> str:
    printing = art.get(slug, slug) if isinstance(art, dict) else slug
    response = requests.get(IMAGE_URL.format(slug=printing), headers=HEADERS, timeout=60)
    if response.status_code != 200 and printing != slug:
        printing = slug
        response = requests.get(IMAGE_URL.format(slug=slug), headers=HEADERS, timeout=60)
    if response.status_code != 200 or not response.headers.get('content-type', '').startswith('image'):
        raise ValueError(f'No image for {slug}')
    sleep(0.05)

    data = response.content
    extension = guess_extension(data, '.webp')
    stem = f'{index}{re.sub(r"[^A-Za-z0-9]", "", display_name(slug)) or index}'
    for counter in range(quantity):
        with open(os.path.join(front_img_dir, f'{stem}{counter + 1}{extension}'), 'wb') as f:
            f.write(data)
    return printing
