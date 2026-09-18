from enum import Enum

from plugins.weiss_schwarz.encoredecks import display_name, extract_deck_id, fetch_card, get_deck, tally

class DeckFormat(str, Enum):
    ENCOREDECKS_URL = 'encoredecks_url'

def parse_encoredecks_url(deck_text: str, front_img_dir: str) -> None:
    deck = get_deck(extract_deck_id(deck_text))
    languages = sorted({card.get('lang') for card in deck.get('cards') or [] if card.get('lang')})
    print(f'Deck: {deck.get("name") or "Untitled deck"}' + (f' ({"/".join(languages)})' if languages else ''))

    error_lines = []
    for index, (card, quantity) in enumerate(tally(deck), start=1):
        name = display_name(card)
        print(f'Index: {index}, quantity: {quantity}, name: {name} ({card.get("cardcode")})')
        try:
            source = fetch_card(index, quantity, card, front_img_dir)
            print(f'    image: {source}')
        except Exception as e:
            print(f'Error: {e}')
            error_lines.append((name, e))

    if len(error_lines) > 0:
        print(f'Errors: {error_lines}')

def parse_deck(deck_text: str, format: DeckFormat, front_img_dir: str) -> None:
    if format == DeckFormat.ENCOREDECKS_URL:
        parse_encoredecks_url(deck_text, front_img_dir)
    else:
        raise ValueError('Unrecognized deck format')
