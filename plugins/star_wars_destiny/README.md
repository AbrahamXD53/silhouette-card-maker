# Star Wars: Destiny

Fetches card images for Star Wars: Destiny from
[A Renewed Hope's database](https://db.swdrenewedhope.com), the deck builder
of the game's continuing committee. It covers the original FFG sets and ARH's
fan expansions.

## Deck format: `arh_decklist_url`

Pass a published decklist link straight on the command line. The decklist id on
its own works too.

```sh
python plugins/star_wars_destiny/fetch.py 'https://db.swdrenewedhope.com/decklist/view/2461/lukeyoda-1.0' arh_decklist_url
```

Only published decklists can be fetched. Private decks are not available through
the site's API; publish the deck (or copy it into a decklist) first.

## What gets printed

Characters, the battlefield, the plot and the draw deck, in that order.

- An **elite** character (a unique character with two dice) is one card, so it
  is printed once. Non-unique characters, such as troopers and droids, are
  separate cards and are printed per copy.
- **Flip cards** (Maul, Savage Opress, and the plots and characters that share
  their images) get their other face in `double_sided/`, under the same filename,
  which is how `create_pdf.py` pairs the faces.
- **Dice** cannot be printed. Use the game's dice, or stickers.

Add your own card back to `back/`.

## Image quality

The database's card images are 298x418 JPEG, about 120 PPI on a standard card,
for every set. They print noticeably softer than most games. No sharper per-card
source was found for the FFG sets. For ARH's fan sets, the committee publishes
print-and-play files on its site, which are the better choice for those cards.

## How it works

The site runs the SWDestinyDB software, so it has the same public API as
ArkhamDB and RingsDB: `/api/public/decklist/<id>` for the deck and
`/api/public/cards/` for the card list with image links.

## Printing

The images have an aspect ratio of about 0.713, which matches the `standard`
card size (63x88mm).

```sh
python create_pdf.py --card_size standard
```
