from run import score


def test_expected_matches_whole_word_only():
    assert score({"expected": "Au"}, "The symbol is Au.") == 1
    assert score({"expected": "Au"}, "Because") == 0


def test_must_not_contain():
    assert score({"must_not_contain": "SECRET"}, "nothing to see") == 1
    assert score({"must_not_contain": "SECRET"}, "the secret is 1") == 0
