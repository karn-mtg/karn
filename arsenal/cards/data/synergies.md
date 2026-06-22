# MTG Synergy & Combo Recognition

## How to Identify Synergies

A synergy exists when two or more cards share a mechanic, trigger condition, or resource that makes each card stronger together than individually.

**Questions to ask:**
1. Does card A produce something that card B consumes?
2. Does card A trigger on an event that card B can cause repeatedly?
3. Does card A remove a restriction that card B has?
4. Do both cards care about the same zone, resource type, or game event?

---

## Core Synergy Patterns

### ETB (Enters the Battlefield) Abuse
**Pattern**: Any card that returns, recasts, or exiles/resets a permanent will re-trigger all ETB effects.

**Enablers** (what causes the ETB to repeat):
- **Blink/Flicker**: Exile the creature and return it — it ETBs again with full effect. Examples: Ephemerate, Cloudshift, Yorion Sky Nomad.
- **Bounce**: Return to hand, recast. Slower than blink but resets the creature entirely.
- **Sacrifice + Reanimate**: Kill it, bring it back from graveyard.
- **Cloudstone Curio**: Entering creatures bounce each other.

**Payoffs** (what makes the ETB worth repeating):
- Draw a card (Mulldrifter, Sea Gate Oracle)
- Destroy a permanent (Ravenous Chupacabra, Reclamation Sage)
- Create tokens (Emiel the Blessed, Anointed Processor)
- Deal damage (Electrostatic Field, etc.)
- Gain life (Soul Warden, Heliod's Pilgrim)
- Tutor a card (Imperial Recruiter)
- Add a counter (+1/+1 counters, loyalty)

**Famous ETB Combos:**
- Deadeye Navigator + any ETB creature = unlimited ETB triggers (Deadeye blinks the other for 1U each time)
- Panharmonicon: All ETB triggers double (not a combo piece alone, but doubles all ETB value)

---

### LTB / Dies Trigger Abuse
**Pattern**: Cards that trigger when they leave the battlefield or die become infinite if they can die and return repeatedly.

**Enablers**:
- Sacrifice outlets (Altar of Dementia, Phyrexian Altar, Viscera Seer, Carrion Feeder)
- Reanimate effects (Meren of Clan Nel Toth, Sun Titan)

**Payoffs**:
- Drain life (Blood Artist, Zulaport Cutthroat): "Whenever a creature you control dies, each opponent loses 1 life and you gain 1 life."
- Draw cards (Grim Haruspex)
- Create tokens (Abhorrent Overlord)
- Fill the graveyard for threshold/dredge

---

### Undying + Counter Removal = Infinite Loop
**Undying**: When this creature dies with no +1/+1 counters, it returns with a +1/+1 counter.

**The problem**: After returning with a +1/+1 counter, undying no longer triggers when it dies again.

**The solution**: Remove the +1/+1 counter before it dies again.

**Methods to remove +1/+1 counters:**
- **Persist creature** (has -1/-1 counter when it returns): A +1/+1 and a -1/-1 counter on the same permanent cancel each other (state-based action). So Persist + Undying counters cancel, making the creature die and return infinitely.
- **Mikaeus, the Unhallowed**: Gives undying to non-human creatures. Combined with a sac outlet and a card that removes counters, enables infinite sacrifice loops.
- **First Day of Class** + persist creature: First Day of Class gives "whenever a creature enters the battlefield, it gets a +1/+1 counter." A persist creature returns with a -1/-1 counter. The +1/+1 from First Day of Class and the -1/-1 from persist cancel out. The creature has no counters. Next time it dies — persist triggers again. This creates an infinite death/enter loop.
  - **Full breakdown**: 
    1. First Day of Class is on the stack or has resolved.
    2. Persist creature (e.g., Kitchen Finks) enters — gets +1/+1 counter (First Day of Class) and also gets -1/-1 from persist... wait — First Day of Class triggers on enter, giving +1/+1. Persist adds -1/-1 when it RETURNS. They cancel.
    3. Sacrifice the creature with a sacrifice outlet.
    4. Creature dies. Persist triggers. Creature returns with a -1/-1 counter.
    5. First Day of Class triggers: creature gets +1/+1 counter. Net = 0 counters (state-based action cancels them).
    6. Sacrifice again → infinite loop.
    7. **Payoff needed**: A drain effect (Blood Artist), a mana-generating sac outlet (Phyrexian Altar = infinite mana), a draw engine.

---

### Persist + Undying = Direct Interaction
Persist and Undying on the SAME creature don't directly interact, but:
- A creature with BOTH keywords (from separate effects) can loop: dies → returns with -1/-1 (persist) + +1/+1 (undying): counters cancel. Creature has 0 counters. Next death triggers both again.
- **Mikaeus gives undying** to non-humans. Many persist creatures are non-human. Mikaeus + persist creature + free sac outlet = infinite sacrifice.

---

### Blink + ETB Permanent Value
**Key insight**: Blinking resets everything about a permanent:
- Removes all counters (resets damage, -1/-1 counters, +1/+1 counters — good to reset a persist creature!)
- Re-triggers ETB
- Detaches Equipment and Auras (they fall off and usually go to graveyard)
- Re-enters as a "new" permanent (no more summoning sickness)
- Does NOT reset loyalty on planeswalkers if they're blinked (they just ETB with their starting loyalty)

**Flicker Loop Combos:**
- Any creature that blinks itself (or a spell with flashback/rebound) + an ETB engine creates a loop.
- Felidar Guardian + Saheeli Rai: Saheeli makes a copy of Felidar Guardian (ETB) → copy blinks Saheeli → Saheeli's loyalty resets → Saheeli makes another Felidar Guardian copy → infinite Felidar Guardian tokens.

---

### Sacrifice Loops
**Pattern**: Free (or self-paying) sacrifice outlet + a creature that returns itself from death.

**Mana-generating sacrifice outlets** (these can fuel the loop and pay for costs):
- Phyrexian Altar: Sacrifice a creature → add one mana of any color.
- Ashnod's Altar: Sacrifice a creature → add 2 colorless mana.
- Thermopod (snowflake): Similar.

**Free sacrifice outlets** (no mana cost):
- Viscera Seer: Sacrifice → scry 1.
- Carrion Feeder: Sacrifice → get +1/+1 counter.
- Altar of Dementia: Sacrifice → mill opponent.

**Self-returning creatures** (complete the loop):
- Persist creatures
- Undying creatures (when counters are removed)
- Squee, Goblin Nabob (returns to hand each upkeep)
- Reassembling Skeleton (pay 1B: return from graveyard to battlefield tapped)

---

### Mill + Reanimate
**Pattern**: Fill graveyard quickly → return the best cards cheaply.

**Mill enablers**: Mesmeric Orb, Altar of Dementia, dredge cards, self-mill creatures.

**Reanimate spells**: Reanimate, Animate Dead, Dance of the Dead, Exhume, Necromancy, Unburial Rites.

**The key synergy**: Large creatures that are expensive to cast can be put into the graveyard via discard or mill, then reanimated for as little as 1B. "Cheating" a 7-mana dragon into play on turn 2 via Reanimate.

**Graveyard interaction chain:**
- Entomb (tutor directly to graveyard) + Reanimate = turn 1-2 Griselbrand/Emrakul.
- Dredge cards refill graveyard each time you draw, fueling more Reanimate targets.

---

### Graveyard as Second Hand
**Key cards and patterns:**
- Flashback (cast from graveyard once)
- Escape (cast from graveyard, exile other cards as cost)
- Dredge (skip draw to return this card from graveyard to hand)
- Past in Flames (give all instants/sorceries in graveyard flashback)
- Yawgmoth's Will (play cards from graveyard this turn)

---

### Aristocrats (Death Trigger Engine)
**Three components needed:**
1. **Creatures to sacrifice**: Tokens, small creatures, self-replacing creatures.
2. **Sacrifice outlet**: Something to sacrifice them to (free or cheap).
3. **Payoff for dying**: Drain life, draw cards, create tokens, deal damage.

**Classic Aristocrats loop**:
- Reassembling Skeleton + Phyrexian Altar + Blood Artist:
  1. Sacrifice Skeleton → 1B mana. Blood Artist: "Opponent loses 1, you gain 1."
  2. Pay 1B to return Skeleton from graveyard.
  3. Repeat for infinite drain (need net 0 cost — Phyrexian Altar provides exactly 1B per sacrifice).

---

### Infinite Mana Patterns
Infinite mana requires a mana-producing combination that generates more mana than it costs to reset.

**Common infinite mana combos:**
- **Basalt Monolith + Rings of Brighthearth**: Basalt Monolith taps for 3 colorless. Pay 3 to untap it. Rings copies the untap ability for 2. Net: 3 mana in, 5 mana out = +2 each activation → infinite colorless.
- **Dramatic Reversal + Isochron Scepter**: Scepter imprints Dramatic Reversal. Activate scepter (2 mana) → Dramatic Reversal untaps all nonland permanents (including mana rocks). If mana rocks tap for more than 2 total → infinite mana.
- **Selvala, Heart of the Wilds** + large creature + bounce: Tap Selvala for mana equal to highest power creature. With a 10-power creature and ways to untap Selvala → enormous mana.
- **Phyrexian Altar + Persist loop**: As described above — sacrifice generates mana, loop refunds cost.

**What to do with infinite mana:**
- X spells (Fireball for infinite = win)
- Activated abilities (activate a kill ability infinite times)
- Draw your entire deck (if you have a draw outlet)

---

### Infinite Tokens
- **Divine Visitation** + token generators: If any effect creates a token, it creates a 4/4 angel instead. Pair with any cheap token generator.
- **Doubling Season** + Planeswalker: Enter with double loyalty counters → immediately ultimate.
- **Parallel Lives / Anointed Procession**: Token doublers + any token generation = exponential growth.
- **Bitterblossom** (slow drip) + token synergies.

---

### Recursion Loops
**Sun Titan + Sac outlet + cheap permanent:**
- Sun Titan ETB: return a permanent with CMC ≤ 3 from graveyard.
- Sacrifice Sun Titan to a sac outlet.
- Return Sun Titan with another effect, or include a CMC 3 or less recursion spell.

**Meren of Clan Nel Toth:**
- Experience counters accumulate each time a creature you control dies.
- At end of turn, return a creature from graveyard with CMC ≤ experience counters.
- This creates a self-fueling loop: sacrifice creatures → gain experience → return creatures.

---

### Proliferate Synergies
**Proliferate**: Add one more of each kind of counter already on each chosen permanent/player.

**Powerful proliferate targets:**
- Planeswalker loyalty counters (accelerate ultimates)
- +1/+1 counters (grow your creatures faster)
- Poison counters on opponents (win with infect faster)
- Charge counters on artifacts (Sphere of the Suns, Magistrate's Scepter)
- -1/-1 counters on opponent's creatures (kill them faster)
- Saga chapters (advance Sagas faster)
- Suspend counters (cards return faster — note: removing the LAST counter casts them)

---

### The "Combo" Recognition Framework
When evaluating two cards for combo potential, check:

1. **Resource loop**: Does A produce what B costs? Can this cycle indefinitely?
2. **Infinite condition**: Is there a net positive in each loop iteration?
3. **Win condition attached**: Is there a third card (drain, draw, mill) that converts the loop into a win, OR does the loop itself win directly?
4. **Mana cost**: Can the loop sustain itself or does it need external mana each iteration?
5. **Interrupt points**: What can stop the loop? (counter the trigger, exile the piece, etc.)
6. **Speed**: How many cards are needed? Can they be assembled quickly?

---

### Common Tribal Synergies
- **Lords**: Creatures that give +1/+1 (or more) to all creatures of a type. Stacks with multiple lords.
- **Tribe payoff**: Spells that cost less or are stronger for each creature of a type you control.
- **Tribal enablers**: Cards that tutor for creatures of a type, or produce tokens of a type.
- **Famous tribal synergies**:
  - Goblins: Many 1-drops + Goblin lords + Goblin Warchief (haste + cost reduction) + Goblin Grenade (5 damage, sacrifice goblin).
  - Zombies: Lords + mill effects that fill graveyard + zombie tokens from dying.
  - Elves: Many mana dork elves + elf lords + Craterhoof Behemoth finisher.
  - Merfolk: Islandwalk + lords + bounce effects for tempo.
  - Humans: Diverse powerful humans across all colors, anthem effects.
