# Battle Spirits Saga

Fetches card images for Bandai's Battle Spirits Saga from
[BSSDB](https://www.bssdb.dev), the community deck builder.

## Deck format: `bssdb_url`

Pass a BSSDB deck link straight on the command line. BSSDB keeps the whole deck
in the link, so any of these work:

- the **Sharable Permalink** from a deck's Export page (`https://bssdb.dev/db/deckview?...`)
- the **Load This Deck** link on the Meta, Starter and Community deck pages (`https://bssdb.dev/?...`)
- the deck code on its own (the part after `?`)

```sh
python plugins/battle_spirits_saga/fetch.py 'https://bssdb.dev/db/deckview?N4Ig5iBcIEYM5xAGhA...' bssdb_url
```

Note the single quotes around the link. A text file containing the link works too.

## Deck format: `bssdb_text`

On a deck's Export page, choose **Text Export → Text** and save it to a file:

```
=== Main Deck ===
4x EX01-001: Fire Elemental Rubeus
4x BSS01-022: Dinoman Tyrannoid

=== Sideboard ===
2x BSS01-122: Deadly Balance
```

```sh
python plugins/battle_spirits_saga/fetch.py deck.txt bssdb_text
```

Hand-written lists work too: `4 BSS01-022`, `4x BSS01-022`, `BSS01-022 x4` and a
bare `BSS01-022` (one copy). Lines that are not cards are skipped and reported.

## Options

| Option | Effect |
| --- | --- |
| `--include_sideboard` | Also fetch the sideboard. By default only the main deck is fetched. |

## How it works

A BSSDB deck code is [lz-string](https://github.com/pieroxy/lz-string) compressed
JSON (`compressToEncodedURIComponent`), holding the deck name, author and a card
id to count map for the main deck and sideboard. The plugin decodes it locally
with a small port of the decompressor (`lzstring.py`), so reading a deck makes
no network request and adds no dependency.

Each card image is then downloaded from `https://www.bssdb.dev/cards/bss/<ID>.png`.
Battle Spirits Saga has no double-faced cards, so only `front/` is written. Add
your own card back to `back/`.

Images fetched from a link are named after the card id (the link carries no card
names), while the text export's names are used when present.

## Printing

Card images are about 600x838 PNG, an aspect ratio of 0.716, which matches the
`standard` card size (63x88mm). At that size they print at about 240 PPI.

```sh
python create_pdf.py --card_size standard
```

Card design and artwork are © BNP/BANDAI. BSSDB is a community-run site, so the
plugin pauses briefly between downloads.
