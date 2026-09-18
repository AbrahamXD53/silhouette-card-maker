# DeckPlanet

Fetches card images for decks built on [DeckPlanet](https://www.deckplanet.net),
a deck builder for many card games. One plugin covers every game DeckPlanet
hosts:

| `--game` | Game | Image size | Special cards |
| --- | --- | --- | --- |
| `alpha_clash` | Alpha Clash | 640x894 and up | contender |
| `cyberpunk` | Cyberpunk TCG | 733x1024 | legends zone |
| `dbs_masters` | Dragon Ball Super Card Game Masters | mostly 260x364 | leader (with awakened side), Z deck |
| `fusion_world` | Dragon Ball Super Card Game Fusion World | about 850x1191 | leader (with awakened side) |
| `gundam` | Gundam Card Game | 640x894 | resource deck |
| `hellbreak` | Hellbreak | 750x1050 and up | monster, locations |
| `naruto_ccg` | Naruto CCG | about 1037x1444 | leader |
| `neuroscape` | Neuroscape | 535x750 | mainframe, cyber and RAM decks |
| `one_piece` | One Piece Card Game | 640x894 | leader |
| `riftbound` | Riftbound | 744x1039 | legend, runes, battlefields |
| `swu` | Star Wars: Unlimited | about 287x400 | leaders (with back side), base |
| `wotf` | Wonders of the First | 743x1037 and up | |

DBS Masters and Star Wars: Unlimited images are small and print soft. For
Star Wars: Unlimited, the dedicated plugin's SWUDB formats are sharper.

## Deck format: `deckplanet_url`

Pass a public deck link straight on the command line. The game is read from the
link.

```sh
python plugins/deckplanet/fetch.py 'https://www.deckplanet.net/fusion_world/deck/112bffff-8f46-4233-ba8a-60c745c26d8c' deckplanet_url
```

A bare deck id works too, with `--game`:

```sh
python plugins/deckplanet/fetch.py 112bffff-8f46-4233-ba8a-60c745c26d8c deckplanet_url --game fusion_world
```

If both a link and `--game` are given and they disagree, the plugin stops rather
than fetching the wrong game. Private decks cannot be fetched.

## Options

| Option | Effect |
| --- | --- |
| `--game` | The DeckPlanet game. Read from the link when omitted; required for a bare id. |
| `--include_sideboard` | Also fetch the side and maybe zones. Every play zone (main, Z deck, resource, rune, battlefield, legend, cyber, RAM...) is always fetched. |

## What gets printed

The game's special cards come first (leader, base, contender, monster,
locations, mainframe or legend), then every zone of the deck.

- **Two-faced cards** (Dragon Ball leaders, Star Wars: Unlimited leaders,
  Hellbreak cards with a back) get their other face in `double_sided/`, under
  the same filename, which is how `create_pdf.py` pairs the faces.
- **Landscape cards** (Star Wars: Unlimited leaders and bases, Hellbreak
  locations, some Riftbound battlefields) are rotated to portrait, since
  `create_pdf.py` lays cards out portrait.

Add your own card back to `back/`.

## How it works

DeckPlanet's data is served by a Directus API with public read access
(`https://api.deckplanet.net/items/<game>_decks/<id>`). The deck lists its cards
with their zone and count, and each card record names its image. Images are
`<image name>.webp` in the game's folder of DeckPlanet's image store, and a
card's other face is `<image name>_b.webp`.

## Printing

```sh
python create_pdf.py --card_size standard
```
