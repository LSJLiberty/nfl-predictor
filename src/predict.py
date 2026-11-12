# predict.py
#
# Turns the saved model bundle into answers: "what are the odds team A beats team B,
# and WHY does the model think so?"

import math
from itertools import permutations

import joblib
import pandas as pd

MODEL_PATH = "models/latest.joblib"

# For explanations, the model's six inputs are grouped into four plain-English reasons.
# (The four "recent form" numbers overlap heavily -- for example, margin is exactly
# points scored minus points allowed -- so it only makes sense to report them together.)
HOME_FIELD = "Home-field advantage"
STRENGTH = "Team strength (Elo)"
FORM = "Recent form"
REST = "Rest"
FACTOR_GROUPS = [
    (HOME_FIELD, []),  # comes from the model's starting value (its "intercept")
    (STRENGTH, ["elo_diff"]),
    (FORM, ["win_pct_diff", "margin_diff", "pts_for_diff", "pts_against_diff"]),
    (REST, ["rest_diff"]),
]


def load_bundle(path=MODEL_PATH):
    """Load the saved model plus the team ratings and recent form."""
    return joblib.load(path)


def sigmoid(x):
    """Turns any number into a probability between 0 and 1."""
    x = max(-50.0, min(50.0, x))  # keeps math.exp from overflowing on extreme inputs
    return 1 / (1 + math.exp(-x))


def explain(bundle, X, details):
    """Break a prediction into reasons, measured in percentage points.

    The model is a logistic regression: it adds up weighted evidence (in "log-odds")
    and converts the total to a probability. Here the evidence is split into four
    reasons, and we measure how far each one moves the probability away from a 50/50
    coin flip. The steps add up exactly to the final answer.

    A reason's effect depends on what was already counted before it (a push from 90%
    to 92% is smaller than one from 50% to 52%), so we average each reason's effect
    over EVERY possible order of adding the four reasons. This is the idea behind
    "Shapley values", and it makes the split fair no matter which reason is listed first.

    Positive points favor the HOME team, negative points favor the AWAY team.
    """
    scaler = bundle["model"].named_steps["scale"]
    classifier = bundle["model"].named_steps["clf"]

    # The model works on scaled inputs; multiplying each by its learned weight gives
    # that input's contribution to the total evidence.
    scaled = scaler.transform(X)[0]
    contribution = dict(zip(bundle["features"], classifier.coef_[0] * scaled))

    # Evidence (in log-odds) behind each of the four reasons.
    evidence = []
    for name, columns in FACTOR_GROUPS:
        if name == HOME_FIELD:
            evidence.append(float(classifier.intercept_[0]))
        else:
            evidence.append(float(sum(contribution[c] for c in columns)))

    # Try every order of adding the reasons (4 reasons -> 24 orders) and record how much
    # each one moves the probability when it is added.
    total_effect = [0.0] * len(evidence)
    orders = list(permutations(range(len(evidence))))
    for order in orders:
        running_total = 0.0
        previous_probability = 0.5
        for i in order:
            running_total += evidence[i]
            probability = sigmoid(running_total)
            total_effect[i] += probability - previous_probability
            previous_probability = probability

    return [
        {
            "name": name,
            # Average over the orders, convert to percentage points, and round for display.
            # "+ 0.0" turns a result of -0.0 into a plain 0.0.
            "points": round(effect / len(orders) * 100, 1) + 0.0,
            "detail": details[name],
        }
        for (name, _), effect in zip(FACTOR_GROUPS, total_effect)
    ]


def predict_matchup(bundle, home_team, away_team, rest_diff=0, with_factors=False):
    """Probability that home_team beats away_team, using the current ratings."""
    ratings = bundle["ratings"]
    form = bundle["team_form"]

    for team in (home_team, away_team):
        if team not in ratings or team not in form.index:
            raise ValueError(f"Unknown team: {team}")

    h = form.loc[home_team]
    a = form.loc[away_team]
    row = {
        "win_pct_diff": h["win_pct_last5"] - a["win_pct_last5"],
        "margin_diff": h["margin_last5"] - a["margin_last5"],
        "rest_diff": rest_diff,
        "pts_for_diff": h["pts_for_last5"] - a["pts_for_last5"],
        "pts_against_diff": h["pts_against_last5"] - a["pts_against_last5"],
        "elo_diff": ratings[home_team] - ratings[away_team],
    }
    X = pd.DataFrame([row])[bundle["features"]]
    home_prob = float(bundle["model"].predict_proba(X)[0, 1])

    result = {
        "home_team": home_team,
        "away_team": away_team,
        "home_win_prob": round(home_prob, 3),
        "away_win_prob": round(1 - home_prob, 3),
        "pick": home_team if home_prob > 0.5 else away_team,
    }

    if with_factors:
        # One short sentence per reason, with the real numbers behind it.
        details = {
            HOME_FIELD: f"{home_team} is playing at home.",
            STRENGTH: (f"Elo rating: {home_team} {ratings[home_team]:.0f} "
                       f"vs {away_team} {ratings[away_team]:.0f}."),
            FORM: (f"Average margin over the last 5 games: {home_team} "
                   f"{h['margin_last5']:+.1f} vs {away_team} {a['margin_last5']:+.1f}."),
            REST: ("Both teams had the same rest." if rest_diff == 0
                   else f"{home_team} had {rest_diff:+d} days of rest compared with {away_team}."),
        }
        result["factors"] = explain(bundle, X, details)

    return result


def predict_upcoming(bundle, upcoming, n=16):
    """Predictions for the next n unplayed games on the schedule."""
    results = []
    for row in upcoming.head(n).itertuples():
        rest_diff = row.home_rest - row.away_rest
        result = predict_matchup(bundle, row.home_team, row.away_team, rest_diff)
        result["gameday"] = str(row.gameday.date())
        results.append(result)
    return pd.DataFrame(results)


if __name__ == "__main__":
    # Imported here, not at the top of the file, so the web API (which imports this
    # file) doesn't have to load the data-downloading libraries just to make predictions.
    from src.data import load_games, split_completed

    bundle = load_bundle()
    print(f"Model trained through {bundle['trained_through']}\n")

    games = load_games()
    _, upcoming = split_completed(games)
    print(predict_upcoming(bundle, upcoming).to_string(index=False))