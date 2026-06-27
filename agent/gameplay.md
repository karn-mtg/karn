# Gameplay Knowledge

This file teaches the agent how to evaluate game states, make decisions, and advise on in-game play — not just deck construction.

<!-- BEGIN GAMEPLAY KNOWLEDGE -->

## The Two Stages of a Commander Game

Understanding which stage the game is in determines how every resource should be used.

### Early Stage (turns 1–5)
- Mana is scarce; hands are full
- Players race to develop boards and establish engines
- **Tempo is the dominant resource** — board presence and mana efficiency matter most
- Aggressive plays are high-value here; falling behind is hard to recover from
- Deploy your best early plays, not your answers

### Late Stage (turns 6+)
- Mana is abundant; hands empty out
- **Card advantage becomes the dominant resource** — the player who runs out of cards loses
- Individual card quality matters more than speed
- Tempo advantages are hard to generate; value extraction from each spell is the priority
- Patience has higher payoff — hold interaction for the most impactful moments

**Rule:** Identify which stage the game is in before deciding how to spend your mana or which spell to cast.

---

## Tempo vs. Card Advantage

These two resources compete constantly. Understanding the trade-off is the core skill of Magic.

**Tempo** = board development, mana efficiency, board presence relative to opponents.
**Card advantage** = having more resources available (cards in hand, permanents generating value) than opponents.

| Situation | Prioritize | Why |
|---|---|---|
| You're ahead on board (early) | Tempo — press the advantage | Force opponents to spend resources catching up |
| You're behind on board | Card advantage — find answers | Raw tempo won't close the gap; need more resources |
| Opponents are doing nothing | Tempo — develop freely | No reason to hold up mana for answers |
| Stack is full, threats inbound | Card advantage — hold interaction | Spend resources on the most impactful threat |
| Mid-game stalemate | Card advantage — draw engines win stalemates | The player who draws more cards breaks parity |

**Practical rule:** In early game, cast your threats and develop your board; don't hold up interaction unless you know a specific threat is coming. In late game, hold interaction and spend it on the must-answer cards, not the first thing opponents play.

---

## Threat Assessment — The Core of Multiplayer Decision-Making

In Commander (4 players), you cannot fight everyone. Threat assessment is analyzing the board state to determine:
1. Who is closest to winning (or who will prevent you from winning)?
2. What is the most dangerous permanent on the board?
3. Where should your removal, attacks, and political capital go?

### Threat Hierarchy (what to target first)

| Threat type | Priority | Notes |
|---|---|---|
| Kills you this turn | Immediately | No choice — must answer |
| Wins the game over time (engine, combo assembly) | Very high | Remove before it's too late |
| Draw engine (Rhystic Study, Tymna, The One Ring) | High | Card advantage threats grow exponentially |
| Mana production advantage (Sol Ring played early, heavy ramp) | High | They'll deploy threats faster than you can answer |
| Large board presence | Medium | Dangerous but often requires time to attack |
| Life total advantages | Low | Matters mainly for control players with long-game plans |

### Key Threat Indicators

- **Card advantage engines** are the #1 threat. The player drawing the most cards typically wins. Remove draw engines early.
- **Mana acceleration** (sol ring, heavy green ramp in first 3 turns) lets players deploy 2–3 threats per turn before anyone else can respond.
- **Single powerful permanents** (Elesh Norn, Doubling Season, Smothering Tithe) often threaten more than a wide board.
- **Combo assembly:** Watch for players tutoring repeatedly or fetching specific pieces. When you see 2 of a 3-card combo assembled, act.
- **Synergy engines** (Aesi + Simic Growth Chamber) generate advantage every turn with no additional investment — remove them before they compound.

### Threat Assessment Mistakes

| Mistake | Why it's wrong |
|---|---|
| Linear thinking (X attacked me last turn, so X is the threat) | Threat status changes every turn — reassess constantly |
| Vindictive play (punishing interaction) | Feeding the actual threat while focusing on personal grievances |
| Using removal on the first threat you see | Hold interaction until it's critical; conserve resources |
| Believing "I haven't done anything" rhetoric | A player ramping and drawing is a massive threat regardless of what they say |
| Attacking the weakest player out of habit | Attack who will win if left unchecked, not who is easiest to damage |

---

## Combat Decision Framework

