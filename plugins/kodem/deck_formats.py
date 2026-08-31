import re

from enum import Enum
from typing import Callable

class DeckFormat(str, Enum):
    DECKBUILDER = 'deckbuilder'

# The deck builder's "Generar Lista" export writes one line per card as
# "IDRMA-001 - Card Name", with a line repeated for each copy. A bare id and an
# explicit quantity prefix are both accepted too, since people hand-edit lists.
#
#   IDRMA-001 - Card Name
#   3 IDRMA-001
#   IDRMA-001
CARD_LINE_PATTERN = re.compile(
    r'^\s*(?:(\d+)\s*[xX]?\s+)?([A-Za-z]{2,8}-[0-9]+[A-Za-z0-9\-]*?)\s*(?:[-\u2013]\s*(.*?))?\s*$'
)

def parse_deckbuilder(deck_text: str, handle_card: Callable) -> None:
    # Repeated lines mean extra copies, so tally them and download once each.
    tally = {}
    order = []
    error_lines = []

    for line in (deck_text or '').strip().splitlines():
        if not line.strip():
            continue

        match = CARD_LINE_PATTERN.match(line)
        if not match:
            print(f'Skipping: "{line.strip()}"')
            continue

        quantity = int(match.group(1) or 1)
        card_id = match.group(2).upper()
        name = (match.group(3) or '').strip()

        if card_id not in tally:
            tally[card_id] = {'quantity': 0, 'name': name}
            order.append(card_id)
        tally[card_id]['quantity'] += quantity
        if name and not tally[card_id]['name']:
            tally[card_id]['name'] = name

    if not order:
        print('No Kodem card ids found. Expected lines like "IDRMA-001 - Card Name".')
        return

    for index, card_id in enumerate(order, start=1):
        entry = tally[card_id]

        parts = [f'Index: {index}', f'quantity: {entry["quantity"]}', f'id: {card_id}']
        if entry['name']:
            parts.append(f'name: {entry["name"]}')
        print(', '.join(parts))

        try:
            handle_card(index, card_id, entry['name'], entry['quantity'])
        except Exception as e:
            print(f'Error: {e}')
            error_lines.append((card_id, e))

    if len(error_lines) > 0:
        print(f'Errors: {error_lines}')

def parse_deck(deck_text: str, format: DeckFormat, handle_card: Callable) -> None:
    if format == DeckFormat.DECKBUILDER:
        parse_deckbuilder(deck_text, handle_card)
    else:
        raise ValueError("Unrecognized deck format")
