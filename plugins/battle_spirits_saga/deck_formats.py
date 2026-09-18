import re

from enum import Enum
from typing import Callable, Dict, List, Tuple

from plugins.battle_spirits_saga.bssdb import decode_deck, extract_deck_code

class DeckFormat(str, Enum):
    BSSDB_URL = 'bssdb_url'
    BSSDB_TEXT = 'bssdb_text'

# BSSDB's Text export, one line per card:
#   4x EX01-001: Fire Elemental Rubeus
# Hand-written lists are accepted too: "4 BSS01-022", "BSS01-022 x4", "BSS01-022".
CARD_LINE_PATTERN = re.compile(
    r'^\s*(?:(\d+)\s*[xX]?\s+)?([A-Za-z]{2,5}\d{0,2}-\d{3})(?:\s*[xX]\s*(\d+))?\s*(?::\s*(.*?))?\s*$'
)
SECTION_PATTERN = re.compile(r'^\s*(?:=+|#+|//)?\s*(main\s*deck|deck|side\s*board|side)\s*(?:=+|:)?\s*$', re.IGNORECASE)

# (card id, quantity, name)
Card = Tuple[str, int, str]

def tally(cards: List[Card]) -> List[Card]:
    """Merge repeated ids, keeping first-seen order."""
    totals: Dict[str, List] = {}
    for card_id, quantity, name in cards:
        entry = totals.setdefault(card_id, [card_id, 0, name])
        entry[1] += quantity
        if name and not entry[2]:
            entry[2] = name
    return [tuple(entry) for entry in totals.values()]

def fetch_cards(cards: List[Card], handle_card: Callable) -> None:
    if not cards:
        print('No Battle Spirits Saga cards found.')
        return

    error_lines = []
    for index, (card_id, quantity, name) in enumerate(cards, start=1):
        parts = [f'Index: {index}', f'quantity: {quantity}', f'id: {card_id}']
        if name:
            parts.append(f'name: {name}')
        print(', '.join(parts))

        try:
            handle_card(index, card_id, name, quantity)
        except Exception as e:
            print(f'Error: {e}')
            error_lines.append((card_id, e))

    if len(error_lines) > 0:
        print(f'Errors: {error_lines}')

def parse_bssdb_url(deck_text: str, handle_card: Callable, include_sideboard: bool) -> None:
    deck = decode_deck(extract_deck_code(deck_text))

    title = deck['name'] or 'Untitled deck'
    print(f'Deck: {title}' + (f' by {deck["author"]}' if deck['author'] else ''))

    cards = [(card_id.upper(), int(quantity), '') for card_id, quantity in deck['deck'].items()]
    if include_sideboard:
        cards += [(card_id.upper(), int(quantity), '') for card_id, quantity in deck['sideboard'].items()]
    elif deck['sideboard']:
        print(f'Skipping the {sum(deck["sideboard"].values())}-card sideboard. Use --include_sideboard to print it too.')

    fetch_cards(tally(cards), handle_card)

def parse_bssdb_text(deck_text: str, handle_card: Callable, include_sideboard: bool) -> None:
    cards = []
    in_sideboard = False
    skipped_sideboard = 0

    for line in (deck_text or '').splitlines():
        if not line.strip():
            continue

        section = SECTION_PATTERN.match(line)
        if section:
            in_sideboard = section.group(1).lower().startswith('side')
            continue

        match = CARD_LINE_PATTERN.match(line)
        if not match:
            print(f'Skipping: "{line.strip()}"')
            continue

        quantity = int(match.group(1) or match.group(3) or 1)
        if in_sideboard and not include_sideboard:
            skipped_sideboard += quantity
            continue

        cards.append((match.group(2).upper(), quantity, (match.group(4) or '').strip()))

    if skipped_sideboard:
        print(f'Skipping the {skipped_sideboard}-card sideboard. Use --include_sideboard to print it too.')

    fetch_cards(tally(cards), handle_card)

def parse_deck(deck_text: str, format: DeckFormat, handle_card: Callable, include_sideboard: bool = False) -> None:
    if format == DeckFormat.BSSDB_URL:
        parse_bssdb_url(deck_text, handle_card, include_sideboard)
    elif format == DeckFormat.BSSDB_TEXT:
        parse_bssdb_text(deck_text, handle_card, include_sideboard)
    else:
        raise ValueError('Unrecognized deck format')
