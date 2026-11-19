"""Conservative parser for Forge 2.0.16 headless results.

Separate stdout and stderr before parsing: Forge emits stack traces from timeout
threads to stderr, which can otherwise split a Game Result line mid-word.
A timeout is never counted as a win, even when Forge prints a winner afterward.
"""
import re

WIN_LINE = re.compile(r"^\s*Game Result:\s*Game\s+(\d+)\s+ended in\s+(\d+)\s+ms\.\s+Ai\((\d+)\)-(.+?)\s+has won!\s*$")
DRAW_LINE = re.compile(r"^\s*Game Result:\s*Game\s+(\d+)\s+ended in a Draw!\s+Took\s+(\d+)\s+ms\.\s*$")

def parse_results(stdout: str, expected_games: int, deck_names: list[str], clock_seconds: int) -> dict:
    outcomes = {}
    timed_out = False
    for line in stdout.splitlines():
        if "Stopping slow match as draw" in line:
            timed_out = True
        win = WIN_LINE.fullmatch(line.strip())
        draw = DRAW_LINE.fullmatch(line.strip())
        if win:
            game, ms, player, name = win.groups()
            game, ms, player = int(game), int(ms), int(player)
            if not (1 <= game <= expected_games and 1 <= player <= len(deck_names)):
                continue
            if name != deck_names[player - 1] or game in outcomes:
                continue
            is_timeout = timed_out or ms >= clock_seconds * 1000
            outcomes[game] = {"game":game,"status":"timeout" if is_timeout else "win","winner":None if is_timeout else player,"duration_ms":ms}
            timed_out = False
        elif draw:
            game, ms = map(int,draw.groups())
            if not (1 <= game <= expected_games) or game in outcomes:
                continue
            is_timeout = timed_out or ms >= clock_seconds * 1000
            outcomes[game] = {"game":game,"status":"timeout" if is_timeout else "draw","winner":None,"duration_ms":ms}
            timed_out = False
    ordered = [outcomes[n] for n in sorted(outcomes)]
    wins = {str(i): sum(x["winner"] == i for x in ordered) for i in range(1,len(deck_names)+1)}
    timeouts = sum(x["status"] == "timeout" for x in ordered)
    draws = sum(x["status"] == "draw" for x in ordered)
    valid = sorted(outcomes) == list(range(1,expected_games+1)) and stdout.count("Game Result:") == expected_games
    return {"games_processed":len(ordered),"games_completed":len(ordered)-timeouts,"wins":wins,"draws":draws,"timeouts":timeouts,"results":ordered,"valid":valid}
