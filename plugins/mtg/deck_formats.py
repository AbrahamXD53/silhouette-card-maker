import csv
import io
import json
import os
import re
import urllib.parse

from enum import Enum
from typing import Callable, Optional, Tuple
from xml.etree import ElementTree as ET

from plugins.mtg.patterns import DECKSTATS_PATTERN, MOXFIELD_PATTERN

import cloudscraper
import mtg_parser
import requests

from plugins.mtg.common import remove_nonalphanumeric
from utilities import guess_extension

card_data_tuple = Tuple[str, str, int, int]

def parse_deck_helper(deck_text: str, is_card_line: Callable[[str], bool], extract_card_data: Callable[[str], card_data_tuple], handle_card: Callable) -> None:
    error_lines = []

    index = 0
    for line in deck_text.strip().split('\n'):
        if is_card_line(line):
            index = index + 1

            name, set_code, collector_number, quantity = extract_card_data(line)

            parts = [f'Index: {index}', f'quantity: {quantity}']
            if set_code: parts.append(f'set code: {set_code}')
            if collector_number: parts.append(f'collector number: {collector_number}')
            if name: parts.append(f'name: {name}')
            print(', '.join(parts))
            try:
                handle_card(index, name, set_code, collector_number, quantity)
            except Exception as e:
                print(f'Error: {e}')
                error_lines.append((line, e))

        else:
            print(f'Skipping: "{line}"')

    if len(error_lines) > 0:
        print(f'Errors: {error_lines}')

# Isshin, Two Heavens as One
# Arid Mesa
# Battlefield Forge
# Blazemire Verge
# Blightstep Pathway
# Blood Crypt
def parse_simple_list(deck_text, handle_card: Callable) -> None:
    def is_simple_card_line(line) -> bool:
        return bool(line.strip())

    def extract_simple_card_data(line) -> card_data_tuple:
        return (line.strip(), "", "", 1)

    parse_deck_helper(deck_text, is_simple_card_line, extract_simple_card_data, handle_card)

# About
# Name Death & Taxes

# Companion
# 1 Yorion, Sky Nomad

# Deck
# 2 Arid Mesa
# 1 Lion Sash
# 1 Loran of the Third Path
# 2 Witch Enchanter

# Sideboard
# 1 Containment Priest
def parse_mtga(deck_text, handle_card: Callable) -> None:
    pattern = re.compile(r'(\d+)x?\s+(.+?)\s+\((\w+)\)\s+(\d+)', re.IGNORECASE)
    fallback_pattern = re.compile(r'(\d+)x?\s+(.+)')

    def is_mtga_card_line(line) -> bool:
        return bool(pattern.match(line) or fallback_pattern.match(line))

    def extract_mtga_card_data(line) -> card_data_tuple:
        match = pattern.match(line)
        if match:
            quantity = int(match.group(1))
            name = match.group(2).strip()
            set_code = match.group(3).strip()
            collector_number = match.group(4).strip()

            return (name, set_code, collector_number, quantity)
        else:
            # Handle simpler "1x Mountain" lines
            fallback_match = fallback_pattern.match(line)
            quantity = int(fallback_match.group(1))
            name = fallback_match.group(2).strip()

            return (name, "", "", quantity)

    parse_deck_helper(deck_text, is_mtga_card_line, extract_mtga_card_data, handle_card)

# 1 Abzan Battle Priest
# 1 Abzan Falconer
# 1 Aerial Surveyor
# 1 Ainok Bond-Kin
# 1 Angel of Condemnation
# 2 Witch Enchanter

# SIDEBOARD:
# 1 Containment Priest
# 3 Deafening Silence
# 2 Disruptor Flute
def parse_mtgo(deck_text, handle_card: Callable) -> None:
    def is_mtgo_card_line(line) -> bool:
        line = line.strip()
        return bool(line and line[0].isdigit())

    def extract_mtgo_card_data(line) -> card_data_tuple:
        parts = line.split(' ', 1)
        quantity = int(parts[0])
        name = parts[1].strip()
        return (name, "", "", quantity)

    parse_deck_helper(deck_text, is_mtgo_card_line, extract_mtgo_card_data, handle_card)

