# evaluate.py
#
# Honest measurement of the model. Two reports are built here:
#
#   1. BACKTEST: train on 2015-2022, test on 2023-2025 (the same experiment as week 4).
#   2. LIVE SEASON: train ONLY on seasons before the current one, then predict this
#      season's games that have already been played. The model never saw those games,
#      so this is a true "how are we doing right now?" scorecard.
#
# Both reports also include a calibration table: when the model says "60-70%", does
# the home team really win about 65% of the time? A model can be accurate and still
# give misleading percentages, so this checks that the percentages mean something.

import math

import numpy as np
from sklearn.metrics import log_loss

from src.features import FEATURES
from src.model import make_model

# Predicted home-win probabilities are sorted into these buckets for the
# calibration table: 0-30%, 30-40%, 40-50%, 50-60%, 60-70%, 70-100%.
CALIBRATION_EDGES = [0.0, 0.3, 0.4, 0.5, 0.6, 0.7, 1.0]

# How many of the most recent finished games to list on the scorecard.
RECENT_GAMES = 12


def wilson_interval(successes, n, z=1.96):
    """A 95% confidence interval for a proportion (like accuracy).

    With a finite number of games, an accuracy of 65.3% is only an estimate of the
    model's true accuracy. This gives the range the true value plausibly lies in.
    (The Wilson formula behaves better than the textbook one for smaller samples.)
    """
    if n == 0:
        return 0.0, 0.0
    p = successes / n
    denominator = 1 + z**2 / n
    centre = (p + z**2 / (2 * n)) / denominator
    half_width = z * math.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / denominator
    return centre - half_width, centre + half_width


def fit_and_predict(train, test):
    """Train a fresh model on `train` and return home-win probabilities for `test`."""
    model = make_model().fit(train[FEATURES], train["home_win"])
    return model.predict_proba(test[FEATURES])[:, 1]


def summarize(y_true, probs):
    """Accuracy (with interval), the always-pick-home baseline, and log loss."""
    picks = (probs > 0.5).astype(int)
    games = len(y_true)
    correct = int((picks == y_true).sum())
    low, high = wilson_interval(correct, games)
    return {
        "games": games,
        "correct": correct,
        "accuracy": correct / games,
        "accuracy_low": low,
        "accuracy_high": high,
        "home_pick_baseline": float(y_true.mean()),
        "log_loss": float(log_loss(y_true, probs, labels=[0, 1])),
    }


def calibration_table(y_true, probs, edges=CALIBRATION_EDGES):
    """For each probability bucket: how many games, what the model predicted on
    average, and how often the home team actually won."""
    # np.digitize returns which bucket (0, 1, 2, ...) each probability falls into.
    # We pass only the inner edges, so the result runs from 0 to len(edges) - 2.
    buckets = np.digitize(probs, edges[1:-1])
    rows = []
    for b in range(len(edges) - 1):
        in_bucket = buckets == b
        games = int(in_bucket.sum())
        rows.append({
            "low": edges[b],
            "high": edges[b + 1],
            "games": games,
            # A bucket with no games has nothing to average, so these stay None.
            "avg_predicted": float(probs[in_bucket].mean()) if games else None,
            "home_win_rate": float(y_true[in_bucket].mean()) if games else None,
        })
    return rows


def backtest_report(table):
    """Train on 2015-2022, test on 2023-2025."""
    train = table[table["season"] <= 2022]
    test = table[table["season"].between(2023, 2025)]
    probs = fit_and_predict(train, test)
    y = test["home_win"].to_numpy()
    return {
        "seasons": "2023-2025",
        "summary": summarize(y, probs),
        "calibration": calibration_table(y, probs),
    }


def live_report(table):
    """Predict the current season's finished games with a model that never saw them."""
    season = int(table["season"].max())
    train = table[table["season"] < season]
    test = table[table["season"] == season].copy()
    if train.empty or test.empty:
        return None

    probs = fit_and_predict(train, test)
    y = test["home_win"].to_numpy()
    test["home_win_prob"] = probs
    test["correct"] = (probs > 0.5).astype(int) == y

    # Accuracy week by week.
    by_week = [
        {"week": int(week), "games": len(group), "correct": int(group["correct"].sum())}
        for week, group in test.groupby("week")
    ]

    # The most recent finished games, newest first.
    recent_games = test.sort_values(["gameday", "game_id"], ascending=False).head(RECENT_GAMES)
    recent = [
        {
            "gameday": str(row.gameday.date()),
            "away_team": row.away_team,
            "home_team": row.home_team,
            "away_score": int(row.away_score),
            "home_score": int(row.home_score),
            "home_win_prob": round(float(row.home_win_prob), 3),
            "pick": row.home_team if row.home_win_prob > 0.5 else row.away_team,
            "correct": bool(row.correct),
        }
        for row in recent_games.itertuples()
    ]

    return {
        "season": season,
        "summary": summarize(y, probs),
        "by_week": by_week,
        "recent": recent,
    }


def build_scorecard(table):
    """Everything the website's 'How accurate is the model?' section shows."""
    return {
        "through": str(table["gameday"].max().date()),
        "backtest": backtest_report(table),
        "live": live_report(table),
    }