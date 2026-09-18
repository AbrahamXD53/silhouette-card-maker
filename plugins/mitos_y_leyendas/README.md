# Mitos y Leyendas

Fetches card images for Mitos y Leyendas (MyL), the Chilean trading card game,
from decks built on [ShadowForge](https://shadow-forge-deck.vercel.app), a
community deck builder.

## Deck format: `shadowforge_url`

Pass a public deck link straight on the command line. The deck number on its
own works too.

```sh
python plugins/mitos_y_leyendas/fetch.py 'https://shadow-forge-deck.vercel.app/decks/155' shadowforge_url
```

Only public decks can be fetched; make the deck public in ShadowForge first.

## Options

| Option | Effect |
| --- | --- |
| `--include_sideboard` | Also fetch the sideboard. By default only the deck is fetched. |

## What gets printed

The starting gold (when the deck sets one), then the deck. A card that is in
both the deck and the sideboard is fetched once, with the copies added up. Add
your own card back to `back/`.

## How it works

ShadowForge is backed by a public REST API: `/api/decks/public/<id>/` returns a
public deck with each card's details and image link (Cloudinary or ImageKit).

## Printing

Card images are 709x1016 PNG, about 280 PPI on a standard card.

```sh
python create_pdf.py --card_size standard
```
