NFL Game Predictor
A machine learning project that predicts the winner of NFL games from historical results. The goal is a full pipeline: raw game data becomes features, features train a model, and the model is served through an API to a web interface.

Status: in progress. Data exploration, feature engineering, and model training are done. The prediction API and web interface are next.

Results
The model is trained on the 2015-2022 seasons and evaluated on the 2023-2025 seasons, which it never sees during training.

Model	Accuracy	Log loss
Always pick the home team	0.549	n/a
Logistic regression, recent-form features	0.630	0.639
Logistic regression, + Elo ratings	0.653	0.629
By season, the final model beat the home-team pick rate every year:

Season	Home-team pick rate	Model accuracy
2023	0.565	0.632
2024	0.547	0.677
2025	0.533	0.649
Feature sets were compared with walk-forward validation (train on all earlier seasons, check on the next one, for 2019-2022) so the 2023-2025 test seasons were held out for the final result:

Feature set	Accuracy	Log loss
Recent form (win rate, margin, rest)	0.621	0.6539
+ offense/defense averages	0.618	0.6523
+ Elo rating	0.638	0.6395
Elo rating only	0.637	0.6399
All features	0.645	0.6385
Takeaways: Elo was the only addition that clearly helped. A single Elo number performs almost as well as all features together, because it accounts for opponent strength and remembers more than five games. Log loss measures the quality of the predicted probabilities, not just the picks, and lower is better.

Tech Stack
Python for data work and modeling
pandas and NumPy for data wrangling and math
nflreadpy for downloading NFL schedule and results data
scikit-learn for model training
joblib for saving trained models
FastAPI for the prediction API (planned)
React for the web interface (planned)
Jupyter notebooks for exploration and experiments
How It Works
Load data. Every NFL game from the 2015-2025 seasons is downloaded with nflreadpy.
Clean team names. Teams that relocated (Oakland to Las Vegas, San Diego to Los Angeles, St. Louis to Los Angeles) are mapped to one identity so their history is continuous.
Create the target. home_win is 1 if the home team scored more than the away team, otherwise 0.
Reshape. The data is converted from one row per game to one row per team per game so each team's history can be followed in date order.
Rolling form features. For each team in each game, averages over its previous five games: win rate, scoring margin, points scored, and points allowed.
Elo ratings. Each team has a strength rating that updates after every game. Wins over strong opponents and larger margins move it more, and ratings are pulled partway back toward average each offseason.
Prevent data leakage. Every feature uses only information known before kickoff. Rolling values are shifted by one game, and each Elo rating is recorded before it is updated.
Difference features. Home minus away for each feature, so the model sees how the two teams compare.
Train and evaluate. A logistic regression (with feature scaling) is trained on earlier seasons and scored on later ones. Splits are by time, never random, so the model is never trained on games that happen after the ones it is tested on.
Baseline
Always picking the home team wins about 55% of games in the 2015-2025 data. A model is only useful if it beats this on held-out seasons.

Project Structure
nfl-predictor/
├── data/                          # local data files (if saved)
├── models/                        # saved trained models
├── notebooks/
│   ├── 01_explore.ipynb           # load and explore the schedule data
│   ├── 02_features.ipynb          # rolling-form features and train/test split
│   ├── 03_model.ipynb             # baseline logistic regression model
│   └── 04_better_features.ipynb   # team-name fix, Elo ratings, feature comparison
├── requirements.txt
└── README.md
Setup (Windows / PowerShell)
powershell
git clone https://github.com/LSJLiberty/nfl-predictor.git
cd nfl-predictor
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
If PowerShell blocks the activation script, allow local scripts for your user and try again:

powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
Then open the notebooks in VS Code and select the .venv kernel. Run the cells in each notebook from top to bottom, and run the notebooks in numerical order.

Roadmap
 Week 1: Load and explore the data
 Week 2: Rolling-form features and a time-based train/test split
 Week 3: Baseline logistic regression model
 Week 4: Elo ratings, relocated-team fix, and validation-based feature comparison
 Move the feature and Elo code into a reusable Python module
 Load the current season's completed games so ratings stay up to date
 Build a FastAPI endpoint that returns win probabilities for an upcoming game
 Build the React front end
Limitations
The model only sees game results. It knows nothing about injuries, quarterback changes, weather, or other information that affects real games, which limits how accurate it can get.
Accuracy is measured on about 855 test games, so small differences between models (a point or two) are within normal luck.
Playoff games are included in training and testing.
Data currently ends with the 2025 season.
Data
Game data comes from nflverse through the nflreadpy package.

