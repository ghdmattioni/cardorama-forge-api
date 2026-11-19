from details import extract_details

SOURCE = """Simulation mode
Turn: Turn 1 (Ai(1)-Demo)
Mulligan: Ai(1)-Demo mulligans
Land: Ai(1)-Demo played Forest
Add To Stack: Ai(1)-Demo cast Cultivate
Resolve Stack: Cultivate resolves
Turn: Turn 2 (Ai(2)-Demo)
Add To Stack: Ai(2)-Demo triggered Brood Sliver
Combat: Ai(2)-Demo attacks
Game Outcome: Turn 2
Game Result: Game 1 ended in 1452 ms. Ai(1)-Demo has won!

Turn: Turn 1 (Ai(2)-Demo)
Land: Ai(2)-Demo played Forest
Game Result: Game 2 ended in a Draw! Took 1500 ms.
"""
DECK = """1 Forest
1 Cultivate
1 Brood Sliver
1 Sinew Sliver"""

def test_events_grouped_by_turn_and_game():
    result = extract_details(SOURCE,[DECK,DECK],2)
    assert result["games_with_logs"] == 2
    assert result["games"][1][0]["turn"] == 1
    assert result["games"][1][5]["turn"] == 2
    assert result["games"][2][0]["turn"] == 1
    assert result["card_analysis"]["Cultivate"]["cast_games"] == 1
    assert result["card_analysis"]["Forest"]["played_games"] == 2
    assert result["card_analysis"]["Brood Sliver"]["signal"] == "observed_without_recorded_play"
    assert result["card_analysis"]["Sinew Sliver"]["signal"] == "not_observed"

def test_resolves_not_confused_with_cast():
    result = extract_details("Turn: Turn 1 (Ai(1)-A)\nResolve Stack: Cultivate resolves\nGame Result: Game 1 ended in 10 ms. Ai(1)-A has won!",[DECK],1)
    assert result["card_analysis"]["Cultivate"]["played_games"] == 0

def test_overlapping_names_not_double_counted():
    d="1 Sliver\n1 Brood Sliver"
    out="Turn: Turn 1 (Ai(1)-Demo)\nAdd To Stack: Ai(1)-Demo cast Brood Sliver\nGame Result: Game 1 ended in 10 ms. Ai(1)-Demo has won!"
    result=extract_details(out,[d],1)
    assert result["card_analysis"]["Sliver"]["observed_games"]==0
    assert result["card_analysis"]["Brood Sliver"]["cast_games"]==1

def test_event_cap_flagged():
    result=extract_details(SOURCE,[DECK],2,max_events=2)
    assert result["events_exceeded"] is True
