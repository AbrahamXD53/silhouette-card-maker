import os
import re
from typing import Dict

import requests

from utilities import guess_extension

BASE_URL = 'https://kodem.wildhogstudio.com'
CARD_INDEX_URL = f'{BASE_URL}/DeckBuilder'
ASSET_URL = BASE_URL + '/assets/{set_code}/{card_id}.webp'

HEADERS = {'user-agent': 'silhouette-card-maker/0.1', 'accept': '*/*'}

# Asset paths appear both plainly and percent-encoded, because the page wraps
# them in Next.js image-optimizer URLs (/_next/image?url=%2Fassets%2F...).
ASSET_PATTERN = re.compile(
    r'(?:/|%2F)assets(?:/|%2F)([A-Za-z0-9]+)(?:/|%2F)([A-Za-z0-9\-]+)\.webp',
    re.IGNORECASE,
)

_card_index: Dict[str, str] = None

def remove_nonalphanumeric(text: str) -> str:
    return re.sub(r'[^a-zA-Z0-9]', '', text or '')

def fetch_card_index(force: bool = False) -> Dict[str, str]:
    """Map every card id to the set folder that holds its image.

    The folder cannot be derived from the id: DMUE-, CMFT-, RMFT- and FAFT- ids
    all live under MFT. The deck builder page is server rendered, so scraping it
    once yields the whole catalogue without needing a browser or an API.
    """
    global _card_index
    if _card_index is not None and not force:
        return _card_index

    response = requests.get(CARD_INDEX_URL, headers=HEADERS, timeout=30)
    response.raise_for_status()

    index = {}
    for set_code, card_id in ASSET_PATTERN.findall(response.text):
        index.setdefault(card_id.upper(), set_code.upper())

    if not index:
        raise RuntimeError(
            f'No cards found on {CARD_INDEX_URL}. The page layout may have changed.'
        )

    _card_index = index
    return index

def fetch_card(index: int, quantity: int, card_id: str, card_name: str, front_img_dir: str) -> None:
    catalogue = fetch_card_index()
    card_id = card_id.upper()

    set_code = catalogue.get(card_id)
    if set_code is None:
        raise ValueError(f'"{card_id}" is not in the Kodem card list')

    response = requests.get(ASSET_URL.format(set_code=set_code, card_id=card_id), headers=HEADERS, timeout=30)
    response.raise_for_status()

    data = response.content
    extension = guess_extension(data, '.webp')
    clean_name = remove_nonalphanumeric(card_name) or card_id.replace('-', '')

    for counter in range(quantity):
        image_path = os.path.join(front_img_dir, f'{index}{clean_name}{counter + 1}{extension}')
        with open(image_path, 'wb') as f:
            f.write(data)

def get_handle_card(front_img_dir: str):
    def configured_fetch_card(index: int, card_id: str, card_name: str, quantity: int = 1):
        fetch_card(index, quantity, card_id, card_name, front_img_dir)

    return configured_fetch_card