**When to attack:**
- Attack players developing long-game resource engines (blue/green control, ramp decks) to deny them time
- Attack to deal commander damage when your commander is the win condition
- Attack when you have enough power to meaningfully threaten a player's life total
- Attack with small creatures into open boards to apply pressure without wasting combat

**When NOT to attack:**
- Don't attack into open mana with blockers available unless the damage is critical
- Don't attack the player with a Ghostly Prison / Propaganda effect without a plan
- Don't attack another player when a third player is clearly assembling a combo — point your combat at the combo player

**Blocking decisions:**
- Block to prevent lethal damage
- Block with higher-value creatures only if the trade is worth it (kills their best attacker)
- Let small attackers through if blocking loses you important pieces

---

## Resource Management Principles

**Mana:** Never waste mana without reason. If you end your turn with mana unused, ask whether you should have cast something. Wasted mana is a tempo loss.

**Cards in hand:** Emptying your hand early makes you vulnerable to interaction. Keep 1–3 cards in hand as "threat of what I might do."

**Life total:** In Commander, life is a resource — spending it (through Phyrexian mana, Ancient Tomb, fetches) is valid if it buys decisive advantage. Don't die to self-inflicted damage, but don't treat life as untouchable either.

**Removal:** Don't over-spend removal on threats other players will handle. In a 4-player game, three other players will also interact with threats. Hold removal for threats that specifically stop you, or that no one else is positioned to answer.

---

## Stack and Priority Decisions

**When to hold up interaction:**
- If you're passing with open mana, you're representing interaction — opponents will play around it
- Hold interaction when you know what you're afraid of (combo piece, specific threat)
- Passing without spending mana is a signal; use it strategically

**When to act vs. respond:**
- Act at sorcery speed (main phase) when you want to maximize the effect or play out development
- Respond at instant speed when order matters or you want to hold your options open
- Let the stack build before responding — other players may handle a threat before it becomes your problem

**Priority passing in multiplayer:**
- When one player casts a threat, wait to see if others respond before spending your interaction
- Responding last on the stack means your spell resolves first — a timing advantage for counters and removal

---

## Political Decision-Making

Commander is a multiplayer social game. Pure optimization without considering table dynamics leads to becoming the target.

**Partner with behind players to address the leader.** A player who is losing is an ally in handling the threat. Propose deals: "I'll use my removal if you attack into them this turn."

**Manage threat perception:** If you're winning, hide it. Don't overextend onto the board unless you can protect it or win immediately. Announce your threats subtly; a player who looks like they're doing nothing is harder to attack.

**Second-biggest threat philosophy:** Often the correct play is to be the second-most dangerous player at the table — threatening enough that people deal with the leader before you, but not so threatening that you become the primary target.

**When deals are useful:**
- When you need to answer a threat your colors can't handle
- When you need combat elsewhere while you're going for a win
- When you need to buy a turn before opponents take a critical action

**When deals are not useful:**
- Don't make deals you can't or won't honor — table reputation matters across multiple games
- Don't promise something to slow down a threat if you're already winning — just win

---

## How to Evaluate a Card During Gameplay

When deciding whether to cast a card in a game situation:

1. **Does casting it advance my win condition?** If no, reconsider.
2. **Does waiting give me more information?** If opponents haven't acted yet, sometimes holding is better.
3. **Can I protect this card's effect once it resolves?** A fragile engine that gets removed immediately may not be worth the tempo.
4. **Does this card slow down the biggest threat?** If yes, it's usually correct to cast it.
5. **Do I have enough mana to also hold up interaction after casting?** If casting leaves you tapped out, make sure you're not leaving a window for opponents to act.

---

## Knowing When to Go for the Win

**Signs you should try to close the game:**
- You have assembled enough pieces to win with protection
- The table is distracted (a threat is being handled)
- You're about to lose your key pieces anyway
- You've drawn into your combo and have counter-magic backup

**Signs to wait:**
- You can win next turn and need opponents to not know yet
- Your win requires passes through opponent interaction you can't answer
- Another player is about to lose, which reduces the number of opponents you face

**The window principle:** Win attempts work best when opponents have spent their interaction on each other. Build toward your win while letting others fight. Execute when interaction is depleted.

<!-- END GAMEPLAY KNOWLEDGE -->
