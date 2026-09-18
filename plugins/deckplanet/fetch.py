import sys
from os import path
from click import command, argument, option, Choice, ClickException

# Add parent directory to path to allow imports when run as a script
REPO_ROOT = path.abspath(path.join(path.dirname(__file__), '..', '..'))
sys.path.insert(0, REPO_ROOT)

from plugins.deckplanet.deck_formats import DeckFormat, parse_deck
from plugins.deckplanet.deckplanet import GAMES
from utilities import configure_console_encoding, ensure_directory

front_directory = path.join(REPO_ROOT, 'game', 'front')
double_sided_directory = path.join(REPO_ROOT, 'game', 'double_sided')

@command()
@argument('deck_path')
@argument('format', type=Choice([t.value for t in DeckFormat], case_sensitive=False))
@option('--game', type=Choice(sorted(GAMES), case_sensitive=False), default=None,
        help='The DeckPlanet game. Read from the deck link when omitted; required for a bare deck id.')
@option('--include_sideboard', default=False, is_flag=True, help='Also fetch side and maybe zones.')

def cli(deck_path: str, format: DeckFormat, game: str, include_sideboard: bool):
    ensure_directory(front_directory)
    ensure_directory(double_sided_directory)

    # A DeckPlanet link or deck id can be passed directly instead of a file.
    if format == DeckFormat.DECKPLANET_URL and not path.isfile(deck_path):
        deck_text = deck_path
    elif path.isfile(deck_path):
        with open(deck_path, 'r', encoding='utf-8') as deck_file:
            deck_text = deck_file.read()
    else:
        print(f'{deck_path} is not a valid file.')
        return

    try:
        # The directories are read here, at call time, so redirected values are honoured.
        parse_deck(deck_text, format, game.lower() if game else None, front_directory, double_sided_directory, include_sideboard)
    except ValueError as error:
        # A bad link, a wrong game or a missing deck: report it plainly and exit non-zero.
        raise ClickException(str(error)) from error

if __name__ == '__main__':
    configure_console_encoding()
    cli()
