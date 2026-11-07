import numpy as np
import pandas as pd

# The six numbers the model sees for every game (all are "home minus away").
FEATURES = [
    "win_pct_diff",
    "margin_diff",
    "rest_diff",
    "pts_for_diff",
    "pts_against_diff",
    "elo_diff",
]

# Elo settings
START = 1500      # every team's starting rating
K = 20            # how fast ratings move
HOME_ADV = 55     # home-field bonus used inside the win-probability formula

# Which team-game columns get a "last 5 games" average, and what to call the result
ROLLING_NAMES = {
    "win": "win_pct_last5",
    "margin": "margin_last5",
    "pts_for": "pts_for_last5",
    "pts_against": "pts_against_last5",
}


def to_team_games(games):
    """One row per team per game (so each team's history is in one timeline)."""
    home = games[["game_id", "gameday", "home_team", "home_score", "away_score"]].copy()
    home.columns = ["game_id", "gameday", "team", "pts_for", "pts_against"]
    home["is_home"] = 1

    away = games[["game_id", "gameday", "away_team", "away_score", "home_score"]].copy()
    away.columns = ["game_id", "gameday", "team", "pts_for", "pts_against"]
    away["is_home"] = 0

    team_games = (
        pd.concat([home, away])
        .sort_values(["team", "gameday"])
        .reset_index(drop=True)
    )
    team_games["win"] = (team_games["pts_for"] > team_games["pts_against"]).astype(int)
    team_games["margin"] = team_games["pts_for"] - team_games["pts_against"]
    return team_games


def add_rolling_features(games):
    """Add last-5-game averages for each team, plus home-minus-away differences.

    Every average is shifted by one game, so a game never sees its own result.
    """
    team_games = to_team_games(games)
    g = team_games.groupby("team")
    for col, new_name in ROLLING_NAMES.items():
        team_games[new_name] = g[col].transform(
            lambda s: s.shift(1).rolling(5, min_periods=1).mean()
        )

    feat_cols = list(ROLLING_NAMES.values())
    feats = team_games[["game_id", "is_home"] + feat_cols]

    home_f = feats[feats["is_home"] == 1].drop(columns="is_home")
    home_f = home_f.rename(columns={c: f"home_{c}" for c in feat_cols})
    away_f = feats[feats["is_home"] == 0].drop(columns="is_home")
    away_f = away_f.rename(columns={c: f"away_{c}" for c in feat_cols})

    games = games.merge(home_f, on="game_id").merge(away_f, on="game_id")
    for c in feat_cols:
        games[c.replace("_last5", "_diff")] = games[f"home_{c}"] - games[f"away_{c}"]
    games["rest_diff"] = games["home_rest"] - games["away_rest"]
    return games


def expected_home_win(home_elo, away_elo):
    """Win probability for the home team implied by the two ratings."""
    diff = (home_elo + HOME_ADV) - away_elo
    return 1 / (1 + 10 ** (-diff / 400))


def add_elo(games):
    """Add each team's rating *before* every game. Returns (games, final_ratings).

    `games` must be in date order.
    """
    elo = {}
    home_elos, away_elos = [], []
    current_season = None

    for row in games.itertuples():
        if row.season != current_season:
            for t in elo:
                elo[t] = elo[t] * (2 / 3) + START * (1 / 3)
            current_season = row.season

        h = elo.get(row.home_team, START)
        a = elo.get(row.away_team, START)
        home_elos.append(h)
        away_elos.append(a)

        if row.home_score > row.away_score:
            actual = 1.0
        elif row.home_score < row.away_score:
            actual = 0.0
        else:
            actual = 0.5

        expected = expected_home_win(h, a)
        margin = abs(row.home_score - row.away_score)
        change = K * np.log(margin + 1) * (actual - expected)

        elo[row.home_team] = h + change
        elo[row.away_team] = a - change

    games = games.copy()
    games["home_elo"] = home_elos
    games["away_elo"] = away_elos
    games["elo_diff"] = games["home_elo"] - games["away_elo"]
    return games, elo


def build_features(played_games):
    """Full feature table for games that have already been played."""
    games = add_rolling_features(played_games)
    games, ratings = add_elo(games)
    games["home_win"] = (games["home_score"] > games["away_score"]).astype(int)
    games = games.dropna(subset=FEATURES).reset_index(drop=True)
    return games, ratings


def current_team_form(played_games):
    """Each team's last-5-game averages as of *now* (used for upcoming games)."""
    team_games = to_team_games(played_games)
    last5 = team_games.groupby("team").tail(5)
    form = last5.groupby("team")[["win", "margin", "pts_for", "pts_against"]].mean()
    return form.rename(columns=ROLLING_NAMES)