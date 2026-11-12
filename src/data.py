import nflreadpy as nfl
import pandas as pd

# Old abbreviations -> current ones, so a relocated team keeps one history.
TEAM_FIX = {"OAK": "LV", "SD": "LAC", "STL": "LA"}


def load_games(first_season=2015, last_season=2026):
    """Download every game from first_season through last_season (inclusive)."""
    games = nfl.load_schedules(seasons=range(first_season, last_season + 1)).to_pandas()
    games["gameday"] = pd.to_datetime(games["gameday"])
    games["home_team"] = games["home_team"].replace(TEAM_FIX)
    games["away_team"] = games["away_team"].replace(TEAM_FIX)
    games = games.sort_values(["gameday", "game_id"]).reset_index(drop=True)
    return games


def split_completed(games):
    """Split into (games already played, games not yet played)."""
    played = games["home_score"].notna() & games["away_score"].notna()
    return games[played].copy(), games[~played].copy()