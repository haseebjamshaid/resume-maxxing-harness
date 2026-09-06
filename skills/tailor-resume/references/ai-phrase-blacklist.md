# AI phrase blacklist

Ported from Resume-Matcher (`apps/backend/app/prompts/refinement.py`). The
machine-readable copy lives in `scripts/ai_phrases.py`, which `lint_resume.py`
enforces; this file is the human-readable brief for the writing passes.

Never emit any of these. Prefer the plain alternative.

## Action verbs

| Avoid | Use |
|---|---|
| spearheaded | led |
| orchestrated | coordinated |
| championed | advocated for |
| synergized | collaborated |
| leveraged | used |
| revolutionized | transformed |
| pioneered | introduced |
| catalyzed | initiated |
| operationalized | implemented |
| architected | designed |
| envisioned | planned |
| effectuated | completed |
| endeavored | worked |
| facilitated | helped |
| utilized | used |

## Corporate buzzwords

| Avoid | Use |
|---|---|
| synergy / synergies | collaboration / collaborations |
| paradigm | approach |
| paradigm shift | change |
| best-in-class | top-performing |
| world-class | high-quality |
| cutting-edge / bleeding-edge | modern |
| game-changer | innovation |
| game-changing / disruptive | innovative |
| disruptor | *(remove)* |
| holistic | comprehensive |
| robust | strong |
| scalable | expandable |
| actionable | practical |
| impactful | effective |
| proactive / proactively | active / actively |
| stakeholder | team member |
| deliverables | outputs |
| bandwidth | capacity |
| circle back | follow up |
| deep dive | analysis |
| move the needle | make progress |
| low-hanging fruit | quick wins |
| touch base | connect |
| value-add | benefit |

## Filler phrases

| Avoid | Use |
|---|---|
| in order to / for the purpose of / with a view to | to |
| at the end of the day | *(remove)* |
| moving forward / going forward | *(remove)* |
| on a daily basis | daily |
| on a regular basis | regularly |
| in a timely manner | promptly |
| at this point in time | now |
| due to the fact that | because |
| in the event that | if |
| in light of the fact that | since |

## Punctuation

`—` (em dash), `---` and `--` are all banned. Use a comma or a semicolon.

## Weak openers

From `ANALYZE_RESUME_PROMPT`'s weak-description indicators. A bullet opening
with any of these says nothing about what you actually did:

`responsible for`, `worked on`, `helped with`, `assisted in`, `involved in`

Also treated as weak upstream, though not mechanically checked: missing
metrics or impact, unclear scope, no named technologies, passive voice with no
ownership, and a single short bullet that does not explain the work.
