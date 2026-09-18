"""Decks and card images from DeckPlanet (deckplanet.net), a multi-game deck builder.

DeckPlanet's data lives in a Directus API at api.deckplanet.net with public read
access: each game has a `<game>_decks` collection whose `deck_cards` point at
`<game>_cards` records. Card images are `<img_link>.webp` in the game's folder
of DeckPlanet's image store, and a card's other face is `<img_link>_b.webp`.
"""
import io
import json
import os
import re
from time import sleep
from typing import Dict, List, Optional, Tuple

import requests
from PIL import Image

from utilities import guess_extension

API_BASE = 'https://api.deckplanet.net/items/'
IMAGE_URL = 'https://multi-deckplanet.us-southeast-1.linodeobjects.com/{game}/{name}.webp'

HEADERS = {'user-agent': 'silhouette-card-maker/0.1', 'accept': 'application/json'}

# Game slug -> (display name, deck fields that each hold one card, in print order).
GAMES: Dict[str, Tuple[str, List[str]]] = {
    'alpha_clash': ('Alpha Clash', ['deck_contender']),
    'cyberpunk': ('Cyberpunk TCG', []),
    'dbs_masters': ('Dragon Ball Super Card Game Masters', ['deck_leader']),
    'fusion_world': ('Dragon Ball Super Card Game Fusion World', ['deck_leader']),
    'gundam': ('Gundam Card Game', []),
    'hellbreak': ('Hellbreak', ['deck_monster', 'deck_location', 'deck_location_2']),
    'naruto_ccg': ('Naruto CCG', ['deck_leader']),
    'neuroscape': ('Neuroscape', ['deck_mainframe']),
    'one_piece': ('One Piece Card Game', ['deck_leader']),
    'riftbound': ('Riftbound', ['deck_legend']),
    'swu': ('Star Wars: Unlimited', ['deck_leader', 'deck_leader_2', 'deck_base']),
    'wotf': ('Wonders of the First', []),
}

# Deck zones that are not played; fetched only with --include_sideboard.
OPTIONAL_ZONES = ('side', 'maybe')

DECK_URL_PATTERN = re.compile(r'deckplanet\.net/(?:[a-z]{2}(?:-[a-z]{2})?/)?([a-z0-9_]+)/deck/([0-9a-f-]{36})', re.IGNORECASE)
DECK_ID_PATTERN = re.compile(r'^\s*([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\s*$', re.IGNORECASE)

def remove_nonalphanumeric(text: str) -> str:
    return re.sub(r'[^a-zA-Z0-9]', '', text or '')

def parse_deck_reference(value: str, game: Optional[str]) -> Tuple[str, str]:
    """Return (game, deck id) from a DeckPlanet deck link, or from a bare id plus --game."""
    value = value or ''
    match = DECK_URL_PATTERN.search(value)
    if match:
        linked_game, deck_id = match.group(1).lower(), match.group(2).lower()
        if game and linked_game != game:
            raise ValueError(f'This is a {GAMES.get(linked_game, (linked_game,))[0]} deck, not {GAMES[game][0]}. '
                             f'Fetch it from the {GAMES.get(linked_game, (linked_game,))[0]} plugin instead.')
        game = linked_game
    else:
        bare = DECK_ID_PATTERN.match(value)
        if not bare:
            raise ValueError(f'No DeckPlanet deck found in "{value.strip()}". Expected a link like '
                             'https://www.deckplanet.net/gundam/deck/<id>.')
        if not game:
            raise ValueError('A bare deck id needs --game, or paste the full DeckPlanet link.')
        deck_id = bare.group(1).lower()

    if game not in GAMES:
        raise ValueError(f'DeckPlanet game "{game}" is not supported. Supported: {", ".join(sorted(GAMES))}.')
    return game, deck_id

