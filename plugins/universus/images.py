import os
import re
from enum import Enum
from time import sleep

import requests

from plugins.universus import official
from plugins.universus.universus_cards import image_url
from utilities import guess_extension

HEADERS = {'user-agent': 'silhouette-card-maker/0.1', 'accept': '*/*'}

class ImageSource(str, Enum):
    OFFICIAL = 'official'
    UNIVERSUS_CARDS = 'universus_cards'

def remove_nonalphanumeric(text: str) -> str:
    return re.sub(r'[^a-zA-Z0-9]', '', text or '')

def download(url: str) -> bytes:
    response = requests.get(url, headers=HEADERS, timeout=60)
    response.raise_for_status()
    sleep(0.075)
    return response.content

def pick_images(card: dict, source: ImageSource):
    """Return (front url, back url or None, description of where they came from)."""
    fallback = (image_url(card['image']), image_url(card['back_image']) if card['back_image'] else None)

    if source != ImageSource.OFFICIAL:
        return (*fallback, 'universus.cards')

    match = official.find_card(card['name'], card['set'], card['number'])
    if match is None:
        return (*fallback, 'universus.cards (no official match)')

    # Keep both sides of a double-faced card from the same source, so they match.
    if card['back_image'] and not match['back_image_url']:
        return (*fallback, 'universus.cards (official image has no back)')

    return match['image_url'], match['back_image_url'], f'official ({match["match"]})'

def write_copies(data: bytes, directory: str, stem: str, quantity: int, default_extension: str) -> None:
    extension = guess_extension(data, default_extension)
    for counter in range(quantity):
        with open(os.path.join(directory, f'{stem}{counter + 1}{extension}'), 'wb') as f:
            f.write(data)

def fetch_card(index: int, quantity: int, card: dict, source: ImageSource, front_img_dir: str, double_sided_dir: str) -> None:
    front_url, back_url, origin = pick_images(card, source)
    print(f'    image: {origin}')

    stem = f'{index}{remove_nonalphanumeric(card["name"]) or card["id"]}'
    write_copies(download(front_url), front_img_dir, stem, quantity, '.png')
    if back_url:
        # Same filename in double_sided/, which is how create_pdf.py pairs the sides.
        write_copies(download(back_url), double_sided_dir, stem, quantity, '.png')

def get_handle_card(source: ImageSource, front_img_dir: str, double_sided_dir: str):
    def configured_fetch_card(index: int, card: dict, quantity: int = 1):
        fetch_card(index, quantity, card, source, front_img_dir, double_sided_dir)

    return configured_fetch_card
