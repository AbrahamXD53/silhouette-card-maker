from enum import Enum
from typing import Optional

from plugins.shard_bugs.shardbugs import SECTION_PATTERN, describe, fetch_card, matches, parse_line

class DeckFormat(str, Enum):
    DECKLIST = 'decklist'

def parse_decklist(deck_text: str, preferred_set: Optional[str], front_img_dir: str) -> None:
    wanted = []
    for line in (deck_text or '').splitlines():
        if not line.strip() or line.lstrip().startswith(('//', '#')):
            continue

        parsed = parse_line(line)
        # A section header ("Main deck", "Tokens") is only skipped when it is not a card.
        if not parsed or (SECTION_PATTERN.match(line) and not matches(parsed[1], preferred_set)):
            print(f'Skipping: "{line.strip()}"')
            continue
        wanted.append(parsed)

    if not wanted:
        print('No Shard Bugs cards found. Expected lines like "3 Honey Alchemist" or "3 001/110".')
        return

    error_lines = []
    index = 0
    for quantity, identifier, hint in wanted:
        found = matches(identifier, hint or preferred_set)
        if not found:
            print(f'Error: "{identifier}" is not in the Shard Bugs card list')
            error_lines.append((identifier, 'unknown card'))
            continue

        index += 1
        card = found[0]
        print(f'Index: {index}, quantity: {quantity}, name: {card.get("CardName")} ({describe(card)})')
        if len(found) > 1:
            print(f'    {len(found)} printings match; add a set in brackets or use --set to choose another')
        try:
            fetch_card(index, quantity, card, front_img_dir)
        except Exception as e:
            print(f'Error: {e}')
            error_lines.append((card.get('CardName'), e))

    if len(error_lines) > 0:
        print(f'Errors: {error_lines}')

def parse_deck(deck_text: str, format: DeckFormat, preferred_set: Optional[str], front_img_dir: str) -> None:
    if format == DeckFormat.DECKLIST:
        parse_decklist(deck_text, preferred_set, front_img_dir)
    else:
        raise ValueError('Unrecognized deck format')
