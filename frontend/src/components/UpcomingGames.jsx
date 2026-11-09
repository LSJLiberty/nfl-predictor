// UpcomingGames.jsx
//
// Shows the model's predictions for the next games on the schedule.
// It receives the list of games as a prop and has no state of its own.

import ProbabilityBar from "./ProbabilityBar";

export default function UpcomingGames({ games }) {
  // Nothing to show (for example, during the offseason).
  if (games.length === 0) {
    return <p className="muted">No upcoming games on the schedule.</p>;
  }

  return (
    <ul className="games">
      {/* .map() turns each game in the list into a piece of the page.
          React needs a unique `key` on each item so it can keep track of them
          when the list changes. */}
      {games.map((game) => (
        <li key={`${game.gameday}-${game.away_team}-${game.home_team}`} className="game">
          <div className="game-header">
            <span>
              {game.away_team} at {game.home_team}
            </span>
            <span className="muted">{game.gameday}</span>
          </div>
          <ProbabilityBar
            awayLabel={game.away_team}
            awayProb={game.away_win_prob}
            homeLabel={game.home_team}
            homeProb={game.home_win_prob}
          />
        </li>
      ))}
    </ul>
  );
}