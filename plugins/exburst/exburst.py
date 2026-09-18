"""Decks and card images from ExBurst (exburst.dev), a multi-game deck builder.

ExBurst keeps its data in Supabase (auth.exburst.dev) and reads public rows with
the site's public "anon" key, which it ships in its own JavaScript. Each game
publishes a config (`/<path>/config/game-config.json`) that names its decklist
table and the columns holding a card's number and image, so the plugin reads the
config instead of hard-coding them. Decklists are text, one "<count> x <card>"
per line; images come in a small (`/sd/`) and a large (`/hd/`) size.
"""
import io
import os
import re
from time import sleep
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin

import requests
from PIL import Image

from utilities import guess_extension

SITE = 'https://exburst.dev/'
SUPABASE_REST = 'https://auth.exburst.dev/rest/v1/'
# The script that carries the site's public Supabase key.
KEY_SOURCE = SITE + 'ua/en/'
KEY_PATTERN = re.compile(r'eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{10,}')

HEADERS = {'user-agent': 'silhouette-card-maker/0.1'}

# --game value -> (display name, config path on exburst.dev, link paths that lead to it)
GAMES: Dict[str, Tuple[str, str, List[str]]] = {
    'union_arena_en': ('Union Arena (English)', 'ua/en', ['ua/en', 'uaen']),
    'union_arena_asia': ('Union Arena (Asia)', 'ua', ['ua']),
    'gundam': ('Gundam Card Game', 'gundam', ['gundam']),
    'riftbound': ('Riftbound', 'riftbound', ['riftbound']),
    'cyberpunk': ('Cyberpunk TCG', 'cyberpunk', ['cyberpunk']),
    'naruto_bandai': ('Naruto Card Game (Bandai)', 'naruto', ['naruto', 'nrtb']),
    # Mythos reports "naruto" as its path too, so a /naruto/ link is ambiguous without --game.
    'naruto_mythos': ('Naruto Mythos TCG', 'mythos', ['mythos', 'naruto']),
}

# Several games under one name: the link decides which.
GAME_GROUPS: Dict[str, List[str]] = {
    'union_arena': ['union_arena_en', 'union_arena_asia'],
}

DECK_URL_PATTERN = re.compile(r'exburst\.dev/([a-z0-9_]+(?:/[a-z]{2})?)/deck/(\d+)', re.IGNORECASE)
BARE_ID_PATTERN = re.compile(r'^\s*(\d+)\s*$')
CARD_LINE_PATTERN = re.compile(r'^\s*(\d+)\s*x\s*(\S.*?)\s*$', re.IGNORECASE)

_key: Optional[str] = None

def remove_nonalphanumeric(text: str) -> str:
    return re.sub(r'[^a-zA-Z0-9]', '', text or '')

def game_choices() -> List[str]:
    return sorted(list(GAMES) + list(GAME_GROUPS))

def resolve_deck(value: str, game: Optional[str]) -> Tuple[str, str]:
    """Return (game, deck id) from an ExBurst deck link, or a bare id plus --game."""
    allowed = GAME_GROUPS.get(game, [game]) if game else list(GAMES)
    value = value or ''
    match = DECK_URL_PATTERN.search(value)
    if match:
        path, deck_id = match.group(1).lower(), match.group(2)
        linked = [g for g, (_, _, paths) in GAMES.items() if path in paths]
        if not linked:
            raise ValueError(f'"{path}" is not an ExBurst game this plugin knows.')
        candidates = [g for g in linked if g in allowed]
        if not candidates:
            names = ' or '.join(GAMES[g][0] for g in linked)
            raise ValueError(f'This is a {names} deck, not {describe(game)}. Fetch it from that game instead.')
        if len(candidates) > 1:
            raise ValueError(f'The link could be {" or ".join(GAMES[g][0] for g in candidates)}; give --game.')
        return candidates[0], deck_id

    bare = BARE_ID_PATTERN.match(value)
    if not bare:
        raise ValueError(f'No ExBurst deck found in "{value.strip()}". Expected a link like '
                         'https://exburst.dev/ua/en/deck/72156')
    if len(allowed) != 1:
        raise ValueError('A bare deck number needs a specific --game; paste the full ExBurst link instead.')
    return allowed[0], bare.group(1)

def describe(game: Optional[str]) -> str:
    if game in GAMES:
        return GAMES[game][0]
    return {'union_arena': 'Union Arena'}.get(game, game or 'this game')

