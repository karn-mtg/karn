# Example Interactions & Q&A

## Simple Synergy Examples

**Q: I have a card that says "Goblins you control get +1/+1" and a 1/1 Goblin creature. Is there a synergy?**
A: Yes. The first card is a "lord" effect — a static ability that buffs all creatures of the named type. Your 1/1 Goblin becomes a 2/2 as long as the lord is on the battlefield. This is a direct tribal synergy. Additional Goblin lords stack: two lords would make your 1/1 Goblin a 3/3.

---

**Q: I have a creature with "When this enters the battlefield, draw a card" and a spell that says "Exile target creature you control, return it to the battlefield under its owner's control." Do these synergize?**
A: Yes — strongly. The exile-and-return effect is called a "blink" or "flicker." When the creature returns to the battlefield, it's treated as a new instance of that permanent, so its ETB (enters the battlefield) trigger fires again. Result: each time you cast that blink spell, you draw another card. With a free or repeatable blink effect this becomes infinite card draw.

---

**Q: I have a mill card ("Target player puts top 4 cards of their library into their graveyard") and a reanimate card ("Pay 1B: Return target creature card from any graveyard to the battlefield under your control"). Synergy?**
A: Yes. This is the classic Mill + Reanimate package. You mill your own library (self-mill) to load it with powerful creatures, then reanimate the best ones cheaply. The synergy: large creatures are expensive to cast legitimately (6-8 mana), but reanimate costs just 1B. Milling yourself bypasses the casting cost entirely. The deck is called "Reanimator."

---

## Complex Combo Examples

**Q: Explain the First Day of Class + Kitchen Finks combo.**
A: This is an infinite death loop. Here's the complete breakdown:

**Cards needed:**
1. First Day of Class (enchantment): "Whenever a creature enters the battlefield under your control, it gets a +1/+1 counter."
2. Kitchen Finks (creature with Persist): When Kitchen Finks dies with NO -1/-1 counters, it returns with a -1/-1 counter.
3. A free sacrifice outlet (e.g., Viscera Seer, Carrion Feeder).
4. A payoff (e.g., Blood Artist: "Whenever a creature you control dies, each opponent loses 1 life and you gain 1 life").

**The loop:**
1. First Day of Class is on the battlefield.
2. Kitchen Finks enters the battlefield. First Day of Class triggers → Finks gets a +1/+1 counter.
3. Sacrifice Finks to your outlet. Blood Artist trigger: each opponent loses 1 life.
4. Persist triggers: Finks returns to the battlefield with a -1/-1 counter.
5. First Day of Class triggers again: Finks gets a +1/+1 counter.
6. State-based actions: the +1/+1 counter and the -1/-1 counter on Finks cancel each other out. Finks now has ZERO counters.
7. Go to step 3. Repeat infinitely.

**Result:** With Blood Artist, each sacrifice causes each opponent to lose 1 life. Infinite sacrifices = infinite life loss = all opponents lose.

**Why it works:** Persist returns the creature with a -1/-1 counter, which would normally prevent persist from firing again. But First Day of Class adds a +1/+1 counter on entry, canceling the -1/-1 counter via state-based actions. The creature perpetually re-enters with no net counters.

---

**Q: What is the Deadeye Navigator combo?**
A: Deadeye Navigator is a creature that can "soul-bond" with another creature, and for 1U you can flicker (blink) the bonded creature. This enables infinite ETB triggers on any creature with a powerful ETB.

**Classic line:**
1. Deadeye Navigator soul-bonds with Peregrine Drake (ETB: untap up to 5 lands).
2. Pay 1U to blink Peregrine Drake.
3. Drake ETBs, untapping 5 lands. Those 5 lands produce 5+ mana.
4. Pay 1U again from that mana. Net: +3 or more mana per activation.
5. Repeat for infinite mana.

With infinite mana: draw your entire deck (if you have a draw outlet), deal infinite damage with a burn outlet, or similar.

---

