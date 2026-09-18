# Palworld TCG

Fetches card images for the Palworld Official Card Game (Bushiroad) from decks
shared on [palworldtcg.gg](https://palworldtcg.gg), a community deck builder.

## Deck format: `palworldtcg_url`

Pass a shared deck link straight on the command line. The deck id on its own
works too.

```sh
python plugins/palworld/fetch.py 'https://palworldtcg.gg/deck/6a5f62a083' palworldtcg_url
```

## Options

| Option | Effect |
| --- | --- |
| `--include_sideboard` | Also fetch the deck's maybe cards. |

## What gets printed

The main deck (50 cards) and the soul deck (10 cards), each card in the printing
the deck chose (special and secret rare arts included). Add your own card back
to `back/`.

## How it works

palworldtcg.gg has no deck API. A shared deck page is rendered by Next.js and
carries the deck in its React Server Components stream as
`{"main", "soul", "maybe", "art"}`, each entry a card slug and count; the plugin
parses that stream. Images are `/img/card-thumbnails/<slug>.webp`.

If the site changes how it renders decks, the plugin stops with "not found"
rather than fetching the wrong cards.

## Printing

Card images are 400x559, the same size as Bushiroad's official images, about
160 PPI on a standard card.

```sh
python create_pdf.py --card_size standard
```
