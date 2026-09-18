"""Decks and card data from universus.cards, the community deck builder."""
import json
import re
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Optional
from urllib.parse import urljoin

import requests

BASE_URL = 'https://universus.cards/'
DECK_API = BASE_URL + 'deck/{deck_id}'
IMAGE_URL = BASE_URL + 'cards/{path}'

HEADERS = {'user-agent': 'silhouette-card-maker/0.1', 'accept': 'application/json, */*'}

DECK_ID_PATTERN = re.compile(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', re.IGNORECASE)

# The site ships its whole card database inside one JavaScript chunk whose
# filename changes on every deploy, as object literals like:
#   {id:10943,image:"aot01/017.webp",name:"Reiner Braun",type:"Character",
#    rarity:"Rare",set:"Attack on Titan: Battle for Humanity",number:17,...,
#    back:{image:"sleb/004B.webp",name:"...",...},...}
DATABASE_SIGNATURE = re.compile(r'\{id:\d+,image:"[a-z0-9]+/[^"]+\.webp",name:')
IMPORT_PATTERN = re.compile(r'''(?:from\s*|import\s*\(\s*|import\s*)["'`](\.{1,2}/[^"'`]+\.js)["'`]''')
ENTRY_PATTERN = re.compile(r'''import\(\s*["']([^"']+\.js)["']\s*\)''')
MAX_SCRIPTS = 400

# A JavaScript string literal in any of its three quote styles.
JS_STRING = r'''("(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*'|`(?:[^`\\]|\\.)*`)'''
RECORD_PATTERN = re.compile(
    r'\{id:(\d+),image:"([^"]+)",name:' + JS_STRING + r',type:' + JS_STRING
    + r',rarity:' + JS_STRING + r',set:' + JS_STRING + r',number:(\d+)'
)
BACK_PATTERN = re.compile(r'back:\{image:"([^"]+)",name:' + JS_STRING)
RECORD_START = re.compile(r'\{id:\d+,image:"')

_database: Optional[Dict[int, dict]] = None

def extract_deck_id(value: str) -> str:
    match = DECK_ID_PATTERN.search(value or '')
    if not match:
        raise ValueError(f'No universus.cards deck id found in "{(value or "").strip()}". '
                         'Expected a link like https://universus.cards/deck/<id>.')
    return match.group(0).lower()

def get_deck(deck_id: str) -> dict:
    response = requests.get(DECK_API.format(deck_id=deck_id), headers=HEADERS, timeout=30)
    response.raise_for_status()
    try:
        deck = response.json()
    except ValueError as error:
        raise ValueError(f'universus.cards did not return a deck for {deck_id}.') from error
    if not deck:
        raise ValueError(f'Deck {deck_id} was not found, or it is private.')
    return deck

def js_string(literal: str) -> str:
    """Decode a JavaScript string literal (double, single or backtick quoted)."""
    body = literal[1:-1]
    if literal[0] == '"':
        return json.loads(literal)
    # Single-quoted and template literals: undo the escapes JSON also knows.
    return json.loads('"' + body.replace('\\' + literal[0], literal[0]).replace('"', '\\"') + '"')

def _fetch_text(url: str) -> str:
    response = requests.get(url, headers=HEADERS, timeout=60)
    response.raise_for_status()
    return response.text

def _find_database_script() -> str:
    """Follow the site's JavaScript imports from its entry points to the card database chunk."""
    page = _fetch_text(BASE_URL)
    frontier = [urljoin(BASE_URL, path) for path in ENTRY_PATTERN.findall(page)]
    if not frontier:
        raise RuntimeError('Could not find the universus.cards app scripts. The site layout may have changed.')

    seen = set()
    with ThreadPoolExecutor(max_workers=8) as pool:
        while frontier and len(seen) < MAX_SCRIPTS:
            batch = [url for url in dict.fromkeys(frontier) if url not in seen]
            seen.update(batch)
            frontier = []
            for url, text in zip(batch, pool.map(_fetch_text, batch)):
                if DATABASE_SIGNATURE.search(text):
                    return text
                frontier += [urljoin(url, path) for path in IMPORT_PATTERN.findall(text)]

    raise RuntimeError('Could not find the card database in the universus.cards scripts. '
                       'The site layout may have changed.')

def parse_database(script: str) -> Dict[int, dict]:
    starts = [match.start() for match in RECORD_START.finditer(script)]
    cards = {}
    for position, start in enumerate(starts):
        end = starts[position + 1] if position + 1 < len(starts) else len(script)
        segment = script[start:end]
        record = RECORD_PATTERN.match(segment)
        if not record:
            continue
        back = BACK_PATTERN.search(segment)
        cards[int(record.group(1))] = {
            'id': int(record.group(1)),
            'image': record.group(2),
            'name': js_string(record.group(3)),
            'set': js_string(record.group(6)),
            'number': int(record.group(7)),
            'back_image': back.group(1) if back else None,
        }
    return cards

def get_database() -> Dict[int, dict]:
    global _database
    if _database is None:
        print('Loading the universus.cards card database...')
        _database = parse_database(_find_database_script())
        if not _database:
            raise RuntimeError('The universus.cards card database could not be read. The site layout may have changed.')
        print(f'Loaded {len(_database)} cards.')
    return _database

def image_url(path: str) -> str:
    return IMAGE_URL.format(path=path)