def get_key() -> str:
    global _key
    if _key is None:
        page = requests.get(KEY_SOURCE, headers=HEADERS, timeout=30).text
        for script in re.findall(r'<script[^>]+src="([^"]+)"', page):
            url = urljoin(KEY_SOURCE, script)
            if not url.startswith(SITE):
                continue
            match = KEY_PATTERN.search(requests.get(url, headers=HEADERS, timeout=60).text)
            if match:
                _key = match.group(0)
                break
        if _key is None:
            raise RuntimeError('Could not find ExBurst\'s public data key. The site may have changed.')
    return _key

def supabase(table: str, params: dict) -> list:
    key = get_key()
    response = requests.get(SUPABASE_REST + table, timeout=30, params=params, headers={
        **HEADERS, 'apikey': key, 'authorization': f'Bearer {key}', 'accept': 'application/json'})
    response.raise_for_status()
    return response.json()

def get_config(game: str) -> dict:
    response = requests.get(f'{SITE}{GAMES[game][1]}/config/game-config.json', headers=HEADERS, timeout=30)
    response.raise_for_status()
    return response.json()

def get_deck(config: dict, deck_id: str) -> dict:
    rows = supabase(config['decklists_table'], {
        'select': 'id,decklist_name,decklist_content,sidedeck,is_public', 'id': f'eq.{deck_id}'})
    if not rows or not rows[0].get('is_public'):
        raise ValueError(f'Deck {deck_id} was not found, or it is not public.')
    return rows[0]

def parse_lines(text: str) -> List[Tuple[str, int]]:
    cards = []
    for line in (text or '').splitlines():
        if not line.strip():
            continue
        match = CARD_LINE_PATTERN.match(line)
        if match:
            cards.append((match.group(2), int(match.group(1))))
        else:
            print(f'Skipping: "{line.strip()}"')
    return cards

def get_cards(config: dict, card_ids: List[str]) -> Dict[str, dict]:
    """Card records by card number, in batches (PostgREST `in` filter)."""
    id_column, image_column = config['cardId_column'], config['cardFront_column']
    name_column = config.get('cardName_column') or 'name'
    found = {}
    for start in range(0, len(card_ids), 40):
        batch = card_ids[start:start + 40]
        quoted = ','.join('"' + card_id.replace('"', '') + '"' for card_id in batch)
        rows = supabase(f'{config["gameid"]}_cards', {
            'select': f'{id_column},{image_column},{name_column}', id_column: f'in.({quoted})'})
        for row in rows:
            found.setdefault(row[id_column], {'image': row.get(image_column), 'name': row.get(name_column)})
    return found

def download(url: str) -> Optional[bytes]:
    response = requests.get(url, headers=HEADERS, timeout=60)
    if response.status_code != 200 or not response.headers.get('content-type', '').startswith('image'):
        return None
    sleep(0.05)
    return response.content

def best_image(url: str) -> Tuple[bytes, str]:
    """The large (/hd/) image when there is one, else the listed one."""
    base = url.split('?')[0]
    if '/sd/' in base:
        data = download(base.replace('/sd/', '/hd/'))
        if data:
            return data, 'large'
    data = download(url)
    if data is None:
        raise ValueError(f'ExBurst has no image at {url}')
    return data, 'large' if '/hd/' in base else 'small'

def to_portrait(data: bytes) -> Tuple[bytes, str, bool]:
    image = Image.open(io.BytesIO(data))
    if image.width <= image.height:
        return data, guess_extension(data, '.webp'), False
    output = io.BytesIO()
    image.rotate(90, expand=True).save(output, format='PNG')
    return output.getvalue(), '.png', True

def fetch_card(index: int, quantity: int, card_id: str, card: dict, front_img_dir: str) -> List[str]:
    if not card.get('image'):
        raise ValueError(f'{card_id} has no image')
    data, size = best_image(card['image'])
    data, extension, rotated = to_portrait(data)

    stem = f'{index}{remove_nonalphanumeric(card.get("name")) or remove_nonalphanumeric(card_id)}'
    for counter in range(quantity):
        with open(os.path.join(front_img_dir, f'{stem}{counter + 1}{extension}'), 'wb') as f:
            f.write(data)

    notes = []
    if size == 'small':
        notes.append('only the small image exists')
    if rotated:
        notes.append('rotated to portrait')
    return notes
