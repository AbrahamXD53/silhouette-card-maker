import sys
from os import path
from click import command, argument, Choice, ClickException

# Add parent directory to path to allow imports when run as a script
REPO_ROOT = path.abspath(path.join(path.dirname(__file__), '..', '..'))
sys.path.insert(0, REPO_ROOT)

from plugins.weiss_schwarz.deck_formats import DeckFormat, parse_deck
from utilities import configure_console_encoding, ensure_directory

front_directory = path.join(REPO_ROOT, 'game', 'front')

@command()
@argument('deck_path')
@argument('format', type=Choice([t.value for t in DeckFormat], case_sensitive=False))

def cli(deck_path: str, format: DeckFormat):
    ensure_directory(front_directory)

    # An EncoreDecks link or deck id can be passed directly instead of a file.
    if format == DeckFormat.ENCOREDECKS_URL and not path.isfile(deck_path):
        deck_text = deck_path
    elif path.isfile(deck_path):
        with open(deck_path, 'r', encoding='utf-8') as deck_file:
            deck_text = deck_file.read()
    else:
        print(f'{deck_path} is not a valid file.')
        return

    try:
        # front_directory is read here, at call time, so a redirected value is honoured.
        parse_deck(deck_text, format, front_directory)
    except ValueError as error:
        # A bad link or a private deck: report it plainly and exit non-zero.
        raise ClickException(str(error)) from error

if __name__ == '__main__':
    configure_console_encoding()
    cli()
