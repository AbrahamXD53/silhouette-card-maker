from enum import Enum

from plugins.cyberpunk.netdeck import ImageFetcher, extract_deck_id, get_deck

class DeckFormat(str, Enum):
    NETDECK_URL = 'netdeck_url'

# Zones that are not part of the deck you play; fetched only with --include_sideboard.
OPTIONAL_ZONE_WORDS = ('side', 'maybe')

def is_optional_zone(zone: dict) -> bool:
    code = f"{zone.get('zone_code') or ''} {zone.get('display_name') or ''}".lower()
    return any(word in code for word in OPTIONAL_ZONE_WORDS)

def parse_netdeck_url(deck_text: str, front_img_dir: str, include_sideboard: bool) -> None:
    deck_id = extract_deck_id(deck_text)
    deck = get_deck(deck_id)

    owner = (deck.get('owner') or {}).get('display_name')
    print(f'Deck: {deck.get("name") or "Untitled deck"}' + (f' by {owner}' if owner else ''))

    # Tally by printing, in zone order (Legends first), merging repeats across zones.
    wanted = {}
    for zone in deck.get('zones') or []:
        if is_optional_zone(zone) and not include_sideboard:
            skipped = sum(int(entry.get('quantity') or 0) for entry in zone.get('cards') or [])
            if skipped:
                print(f'Skipping {skipped} card(s) in {zone.get("display_name") or zone.get("zone_code")}. '
                      'Use --include_sideboard to print them too.')
            continue
        for entry in zone.get('cards') or []:
            card = entry.get('card') or {}
            printing_id = card.get('printing_id') or entry.get('preferred_printing_id')
            if not printing_id:
                continue
            name = card.get('display_name') or card.get('name') or ''
            item = wanted.setdefault(printing_id, {'name': name, 'quantity': 0, 'zone': zone.get('display_name')})
            item['quantity'] += int(entry.get('quantity') or 0)

    if not wanted:
        print('The deck has no cards.')
        return

    fetcher = ImageFetcher(deck_id, deck, front_img_dir)
    error_lines = []
    for index, (printing_id, item) in enumerate(wanted.items(), start=1):
        if item['quantity'] <= 0:
            continue
        print(f'Index: {index}, quantity: {item["quantity"]}, name: {item["name"]} ({item["zone"]})')
        try:
            fetcher.fetch_card(index, item['quantity'], printing_id, item['name'])
        except Exception as e:
            print(f'Error: {e}')
            error_lines.append((item['name'], e))

    if len(error_lines) > 0:
        print(f'Errors: {error_lines}')

def parse_deck(deck_text: str, format: DeckFormat, front_img_dir: str, include_sideboard: bool = False) -> None:
    if format == DeckFormat.NETDECK_URL:
        parse_netdeck_url(deck_text, front_img_dir, include_sideboard)
    else:
        raise ValueError('Unrecognized deck format')