# 1x Agadeem's Awakening // Agadeem, the Undercrypt (znr) 90 [Resilience,Land]
# 1x Ancient Cornucopia (big) 16 [Maybeboard{noDeck}{noPrice},Mana Advantage]
# 1x Arachnogenesis (cmm) 647 [Maybeboard{noDeck}{noPrice},Mass Disruption]
# 1x Ashnod's Altar (ema) 218 *F* [Mana Advantage]
# 1x Assassin's Trophy (sld) 139 [Targeted Disruption]
# 2x Boseiju Reaches Skyward // Branch of Boseiju (neo) 177 [Ramp] ^Have,#37d67a^
def parse_archidekt(deck_text, handle_card: Callable) -> None:
    pattern = re.compile(r'^(\d+)x?\s+(.+?)\s+\((\w+)\)\s+([\w\-]+).*')
    def is_archidekt_card_line(line: str) -> bool:
        return bool(pattern.match(line))

    def extract_archidekt_card_data(line: str) -> card_data_tuple:
        match = pattern.match(line)
        quantity = int(match.group(1))
        name = match.group(2).strip()
        set_code = match.group(3).strip()
        collector_number = match.group(4).strip()

        return (name, set_code, collector_number, quantity)

    parse_deck_helper(deck_text, is_archidekt_card_line, extract_archidekt_card_data, handle_card)

# //Main
# 1 [2XM#310] Ash Barrens
# 1 Blinkmoth Nexus
# 1 Bloodstained Mire
# 1 Buried Ruin
# 2 Command Beacon

# //Sideboard
# 1 [2XM#315] Darksteel Citadel

# //Maybeboard
# 1 [MID#159] Smoldering Egg // Ashmouth Dragon
def parse_deckstats(deck_text, handle_card: Callable) -> None:
    def is_deckstats_card_line(line: str) -> bool:
        return bool(DECKSTATS_PATTERN.match(line))

    def extract_deckstats_card_data(line: str) -> card_data_tuple:
        match = DECKSTATS_PATTERN.match(line)
        quantity = int(match.group(1))
        set_code = match.group(2) or ""
        collector_number = match.group(3) or ""
        name = re.sub(r'\s*#!.*$', '', match.group(4).strip())

        return (name, set_code, collector_number, quantity)

    parse_deck_helper(deck_text, is_deckstats_card_line, extract_deckstats_card_data, handle_card)

# 1 Lulu, Loyal Hollyphant (CLB) 477 *E*
# 1 Abzan Battle Priest (IMA) 2
# 1 Abzan Falconer (ZNC) 9
# 1 Aerial Surveyor (NEC) 5
# 1 Ainok Bond-Kin (2X2) 5
# 1 Pegasus Guardian // Rescue the Foal (CLB) 36
# 4 Plains (MOM) 277
# 2 Witch Enchanter // Witch-Blessed Meadow (MH3) 239

# SIDEBOARD:
# 1 Containment Priest (M21) 13
# 1 Deafening Silence (MB2) 9
# 1 Disruptor Flute (MH3) 209
def parse_moxfield(deck_text, handle_card: Callable) -> None:
    def is_moxfield_card_line(line: str) -> bool:
        return bool(MOXFIELD_PATTERN.match(line))

    def extract_moxfield_card_data(line: str) -> card_data_tuple:
        match = MOXFIELD_PATTERN.match(line)
        quantity = int(match.group(1))
        name = match.group(2).strip()
        set_code = match.group(3).strip()
        collector_number = match.group(4).strip()

        return (name, set_code, collector_number, quantity)

    parse_deck_helper(deck_text, is_moxfield_card_line, extract_moxfield_card_data, handle_card)

