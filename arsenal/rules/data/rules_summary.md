# MTG Core Rules

## Turn Structure
Each turn follows this sequence:
1. **Untap** — Untap all permanents you control. No player gets priority.
2. **Upkeep** — Triggered abilities that say "at the beginning of your upkeep" trigger. Players get priority.
3. **Draw** — Active player draws a card. Triggered draw abilities trigger.
4. **Pre-combat Main Phase** — Cast spells and play lands. Creatures with summoning sickness can't attack yet.
5. **Beginning of Combat** — Triggered abilities "at the beginning of combat" trigger.
6. **Declare Attackers** — Active player chooses attacking creatures (must be untapped, no summoning sickness).
7. **Declare Blockers** — Defending player assigns blockers.
8. **Combat Damage** — Creatures deal damage simultaneously (unless first/double strike).
9. **End of Combat** — Post-combat triggers resolve.
10. **Post-combat Main Phase** — Cast spells, play lands (if not done pre-combat).
11. **End Step** — "At end of turn" triggers. Discard to hand size (7) in cleanup.

## Zones
- **Library**: Your deck. Cards are face-down.
- **Hand**: Cards you hold. Only you see them (unless effect reveals).
- **Battlefield**: Where permanents (creatures, artifacts, enchantments, lands, planeswalkers) live.
- **Graveyard**: Discard pile. Face-up. Key zone for many strategies.
- **Exile**: Removed from game. Usually inaccessible unless a card specifically references it.
- **Stack**: Where spells and abilities go when cast/activated. Resolves LIFO (last in, first out).
- **Command Zone**: Where commanders, emblems, and dungeons live in specific formats.

