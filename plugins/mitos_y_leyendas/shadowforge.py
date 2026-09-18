"""Decks and card images from ShadowForge, a Mitos y Leyendas deck builder.

ShadowForge (shadow-forge-deck.vercel.app) is backed by a public REST API: a
public deck returns its cards with full details, including an image link.
"""
import os
import re
from time import sleep

import requests

from utilities import guess_extension

DECK_API = 'https://iterva.pythonanywhere.com/api/decks/public/{deck_id}/'

HEADERS = {'user-agent': 'silhouette-card-maker/0.1', 'accept': 'application/json'}

DECK_URL_PATTERN = re.compile(r'/decks/(\d+)')
BARE_ID_PATTERN = re.compile(r'^\s*(\d+)\s*$')

def remove_nonalphanumeric(text: str) -> str:
    return re.sub(r'[^a-zA-Z0-9]', '', text or '')

def extract_deck_id(value: str) -> str:
    value = value or ''
    match = DECK_URL_PATTERN.search(value) or BARE_ID_PATTERN.match(value)
    if not match:
        raise ValueError(f'No ShadowForge deck found in "{value.strip()}". Expected a link like '
                         'https://shadow-forge-deck.vercel.app/decks/155')
    return match.group(1)

def get_deck(deck_id: str) -> dict:
    response = requests.get(DECK_API.format(deck_id=deck_id), headers=HEADERS, timeout=30)
    if response.status_code in (401, 403, 404):
        raise ValueError(f'Deck {deck_id} was not found, or it is not public.')
    response.raise_for_status()
    return response.json()

def fetch_card(index: int, quantity: int, card: dict, front_img_dir: str) -> None:
    url = card.get('image_url')
    if not url:
        raise ValueError(f'{card.get("name")} has no image')

    response = requests.get(url, headers={'user-agent': HEADERS['user-agent']}, timeout=60)
    response.raise_for_status()
    sleep(0.05)

    data = response.content
    extension = guess_extension(data, '.png')
    clean_name = remove_nonalphanumeric(card.get('name')) or remove_nonalphanumeric(card.get('slug')) or str(card.get('id'))
    for counter in range(quantity):
        with open(os.path.join(front_img_dir, f'{index}{clean_name}{counter + 1}{extension}'), 'wb') as f:
            f.write(data)