# Scryfall deck builder JSON
def parse_scryfall_json(deck_text, handle_card: Callable, front_img_dir: str = '', double_sided_dir: str = '') -> None:
    data = json.loads(deck_text)
    entries = data.get("entries", {})
    for entry in entries.values():
        for index, item in enumerate(entry, start=1):
            card_digest = item.get("card_digest", {})
            if card_digest is None:
                continue

            name = card_digest.get("name", "")
            set_code = card_digest.get("set", "")
            collector_number = card_digest.get("collector_number", "")
            quantity = item.get("count", 1)
            image_uris = card_digest.get("image_uris")

            parts = [f'Index: {index}', f'quantity: {quantity}']
            if set_code: parts.append(f'set code: {set_code}')
            if collector_number: parts.append(f'collector number: {collector_number}')
            if name: parts.append(f'name: {name}')
            print(', '.join(parts))

            # Scryfall JSON may already include image URIs, so we can fetch directly without an extra Scryfall API call. If not, fall back to handle_card which will query Scryfall by set/collector number or name.
            if image_uris and front_img_dir:
                clean_name = remove_nonalphanumeric(name)

                front_url = image_uris.get("front")
                if front_url:
                    response = requests.get(front_url, headers={'user-agent': 'silhouette-card-maker/0.1', 'accept': '*/*'})
                    response.raise_for_status()
                    for counter in range(quantity):
                        with open(os.path.join(front_img_dir, f'{index}{clean_name}{counter + 1}.png'), 'wb') as f:
                            f.write(response.content)

                back_url = image_uris.get("back")
                if back_url and double_sided_dir:
                    response = requests.get(back_url, headers={'user-agent': 'silhouette-card-maker/0.1', 'accept': '*/*'})
                    response.raise_for_status()
                    for counter in range(quantity):
                        with open(os.path.join(double_sided_dir, f'{index}{clean_name}{counter + 1}.png'), 'wb') as f:
                            f.write(response.content)
            else:
                handle_card(index, name, set_code, collector_number, quantity)

# MPCFill XML
def extract_card_name(raw_name: str) -> str:
    """Extract card name by stripping the file extension (e.g. 'Mountain.png' -> 'Mountain')."""
    parts = raw_name.split(".")
    return ".".join(parts[:-1]) if len(parts) > 1 else parts[0]


def extract_mpcfill_card_ids(deck_text: str) -> set[str]:
    """Extract all unique card IDs from MPCFill XML for prefetching."""
    data = ET.fromstring(deck_text)
    card_ids = set()

    fronts = data.find("fronts")
    if fronts:
        for front in fronts.findall("card"):
            card_ids.add(front.find("id").text)

    backs = data.find("backs")
    if backs:
        for back in backs.findall("card"):
            card_ids.add(back.find("id").text)

    return card_ids


def parse_mpcfill_xml(deck_text, handle_card: Callable) -> None:
    """
    Parse MPCFill XML and call handle_card once per slot.

    Each slot represents one physical card. handle_card signature:
        handle_card(slot, front_id, front_name, back_id, back_name)

    back_id and back_name will be None if the slot has no custom back.
    """
    data = ET.fromstring(deck_text)
    fronts = data.find("fronts")
    backs = data.find("backs")

    card_qty = int(data.find("details").find("quantity").text)

    # Create per-slot entries: {front_id, front_name, back_id, back_name}
    slots = [{"front_id": None, "front_name": None, "back_id": None, "back_name": None} for _ in range(card_qty)]

    if fronts is None:
        raise ValueError("No fronts found in decklist")

    # Assign fronts to ALL their slots
    for front in fronts.findall("card"):
        card_id = front.find("id").text
        name = extract_card_name(front.find("name").text)
        slot_indices = [int(s) for s in front.find("slots").text.split(",")]
        for slot_idx in slot_indices:
            slots[slot_idx]["front_id"] = card_id
            slots[slot_idx]["front_name"] = name

    # Assign backs to ALL their slots
    if backs:
        for back in backs.findall("card"):
            card_id = back.find("id").text
            name = extract_card_name(back.find("name").text)
            slot_indices = [int(s) for s in back.find("slots").text.split(",")]
            for slot_idx in slot_indices:
                slots[slot_idx]["back_id"] = card_id
                slots[slot_idx]["back_name"] = name

    # Call handle_card once per slot (1-indexed for display and filenames)
    for slot_idx, slot in enumerate(slots):
        slot_num = slot_idx + 1
        if slot["front_id"] is None:
            print(f"Warning: Slot {slot_num} has no front image, skipping")
            continue

        print(f"Slot {slot_num}: {slot['front_name']}" + (f" / {slot['back_name']}" if slot['back_id'] else ""))
        handle_card(slot_num, slot["front_id"], slot["front_name"], slot["back_id"], slot["back_name"])