## The Stack (Priority System)
- When a spell is cast or ability activated, it goes on the stack.
- Each player gets priority to respond before anything resolves.
- Responses also go on the stack (LIFO — last cast resolves first).
- A spell or ability only resolves when both players pass priority with no new responses.
- **Instant speed**: Can be cast any time you have priority (including opponent's turn, in response to spells).
- **Sorcery speed**: Can only be cast during your main phase when the stack is empty.

## Card Types
- **Creature**: Has power/toughness. Can attack and block. Has summoning sickness (can't attack or use tap abilities the turn it enters unless it has Haste).
- **Instant**: One-time effect. Cast at instant speed.
- **Sorcery**: One-time effect. Cast at sorcery speed only.
- **Enchantment**: Permanent. Stays on battlefield. Auras attach to permanents; if attached permanent leaves, aura goes to graveyard.
- **Artifact**: Permanent. Usually colorless. Equipment attaches to creatures.
- **Planeswalker**: Permanent. Has loyalty counters. Can activate one loyalty ability per turn (sorcery speed). Damaged when opponent's creature attacks them or opponent redirects combat damage.
- **Land**: Permanent. Produces mana. Can only play one land per turn (unless effect says otherwise). Playing a land is not casting a spell — it cannot be countered.
- **Battle**: Permanent. Opponent can attack them. Newer card type.

## Triggered vs Activated vs Static Abilities
- **Triggered**: Uses "when", "whenever", or "at". Goes on stack automatically when condition is met.
- **Activated**: Uses "[cost]: [effect]". Player must pay cost to use it. Can be at instant or sorcery speed depending on the ability.
- **Static**: No trigger or activation. Continuously applies as long as permanent is on battlefield (e.g., "Creatures you control get +1/+1").

## Replacement Effects
- Replace one event with another. Use "instead" keyword.
- They never go on the stack — they change how an event happens.
- Example: "If a creature would die, exile it instead."
- Multiple replacement effects: controller of affected object usually chooses order.

## State-Based Actions (SBAs)
Checked continuously. No player gets priority during SBA checks:
- Creature with 0 or less toughness dies.
- Creature with lethal damage dies.
- Planeswalker with 0 loyalty counters dies.
- A player with 0 or less life loses.
- A player who drew from an empty library loses.
- A permanent with the same legendary name as another you control: you choose one to keep (the "legend rule").

## Damage and Death
- Creatures die when they have damage equal to or greater than their toughness (lethal damage) OR have a "destroy" effect applied.
- Damage is removed at end of turn (cleanup step).
- **Indestructible** creatures cannot be destroyed by damage or "destroy" effects. They can still be killed by -X/-X effects, exile, or toughness reduction to 0.
- **Deathtouch**: Any amount of damage from this source is lethal.
- **Lifelink**: Damage dealt also causes controller to gain that much life.

## Mana System
- Mana costs use symbols: W (white), U (blue), B (black), R (red), G (green), C (colorless), and numbers (generic mana, any color/type).
- Lands tap to produce mana. Mana empties from your mana pool at end of each step/phase.
- **Mana curve**: The distribution of casting costs in your deck. A good curve ensures you have plays on each turn.

## Counters
- **+1/+1 counters**: Increase creature's power and toughness permanently.
- **-1/-1 counters**: Decrease creature's power and toughness permanently.
- +1/+1 and -1/-1 counters on the same creature cancel each other (state-based action).
- Other counters: loyalty, charge, time, poison, etc.

## Combat Rules
- **Attacking**: Tap creature (unless it has vigilance). Must be untapped and have no summoning sickness.
- **Blocking**: Can use any untapped creature to block. Multiple blockers can block one attacker. One blocker can only block one attacker (unless it has an ability like "can block multiple attackers").
- **Trample**: If blocked, excess damage assigned to defending player.
- **Unblocked creatures**: Deal full damage to player/planeswalker.
- **First Strike**: Deals combat damage before creatures without first strike.
- **Double Strike**: Deals combat damage in both first strike and regular combat damage steps.

---

## Playing a Card

**Timing — Sorcery vs Instant Speed**
- Sorceries and creatures can only be cast on your main phase, when the stack is empty, and you have priority.
- Instants and abilities with flash can be cast any time you have priority.
- "At sorcery speed" = sorcery timing restriction applies.

**The Stack**
1. Player announces the spell/ability and pays costs.
2. Opponents get priority to respond. The stack is LIFO — last in, first out.
3. When all players pass priority consecutively, the top of the stack resolves.
4. After each resolution, active player gets priority again before the next resolves.

**Targets**
- Targets are chosen when the spell is put on the stack, not when it resolves.
- If all targets are illegal when the spell resolves, it is countered by the rules (fizzles).

---

## Commander-Specific Rules

- **Command Zone:** Commanders start here. When your commander would go to graveyard or exile, you may return it to the command zone instead.
- **Commander Tax:** Each time you cast your commander from the command zone, it costs {2} more per previous cast from the command zone.
- **Color Identity:** Includes all mana symbols in mana cost AND rules text (including land abilities). A deck may only contain cards whose color identity is a subset of the commander's.
- **Combat Damage to Commanders:** If a player has been dealt 21 or more combat damage by a single commander over the game (tracked cumulatively), that player loses.
- **Partner:** Two legendary creatures with Partner can both be commanders. The color identity is the union of both.
- **Tucking:** If a commander is put into a library (tutored to bottom/shuffled), the owner may choose to put it in the command zone instead. This changed in 2015 — tuck no longer forces it into the library permanently.

---

## Common Gotchas

- **Legendary Rule:** If you control two or more legendary permanents with the same name, you choose one to keep; the rest go to the graveyard (state-based action). This is NOT a "dies" trigger.
- **Tokens vs Copies:** Tokens are not cards and cannot exist outside the battlefield (they cease to exist in zones). Copies of spells on the stack are also not cards but can have ETB triggers when they resolve and become permanents.
- **Damage vs Destroy vs Exile:** Damage does not automatically destroy creatures — lethal damage causes destruction via state-based actions. "Destroy" can be prevented by indestructible or regeneration. "Exile" bypasses both.
- **"Until end of turn" vs permanent:** Effects that say "until end of turn" or "this turn" wear off during the cleanup step. If a creature gets +N/+0 until end of turn and that would kill it, it survives to the cleanup step, then dies from state-based actions.
- **Summoning Sickness:** A creature must have been under your control since the beginning of your most recent turn to attack or use {T} abilities. Haste bypasses this.
- **Priority:** You do not automatically get to respond to things — you need priority. After each spell/ability resolves, the active player gets priority. If you do not hold priority, you cannot respond.
- **"Dies" triggers and state-based actions:** A creature that has 0 toughness ceases to exist as a state-based action — it is NOT put into the graveyard by "dying" in the triggered-ability sense. Triggers that watch for "when X dies" DO trigger when it is destroyed or when lethal damage is applied, but NOT when it has 0 toughness removed.

---

## How to Read a Card

Reading top-down on Oracle text:
1. **Mana Cost** (top right) — what you pay to cast it.
2. **Type Line** — card type (Creature, Instant, etc.) and subtypes. Subtypes matter for tribal synergies and some rules.
3. **Keyword abilities** (first line of text box) — Flying, Trample, etc. These have full definitions in the Comprehensive Rules; look them up with `get_glossary()`.
4. **Triggered abilities** — "When/Whenever/At" — go on the stack and use the stack.
5. **Activated abilities** — "Cost: Effect" — also use the stack unless they say they don't.
6. **Static abilities** — everything else — apply continuously, never use the stack.
7. **Power/Toughness** (bottom right, creatures only).
8. **Loyalty** (bottom right, planeswalkers only).
