from enum import Enum
from typing import Optional

from plugins.deckplanet.deckplanet import GAMES, card_name, deck_entries, fetch_card, get_deck, parse_deck_reference

class DeckFormat(str, Enum):
    DECKPLANET_URL = 'deckplanet_url'

def parse_deckplanet_url(deck_text: str, game: Optional[str], front_img_dir: str, double_sided_dir: str, include_sideboard: bool) -> None:
    game, deck_id = parse_deck_reference(deck_text, game)
    deck = get_deck(game, deck_id)
    print(f'Deck: {(deck.get("deck_name") or "").strip() or "Untitled deck"} ({GAMES[game][0]})')

    entries, skipped = deck_entries(game, deck, include_sideboard)
    for zone, count in skipped.items():
        print(f'Skipping {count} card(s) in the {zone} zone. Use --include_sideboard to print them too.')
    if not entries:
        print('The deck has no cards.')
        return

    error_lines = []
    for index, (card, quantity, section) in enumerate(entries, start=1):
        name = card_name(card)
        print(f'Index: {index}, quantity: {quantity}, name: {name} ({section})')
        try:
            notes = fetch_card(game, index, quantity, card, front_img_dir, double_sided_dir)
            if notes:
                print(f'    {", ".join(notes)}')
        except Exception as e:
            print(f'Error: {e}')
            error_lines.append((name, e))

    if len(error_lines) > 0:
        print(f'Errors: {error_lines}')

def parse_deck(deck_text: str, format: DeckFormat, game: Optional[str], front_img_dir: str, double_sided_dir: str, include_sideboard: bool = False) -> None:
    if format == DeckFormat.DECKPLANET_URL:
        parse_deckplanet_url(deck_text, game, front_img_dir, double_sided_dir, include_sideboard)
    else:
        raise ValueError('Unrecognized deck format')