# CubeCobra CSV
# Exported from CubeCobra (https://cubecobra.com)
# CSV columns: name, CMC, Type, Color, Set, Collector Number, Rarity, Color Category,
#              status, Finish, maybeboard, image URL, image Back URL, tags, Notes, MTGO ID, Custom
#
# Cards with an image URL are fetched directly. Cards without an image URL are fetched
# from Scryfall using set and collector number, or by name as a fallback.
# Identical cards are tallied to minimize Scryfall API calls.
def parse_cubecobra_csv(deck_text, handle_card: Callable, front_img_dir: str, double_sided_dir: str) -> None:
    reader = csv.DictReader(io.StringIO(deck_text))

    # Phase 1: Parse all rows and tally unique cards
    # Key: (name, set_code, collector_number, image_url, image_back_url)
    # Value: quantity (number of identical rows)
    unique_cards = {}

    for row in reader:
        name = row.get('name', '')
        set_code = row.get('Set', '')
        collector_number = row.get('Collector Number', '')
        image_url = row.get('image URL', '')
        image_back_url = row.get('image Back URL', '')

        key = (name, set_code, collector_number, image_url, image_back_url)
        unique_cards[key] = unique_cards.get(key, 0) + 1

    total_cards = sum(unique_cards.values())
    print(f'Parsed {total_cards} cards into {len(unique_cards)} unique entries')

    # Phase 2: Process unique cards
    error_lines = []

    index = 0
    for (name, set_code, collector_number, image_url, image_back_url), quantity in unique_cards.items():
        index += 1

        parts = [f'Index: {index}', f'quantity: {quantity}']
        if set_code: parts.append(f'set code: {set_code}')
        if collector_number: parts.append(f'collector number: {collector_number}')
        if name: parts.append(f'name: {name}')
        print(', '.join(parts))

        try:
            if image_url:
                # Fetch image directly from URL
                print(f'Fetching image from URL: {image_url}')
                clean_name = remove_nonalphanumeric(name)
                response = requests.get(image_url, headers={'user-agent': 'silhouette-card-maker/0.1', 'accept': '*/*'})
                response.raise_for_status()
                ext = guess_extension(response.content)
                for counter in range(quantity):
                    image_path = os.path.join(front_img_dir, f'{str(index)}{clean_name}{str(counter + 1)}{ext}')
                    with open(image_path, 'wb') as f:
                        f.write(response.content)

                if image_back_url:
                    print(f'Fetching back image from URL: {image_back_url}')
                    back_response = requests.get(image_back_url, headers={'user-agent': 'silhouette-card-maker/0.1', 'accept': '*/*'})
                    back_response.raise_for_status()
                    back_ext = guess_extension(back_response.content)
                    for counter in range(quantity):
                        image_path = os.path.join(double_sided_dir, f'{str(index)}{clean_name}{str(counter + 1)}{back_ext}')
                        with open(image_path, 'wb') as f:
                            f.write(back_response.content)
            else:
                # Fetch from Scryfall using set/collector number or name
                handle_card(index, name, set_code, collector_number, quantity)
        except Exception as e:
            print(f'Error: {e}')
            error_lines.append((name, e))

    if len(error_lines) > 0:
        print(f'Errors: {error_lines}')

# URL Auto-Import
#   Supported sites:
#     Aetherhub, Archidekt, Deckstats, Moxfield, MTG Goldfish,
#     MTGJSON, Scryfall, Tapped Out, TCGPlayer
def parse_url(deck_url, handle_card: Callable, front_img_dir: str = '', double_sided_dir: str = '',
              copies: int = 1, unique: str = None, order: str = None) -> None:
    # A search URL is not a decklist; mtg_parser cannot read one, so hand it to
    # the query parser rather than failing on something we can clearly handle.
    if is_scryfall_search_url(deck_url):
        print('Detected a Scryfall search URL.')
        parse_scryfall_query(deck_url, front_img_dir, double_sided_dir, copies, unique, order)
        return

    scraper = cloudscraper.create_scraper()
    try:
        cards = mtg_parser.parse_deck(deck_url, scraper)
    except Exception as e:
        print(f"Error while fetching deck from URL: {deck_url} ({e})")
        return

    if not cards:
        # mtg_parser returns None when no parser recognizes the URL (unsupported
        # site or malformed link), as opposed to a recognized site failing to fetch.
        print(f"URL not recognized by any supported site: {deck_url}")
        return

    error_lines = []
    card_iter = iter(cards)
    index = 0

    while True:
        try:
            card = next(card_iter)
        except StopIteration:
            break
        except Exception as e:
            # mtg_parser lazily fetches/parses per card, so a site-side issue
            # (deck deleted, made private, malformed API response, etc.) only
            # surfaces here, mid-iteration, rather than when parse_deck() is called.
            print(
                f"Failed to parse deck from URL: {deck_url}. "
                f"The deck may be private, deleted, or the URL may be incorrect. "
                f"(underlying error: {e!r})"
            )
            break

        index += 1
        name = card.name
        set_code = card.extension
        collector_number = card.number
        quantity = card.quantity

        parts = [f'Index: {index}', f'quantity: {quantity}']
        if set_code: parts.append(f'set code: {set_code}')
        if collector_number: parts.append(f'collector number: {collector_number}')
        if name: parts.append(f'name: {name}')
        print(', '.join(parts))
        try:
            handle_card(index, name, set_code, collector_number, quantity)
        except Exception as e:
            print(f'Error: {e}')
            error_lines.append((name, e))

    if len(error_lines) > 0:
        print(f'Errors: {error_lines}')

