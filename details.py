"""Read-only event extraction for Forge headless -- no inference of hidden hands.

Extracts turn, phase, cast, triggered, activated, land, combat, life and zone
events printed by Forge GameLogEntry. Observations are *not* card quality scores.
"""
import re
from collections import defaultdict

CAPTIONS = {
    "Turn":"turn", "Phase":"phase", "Mulligan":"mulligan",
    "Add To Stack":"stack_add", "Resolve Stack":"stack_resolve",
    "Land":"land", "Damage":"damage", "Life":"life",
    "Zone Change":"zone_change", "Discard":"discard",
    "Combat":"combat", "Mana":"mana", "Information":"information",
    "Replacement Effect":"replacement_effect", "Player Control":"player_control",
    "Game Outcome":"game_outcome", "Match Result":"match_result",
    "Sideboard":"sideboard", "Ante":"ante"
}
LOG_RX = re.compile(r"^("+"|".join(re.escape(x) for x in sorted(CAPTIONS,key=len,reverse=True))+r"):\s*(.*)$")
RESULT_RX = re.compile(r"^Game Result:\s*Game\s+(\d+)\s+ended",re.I)
TURN_RX = re.compile(r"\b(?:turn|turno)\s*(\d+)\b",re.I)
ACTOR_RX = re.compile(r"Ai\((\d+)\)-",re.I)

def catalogue(decklists):
    """Decklists in Forge DCK or import text; preserve exact card names."""
    found = set()
    for text in decklists:
        for line in text.splitlines():
            m = re.fullmatch(r"\s*(\d{1,3})\s+(.+?)\s*",line)
            if m:
                found.add(m.group(2))
    # Some card names contain regex metacharacters. Match longest first.
    return [(c,re.compile(r"(?<![A-Za-z0-9])"+re.escape(c)+r"(?![A-Za-z0-9])",re.I)) for c in sorted(found,key=len,reverse=True)]

def extract_details(stdout, decklists, expected_games, max_events=30000):
    """Parse complete log lines between Game Result separators.

    game logs appear *before* Game Result, and reset on each match.
    The number of processed lines is capped to avoid exhausting a 1 GB worker.
    """
    patterns = catalogue(decklists)
    games = {}
    current = []
    turn = None
    total = 0
    exceeded = False
    for line in stdout.splitlines():
        closing = RESULT_RX.match(line)
        if closing:
            num = int(closing.group(1))
            if 1 <= num <= expected_games and num not in games:
                games[num] = current
            current = []
            turn = None
            continue
        parsed = LOG_RX.match(line)
        if not parsed:
            continue
        if total >= max_events:
            exceeded = True
            continue
        caption,message = parsed.groups()
        kind = CAPTIONS[caption]
        if kind == "turn":
            turn_match = TURN_RX.search(message)
            turn = int(turn_match.group(1)) if turn_match else None
        actor_match = ACTOR_RX.search(message)
        actor = int(actor_match.group(1)) if actor_match else None
        cards = []
        spans = []
        # Prevent a shorter card name being credited within a longer card name.
        for name,pattern in patterns:
            for match in pattern.finditer(message):
                if all(match.end() <= a or match.start() >= b for a,b in spans):
                    spans.append((match.start(),match.end()))
                    cards.append(name)
                    break
        action = kind
        if kind == "stack_add":
            if re.search(r"\bcast\b",message,re.I):
                action = "spell_cast"
            elif re.search(r"\bactivated\b",message,re.I):
                action = "ability_activated"
            elif re.search(r"\btriggered\b",message,re.I):
                action = "ability_triggered"
        elif kind == "land":
            action = "land_played"
        ev = {"seq":len(current)+1,"turn":turn,"player":actor,"type":action,"text":message,"cards":cards}
        current.append(ev)
        total += 1
    analysis = {}
    for name,_ in patterns:
        observed_games = set()
        played_games = set()
        cast_games = set()
        actions = defaultdict(int)
        for game,events in games.items():
            for ev in events:
                if name not in ev["cards"]:
                    continue
                observed_games.add(game)
                actions[ev["type"]]+=1
                if ev["type"] in ("spell_cast","land_played"):
                    played_games.add(game)
                    if ev["type"] == "spell_cast":
                        cast_games.add(game)
        if not observed_games:
            signal = "not_observed"
        elif not played_games:
            signal = "observed_without_recorded_play"
        else:
            signal = "played"
        analysis[name]={
            "observed_games":len(observed_games),
            "played_games":len(played_games),
            "cast_games":len(cast_games),
            "event_counts":dict(actions),
            "signal":signal,
            "note":"Ausência nos logs não prova que a carta não foi comprada ou que seja fraca."
        }
    return {
        "games":games,
        "card_analysis":analysis,
        "events_captured":total,
        "events_exceeded":exceeded,
        "games_with_logs":len(games),
        "limitations":[
            "Forge GameLog não contém todas as compras e mãos ocultas.",
            "Observações baseadas em texto são heurísticas, não garantias de identidade da carta.",
            "Ativações/habilidades podem ser registradas sem que a carta tenha sido conjurada.",
            "Para medir turnos presa na mão, seria necessária instrumentação do motor Forge."
        ]
    }
