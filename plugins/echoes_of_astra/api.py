from os import path
from requests import Response, Session
from time import sleep
import re

ASTRA_REST_BASE = 'https://pphqxjttokwymgemkqvh.supabase.co/rest/v1'

session = Session()

# Supabase public/anon key - this is intentionally public and safe to commit.
# It only provides read access to public decks via Row Level Security (RLS).
ASTRA_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InBwaHF4anR0b2t3eW1nZW1rcXZoIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTg3MzQ3OTcsImV4cCI6MjA3NDMxMDc5N30.z-xZSeC4Jl_s3EpeoCXfD8nl6Q4yDV6EohAgmsSUaS0'

def request_astra_rest(table: str, params: dict):
    headers = {
        'user-agent': 'silhouette-card-maker/0.1', 'accept': '*/*',
        'ApiKey': ASTRA_ANON_KEY
    }

    resp = session.get(f'{ASTRA_REST_BASE}/{table}', params=params, headers=headers, timeout=20)
    resp.raise_for_status()
    return resp.json()

def get_astra_deck(deck_id: str):
    # deck_cards.card_id no longer has a foreign key to cards, so Supabase can't
    # embed the cards in one query. Fetch the deck rows, then the cards they name.
    decks = request_astra_rest('decks', {'select': 'id,is_public', 'id': f'eq.{deck_id}'})
    if not decks:
        raise ValueError(f'Deck {deck_id} was not found or is not public.')

    deck_cards = request_astra_rest('deck_cards', {'select': 'quantity,card_id', 'deck_id': f'eq.{deck_id}'})
    card_ids = sorted({row['card_id'] for row in deck_cards if row.get('card_id')})

    cards = {}
    if card_ids:
        quoted = ','.join(f'"{card_id}"' for card_id in card_ids)
        for card in request_astra_rest('cards', {'select': '*', 'id': f'in.({quoted})'}):
            cards[card['id']] = card

    # Same shape the embedded query used to return: [{quantity, cards: {...}}]
    return [{'quantity': row.get('quantity'), 'cards': cards.get(row.get('card_id'), {})} for row in deck_cards]

def request_astra(query: str) -> Response:
    r = session.get(query, headers = {'user-agent': 'silhouette-card-maker/0.1', 'accept': '*/*'})

    # Check for 2XX response code
    r.raise_for_status()

    sleep(0.075)

    return r

def remove_nonalphanumeric(s: str) -> str:
    return re.sub(r'[^\w]', '', s)

def fetch_card(
    index: int,
    quantity: int,
    card_name: str,
    image_url: str,
    front_img_dir: str,
):
    card_art = request_astra(image_url).content
    clean_card_name = remove_nonalphanumeric(card_name)

    for counter in range(quantity):
        image_path = path.join(front_img_dir, f'{str(index)}{clean_card_name}{str(counter + 1)}.png')

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