class DeckFormat(str, Enum):
    ARCHIDEKT = "archidekt"
    CUBECOBRA_CSV = "cubecobra_csv"
    DECKSTATS = "deckstats"
    MOXFIELD = "moxfield"
    MPCFILL_XML = "mpcfill_xml"
    MTGA = "mtga"
    MTGO = "mtgo"
    SCRYFALL_JSON = "scryfall_json"
    SCRYFALL_QUERY = "scryfall_query"
    SIMPLE = "simple"
    URL = "url"

SCRYFALL_SEARCH_URL = 'https://api.scryfall.com/cards/search'

# Real parameters of the Scryfall search API. The search page also puts UI-only
# ones in the address bar (`as=grid`), which are ignored.
SCRYFALL_SEARCH_PARAMS = ('unique', 'order', 'dir', 'include_extras', 'include_multilingual', 'include_variations')

def is_scryfall_search_url(text: str) -> bool:
    text = (text or '').strip()
    if not text:
        return False
    lowered = text.lower()
    if not lowered.startswith(('http://', 'https://', 'scryfall.com/', 'api.scryfall.com/')):
        return False
    parsed = urllib.parse.urlparse(text if '://' in lowered else 'https://' + text)
    return parsed.netloc.lower().endswith('scryfall.com') and '/search' in parsed.path

def split_scryfall_search(text: str) -> Tuple[str, dict]:
    """Accept either a bare query or a Scryfall search URL.

    Returns the query plus any search parameters carried in the URL, so pasting
    a link straight from the address bar keeps its unique/order settings.
    """
    text = (text or '').strip()
    if not is_scryfall_search_url(text):
        return text, {}

    raw = text if '://' in text.lower() else 'https://' + text
    query_string = urllib.parse.parse_qs(urllib.parse.urlparse(raw).query)
    query = (query_string.get('q') or [''])[0].strip()
    params = {k: query_string[k][0] for k in SCRYFALL_SEARCH_PARAMS if query_string.get(k)}
    return query, params


def scryfall_face_images(card: dict) -> Tuple[Optional[str], Optional[str]]:
    """(front, back) PNG urls for a Scryfall card object.

    Single-faced cards carry a top-level image_uris. Transform, modal and
    reversible cards instead carry one image per entry in card_faces, so the
    second face becomes the double-sided back.
    """
    images = card.get('image_uris') or {}
    if images.get('png'):
        return images['png'], None

    faces = [f.get('image_uris', {}).get('png') for f in (card.get('card_faces') or [])]
    faces = [url for url in faces if url]
    if not faces:
        return None, None
    return faces[0], (faces[1] if len(faces) > 1 else None)