def get_deck(game: str, deck_id: str) -> dict:
    single_fields = GAMES[game][1]
    fields = ['deck_name', 'deck_cards.amount_in_deck', 'deck_cards.zone', 'deck_cards.card_id.*']
    fields += [f'{field}.*' for field in single_fields]
    response = requests.get(f'{API_BASE}{game}_decks/{deck_id}', headers=HEADERS, timeout=30,
                            params={'fields': ','.join(fields)})
    if response.status_code in (401, 403, 404):
        raise ValueError(f'Deck {deck_id} was not found, or it is private.')
    response.raise_for_status()
    deck = response.json().get('data')
    if not deck:
        raise ValueError(f'Deck {deck_id} was not found, or it is private.')
    return deck

def has_other_face(card: dict) -> bool:
    return bool(
        (card.get('card_back_name') or '').strip()
        # Two-faced cards named "Front // Back", like Star Wars: Unlimited leaders.
        or ' // ' in (card.get('card_name') or '')
        or card.get('card_back_img_link')
        or card.get('has_backside')
        or card.get('art_back_horizontal') is not None
    )

def card_name(card: dict) -> str:
    return card.get('card_name') or card.get('name') or card.get('card_number') or card.get('img_link') or ''

def deck_entries(game: str, deck: dict, include_sideboard: bool):
    """Yield (card, quantity, section) in print order: special cards, then zones as listed."""
    entries = []
    for field in GAMES[game][1]:
        card = deck.get(field)
        if isinstance(card, dict) and card.get('img_link'):
            label = field.replace('deck_', '').replace('_', ' ')
            entries.append((card, 1, label))

    skipped = {}
    for entry in deck.get('deck_cards') or []:
        card = entry.get('card_id')
        quantity = int(entry.get('amount_in_deck') or 0)
        if not isinstance(card, dict) or quantity <= 0:
            continue
        zone = (entry.get('zone') or 'main').lower()
        if zone.startswith(OPTIONAL_ZONES) and not include_sideboard:
            skipped[zone] = skipped.get(zone, 0) + quantity
            continue
        entries.append((card, quantity, zone))

    return entries, skipped

def download(url: str) -> Optional[bytes]:
    response = requests.get(url, headers={'user-agent': HEADERS['user-agent']}, timeout=60)
    if response.status_code in (403, 404):
        return None
    response.raise_for_status()
    if not response.headers.get('content-type', '').startswith('image'):
        return None
    sleep(0.05)
    return response.content

def to_portrait(data: bytes) -> Tuple[bytes, str, bool]:
    """Rotate a landscape card (bases, locations...) to portrait, as create_pdf.py lays cards out portrait."""
    image = Image.open(io.BytesIO(data))
    if image.width <= image.height:
        return data, guess_extension(data, '.webp'), False
    rotated = image.rotate(90, expand=True)
    output = io.BytesIO()
    rotated.save(output, format='PNG')
    return output.getvalue(), '.png', True

def write_copies(data: bytes, extension: str, directory: str, stem: str, quantity: int) -> None:
    for counter in range(quantity):
        with open(os.path.join(directory, f'{stem}{counter + 1}{extension}'), 'wb') as f:
            f.write(data)

def fetch_card(game: str, index: int, quantity: int, card: dict, front_img_dir: str, double_sided_dir: str) -> List[str]:
    notes = []
    front = download(IMAGE_URL.format(game=game, name=card['img_link']))
    if front is None:
        raise ValueError(f'DeckPlanet has no image for {card["img_link"]}')

    stem = f'{index}{remove_nonalphanumeric(card_name(card)) or remove_nonalphanumeric(card["img_link"])}'
    data, extension, rotated = to_portrait(front)
    if rotated:
        notes.append('rotated to portrait')
    write_copies(data, extension, front_img_dir, stem, quantity)

    if has_other_face(card):
        back_name = card.get('card_back_img_link') or f'{card["img_link"]}_b'
        back = download(IMAGE_URL.format(game=game, name=back_name))
        if back is None:
            notes.append('back face image not found')
        else:
            data, extension, _ = to_portrait(back)
            # Same filename in double_sided/, which is how create_pdf.py pairs the faces.
            write_copies(data, extension, double_sided_dir, stem, quantity)
            notes.append('back face in double_sided')
    return notes
