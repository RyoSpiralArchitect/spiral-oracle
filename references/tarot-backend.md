# Spiral Tarot backend v1

Read this reference when implementing, interpreting, or auditing
`spiral-tarot`.

## Fixed basis

The backend uses identifiers from the Waite-Smith deck documented in A. E.
Waite's *The Pictorial Key to the Tarot*, with artwork by Pamela Colman Smith.
That selected basis has 78 cards: 22 Major Arcana and 56 Minor Arcana across
Wands, Cups, Swords, and Pentacles. It numbers Strength as VIII and Justice as
XI.

These are facts about the selected Waite-Smith basis, not claims that every
historical or contemporary Tarot deck uses the same names, order, suits,
numbering, orientation practice, or spread.

Primary-source references:

- Full public-domain work and publication record:
  <https://en.wikisource.org/wiki/The_Pictorial_Key_to_the_Tarot>
- Deck structure and distinctions:
  <https://en.wikisource.org/wiki/The_Pictorial_Key_to_the_Tarot/Part_1>
- Major Arcana identifiers and Strength/Justice numbering:
  <https://en.wikisource.org/wiki/The_Pictorial_Key_to_the_Tarot/Part_2>
- Minor Arcana, reversed readings, and divination procedures:
  <https://en.wikisource.org/wiki/The_Pictorial_Key_to_the_Tarot/Part_3>
- Museum record for a complete 78-card pack after Waite and Smith:
  <https://www.britishmuseum.org/collection/object/P_1982-U-4643-1-78>

## Spiral Oracle conventions

Ruleset `single-card-independent-orientation/v1` does exactly this:

1. Select one integer uniformly from `0..77` using OS-backed randomness.
2. Independently select `0` or `1` with equal probability.
3. Interpret `0` as upright and `1` as reversed.

The one-card format, software catalog order, and independent 50/50 orientation
are backend conventions chosen for simplicity and replayability. They are not
presented as universal Tarot rules. Reversed does not mean bad, and the backend
does not mechanically negate an upright association.

Catalog `waite-smith-identifiers-en/v1` orders cards as follows:

- Indices `0..21`: Major Arcana, the Fool through the World, using Waite-Smith
  numbering.
- Indices `22..77`: Wands, Cups, Swords, Pentacles. Within each suit: Ace
  through Ten, then Page, Knight, Queen, King.

The Minor ordering is a software convention. Waite's book presents the ranks in
a different order. English display names are also normalized software
identifiers rather than facsimile transcriptions. In particular, card XX is
rendered `Judgement`, following the card label's spelling rather than combining
it with the book heading `The Last Judgment`.

## Deliberate omissions

The backend includes no artwork, fixed divinatory meanings, favorable or
unfavorable score, prediction, significator selection, or recommendation.
Contextual interpretation belongs to the model after the draw. State whether an
association comes from the selected Waite-Smith tradition or is a creative
contextual reading.

Do not import Waite's period-specific assumptions about gender, appearance, or
social role as defaults for people in the user's context.

## Replay contract

The replay payload contains exactly:

```json
{
  "schema": "spiral-oracle.replay.tarot/v1",
  "catalog_version": "waite-smith-identifiers-en/v1",
  "ruleset_version": "single-card-independent-orientation/v1",
  "card_index": 0,
  "orientation_bit": 0
}
```

`card_index` must be an integer in `0..77`; `orientation_bit` must be integer
`0` or `1`. Booleans are rejected even though Python treats them as integers.
