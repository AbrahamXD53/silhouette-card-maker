# Kodem

Fetches card images for [Kodem](https://kodem.wildhogstudio.com) (Wild Hog Studio).

## Deck format: `deckbuilder`

Open the [deck builder](https://kodem.wildhogstudio.com/DeckBuilder), build a
deck, and use **Generar Lista** (or **Copiar Deck**). Each line looks like:

```
IDRMA-001 - Card Name
```

Save the list to a text file and run:

```sh
python plugins/kodem/fetch.py <path_to_deck> deckbuilder
```

The parser is deliberately tolerant, so hand-written lists work too:

| Line | Meaning |
| --- | --- |
| `IDRMA-001 - Card Name` | one copy |
| `IDRMA-001` | one copy, name optional |
| `3 LGRO-010` | three copies |
| repeated identical lines | one copy each, tallied |

## How images are located

Card images live at `/assets/{SET}/{CARD_ID}.webp`, but **the set folder cannot
be derived from the card id** — `DMUE-`, `CMFT-`, `RMFT-` and `FAFT-` ids all
live under `MFT`. The deck builder page is server rendered, so the plugin
scrapes it once per run to build the id to set mapping for all 393 cards. No
API key or browser is required.

If the site's markup changes, the plugin fails loudly rather than silently
fetching nothing.

## Printing

Card images are 1071x1465 WebP, an aspect ratio of 0.731. The closest supported
card size is `standard` (63x88mm, 0.716), about 1.5% off — under a millimetre of
distortion. Use `--fit crop` to preserve the aspect ratio instead of stretching.

```sh
python create_pdf.py --card_size standard --fit crop
```
