from enum import Enum
from typing import Optional

from plugins.exburst.exburst import GAMES, fetch_card, get_cards, get_config, get_deck, parse_lines, resolve_deck

class DeckFormat(str, Enum):
    EXBURST_URL = 'exburst_url'

def parse_exburst_url(deck_text: str, game: Optional[str], front_img_dir: str, include_sideboard: bool) -> None:
    game, deck_id = resolve_deck(deck_text, game)
    config = get_config(game)
    deck = get_deck(config, deck_id)
    print(f'Deck: {(deck.get("decklist_name") or "").strip() or "Untitled deck"} ({GAMES[game][0]})')

    wanted = parse_lines(deck.get('decklist_content'))
    side = parse_lines(deck.get('sidedeck'))
    if include_sideboard:
        wanted += side
    elif side:
        print(f'Skipping the {sum(q for _, q in side)}-card side deck. Use --include_sideboard to print it too.')

    # Merge repeats, keeping first-seen order.
    totals = {}
    for card_id, quantity in wanted:
        totals[card_id] = totals.get(card_id, 0) + quantity
    if not totals:
        print('The deck has no cards.')
        return

    cards = get_cards(config, list(totals))
    error_lines = []
    for index, (card_id, quantity) in enumerate(totals.items(), start=1):
        card = cards.get(card_id)
        name = (card or {}).get('name') or card_id
        print(f'Index: {index}, quantity: {quantity}, name: {name} ({card_id})')
        if card is None:
            print(f'Error: {card_id} is not in the {GAMES[game][0]} card list')
            error_lines.append((card_id, 'unknown card'))
            continue
        try:
            notes = fetch_card(index, quantity, card_id, card, front_img_dir)
            if notes:
                print(f'    {", ".join(notes)}')
        except Exception as e:
            print(f'Error: {e}')
            error_lines.append((name, e))

    if len(error_lines) > 0:
        print(f'Errors: {error_lines}')

def parse_deck(deck_text: str, format: DeckFormat, game: Optional[str], front_img_dir: str, include_sideboard: bool = False) -> None:
    if format == DeckFormat.EXBURST_URL:
        parse_exburst_url(deck_text, game, front_img_dir, include_sideboard)
    else:
        raise ValueError('Unrecognized deck format')
