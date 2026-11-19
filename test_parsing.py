from parsing import parse_results

def test_mirror_match_with_timeouts_and_same_names():
    log = """Simulation mode
Game Result: Game 1 ended in 37412 ms. Ai(1)-Sliver Demonstration has won!
Stopping slow match as draw
Game Result: Game 2 ended in 60001 ms. Ai(2)-Sliver Demonstration has won!
Game Result: Game 3 ended in 17644 ms. Ai(2)-Sliver Demonstration has won!
Stopping slow match as draw
Game Result: Game 4 ended in a Draw! Took 60001 ms.
"""
    d = parse_results(log,4,["Sliver Demonstration","Sliver Demonstration"],60)
    assert d["valid"] is True
    assert d["games_processed"] == 4
    assert d["games_completed"] == 2
    assert d["timeouts"] == 2
    assert d["wins"] == {"1":1, "2":1}
    assert d["results"][1]["winner"] is None
    assert d["results"][1]["status"] == "timeout"

def test_missing_results_is_not_valid():
    d = parse_results("Game Result: Game 1 ended in 100 ms. Ai(1)-A has won!", 2, ["A","A"],60)
    assert not d["valid"]

def test_no_timeout_when_valid_game_finishes():
    d = parse_results("Game Result: Game 1 ended in 100 ms. Ai(1)-A has won!",1, ["A","A"],60)
    assert d["valid"] and d["games_completed"] == 1 and d["timeouts"] == 0

def test_near_clock_without_message_is_conservative():
    d = parse_results("Game Result: Game 1 ended in 60000 ms. Ai(2)-A has won!",1, ["A","A"],60)
    assert d["timeouts"] == 1 and d["wins"]["2"] == 0
