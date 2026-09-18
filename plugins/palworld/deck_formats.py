from enum import Enum

from plugins.palworld.palworldtcg import display_name, entries, extract_deck_id, fetch_card, get_deck

class DeckFormat(str, Enum):
    PALWORLDTCG_URL = 'palworldtcg_url'

def parse_palworldtcg_url(deck_text: str, front_img_dir: str, include_sideboard: bool) -> None:
    deck = get_deck(extract_deck_id(deck_text))
    colors = deck.get('colors') if isinstance(deck.get('colors'), list) else []
    print(f'Deck: {deck.get("title") or "Untitled deck"}' + (f' ({" / ".join(colors)})' if colors else ''))

    # The soul deck is played alongside the main deck; maybe cards are not.
    wanted = [(slug, count, 'main') for slug, count in entries(deck.get('main'))]
    wanted += [(slug, count, 'soul') for slug, count in entries(deck.get('soul'))]
    maybe = entries(deck.get('maybe'))
    if include_sideboard:
        wanted += [(slug, count, 'maybe') for slug, count in maybe]
    elif maybe:
        print(f'Skipping {sum(c for _, c in maybe)} maybe card(s). Use --include_sideboard to print them too.')

    # Merge repeats, keeping first-seen order.
    merged = {}
    for slug, count, section in wanted:
        if slug in merged:
            merged[slug][0] += count
        else:
            merged[slug] = [count, section]

    art = deck.get('art') if isinstance(deck.get('art'), dict) else {}
    error_lines = []
    for index, (slug, (quantity, section)) in enumerate(merged.items(), start=1):
        if quantity <= 0:
            continue
        name = display_name(slug)
        print(f'Index: {index}, quantity: {quantity}, name: {name} ({section})')
        try:
            printing = fetch_card(index, quantity, slug, art, front_img_dir)
            if printing != slug:
                print(f'    printing: {printing}')
        except Exception as e:
            print(f'Error: {e}')
            error_lines.append((name, e))

    if len(error_lines) > 0:
        print(f'Errors: {error_lines}')

def parse_deck(deck_text: str, format: DeckFormat, front_img_dir: str, include_sideboard: bool = False) -> None:
    if format == DeckFormat.PALWORLDTCG_URL:
        parse_palworldtcg_url(deck_text, front_img_dir, include_sideboard)
    else:
        raise ValueError('Unrecognized deck format')
