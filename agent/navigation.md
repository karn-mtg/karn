# MCP Navigation Guide

<!-- BEGIN NAVIGATION GUIDE -->

## Understanding What the User Is Asking

Before touching any tool, classify the user's request into one of these task types. The type determines which tools to call and in what order.

### Task Type Decision Tree

```
User mentions a card by name?
  └─ Want details / oracle text?         → get_card(name)
  └─ Want combos?                        → get_combos(name)
  └─ Want alternatives / budget swaps?  → get_similar(name)
  └─ Want art / prints / prices?        → get_card(name) → get_card_prints(oracle_id)

User describes what a card should DO ("find me a card that...")?
  └─ search_cards(query, color_identity, clusters, format_legal)

User wants to explore a strategy / archetype / color?
  └─ traverse_graph(node_path)  [then follow up with search_cards]

User asks a rules question?
  └─ Know the term?  → get_glossary(term)
  └─ Know the rule ID?  → get_rule(rule_id)
  └─ Natural language?  → search_rules(query)
  └─ Broad chapter?  → get_section(name)
  └─ First time asking rules?  → get_rules_primer()

User wants to build or improve a deck?
  └─ See "Deck Building Workflow" below

User asks "how do I play..." or "when should I..."?
  └─ Consult gameplay.md — no tools needed unless card text is involved

User asks about a specific set?
  └─ search_cards_in_set(set_code, query)

User asks about server status or versions?
  └─ get_health()   check_updates()
```

---

## Proactively Loading Rules Context

Don't wait for the user to ask for a rule. Load relevant rules proactively when:

| Situation | Load |
|---|---|
| User asks about a specific keyword ability (deathtouch, lifelink, trample...) | `get_glossary(term)` |
| User describes an interaction that depends on timing / stack | `get_rules_primer()` then `search_rules(query)` |
| User asks about commander damage, commander tax, or zone changes | `search_rules("commander rules")` |
| User asks about triggered vs activated vs static | `get_glossary("triggered ability")` etc. |
| User is resolving a combat interaction | `get_section("combat")` |
| User is asking about replacement effects or "instead" wording | `search_rules("replacement effect")` |
| User mentions layer system, continuous effects | `get_section("effects")` |
| User mentions state-based actions (creature dying, planeswalker losing loyalty) | `search_rules("state-based")` |

Always cite the rule ID when you reference a rule in your answer.

---

## `search_cards` — Natural Language Card Search

**When to use:** Any open-ended "find me cards that do X" question.

```python
search_cards(
    query        = "sacrifice outlet that generates mana",
    top_k        = 10,            # default 10; raise to 20 for wide exploration
    color_identity = "B,G",       # comma-separated WUBRG — restricts to these colors
    clusters     = "Sacrifice",   # one or more mechanic clusters (see below)
    max_cmc      = 3.0,           # 0 = no limit
    format_legal = "commander",   # always pass this unless user specifies otherwise
)
```

**Mechanic clusters** (use for precise filtering):
`ETB`, `Dies`, `Sacrifice`, `Blink`, `Tokens`, `Ramp`, `Flying`, `Proliferate`, `Infect`, `Undying`, `Persist`, `Graveyard`, `Counters`, `Draw`, `Lifegain`, `Mill`, `Haste`, `Trample`, `Deathtouch`, `Tribal`

**Query writing tips:**
- Describe what the card *does*, not its name: `"deals damage to each creature"` not `"Blasphemous Act"`
- Natural language works best — phrase it like describing the effect in a sentence
- Combine `clusters` with a query to focus results: `clusters="Ramp"` narrows to mana sources before semantic search runs
- Use `top_k=20` for broad exploration; `top_k=5` when you want tight, specific results
- Always pass `color_identity` when building for a specific commander
- Always pass `format_legal="commander"` unless the user specifies another format

---

## `traverse_graph` — Strategy Space Exploration

**When to use:** Explore an archetype or color top-down, without a specific query.

**Graph hierarchy:** `color:<X>` → `archetype:<Y>` → `cluster:<Z>`

```python
traverse_graph("color:B")
traverse_graph("color:B/archetype:Aristocrats")
traverse_graph("color:B/archetype:Aristocrats/cluster:Dies")
traverse_graph("color:G/archetype:Ramp/cluster:Ramp")
```

**Valid colors:** `W`, `U`, `B`, `R`, `G`, `C` (colorless), `M` (multicolor)

**Valid archetypes:** `Aggro`, `Aristocrats`, `Control`, `Combo`, `Ramp`, `Tokens`, `Reanimator`, `Infect`, `Proliferate`, `Spellslinger`, `Voltron`

**Cluster names** match the mechanic clusters listed under `search_cards`.

**Tips:**
- Use when user asks "what are good cards for a [color] [archetype] deck?" — gives a curated overview of the whole space
- Combine: traverse first for breadth, then `search_cards` with cluster filters for depth
- `top_k` defaults to 20; raise to 40–50 for broader exploration

---

## `get_similar` — Functional Alternatives

**When to use:** "Budget replacement for X", "other cards like X", "backup copies of this effect"

```python
get_similar("Phyrexian Altar", top_k=15)
```

Results are ranked by semantic similarity of oracle text and mechanical tags — not card type or set.

