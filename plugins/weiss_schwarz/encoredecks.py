"""Weiss Schwarz decks from EncoreDecks (encoredecks.com), with official card images.

EncoreDecks has a public JSON API: `/api/deck/<id>` returns the deck with one
entry per copy, each with its card code and language. Card images come from the
official sites when they have them (en.ws-tcg.com for English cards, ws-tcg.com
for Japanese ones, both about 400x558) and from EncoreDecks otherwise, whose own
images are small for older sets.
"""
import io
import os
import re
from time import sleep
from typing import Dict, List, Optional, Tuple

import requests
from PIL import Image

from utilities import guess_extension

DECK_API = 'https://www.encoredecks.com/api/deck/{deck_id}'
ENCOREDECKS_IMAGE = 'https://www.encoredecks.com/images/{path}'
ENGLISH_IMAGE = 'https://en.ws-tcg.com/wordpress/wp-content/images/cardimages/{initial}/{folder}/{file}.png'
JAPANESE_IMAGE = 'https://ws-tcg.com/wordpress/wp-content/images/cardlist/{initial}/{folder}/{file}.png'
ENGLISH_CARD_PAGE = 'https://en.ws-tcg.com/cardlist/list/'

HEADERS = {'user-agent': 'silhouette-card-maker/0.1', 'accept': 'application/json'}

DECK_URL_PATTERN = re.compile(r'encoredecks\.com/deck/([A-Za-z0-9_-]+)', re.IGNORECASE)
BARE_ID_PATTERN = re.compile(r'^\s*([A-Za-z0-9_-]{6,})\s*$')
CARD_CODE_PATTERN = re.compile(r'^([A-Za-z0-9]+)/([A-Za-z0-9]+)-([A-Za-z0-9]+)$')

def extract_deck_id(value: str) -> str:
    value = value or ''
    match = DECK_URL_PATTERN.search(value) or BARE_ID_PATTERN.match(value)
    if not match:
        raise ValueError(f'No EncoreDecks deck found in "{value.strip()}". Expected a link like '
                         'https://www.encoredecks.com/deck/A33QHgxiD')
    return match.group(1)

def get_deck(deck_id: str) -> dict:
    try:
        response = requests.get(DECK_API.format(deck_id=deck_id), headers=HEADERS, timeout=30)
    except requests.ConnectionError as error:
        # EncoreDecks drops the connection instead of answering 404 for an unknown id.
        raise ValueError(f'EncoreDecks did not return deck {deck_id}; check the link, or the deck may be private.') from error
    if response.status_code in (401, 403, 404):
        raise ValueError(f'Deck {deck_id} was not found, or it is private.')
    response.raise_for_status()
    try:
        deck = response.json()
    except ValueError:
        deck = None
    if not isinstance(deck, dict) or not deck.get('cards'):
        raise ValueError(f'Deck {deck_id} was not found, or it is private.')
    return deck

def tally(deck: dict) -> List[Tuple[dict, int]]:
    """One entry per card, with its copies counted, in deck order."""
    counts: Dict[str, List] = {}
    for card in deck.get('cards') or []:
        key = card.get('_id') or card.get('cardcode')
        if key in counts:
            counts[key][1] += 1
        else:
            counts[key] = [card, 1]
    return [(card, quantity) for card, quantity in counts.values()]

def display_name(card: dict) -> str:
    english = ((card.get('locale') or {}).get('EN') or {}).get('name')
    return english or card.get('name') or card.get('cardcode') or ''

def official_image_url(card: dict) -> Optional[str]:
    """The official site's image for a card code like "NGL/S58-E001"."""
    match = CARD_CODE_PATTERN.match(card.get('cardcode') or '')
    if not match:
        return None
    series, release, number = match.groups()
    folder = f'{series}_{release}'.lower()
    initial = series[0].lower()
    if card.get('lang') == 'EN':
        return ENGLISH_IMAGE.format(initial=initial, folder=folder, file=f'{series}_{release}_{number}'.upper())
    return JAPANESE_IMAGE.format(initial=initial, folder=folder, file=f'{series}_{release}_{number}'.lower())

def download(url: str) -> Optional[bytes]:
    response = requests.get(url, headers={'user-agent': HEADERS['user-agent']}, timeout=60)
    if response.status_code != 200 or not response.headers.get('content-type', '').startswith('image'):
        return None
    sleep(0.075)
    return response.content

def english_card_page_image(card: dict) -> Optional[str]:
    """Some English sets use their own folders (BanG Dream: BDAM/W125_E098.png), so ask the card page."""
    page = requests.get(ENGLISH_CARD_PAGE, params={'cardno': card.get('cardcode')},
                        headers={'user-agent': HEADERS['user-agent']}, timeout=30)
    if page.status_code != 200:
        return None
    match = re.search(r'/wordpress/wp-content/images/cardimages/[^"\'\s]+\.(?:png|jpg|gif)', page.text)
    return f'https://en.ws-tcg.com{match.group(0)}' if match else None

def card_image(card: dict) -> Tuple[bytes, str]:
    official = official_image_url(card)
    if official:
        data = download(official)
        if data:
            return data, 'official'
    if card.get('lang') == 'EN':
        listed = english_card_page_image(card)
        data = download(listed) if listed else None
        if data:
            return data, 'official'
    if card.get('imagepath'):
        data = download(ENCOREDECKS_IMAGE.format(path=card['imagepath']))
        if data:
            return data, 'EncoreDecks'
    raise ValueError(f'No image found for {card.get("cardcode")}')

def to_portrait(data: bytes) -> Tuple[bytes, str]:
    """Climax cards are landscape; turn them like the Bushiroad plugin does."""
    image = Image.open(io.BytesIO(data))
    if image.width <= image.height:
        return data, guess_extension(data, '.png')
    output = io.BytesIO()
    image.rotate(-90, expand=True).save(output, format='PNG')
    return output.getvalue(), '.png'

def fetch_card(index: int, quantity: int, card: dict, front_img_dir: str) -> str:
    data, source = card_image(card)
    small = Image.open(io.BytesIO(data)).width < 300
    data, extension = to_portrait(data)

    stem = f'{index}{re.sub(r"[^A-Za-z0-9]", "", card.get("cardcode") or "") or index}'
    for counter in range(quantity):
        with open(os.path.join(front_img_dir, f'{stem}{counter + 1}{extension}'), 'wb') as f:
            f.write(data)
    return source + (' (small image)' if small else '')
