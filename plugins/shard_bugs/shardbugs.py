"""Card data and images for Shard Bugs TCG (shardbugstcg.com).

The site publishes its whole card database at `/_functions/cards`, each card
with a Google Drive image link. The deck builder is behind a login, so decks
are given as a decklist instead: a card is matched by its number ("001/110") or
by name.

Names and numbers repeat across sets and printings (1093 printings of 747
cards), so when a line matches several printings the plainest one is used --
English, standard numbering, ordinary rarity -- unless the line or `--set` says
which set to use.
"""
import os
import re
from time import sleep
from typing import Dict, List, Optional, Tuple

import requests

from utilities import guess_extension

CARDS_API = 'https://www.shardbugstcg.com/_functions/cards'
# Google Drive's image host; "=s4096" asks for the full-size original.
IMAGE_URL = 'https://lh3.googleusercontent.com/d/{drive_id}=s4096'

HEADERS = {'user-agent': 'silhouette-card-maker/0.1', 'accept': 'application/json'}

DRIVE_ID_PATTERN = re.compile(r'(?:id=|/d/)([A-Za-z0-9_-]{20,})')
# "3 Honey Alchemist", "3x 001/110", "Honey Alchemist (The Bug-inning)", "1 Maize Weevil [010/161]"
CARD_LINE_PATTERN = re.compile(
    r'^\s*(?:(\d+)\s*[xX]?\s+)?(.+?)\s*(?:[\[(]\s*([^\])]+?)\s*[\])])?\s*$'
)
SECTION_PATTERN = re.compile(r'^\s*(?:[-=/#*]+\s*)?(deck|main\s*deck|hive|field|sideboard|side\s*deck|tokens?)\b.*$', re.IGNORECASE)
CARD_NUMBER_PATTERN = re.compile(r'^[A-Za-z0-9-]{1,6}/\d{1,4}$|^[A-Za-z]-\d{1,4}$|^\d{1,4}$')

# Rarities that are ordinary printings, preferred over special ones.
PLAIN_RARITIES = ('common', 'uncommon', 'rare', 'token', 'promo')

_cards: Optional[List[dict]] = None

def remove_nonalphanumeric(text: str) -> str:
    return re.sub(r'[^a-zA-Z0-9]', '', text or '')

def normalize(text: str) -> str:
    return re.sub(r'[^a-z0-9]+', ' ', (text or '').lower()).strip()

def get_cards() -> List[dict]:
    global _cards
    if _cards is None:
        response = requests.get(CARDS_API, headers=HEADERS, timeout=60)
        response.raise_for_status()
        payload = response.json()
        _cards = payload.get('results') if isinstance(payload, dict) else payload
        if not _cards:
            raise RuntimeError('The Shard Bugs card list came back empty. The site may have changed.')
        print(f'Loaded {len(_cards)} card printings.')
    return _cards

def printing_rank(card: dict) -> tuple:
    """Lower sorts first: the plainest printing of a card."""
    rarity = (card.get('Rarity') or '').strip().lower()
    number = (card.get('Number') or '').strip()
    return (
        0 if (card.get('Language') or 'English').strip().lower() == 'english' else 1,
        0 if re.match(r'^\d{1,4}/\d{1,4}$', number) else 1,   # standard set numbering
        PLAIN_RARITIES.index(rarity) if rarity in PLAIN_RARITIES else len(PLAIN_RARITIES),
        0 if 'non' in (card.get('Finish') or '').lower() else 1,
        card.get('SetName') or '',
    )

def matches(identifier: str, preferred_set: Optional[str]) -> List[dict]:
    """Every printing a decklist line could mean, best first."""
    wanted = normalize(identifier)
    by_number = [c for c in get_cards() if normalize(c.get('Number')) == wanted]
    found = by_number or [c for c in get_cards() if normalize(c.get('CardName')) == wanted]

    if preferred_set:
        preferred = normalize(preferred_set)
        narrowed = [c for c in found if preferred in normalize(c.get('SetName'))]
        found = narrowed or found
    return sorted(found, key=printing_rank)

def parse_line(line: str) -> Optional[Tuple[int, str, Optional[str]]]:
    """(quantity, identifier, set hint) from a decklist line."""
    match = CARD_LINE_PATTERN.match(line)
    if not match:
        return None
    quantity = int(match.group(1) or 1)
    identifier = (match.group(2) or '').strip(' -\t')
    hint = match.group(3)
    if not identifier:
        return None
    # "Honey Alchemist (001/110)" puts the number in the brackets.
    if hint and CARD_NUMBER_PATTERN.match(hint.strip()):
        identifier, hint = hint.strip(), None
    return quantity, identifier, hint

def image_url(card: dict) -> str:
    match = DRIVE_ID_PATTERN.search(card.get('Image') or '')
    if not match:
        raise ValueError(f'{card.get("CardName")} has no image')
    return IMAGE_URL.format(drive_id=match.group(1))

def fetch_card(index: int, quantity: int, card: dict, front_img_dir: str) -> None:
    response = requests.get(image_url(card), headers={'user-agent': HEADERS['user-agent']}, timeout=120)
    response.raise_for_status()
    if not response.headers.get('content-type', '').startswith('image'):
        raise ValueError(f'{card.get("CardName")} did not return an image')
    sleep(0.075)

    data = response.content
    extension = guess_extension(data, '.png')
    stem = f'{index}{remove_nonalphanumeric(card.get("CardName")) or remove_nonalphanumeric(card.get("Number"))}'
    for counter in range(quantity):
        with open(os.path.join(front_img_dir, f'{stem}{counter + 1}{extension}'), 'wb') as f:
            f.write(data)

def describe(card: dict) -> str:
    parts = [card.get('Number'), card.get('SetName'), card.get('Rarity')]
    return ', '.join(p for p in parts if p)
