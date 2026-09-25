import sys
from os import path
from click import command, argument, option, Choice, ClickException

# Add parent directory to path to allow imports when run as a script
REPO_ROOT = path.abspath(path.join(path.dirname(__file__), '..', '..'))
sys.path.insert(0, REPO_ROOT)

from plugins.shard_bugs.deck_formats import DeckFormat, parse_deck
from utilities import configure_console_encoding, ensure_directory

front_directory = path.join(REPO_ROOT, 'game', 'front')

@command()
@argument('deck_path')
@argument('format', type=Choice([t.value for t in DeckFormat], case_sensitive=False))
@option('--set', 'preferred_set', default=None,
        help='Prefer printings from this set when a card has several, e.g. "The Bug-inning: 1st Edition".')

def cli(deck_path: str, format: DeckFormat, preferred_set: str):
    ensure_directory(front_directory)
    if not path.isfile(deck_path):
        print(f'{deck_path} is not a valid file.')
        return

    with open(deck_path, 'r', encoding='utf-8') as deck_file:
        deck_text = deck_file.read()

    try:
        # front_directory is read here, at call time, so a redirected value is honoured.
        parse_deck(deck_text, format, preferred_set, front_directory)
    except (ValueError, RuntimeError) as error:
        # A site change or an unreadable card list: report it plainly and exit non-zero.
        raise ClickException(str(error)) from error

if __name__ == '__main__':
    configure_console_encoding()
    cli()
