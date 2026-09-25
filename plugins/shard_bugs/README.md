# Shard Bugs TCG

Fetches card images for [Shard Bugs TCG](https://www.shardbugstcg.com) from a
decklist. The site publishes its whole card database, and its images are large
(1560x2160, about 620 PPI on a standard card).

The site's deck builder (OP Network) is behind a login and has no public deck
links, so decks are given as a decklist rather than a URL.

## Deck format: `decklist`

Put your decklist in a text file and run:

```sh
python plugins/shard_bugs/fetch.py game/decklist/deck.txt decklist
```

Cards are matched by name or card number:

```
// Bug-inning starter
Main deck
3 Honey Alchemist
2x 010/161
1 Maize Weevil [010/161]
4 Moth of Peppered Flame (The Bug-inning: Standard Edition)
```

| Line | Meaning |
| --- | --- |
| `3 Honey Alchemist` | three copies, matched by name |
| `2x 010/161` | two copies, matched by card number |
| `Maize Weevil [010/161]` | one copy, name with its card number |
| `Moth of Peppered Flame (The Bug-inning)` | one copy, preferring that set |
| `Main deck`, `Tokens`, `// note` | section headers and comments are skipped |

## Options

| Option | Effect |
| --- | --- |
| `--set` | Prefer printings from this set, e.g. `--set "The Bug-inning: Standard Edition"`. A set named on a line wins over this. |

## Choosing a printing

There are 1093 printings of 747 cards, and names and numbers repeat across sets,
so a line often matches several. The plainest printing is used -- English,
standard set numbering, ordinary rarity, non-holo -- and the log says how many
printings matched and which was taken. Name a set on the line or use `--set` to
pick another. 1st Edition and Standard Edition share the same art; promos and
sketch cards have their own.

## How it works

The card list comes from the site's public endpoint
(`https://www.shardbugstcg.com/_functions/cards`), and each card's image from
the Google Drive link it carries, at full size.

## Printing

Cards have a single face; add your own card back to `back/`.

```sh
python create_pdf.py --card_size standard
```