# Scryfall search query
#   Any query the search page accepts, e.g. (game:paper) set:slz prefer:best
#
#   The search already resolves to exact printings, so images come straight from
#   the result rather than being looked up a second time per card. That makes it
#   one request per page of 175 cards plus one per image.
def parse_scryfall_query(query: str, front_img_dir: str, double_sided_dir: str, copies: int = 1,
                         unique: str = None, order: str = None) -> None:
    from plugins.mtg.scryfall import request_scryfall, save_card_art_copies

    raw_input_text = (query or '').strip()
    query, url_params = split_scryfall_search(raw_input_text)
    if not query:
        if is_scryfall_search_url(raw_input_text):
            print('That Scryfall search URL has no "q" parameter.')
        else:
            print('Empty Scryfall query.')
        return

    # Precedence: explicit options beat the URL, which beats the defaults.
    params = {'unique': 'cards', 'order': 'name'}
    params.update(url_params)
    if unique:
        params['unique'] = unique
    if order:
        params['order'] = order
    params['q'] = query

    print(f'Scryfall search: {query}')
    print(f'  unique={params["unique"]}, order={params["order"]}')

    url = SCRYFALL_SEARCH_URL
    index = 0
    total = None
    error_cards = []

    while url:
        # request_scryfall raises for status, so a bad query arrives as an
        # exception. Scryfall puts a readable explanation in the body, which is
        # far more useful than the status code alone.
        try:
            response = request_scryfall(url, params=params)
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else None
            details = ''
            try:
                details = (e.response.json() or {}).get('details', '')
            except Exception:
                pass
            if status == 404:
                print(f'No cards matched: {query}')
                if details:
                    print(f'  {details}')
            else:
                print(f'Scryfall search failed ({status}) for: {query}')
                if details:
                    print(f'  {details}')
            return
        params = None  # next_page already carries the encoded query

        page = response.json()
        if total is None:
            total = page.get('total_cards', 0)
            suffix = '' if copies == 1 else f', {copies} copies each'
            print(f'Scryfall query matched {total} card(s){suffix}')

        for card in page.get('data', []):
            index += 1
            name = card.get('name', '')
            clean_name = remove_nonalphanumeric(name)

            parts = [f'Index: {index}', f'quantity: {copies}']
            if card.get('set'): parts.append(f'set code: {card["set"]}')
            if card.get('collector_number'): parts.append(f'collector number: {card["collector_number"]}')
            if name: parts.append(f'name: {name}')
            print(', '.join(parts))

            try:
                front_url, back_url = scryfall_face_images(card)
                if not front_url:
                    raise ValueError(f'no printable image for layout "{card.get("layout")}"')

                save_card_art_copies(request_scryfall(front_url).content, front_img_dir, index, clean_name, copies)
                if back_url and double_sided_dir:
                    save_card_art_copies(request_scryfall(back_url).content, double_sided_dir, index, clean_name, copies)
            except Exception as e:
                print(f'Error: {e}')
                error_cards.append((name, e))

        url = page.get('next_page') if page.get('has_more') else None

    if error_cards:
        print(f'Errors: {error_cards}')

def parse_deck(deck_text: str, format: DeckFormat, handle_card: Callable, front_img_dir: str = '', double_sided_dir: str = '',
               copies: int = 1, unique: str = None, order: str = None) -> None:
    if format == DeckFormat.SIMPLE:
        parse_simple_list(deck_text, handle_card)
    elif format == DeckFormat.MTGA:
        parse_mtga(deck_text, handle_card)
    elif format == DeckFormat.MTGO:
        parse_mtgo(deck_text, handle_card)
    elif format == DeckFormat.ARCHIDEKT:
        parse_archidekt(deck_text, handle_card)
    elif format == DeckFormat.DECKSTATS:
        parse_deckstats(deck_text, handle_card)
    elif format == DeckFormat.MOXFIELD:
        parse_moxfield(deck_text, handle_card)
    elif format == DeckFormat.SCRYFALL_JSON:
        parse_scryfall_json(deck_text, handle_card, front_img_dir, double_sided_dir)
    elif format == DeckFormat.SCRYFALL_QUERY:
        parse_scryfall_query(deck_text, front_img_dir, double_sided_dir, copies, unique, order)
    elif format == DeckFormat.MPCFILL_XML:
        parse_mpcfill_xml(deck_text, handle_card)
    elif format == DeckFormat.CUBECOBRA_CSV:
        parse_cubecobra_csv(deck_text, handle_card, front_img_dir, double_sided_dir)
    elif format == DeckFormat.URL:
        parse_url(deck_text, handle_card, front_img_dir, double_sided_dir, copies, unique, order)
    else:
        raise ValueError("Unrecognized deck format")