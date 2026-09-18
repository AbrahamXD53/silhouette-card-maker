"""Decks and card images from netdeck.gg, which powers cyberpunktcg.com's deck builder."""
import os
import re
from time import sleep
from typing import Dict

import requests

from utilities import guess_extension

DECK_API = 'https://api.netdeck.gg/api/cyberpunk/decks/{deck_id}'

HEADERS = {'user-agent': 'silhouette-card-maker/0.1', 'accept': 'application/json'}

DECK_ID_PATTERN = re.compile(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', re.IGNORECASE)

def remove_nonalphanumeric(text: str) -> str:
    return re.sub(r'[^a-zA-Z0-9]', '', text or '')

def extract_deck_id(value: str) -> str:
    match = DECK_ID_PATTERN.search(value or '')
    if not match:
        raise ValueError(f'No deck id found in "{(value or "").strip()}". '
                         'Expected a link like https://cyberpunktcg.com/decks/<id>.')
    return match.group(0).lower()

def get_deck(deck_id: str) -> dict:
    response = requests.get(DECK_API.format(deck_id=deck_id), headers=HEADERS, timeout=30)
    if response.status_code == 404:
        raise ValueError(f'Deck {deck_id} was not found, or it is private.')
    response.raise_for_status()
    return response.json()

def image_urls(deck: dict) -> Dict[str, str]:
    """printing id -> signed image URL, for every card in the deck."""
    urls = {}
    for zone in deck.get('zones') or []:
        for entry in zone.get('cards') or []:
            card = entry.get('card') or {}
            if card.get('printing_id') and card.get('image_url'):
                urls[card['printing_id']] = card['image_url']
    return urls

class ImageFetcher:
    """Downloads card images through the deck's signed URLs.

    The URLs expire five minutes after the deck is read, so if one is refused
    the deck is read again to get fresh ones.
    """

    def __init__(self, deck_id: str, deck: dict, front_img_dir: str):
        self.deck_id = deck_id
        self.urls = image_urls(deck)
        self.front_img_dir = front_img_dir

    def download(self, printing_id: str) -> bytes:
        for attempt in range(2):
            url = self.urls.get(printing_id)
            if not url:
                raise ValueError(f'The deck has no image for printing {printing_id}')
            response = requests.get(url, headers={'user-agent': HEADERS['user-agent']}, timeout=60)
            if response.status_code in (401, 403) and attempt == 0:
                print('    Image links expired; reading the deck again.')
                self.urls = image_urls(get_deck(self.deck_id))
                continue
            response.raise_for_status()
            sleep(0.075)
            return response.content
        raise RuntimeError('unreachable')

    def fetch_card(self, index: int, quantity: int, printing_id: str, card_name: str) -> None:
        data = self.download(printing_id)
        extension = guess_extension(data, '.webp')
        clean_name = remove_nonalphanumeric(card_name) or printing_id.replace('-', '')

        for counter in range(quantity):
            image_path = os.path.join(self.front_img_dir, f'{index}{clean_name}{counter + 1}{extension}')
            with open(image_path, 'wb') as f:
                f.write(data)
