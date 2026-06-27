# Deck Building Logic

<!-- BEGIN DECK BUILDING RULES -->

## The First Rule: Mission Statement

Before selecting a single card, write a one-sentence mission statement for the deck:

> "This deck wins by [strategy] using [primary mechanism], aiming to close games by [turn range]."

Every card selection test flows from this: *"Does this card help my deck accomplish its mission?"* Cards that don't serve the mission are a distraction — even powerful ones. A deck is a coherent strategy, not a pile of individually strong cards.

**Linear decks** (tribal, combo, Voltron): push the strategy hard. Maximize critical mass of synergistic cards; redundancy is a feature.

**Good-stuff decks** (midrange, control): win through raw card quality and favorable trades. Mission statement focuses on card advantage and surviving to the late game.

---

## The 8×8 Framework (Primary Structure)

A Commander deck has **100 cards = 1 commander + 64 spells + 35 lands**.

Organize the 64 spells into **8 strategies × ~8 cards each**. This keeps the deck coherent and ensures each strategy appears in your opening hand reliably.

### Primary Mandatory Strategies (always include)

| Strategy | Slot Count | Ratio |
|---|---|---|
| Card Draw / Advantage | 12 | 1.5× |
| Mana Ramp | 12 | 1.5× |
| Removal / Interaction | 12 | 1.5× |
| Board Wipes / Resets | 4 | 0.5× |
| **Primary total** | **~40** | |

### Secondary Strategies (deck-specific, remaining ~24 slots)

Fill with 4–8 strategies native to your plan:
- Win conditions / payoffs
- Combo pieces
- Protection / countermagic
- Tutors
- Synergy engines
- Tribal support
- Graveyard recursion
- etc.

### Strategy Ratio Reference

| Ratio | Card Count | When to use |
|---|---|---|
| 0.5× | 4 cards | Minimum viable; rarely matters but useful enough to include |
| 1.0× | 8 cards | Standard supporting strategy |
| 1.5× | 12 cards | Important category (ramp, draw, removal) |
| 2.0× | 16 cards | Deck's central mechanism |
| 3.0× | 24 cards | All-in strategy (build around this) |

**Minimum Viable Strategy (MVS):** 4 cards. Below this, the strategy won't appear often enough to matter. Adjust in increments of 4.

**The 12 Opening Hands Principle:** A 100-card deck yields ~12 possible opening hands of 8 cards. A 12-card strategy will appear in roughly 1 of those 12 hands — reliable enough to count on. A 4-card strategy appears ~once every 3 games — useful but not a cornerstone.

---

## Land Count Formula

**Start at 40 lands, then adjust:**

