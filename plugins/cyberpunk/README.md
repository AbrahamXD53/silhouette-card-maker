# Cyberpunk TCG

Fetches card images for the Cyberpunk Trading Card Game from decks built on
[cyberpunktcg.com](https://cyberpunktcg.com), whose deck builder is powered by
[netdeck.gg](https://netdeck.gg).

## Deck format: `netdeck_url`

Pass a deck link straight on the command line. Your own decks, shared links and
Community Decks all work, and so does the deck id on its own.

```sh
python plugins/cyberpunk/fetch.py 'https://cyberpunktcg.com/decks/46dc23a4-e195-497a-85ef-d8bff43b6f21' netdeck_url
```

A text file containing the link works too. Private decks cannot be fetched.

The Legends and the main deck are fetched, Legends first.

## Options

| Option | Effect |
| --- | --- |
| `--include_sideboard` | Also fetch sideboard or maybeboard zones, if the deck has any. |

## How it works

The deck comes from netdeck.gg's public deck API
(`https://api.netdeck.gg/api/cyberpunk/decks/<id>`), which lists each card with
the printing chosen in the deck and a link to its image. Those links are signed
and expire five minutes after the deck is read, so the images are downloaded
straight away, and if a link has expired the deck is read again for fresh ones.

Cards have a single face, so only `front/` is written. Add your own card back to
`back/`.

## Printing

Card images are 733x1024 WebP, an aspect ratio of 0.716, which matches the
`standard` card size (63x88mm) at about 290 PPI.

```sh
python create_pdf.py --card_size standard
```
