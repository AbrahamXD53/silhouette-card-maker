from enum import Enum
from typing import Callable

from plugins.universus.universus_cards import extract_deck_id, get_database, get_deck

class DeckFormat(str, Enum):
    UNIVERSUS_CARDS_URL = 'universus_cards_url'

def parse_universus_cards_url(deck_text: str, handle_card: Callable, include_sideboard: bool) -> None:
    deck = get_deck(extract_deck_id(deck_text))
    print(f'Deck: {deck.get("name") or "Untitled deck"}' + (f' ({deck["format"]})' if deck.get('format') else ''))

    # Each entry is [card id, mainboard copies, sideboard copies]; the starting
    # character is part of the mainboard.
    wanted = []
    skipped_sideboard = 0
    for entry in deck.get('cards') or []:
        card_id, main, side = (list(entry) + [0, 0, 0])[:3]
        copies = int(main or 0) + (int(side or 0) if include_sideboard else 0)
        if not include_sideboard:
            skipped_sideboard += int(side or 0)
        if copies > 0:
            wanted.append((int(card_id), copies))

    if skipped_sideboard:
        print(f'Skipping the {skipped_sideboard}-card sideboard. Use --include_sideboard to print it too.')
    if not wanted:
        print('The deck has no cards.')
        return

    database = get_database()
    error_lines = []
    for index, (card_id, quantity) in enumerate(wanted, start=1):
        card = database.get(card_id)
        if card is None:
            print(f'Index: {index}, quantity: {quantity}, id: {card_id}')
            print(f'Error: card {card_id} is not in the universus.cards database')
            error_lines.append((card_id, 'unknown card'))
            continue

        print(f'Index: {index}, quantity: {quantity}, name: {card["name"]} ({card["set"]} #{card["number"]})'
              + (', double-faced' if card['back_image'] else ''))
        try:
            handle_card(index, card, quantity)
        except Exception as e:
            print(f'Error: {e}')
            error_lines.append((card['name'], e))

    if len(error_lines) > 0:
        print(f'Errors: {error_lines}')

def parse_deck(deck_text: str, format: DeckFormat, handle_card: Callable, include_sideboard: bool = False) -> None:
    if format == DeckFormat.UNIVERSUS_CARDS_URL:
        parse_universus_cards_url(deck_text, handle_card, include_sideboard)
    else:
        raise ValueError('Unrecognized deck format')
