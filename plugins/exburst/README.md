# ExBurst

Fetches card images for decks built on [ExBurst](https://exburst.dev), a deck
builder for several card games. One plugin covers every game ExBurst hosts:

| `--game` | Game | Deck links | Image size |
| --- | --- | --- | --- |
| `union_arena_en` | Union Arena (English) | `exburst.dev/ua/en/deck/<n>` | 600x837 |
| `union_arena_asia` | Union Arena (Asia) | `exburst.dev/ua/deck/<n>` | 600x837 |
| `union_arena` | either Union Arena version, read from the link | | |
| `gundam` | Gundam Card Game | `exburst.dev/gundam/deck/<n>` | 600x838 |
| `riftbound` | Riftbound | `exburst.dev/riftbound/deck/<n>` | 744x1039 |
| `cyberpunk` | Cyberpunk TCG | `exburst.dev/cyberpunk/deck/<n>` | 600x838 |
| `naruto_bandai` | Naruto Card Game (Bandai) | `exburst.dev/naruto/deck/<n>` | 600x831 |
| `naruto_mythos` | Naruto Mythos TCG | `exburst.dev/mythos/deck/<n>` | about 1569x2197 |

## Deck format: `exburst_url`

Pass a public deck link straight on the command line; the game is read from the
link.

```sh
python plugins/exburst/fetch.py 'https://exburst.dev/ua/en/deck/72156' exburst_url
```

A bare deck number works with a specific `--game`:

```sh
python plugins/exburst/fetch.py 72156 exburst_url --game union_arena_en
```

Both Naruto games have used `exburst.dev/naruto/...` links, so for those give
`--game naruto_bandai` or `--game naruto_mythos`. If a link and `--game`
disagree, the plugin stops rather than fetching the wrong game. Private decks
cannot be fetched.

## Options

| Option | Effect |
| --- | --- |
| `--game` | The ExBurst game. Read from the link when omitted. |
| `--include_sideboard` | Also fetch the side deck. |

## What gets printed

Every card in the deck (for Riftbound this includes the legend, battlefields and
runes), in the order the deck lists them. Landscape cards, such as Riftbound
battlefields, are rotated to portrait. ExBurst's games have no two-faced cards;
add your own card back to `back/`.

## How it works

ExBurst stores decks and cards in Supabase and reads public rows with the
public key it ships in its own JavaScript; the plugin finds that key the same
way. Each game's config (`exburst.dev/<path>/config/game-config.json`) names its
decklist table and the columns holding a card's number and image, so the plugin
follows the config rather than hard-coding them. Decklists are text, one
`<count> x <card number>` per line, and the large (`/hd/`) image is used when
there is one.

## Printing

```sh
python create_pdf.py --card_size standard
```
