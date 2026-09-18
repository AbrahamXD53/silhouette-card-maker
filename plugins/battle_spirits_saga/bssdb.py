import json
import os
import re
from time import sleep
from urllib.parse import urlsplit

import requests

from plugins.battle_spirits_saga.lzstring import URI_SAFE_ALPHABET, decompress_from_encoded_uri_component
from utilities import guess_extension

BASE_URL = 'https://www.bssdb.dev'
IMAGE_URL = BASE_URL + '/cards/bss/{card_id}.png'

HEADERS = {'user-agent': 'silhouette-card-maker/0.1', 'accept': '*/*'}

CODE_PATTERN = re.compile('[' + re.escape(URI_SAFE_ALPHABET) + ']{16,}')
CARD_ID_PATTERN = re.compile(r'^[A-Z]{2,5}\d{0,2}-\d{3}$')

def remove_nonalphanumeric(text: str) -> str:
    return re.sub(r'[^a-zA-Z0-9]', '', text or '')

def extract_deck_code(value: str) -> str:
    """Pull the deck code out of a BSSDB link, or accept a bare code.

    Share links carry the code as the whole query string:
        https://bssdb.dev/?N4Ig5iBc...
        https://bssdb.dev/db/deckview?N4Ig5iBc...
    """
    value = (value or '').strip()
    source = urlsplit(value).query if re.match(r'^[a-z]+://', value, re.IGNORECASE) else value
    matches = CODE_PATTERN.findall(source)
    if not matches:
        raise ValueError(f'No BSSDB deck code found in "{value}". Copy the Sharable Permalink from the Export page.')
    return max(matches, key=len)

def decode_deck(code: str) -> dict:
    """Decode a deck code into {'name', 'author', 'deck': {id: n}, 'sideboard': {id: n}}."""
    text = decompress_from_encoded_uri_component(code)
    if not text:
        raise ValueError('The BSSDB deck code could not be decoded. Check that the whole link was copied.')

    try:
        data = json.loads(text)
    except json.JSONDecodeError as error:
        raise ValueError(f'The BSSDB deck code did not contain a deck: {error}') from error

    if data.get('g') not in (None, 'bss'):
        raise ValueError(f'This BSSDB link is for "{data.get("g")}", not Battle Spirits Saga.')

    boards = data.get('d') or {}
    return {
        'name': data.get('n') or '',
        'author': data.get('a') or '',
        'deck': boards.get('deck') or {},
        'sideboard': boards.get('sideboard') or {},
    }

def request_image(card_id: str) -> bytes:
    response = requests.get(IMAGE_URL.format(card_id=card_id), headers=HEADERS, timeout=30)
    if response.status_code == 404:
        raise ValueError(f'BSSDB has no image for "{card_id}"')
    response.raise_for_status()

    # Be gentle with a community-run site.
    sleep(0.075)
    return response.content

def fetch_card(index: int, quantity: int, card_id: str, card_name: str, front_img_dir: str) -> None:
    card_id = card_id.upper()
    if not CARD_ID_PATTERN.match(card_id):
        raise ValueError(f'"{card_id}" is not a Battle Spirits Saga card id')

    data = request_image(card_id)
    extension = guess_extension(data, '.png')
    clean_name = remove_nonalphanumeric(card_name) or card_id.replace('-', '')

    for counter in range(quantity):
        image_path = os.path.join(front_img_dir, f'{index}{clean_name}{counter + 1}{extension}')
        with open(image_path, 'wb') as f:
            f.write(data)

def get_handle_card(front_img_dir: str):
    def configured_fetch_card(index: int, card_id: str, card_name: str, quantity: int = 1):
        fetch_card(index, quantity, card_id, card_name, front_img_dir)

    return configured_fetch_card
