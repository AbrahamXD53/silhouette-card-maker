import sys
from os import path
from click import command, argument, option, Choice, ClickException

# Add parent directory to path to allow imports when run as a script
REPO_ROOT = path.abspath(path.join(path.dirname(__file__), '..', '..'))
sys.path.insert(0, REPO_ROOT)

from plugins.universus.deck_formats import DeckFormat, parse_deck
from plugins.universus.images import ImageSource, get_handle_card
from utilities import configure_console_encoding, ensure_directory

front_directory = path.join(REPO_ROOT, 'game', 'front')
double_sided_directory = path.join(REPO_ROOT, 'game', 'double_sided')

@command()
@argument('deck_path')
@argument('format', type=Choice([t.value for t in DeckFormat], case_sensitive=False))
@option('--include_sideboard', default=False, is_flag=True, help='Also fetch the sideboard.')
@option(
    '--image_source',
    default=ImageSource.OFFICIAL.value,
    type=Choice([s.value for s in ImageSource], case_sensitive=False),
    show_default=True,
    help='Where card images come from. "official" uses the higher resolution UniVersus gallery and falls back to universus.cards for cards it cannot match.',
)

def cli(deck_path: str, format: DeckFormat, include_sideboard: bool, image_source: str):
    ensure_directory(front_directory)
    ensure_directory(double_sided_directory)

    # A universus.cards link or deck id can be passed directly instead of a file.
    if format == DeckFormat.UNIVERSUS_CARDS_URL and not path.isfile(deck_path):
        deck_text = deck_path
    elif path.isfile(deck_path):
        with open(deck_path, 'r', encoding='utf-8') as deck_file:
            deck_text = deck_file.read()
    else:
        print(f'{deck_path} is not a valid file.')
        return

    handle_card = get_handle_card(ImageSource(image_source), front_directory, double_sided_directory)
    try:
        parse_deck(deck_text, format, handle_card, include_sideboard)
    except (ValueError, RuntimeError) as error:
        # A bad link, a missing deck, or a site change: report it plainly and exit non-zero.
        raise ClickException(str(error)) from error

if __name__ == '__main__':
    configure_console_encoding()
    cli()
