# Weiss Schwarz

Fetches Weiss Schwarz decks from [EncoreDecks](https://www.encoredecks.com), the
community deck builder, with card images from the official sites. English,
Japanese and mixed decks all work.

For Bushiroad Deck Log links (English or Japanese), use the
[Bushiroad plugin](../bushiroad/README.md).

## Deck format: `encoredecks_url`

Pass a deck link straight on the command line. The deck id on its own works too.

```sh
python plugins/weiss_schwarz/fetch.py 'https://www.encoredecks.com/deck/A33QHgxiD' encoredecks_url
```

## Where images come from

EncoreDecks' own images are small for older sets (some are 130x182), so each
card is fetched from the official site first:

| Card language | Official image |
| --- | --- |
| English | `en.ws-tcg.com/wordpress/wp-content/images/cardimages/...`, found from the card number, or from the card's page on en.ws-tcg.com for sets filed elsewhere (BanG Dream) |
| Japanese | `ws-tcg.com/wordpress/wp-content/images/cardlist/...`, found from the card number |

If the official site has no image, the EncoreDecks image is used and the log
says so ("small image" when it is under 300 pixels wide). Official images are
about 400x558, about 160 PPI on a standard card; that is as large as Weiss
Schwarz images come.

Climax cards are landscape and are rotated upright. Cards have a single face;
add your own card back to `back/`.

## How it works

EncoreDecks has a public JSON API: `/api/deck/<id>` returns the deck with one
entry per copy, each with its card code, language and EncoreDecks image path.

## Printing

```sh
python create_pdf.py --card_size standard
```
