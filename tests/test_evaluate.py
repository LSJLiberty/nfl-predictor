import numpy as np
import pandas as pd
import pytest

from src.evaluate import build_scorecard, calibration_table, summarize, wilson_interval
from src.features import FEATURES


def make_table(games_per_season=40, seed=0):
    """A fake feature table (seasons 2015-2026) where a bigger elo_diff really does
    make a home win more likely, so a trained model should beat a coin flip."""
    rng = np.random.default_rng(seed)
    frames = []
    for season in range(2015, 2027):
        n = games_per_season
        features = pd.DataFrame(rng.normal(size=(n, len(FEATURES))), columns=FEATURES)
        chance_home_wins = 1 / (1 + np.exp(-1.5 * features["elo_diff"]))
        features["home_win"] = (rng.random(n) < chance_home_wins).astype(int)
        features["season"] = season
        features["week"] = np.arange(n) % 18 + 1
        features["gameday"] = pd.to_datetime(f"{season}-09-01") + pd.to_timedelta(np.arange(n), unit="D")
        features["game_id"] = [f"{season}_{i:03d}" for i in range(n)]
        features["home_team"] = "AAA"
        features["away_team"] = "BBB"
        features["home_score"] = np.where(features["home_win"] == 1, 27, 20)
        features["away_score"] = np.where(features["home_win"] == 1, 20, 27)
        frames.append(features)
    return pd.concat(frames, ignore_index=True)


def test_wilson_interval_for_a_known_case():
    low, high = wilson_interval(50, 100)
    assert low == pytest.approx(0.404, abs=0.002)
    assert high == pytest.approx(0.596, abs=0.002)


def test_wilson_interval_with_no_games_does_not_crash():
    assert wilson_interval(0, 0) == (0.0, 0.0)


def test_summarize_perfect_predictions():
    y = np.array([1, 0, 1, 1])
    probs = np.array([0.9, 0.1, 0.8, 0.7])
    summary = summarize(y, probs)
    assert summary["accuracy"] == 1.0
    assert summary["correct"] == 4
    assert summary["home_pick_baseline"] == 0.75  # the home team won 3 of 4


def test_calibration_buckets_cover_every_game():
    probs = np.array([0.1, 0.35, 0.5, 0.55, 0.65, 0.9])
    y = np.array([0, 0, 1, 1, 1, 1])
    rows = calibration_table(y, probs)
    assert sum(r["games"] for r in rows) == len(probs)
    # A probability of exactly 0.5 belongs in the 50-60% bucket.
    bucket_50_60 = next(r for r in rows if r["low"] == 0.5)
    assert bucket_50_60["games"] == 2
    # A bucket with no games reports None instead of a made-up number.
    empty = [r for r in rows if r["games"] == 0]
    assert all(r["avg_predicted"] is None for r in empty)


def test_scorecard_has_a_backtest_and_a_live_season():
    card = build_scorecard(make_table())
    assert card["backtest"]["summary"]["games"] == 3 * 40   # seasons 2023-2025
    assert card["backtest"]["summary"]["accuracy"] > 0.6    # the fake signal is strong
    live = card["live"]
    assert live["season"] == 2026
    assert live["summary"]["games"] == 40
    assert len(live["recent"]) == 12
    # Newest game first.
    dates = [g["gameday"] for g in live["recent"]]
    assert dates == sorted(dates, reverse=True)
    # Weeks add up to all the games.
    assert sum(w["games"] for w in live["by_week"]) == 40