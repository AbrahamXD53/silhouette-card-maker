import sys
from os import path
from click import command, argument, option, Choice, ClickException

# Add parent directory to path to allow imports when run as a script
REPO_ROOT = path.abspath(path.join(path.dirname(__file__), '..', '..'))
sys.path.insert(0, REPO_ROOT)

from plugins.battle_spirits_saga.deck_formats import DeckFormat, parse_deck
from plugins.battle_spirits_saga.bssdb import get_handle_card
from utilities import configure_console_encoding, ensure_directory

front_directory = path.join(REPO_ROOT, 'game', 'front')

@command()
@argument('deck_path')
@argument('format', type=Choice([t.value for t in DeckFormat], case_sensitive=False))
@option('--include_sideboard', default=False, is_flag=True, help='Also fetch the sideboard.')

def cli(deck_path: str, format: DeckFormat, include_sideboard: bool):
    ensure_directory(front_directory)

    # A BSSDB link or deck code can be passed directly instead of a file.
    if format == DeckFormat.BSSDB_URL and not path.isfile(deck_path):
        deck_text = deck_path
    elif path.isfile(deck_path):
        with open(deck_path, 'r', encoding='utf-8') as deck_file:
            deck_text = deck_file.read()
    else:
        print(f'{deck_path} is not a valid file.')
        return

    try:
        parse_deck(deck_text, format, get_handle_card(front_directory), include_sideboard)
    except ValueError as error:
        # A bad link or code: report it plainly and exit non-zero.
        raise ClickException(str(error)) from error

if __name__ == '__main__':
    configure_console_encoding()
    cli()
