// Rankings.jsx
//
// Power rankings: every team ordered by its current Elo rating. The API already sends
// the teams strongest-first, so we just number them.

import { teamName } from "../teamNames";

export default function Rankings({ teams }) {
  const ratings = teams.map((t) => t.elo);
  const lowest = Math.min(...ratings);
  const highest = Math.max(...ratings);
  const spread = highest - lowest || 1; // avoid dividing by zero if every rating is equal

  return (
    <ol className="rankings">
      {teams.map((t, index) => {
        // Bars run from 8% (weakest team) to 100% (strongest) so every team shows a bar.
        const width = 8 + 92 * ((t.elo - lowest) / spread);
        return (
          <li key={t.team}>
            <span className="rank">{index + 1}</span>
            <span className="rank-name">{teamName(t.team)}</span>
            <span className="rank-bar" aria-hidden="true">
              <span style={{ width: `${width}%` }} />
            </span>
            <span className="rank-elo">{Math.round(t.elo)}</span>
          </li>
        );
      })}
    </ol>
  );
}