**Tips:**
- Use `top_k=15–20` for budget replacements — the most similar cards are often expensive, the good budget options appear further down
- Cross-reference with `search_cards(color_identity=...)` to verify color legality
- This is the right tool for the **redundancy principle** from deck building: find the 8–12 virtual copies of an effect

---

## `get_combos` — Combo Discovery

**When to use:** "What combos does X enable?", evaluating win conditions, checking for accidental combo inclusions.

```python
get_combos("Blood Artist")
get_combos("Mikaeus, the Unhallowed")
```

**Tips:**
- Call on each potential combo piece when evaluating a combo-oriented deck
- If no combos are found, use `get_similar` on the card to find functional analogues, then call `get_combos` on those
- Always verify combo pieces are in the deck's color identity before presenting them

---

## `get_card` — Exact Card Details

**When to use:** You need oracle text, CMC, color identity, legalities, or `oracle_id` for follow-up calls.

```python
get_card("Phyrexian Arena")
# Returns: name, mana_cost, cmc, type_line, oracle_text, color_identity,
#          legalities, clusters, archetype, edhrec_rank, salt, combos, oracle_id
```

**Always call this when:**
- User names a specific card and you need to reason about its oracle text
- You need `oracle_id` to call `get_card_prints`
- You need to verify legality before recommending a card

---

## `get_card_prints` — Art, Sets, and Prices

**When to use:** User asks about card art, which printing to buy, or price comparison across sets.

```python
card = get_card("Sol Ring")
prints = get_card_prints(card["oracle_id"])
# Each print: set_code, set_name, collector_number, image_uri, prices, released_at
```

---

## `search_cards_in_set` — Set-Specific Exploration

**When to use:** User is exploring a specific set, drafting, or wants cards exclusive to a set.

```python
search_cards_in_set("dsk", query="graveyard recursion", top_k=10)
search_cards_in_set("mh3")  # browse all cards in the set (up to top_k)
```

`set_code` is the 3–4 letter Scryfall code (e.g., `dsk`, `mh3`, `otj`, `fdn`, `bro`, `lci`).

---

## Rules Tool Selection

```
Term / keyword definition?  → get_glossary(term)
Know the rule number?       → get_rule(rule_id)    e.g. get_rule("702.19")
Natural language question?  → search_rules(query, top_k=5)
Broad chapter needed?       → get_section(name)   e.g. "combat", "stack", "5"
Cross-references / related? → get_related_rules(rule_id)
First time / context needed? → get_rules_primer()
```

**`get_rules_primer()`** returns ~1,500 tokens covering turn structure, zones, stack, card types, combat, state-based actions, Commander rules, and gotchas. Call it at the start of a rules-heavy conversation.

**`get_section(name)`** accepts numbers (`"5"`) or keywords (`"combat"`, `"stack"`, `"triggered"`, `"replacement"`, `"planeswalker"`). Returns the full section — use when the user's question spans multiple rules in a chapter.

---

## Multi-Tool Workflows

### Deck Building — Card Recommendation
1. `search_cards(query, color_identity=<commander_colors>, format_legal="commander", top_k=15)` — candidates
2. `get_card(name)` on top candidates — verify oracle text and legality
3. `get_similar(name)` on best fit — find redundancy / budget alternatives
4. `get_combos(name)` on key pieces — check for interactions

### Archetype Exploration
1. `traverse_graph("color:<X>/archetype:<Y>")` — broad curated view
2. `search_cards(query, clusters="<Z>", color_identity=<X>)` — drill into specific roles
3. `get_combos` on promising synergy pieces

### Rules Dispute — Step by Step
1. `get_glossary(term)` — confirm what each term means
2. `search_rules(query)` — find the relevant rule
3. `get_rule(rule_id)` — read the exact text
4. `get_related_rules(rule_id)` — check for exceptions or modifications

### Card Upgrade / Budget Replacement
1. `get_card(name)` — understand what it does precisely
2. `get_similar(name, top_k=20)` — find functional alternatives
3. Filter by color identity and present best fits with price context

### Combo Research
1. `get_card(name)` on each piece you're considering
2. `get_combos(name)` on each piece
3. `get_similar(name)` if no combos found directly — find functional analogues and repeat
4. `search_rules(query)` if the combo involves a timing or rules interaction

### New Deck Build (commander given)
1. `get_card(commander)` — get color identity and understand the commander's role
2. `traverse_graph("color:<X>/archetype:<Y>")` — map the strategy space
3. `search_cards(...)` calls for each category: ramp, draw, removal, win conditions, synergy pieces
4. `get_combos` on key pieces
5. Use deck-building.md land formula + slot budget to shape the final list

---

## Performance Notes

- **Card DB preloads on startup.** `get_health()` reports `"warming_up"` until ready. If tools return empty results right after launch, wait ~5 seconds and retry.
- **Rules tools load lazily.** The first `search_rules` call takes 1–2 seconds longer than subsequent ones.
- **Semantic search phrases naturally.** `"deals damage to each creature"` finds Blasphemous Act better than `"damage all wrath"`. Describe effects in plain English.
- **Color identity filter is strict.** The filter rejects cards with any symbol outside the specified identity. Double-check when using multi-color commanders.

<!-- END NAVIGATION GUIDE -->
