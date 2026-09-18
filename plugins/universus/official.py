"""High resolution card images from the official UniVersus card gallery (play.uvsgames.com).

The gallery is backed by carde.io's public deck builder API. Its cards have
different ids from universus.cards, so a card is matched by name, then set and
collector number.
"""
import re
from time import sleep
from typing import Optional

import requests

SEARCH_URL = 'https://api-hydra.carde.io/api/v2/deckbuilder/cards/search-with-filters/'
GAME_ID = 298  # UniVersus
PAGE_SIZE = 50
MAX_PAGES = 4

HEADERS = {'user-agent': 'silhouette-card-maker/0.1', 'accept': 'application/json'}

QUOTES = str.maketrans({'‘': "'", '’': "'", '“': '"', '”': '"'})

def normalize_name(name: str) -> str:
    return ' '.join((name or '').translate(QUOTES).lower().split())

def slug(text: str) -> str:
    return re.sub(r'[^a-z0-9]+', '-', (text or '').lower()).strip('-')

def search(name: str) -> list:
    found = []
    for page in range(MAX_PAGES):
        response = requests.post(SEARCH_URL, headers=HEADERS, timeout=30, json={
            'game_id': GAME_ID,
            'query': name,
            'filters': {},
            'sort_by': 'name',
            'sort_order': 'asc',
            'limit': PAGE_SIZE,
            'offset': page * PAGE_SIZE,
        })
        response.raise_for_status()
        data = response.json()
        found += data.get('cards') or []
        sleep(0.1)
        if not data.get('has_more'):
            break
    return found

def find_card(name: str, set_name: str, number: int) -> Optional[dict]:
    """Return the best official printing of a card, with how it was matched, or None."""
    wanted = normalize_name(name)
    candidates = [card for card in search(name.translate(QUOTES))
                  if normalize_name(card.get('name')) == wanted and card.get('image_url')]
    if not candidates:
        return None

    wanted_set = slug(set_name)

    def score(card):
        attributes = card.get('attribute_values') or {}
        card_set = slug(((attributes.get('Card Set') or {}).get('option')) or '')
        same_set = bool(card_set) and (card_set == wanted_set or wanted_set in card_set or card_set in wanted_set)
        same_number = attributes.get('Collector Number') == number
        return (same_set and same_number, same_set, same_number)

    best = max(candidates, key=score)
    exact = score(best)[0]
    return {
        'image_url': best['image_url'],
        'back_image_url': best.get('back_image_url'),
        'match': 'exact' if exact else ('name' if len(candidates) == 1 else 'name, several printings'),
    }
