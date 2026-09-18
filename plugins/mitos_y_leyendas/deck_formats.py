from enum import Enum
from typing import Callable

from plugins.mitos_y_leyendas.shadowforge import extract_deck_id, get_deck

class DeckFormat(str, Enum):
    SHADOWFORGE_URL = 'shadowforge_url'

def entries_of(deck: dict, key: str):
    for entry in deck.get(key) or []:
        card = entry.get('card_detail')
        quantity = int(entry.get('quantity') or 0)
        if isinstance(card, dict) and quantity > 0:
            yield card, quantity

def parse_shadowforge_url(deck_text: str, handle_card: Callable, include_sideboard: bool) -> None:
    deck = get_deck(extract_deck_id(deck_text))
    owner = deck.get('owner_username')
    print(f'Deck: {deck.get("name") or "Untitled deck"}' + (f' by {owner}' if owner else ''))

    cards = []
    # The starting gold is chosen separately from the 49 other cards.
    gold = deck.get('starting_gold_detail')
    if isinstance(gold, dict) and gold.get('image_url'):
        cards.append((gold, 1, 'starting gold'))

    cards += [(card, quantity, 'deck') for card, quantity in entries_of(deck, 'entries')]

    sideboard = list(entries_of(deck, 'sideboard_entries'))
    if include_sideboard:
        cards += [(card, quantity, 'sideboard') for card, quantity in sideboard]
    elif sideboard:
        print(f'Skipping the {sum(q for _, q in sideboard)}-card sideboard. Use --include_sideboard to print it too.')

    # Merge repeats (a card in both the deck and the sideboard) into one entry.
    merged = {}
    for card, quantity, section in cards:
        key = card.get('id') or card.get('image_url')
        if key in merged:
            merged[key][1] += quantity
        else:
            merged[key] = [card, quantity, section]

    if not merged:
        print('The deck has no cards.')
        return

    error_lines = []
    for index, (card, quantity, section) in enumerate(merged.values(), start=1):
        name = card.get('name') or ''
        edition = card.get('edition_title')
        print(f'Index: {index}, quantity: {quantity}, name: {name}' + (f' ({edition})' if edition else '')
              + (f' [{section}]' if section != 'deck' else ''))
        try:
            handle_card(index, card, quantity)
        except Exception as e:
            print(f'Error: {e}')
            error_lines.append((name, e))

    if len(error_lines) > 0:
        print(f'Errors: {error_lines}')

def parse_deck(deck_text: str, format: DeckFormat, handle_card: Callable, include_sideboard: bool = False) -> None:
    if format == DeckFormat.SHADOWFORGE_URL:
        parse_shadowforge_url(deck_text, handle_card, include_sideboard)
    else:
        raise ValueError('Unrecognized deck format')