**Q: Two cards: "Sacrifice a creature: Add one mana of any color" (Phyrexian Altar) and a creature with both Undying AND the effect from Mikaeus, the Unhallowed who gives all non-human creatures Undying. Synergy?**
A: Phyrexian Altar + persist creature (+ Mikaeus for undying) is the classic infinite sacrifice combo.

**Mikaeus, the Unhallowed** gives all non-human creatures you control +1/+1 and undying.

**Full loop:**
1. Non-human persist creature (e.g., Murderous Redcap) is on the battlefield with no counters.
2. Sacrifice to Phyrexian Altar: add one mana.
3. Murderous Redcap dies. BOTH persist and undying (from Mikaeus) want to trigger. Only one can apply as a replacement effect. Choose persist: returns with -1/-1 counter. Mikaeus also gives +1/+1... they cancel.
4. Actually: Mikaeus gives the creature +1/+1 as a static effect (not a counter). The +1/+1 counter from Mikaeus's undying triggers when it returns. The -1/-1 from persist and the +1/+1 from undying cancel. Net: 0 counters.
5. Sacrifice again → repeat.

**Payoff**: Murderous Redcap's ETB deals damage equal to its power. Each time it re-enters, it deals damage. Infinite damage to opponents.

---

**Q: What is the Splinter Twin / Kiki-Jiki combo?**
A: Both Splinter Twin (enchantment) and Kiki-Jiki, Mirror Breaker (creature) create a tapped token copy of an enchanted/targeted creature at instant speed, with the token being sacrificed at end of turn.

**The combo:**
1. Attach Splinter Twin to a creature with "When this enters the battlefield, untap target creature" (e.g., Pestermite, Deceiver Exarch).
2. Tap the enchanted creature to create a tapped token copy.
3. The token's ETB triggers: untap the original creature.
4. Tap the original creature again to create another token.
5. Repeat for infinite tokens.
6. Attack with all tokens for lethal (they're sacrificed at end of turn, but you attack first in your combat step).

**Format note**: This combo was banned in Modern due to its speed and consistency.

---

## Archetype Recognition Examples

**Q: My opponent has a deck with lots of cheap creatures, Lightning Bolt, and Goblin Guide. What archetype is this?**
A: Mono-Red Burn or Red Aggro. Classic aggro archetype. Plan is to deal 20 damage before you can stabilize. Priority: don't take early damage, use your removal proactively, gain life if possible. Aggro runs out of cards — the longer the game goes, the better for you (if you're on control/midrange).

---

**Q: My deck has: Soul Warden, Zulaport Cutthroat, Viscera Seer, Reassembling Skeleton, Phyrexian Altar, and Blood Artist. What archetype is this?**
A: Aristocrats — a sacrifice-based combo/value deck. Your win condition is draining opponents via Blood Artist and Zulaport Cutthroat triggers from repeated creature deaths. The engine: Reassembling Skeleton returns for 1B each time, which is funded by Phyrexian Altar. Soul Warden gains life on each entry, padding your life total. Viscera Seer is a free sacrifice outlet to scry and trigger your drains.

---

## Card Interaction Edge Cases

**Q: My creature has Hexproof. Can my opponent target it?**
A: No — Hexproof means "This permanent can't be the target of spells or abilities your opponents control." Your opponent cannot legally target it with removal, auras, or any other targeted effect. You CAN target your own hexproof creatures.

---

**Q: My creature is Indestructible. My opponent plays "Target creature gets -4/-4 until end of turn." Does it die?**
A: Yes. Indestructible only prevents death from damage and "destroy" effects. If your creature's toughness drops to 0 or less from a -X/-X effect, it dies from a state-based action (zero toughness), which bypasses indestructible. For example, a 2/2 indestructible creature targeted by -4/-4 becomes -2/-2: dies immediately from 0 or less toughness.

---

**Q: My opponent attacks with a 5/5 Trample creature. I block with a 2/2. How much damage do I take?**
A: 3 damage. The attacking creature must assign lethal damage to your blocker first (2 damage, equal to its toughness). The remaining 3 damage tramples over to you. If your blocker had First Strike, it would deal damage first (killing the 5/5 before it can deal trample damage), and you'd take 0.
