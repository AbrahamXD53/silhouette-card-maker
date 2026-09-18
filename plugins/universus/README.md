# UniVersus

Fetches card images for UniVersus (UVS Games) decks built on
[universus.cards](https://universus.cards), the community deck builder.

## Deck format: `universus_cards_url`

Pass a deck link from universus.cards (your own decks, Public Decks or Tournament
Decks) straight on the command line. The deck id on its own works too.

```sh
python plugins/universus/fetch.py 'https://universus.cards/deck/e4c57177-8a10-40e6-9786-0cbf35268bd9' universus_cards_url
```

A text file containing the link works too. Private decks cannot be fetched.

## Options

| Option | Effect |
| --- | --- |
| `--include_sideboard` | Also fetch the sideboard. By default the mainboard and starting character are fetched. |
| `--image_source official` | Default. Card images from the official UniVersus card gallery (play.uvsgames.com), about 744x1039. |
| `--image_source universus_cards` | Card images from universus.cards, 358x500, always the exact printing in the deck. |

## Where images come from

universus.cards images are small (358x500, about 145 PPI on a standard card),
so by default the plugin looks each card up in the official gallery, whose
images are about 744x1039 (about 300 PPI). The two sites use different card
ids, so a card is matched by name, then by set and collector number. The log
says how each card was matched:

| Log line | Meaning |
| --- | --- |
| `official (exact)` | Same name, set and collector number. |
| `official (name)` | The only official card with that name. universus.cards numbers some sets differently, so this is usually still the same printing. |
| `official (name, several printings)` | Several printings share the name; the closest one was used, which may be a different art. |
| `universus.cards (no official match)` | Not in the official gallery; the universus.cards image was used. |
| `universus.cards (official image has no back)` | A double-faced card the official gallery has no back for. Both sides come from universus.cards so they match. |

Use `--image_source universus_cards` if you need every card to be the exact
printing in the deck.

## Double-faced cards

Some characters transform and some Solo Leveling cards have a second face. Their
back goes to `double_sided/` under the same filename as the front, which is how
`create_pdf.py` pairs them. Add your own card back to `back/` for everything
else.

## How it works

The deck comes from universus.cards' deck API (`/deck/<id>` returns JSON with
`[card id, mainboard, sideboard]` entries). The site has no card API: it ships
its whole card database inside a JavaScript file whose name changes on every
deploy. The plugin follows the site's script imports from its entry points to
find that file (a few MB, a few seconds), then reads each card's name, set,
number and image paths from it. If the site's layout changes, the plugin stops
with an error rather than fetching the wrong cards.

Official images come from the public carde.io deck builder API that backs
play.uvsgames.com.

## Printing

Both image sources have an aspect ratio of 0.716, which matches the `standard`
card size (63x88mm).

```sh
python create_pdf.py --card_size standard
```
