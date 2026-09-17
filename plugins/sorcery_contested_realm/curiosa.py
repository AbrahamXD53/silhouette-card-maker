from os import path
from requests import Session
from time import sleep
from json import dumps
import re

def remove_nonalphanumeric(s: str) -> str:
    return re.sub(r'[^\w]', '', s)

# Curiosa moved to sorcerytcg.com; curiosa.io redirects there but drops the API path.
CURIOSA_API_BASE = 'https://sorcerytcg.com/api/trpc/'

session = Session()
CURIOSA_REFERER = 'https://sorcerytcg.com/'

def to_decklist_entry(entry):
    # Keep the shape deck_formats reads: card name, quantity and the chosen printing's image.
    card = entry.get('card') or {}
    variants = [
        {'id': printing.get('id'), 'src': (printing.get('meta') or {}).get('image')}
        for printing in card.get('printings') or []
    ]
    printing = entry.get('printing') or {}
    image = (printing.get('meta') or {}).get('image')
    if image and not any(variant['id'] == printing.get('id') for variant in variants):
        variants.insert(0, {'id': printing.get('id'), 'src': image})

    return {
        'quantity': entry.get('quantity'),
        'variantId': entry.get('printingId'),
        'card': {'name': card.get('name'), 'variants': variants},
    }

def get_curiosa_decklist(deck_id: str):
    deck_id = deck_id.strip()

    payload = {'0': {'json': {'id': deck_id, 'collectionTracking': False}}}
    params = {'batch': '1', 'input': dumps(payload)}
    headers = {'referer': CURIOSA_REFERER}

    r = session.get(CURIOSA_API_BASE + 'deck.get', params=params, headers=headers)

    # Check for 2XX response code
    r.raise_for_status()

    sleep(0.075)

    deck = r.json()[0].get('result', {}).get('data', {}).get('json')
    if not deck:
        raise ValueError(f'Deck {deck_id} was not found or is not public.')

    # Every board (Main, Avatar, Sideboard, Maybeboard), as the old per-board endpoints returned.
    return [to_decklist_entry(entry) for entry in deck.get('decklist') or []]

def request_curiosa(url: str):
    r = session.get(url)

    # Check for 2XX response code
    r.raise_for_status()

    sleep(0.075)
    return r

def fetch_card(
    index: int,
    quantity: int,
    card_name: str,
    image_url: str,
    front_img_dir: str,
):
    card_art = request_curiosa(image_url).content
    clean_name = remove_nonalphanumeric(card_name)

    for counter in range(quantity):
        image_path = path.join(front_img_dir, f'{index}{clean_name}{counter + 1}.png')

        with open(image_path, 'wb') as f:
            f.write(card_art)

def get_handle_card(
    front_img_dir: str,
):
    def configured_fetch_card(index: int, card_name: str, image_url: str, quantity: int = 1):
        fetch_card(
            index,
            quantity,
            card_name,
            image_url,
            front_img_dir
        )

    return configured_fetch_card