from enum import Enum
from typing import Callable

from plugins.star_wars_destiny.arh import extract_decklist_id, get_cards, get_decklist

class DeckFormat(str, Enum):
    ARH_DECKLIST_URL = 'arh_decklist_url'

# Print order: what goes on the table first, then the draw deck.
TYPE_ORDER = ['character', 'battlefield', 'plot', 'upgrade', 'downgrade', 'support', 'event']

def copies_to_print(card: dict, quantity: int) -> int:
    # An elite unique character is one card with two dice, listed as quantity 2.
    # Non-unique characters (troopers, droids...) are separate cards.
    if card.get('type_code') == 'character' and card.get('is_unique'):
        return 1
    return quantity

def parse_arh_decklist_url(deck_text: str, handle_card: Callable) -> None:
    deck = get_decklist(extract_decklist_id(deck_text))
    print(f'Deck: {deck.get("name") or "Untitled deck"}'
          + (f' ({deck["format_name"]})' if deck.get('format_name') else ''))

    cards = get_cards()
    entries = []
    error_lines = []
    for code, slot in (deck.get('slots') or {}).items():
        card = cards.get(code)
        if card is None:
            error_lines.append((code, 'unknown card'))
            print(f'Error: card {code} is not in the card list')
            continue
        quantity = int((slot or {}).get('quantity') or 0)
        if quantity > 0:
            entries.append((card, copies_to_print(card, quantity), quantity))

    def order(entry):
        card = entry[0]
        type_code = card.get('type_code') or ''
        rank = TYPE_ORDER.index(type_code) if type_code in TYPE_ORDER else len(TYPE_ORDER)
        return rank, card.get('name') or '', card['code']

    for index, (card, copies, listed) in enumerate(sorted(entries, key=order), start=1):
        name = card['name'] + (f', {card["subtitle"]}' if card.get('subtitle') else '')
        notes = [card.get('type_name') or card.get('type_code') or '']
        if copies != listed:
            notes.append(f'elite, {listed} dice')
        if card.get('flip_card'):
            notes.append('flip card')
        print(f'Index: {index}, quantity: {copies}, name: {name} ({", ".join(n for n in notes if n)})')

        try:
            handle_card(index, card, copies)
        except Exception as e:
            print(f'Error: {e}')
            error_lines.append((name, e))

    if len(error_lines) > 0:
        print(f'Errors: {error_lines}')

def parse_deck(deck_text: str, format: DeckFormat, handle_card: Callable) -> None:
    if format == DeckFormat.ARH_DECKLIST_URL:
        parse_arh_decklist_url(deck_text, handle_card)
    else:
        raise ValueError('Unrecognized deck format')
