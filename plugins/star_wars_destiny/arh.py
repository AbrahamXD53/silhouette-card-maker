"""Decklists and card images from A Renewed Hope's Star Wars: Destiny database.

db.swdrenewedhope.com runs the SWDestinyDB software, so it has the same public
API as ArkhamDB and RingsDB.
"""
import os
import re
from time import sleep
from typing import Dict, Optional

import requests

from utilities import guess_extension

API_BASE = 'https://db.swdrenewedhope.com/api/public/'
DECKLIST_API = API_BASE + 'decklist/{decklist_id}'
CARDS_API = API_BASE + 'cards/'

HEADERS = {'user-agent': 'silhouette-card-maker/0.1', 'accept': 'application/json'}

DECKLIST_PATTERN = re.compile(r'decklist/(?:view/)?(\d+)', re.IGNORECASE)
BARE_ID_PATTERN = re.compile(r'^\s*(\d+)\s*$')

# Flip cards keep their two faces as <code>A.jpg and <code>B.jpg.
FACE_PATTERN = re.compile(r'([AB])(\.[a-z]+)$', re.IGNORECASE)

_cards: Optional[Dict[str, dict]] = None

def remove_nonalphanumeric(text: str) -> str:
    return re.sub(r'[^a-zA-Z0-9]', '', text or '')

def extract_decklist_id(value: str) -> str:
    value = value or ''
    match = DECKLIST_PATTERN.search(value) or BARE_ID_PATTERN.match(value)
    if not match:
        raise ValueError(f'No decklist found in "{value.strip()}". Expected a published decklist link like '
                         'https://db.swdrenewedhope.com/decklist/view/2461/luke-yoda-1.0')
    return match.group(1)

def get_decklist(decklist_id: str) -> dict:
    response = requests.get(DECKLIST_API.format(decklist_id=decklist_id), headers=HEADERS, timeout=30)
    response.raise_for_status()
    try:
        deck = response.json()
    except ValueError:
        deck = None
    if not deck or not isinstance(deck, dict) or 'slots' not in deck:
        raise ValueError(f'Decklist {decklist_id} was not found. Only published decklists can be fetched; '
                         'private decks are not available through the site\'s API.')
    return deck

def get_cards() -> Dict[str, dict]:
    global _cards
    if _cards is None:
        response = requests.get(CARDS_API, headers=HEADERS, timeout=60)
        response.raise_for_status()
        _cards = {card['code']: card for card in response.json()}
    return _cards

def other_face_url(card: dict) -> Optional[str]:
    """For a flip card, the image of its other face."""
    if not card.get('flip_card') or not card.get('imagesrc'):
        return None
    match = FACE_PATTERN.search(card['imagesrc'])
    if not match:
        return None
    other = 'B' if match.group(1).upper() == 'A' else 'A'
    return card['imagesrc'][:match.start()] + other + match.group(2)

def download(url: str) -> bytes:
    response = requests.get(url, headers={'user-agent': HEADERS['user-agent']}, timeout=60)
    response.raise_for_status()
    sleep(0.075)
    return response.content

def write_copies(data: bytes, directory: str, stem: str, quantity: int) -> None:
    extension = guess_extension(data, '.jpg')
    for counter in range(quantity):
        with open(os.path.join(directory, f'{stem}{counter + 1}{extension}'), 'wb') as f:
            f.write(data)

def fetch_card(index: int, quantity: int, card: dict, front_img_dir: str, double_sided_dir: str) -> None:
    if not card.get('imagesrc'):
        raise ValueError(f'{card["name"]} has no image')

    stem = f'{index}{remove_nonalphanumeric(card["name"]) or card["code"]}'
    write_copies(download(card['imagesrc']), front_img_dir, stem, quantity)

    back_url = other_face_url(card)
    if back_url:
        # Same filename in double_sided/, which is how create_pdf.py pairs the faces.
        write_copies(download(back_url), double_sided_dir, stem, quantity)

def get_handle_card(front_img_dir: str, double_sided_dir: str):
    def configured_fetch_card(index: int, card: dict, quantity: int = 1):
        fetch_card(index, quantity, card, front_img_dir, double_sided_dir)

    return configured_fetch_card