| Condition | Adjustment |
|---|---|
| Each 2–3 mana rocks beyond 8 | −1 land |
| Heavy card draw (10+ draw spells) | −1 to −2 lands |
| Average CMC > 4 | +1 to +2 lands |
| Mana sink cards (X spells, activated abilities) | +1 to +2 lands |
| 4–5 color identity | Keep at 38–40 regardless of curve |
| Green land ramp (Cultivate, Kodama's Reach, etc.) | −1 per 2 ramp spells |

**Total mana sources target: 43–55** (lands + ramp combined)

- Typical split: 36–40 lands + 10–15 ramp pieces
- The EDHREC community average (~29 lands + 4 rocks) produces a **47% failure rate** on turn-3 land drops — far too low
- Preconstructed decks average 37+ lands — a safer baseline

**Nate Burgess formula** (rough heuristic):
```
Lands = 31 + (number of colors in commander's identity) + (commander's CMC)
(count 0-CMC mana rocks as additional lands)
```

**By deck archetype:**

| Deck type | Land count | Notes |
|---|---|---|
| High CMC / ramp-heavy | 37–42 | Big spells need consistent mana |
| Low CMC / aggressive | 33–35 | Card draw fills the gaps |
| Standard midrange | 36–40 | Default starting point |
| Mana sink / X-spells | 39–42 | Never have too much mana |
| cEDH (avg CMC 1.7–2.0) | 28–33 | Offset with 16–20 ramp pieces |

---

## Ramp Philosophy

**Sweet spot goal:** Consistently casting two spells per turn. This is where decks truly shine.

Prioritize ramp costing **2 mana or less**. Paying 3 mana to net 1 mana is rarely worth the slot.

**By CMC of commander:**
- 4-drop commanders: need turn-2 ramp (Signets, Fellwar Stone) to deploy on turn 3
- 5-drop commanders: turn-3 ramp with higher value pieces
- 7+ drop commanders: need multiple ramp pieces or dedicated acceleration

**Ramp efficiency tiers (casual):**

| Tier | Ramp count | Notes |
|---|---|---|
| A | 12–16 with good curve | Consistently hits 2-spell turns |
| B | 8–12 | Functional in most games |
| C | 4–8 | Inconsistent; will lose games to mana |
| D | ≤4 | Too slow |

**By type:**
- 1–2 mana rocks: Sol Ring, Arcane Signet, Fellwar Stone, Signets — always include
- Land search: Cultivate, Kodama's Reach, Three Visits, Nature's Lore — green's best ramp (fetchable land is mana that survives artifact removal)
- Mana dorks (green): Birds of Paradise, Llanowar Elves — great, but vulnerable to wraths
- 3-mana rocks: include only if you need color fixing; pure acceleration at 3 is usually not worth it

**Non-green decks:** budget 10–12 two-mana rocks minimum. Without green's land ramp, rocks are your only reliable acceleration.

---

## Card Draw — The Unique Pillar

Card draw is the only one of the four fundamental pillars (ramp, draw, removal, recursion) that **can be increased without detriment to the others**. More draw finds your removal, your recursion, and your win conditions — it makes everything else better.

| Draw type | Examples | Notes |
|---|---|---|
| Repeatable draw | Rhystic Study, Phyrexian Arena, The One Ring | Best value; prioritize these |
| Wheel / mass draw | Wheel of Fortune, Windfall | Risks helping opponents; excellent in aggressive/red decks |
| Conditional draw | Skullclamp, Coastal Piracy | Only include if deck reliably triggers the condition |
| Cantrip | Ponder, Brainstorm | Filtering more than drawing; count as ~½ draw slot |
| Impulse draw | Light Up the Stage, Jeska's Will | Good in aggressive/red |
| Tutor | Demonic Tutor, Enlightened Tutor | Counts as draw; finds exactly what you need |

**Healthy draw package:** Mix repeatable sources (2–4 cards) with burst draw (Wheels, one-shot draw spells). If you can't name 8+ draw/selection spells in your list, you need more.

---

## Removal Principles

**Spot removal priority order:**
1. Exile > destroy (bypasses indestructible, recursion, regeneration)
2. Flexible > narrow (hits any permanent > creatures only)
3. Low CMC > high CMC

**Board wipes:** Include 2–3. Know how they interact with your own board:
- Aristocrats/token decks: use wraths that trigger death (Blasphemous Act, Living Death, Toxic Deluge)
- Tribal decks: use wraths that spare your type (Kindred Dominance, Vanquish the Horde)
- Indestructible commanders/boards: need exile wipes (Cyclonic Rift, Merciless Eviction)

**When to hold removal vs spend it:**
- Spend removal immediately if the threat kills you this turn or next
- Hold removal if another opponent will likely deal with it, or if something bigger is coming
- Never use a 1-for-1 removal on a threat another opponent is about to answer — save it for your target

---

## Win Condition Evaluation

A win condition must answer: **How does this deck actually close the game?**

| Win condition type | Needs | Weakness |
|---|---|---|
| Commander damage / Voltron | Evasion + protection + Equipment | Removal-heavy pods |
| Infinite combo | Tutors for consistency | Disruption, counter-magic |
| Token / combat swarm | Wide board protection | Single wrath |
| Engine + payoff | Sustained draw / mana | Requires multiple pieces |
| Alternate win (Thassa's Oracle, etc.) | Specific enablers | Hate cards |

**Redundancy law from hypergeometric math:** Running 12 virtual copies of a key effect (e.g., 4 copies of 3 cards that all do the same job) achieves ~80.9% probability of drawing at least one in your opening hand — the reliable baseline for anything central to your strategy. Critical pieces need 8–12 representations; situational answers need 4.

Include **2–3 distinct win conditions** so the deck has lines when one is disrupted.

---

## Support Over Payoffs

A critical and often-missed principle: **the support structure is more important than the payoffs themselves.**

A game-winning payoff card is useless without enough enablers. Before adding another payoff, ask: do I have enough cards that make the payoff work? Example: an Arti-combo payoff needs cheap artifacts; a reanimation payoff needs discard/mill enablers AND reanimation spells.

Every card in the deck must serve the central strategy or the core infrastructure (ramp/draw/removal). "Good card in a vacuum" is not enough.

---

## Graveyard as a Resource

Treat the graveyard as an extension of your hand. Effects traditionally viewed as drawbacks — discard, sacrifice, mill — become advantages when you can reliably:
- Return creatures from the graveyard (Gravecrawler, Reanimate)
- Recast spells (Flashback, Escape)
- Loop resources (Eternal Witness + blink)

Graveyard recursion is the fourth fundamental pillar alongside ramp, draw, and removal. Any deck playing 5+ graveyard cards should build in dedicated recursion.

---

## Color Identity Constraints

Every nonland card must use only mana symbols within the commander's color identity. This is a hard rule, not a preference.

- Colorless cards (no colored symbols) are always legal
- Hybrid mana ({W/U}) belongs to both colors' identities
- Snow mana ({S}) and Phyrexian mana ({W/P}) do not expand color identity

When using `search_cards`, always pass the `color_identity` parameter to filter correctly before presenting recommendations.

---

## Budget Tiers

| Tier | Per-card | Deck total (approx.) | Strategy |
|---|---|---|---|
| Budget | <$2 | <$50 | Lean on synergy and redundancy; avoid staples |
| Moderate | <$10 | <$150 | Most staples accessible; pick battles |
| Optimized | <$30 | <$400 | Full staple access; fetch/dual mana base |
| cEDH | No limit | $800+ | Moxen, Mana Crypt, Force of Will viable |

Budget decks compensate for lacking power-staples by running more cards doing the same job (higher redundancy) and focusing the strategy more narrowly (fewer off-plan cards).

---

## Common Construction Mistakes

- **Too many 5+ CMC cards.** Keep ≤10 cards at 5 CMC or more (excluding commander). A high curve means slow starts and dead hands.
- **Running tutors without clear targets.** If you can't immediately name what you'd tutor in most game states, the tutor is wasted. Know your lines.
- **Under-ramping in non-green.** Blue/black decks often run 6–8 ramp pieces and run out of gas. Minimum 10 mana rocks.
- **Over-relying on the commander.** Build enough redundancy that the deck functions after the commander is removed twice.
- **Ignoring recursion.** Decks without recursion run out of steam in long games. Include at least 3–4 ways to get back key pieces.
- **Random "good cards" with no synergy.** A powerful card that doesn't serve the mission is a dead draw that replaces a card that would have.

<!-- END DECK BUILDING RULES -->
