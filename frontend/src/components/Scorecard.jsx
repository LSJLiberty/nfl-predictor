// Scorecard.jsx
//
// "How accurate is the model?" -- the part of the page that keeps the project honest.
// It shows how the model has really done, not just how it did on data it trained on.

import { teamName } from "../teamNames";

// 0.6534 -> "65.3%"
const percent = (value, digits = 1) => `${(value * 100).toFixed(digits)}%`;

export default function Scorecard({ scorecard }) {
  // If the server couldn't provide a scorecard, say so instead of showing nothing.
  if (!scorecard) {
    return <p className="muted">The accuracy report isn&rsquo;t available right now.</p>;
  }

  const { backtest, live } = scorecard;
  const back = backtest.summary;

  return (
    <div className="scorecard">
      {live && (
        <div className="stat-block">
          <h3>{live.season} season so far</h3>
          <p className="big">
            {live.summary.correct} of {live.summary.games} correct (
            {percent(live.summary.accuracy)})
          </p>
          <p className="muted small">
            Picking the home team every time would be right{" "}
            {percent(live.summary.home_pick_baseline)} of the time. These predictions come
            from a model trained only on earlier seasons, so it had never seen these games.
          </p>
          <div className="weeks">
            {live.by_week.map((w) => (
              <div key={w.week} className="week" title={`Week ${w.week}: ${w.correct} of ${w.games}`}>
                <div className="week-bar">
                  <div style={{ height: `${(w.correct / w.games) * 100}%` }} />
                </div>
                <span>{w.week}</span>
              </div>
            ))}
          </div>
          <p className="muted small">Correct picks by week (taller is better).</p>
        </div>
      )}

      <div className="stat-block">
        <h3>Backtest on {backtest.seasons}</h3>
        <p className="big">
          {percent(back.accuracy)} accuracy on {back.games} games
        </p>
        <p className="muted small">
          95% confidence interval: {percent(back.accuracy_low)} to {percent(back.accuracy_high)}.
          The home-team baseline is {percent(back.home_pick_baseline)}. Log loss:{" "}
          {back.log_loss.toFixed(3)} (lower is better; 0.693 is a coin flip).
        </p>
      </div>

      <div className="stat-block">
        <h3>Are the percentages trustworthy?</h3>
        <p className="muted small">
          When the model gives the home team a certain chance, does the home team win about
          that often? Close numbers in the last two columns mean yes.
        </p>
        <table className="calibration">
          <thead>
            <tr>
              <th>Model said</th>
              <th>Games</th>
              <th>Model&rsquo;s average</th>
              <th>Home team won</th>
            </tr>
          </thead>
          <tbody>
            {backtest.calibration.map((bin) => (
              <tr key={bin.low}>
                <td>
                  {Math.round(bin.low * 100)}&ndash;{Math.round(bin.high * 100)}%
                </td>
                <td>{bin.games}</td>
                <td>{bin.avg_predicted === null ? "–" : percent(bin.avg_predicted, 0)}</td>
                <td>{bin.home_win_rate === null ? "–" : percent(bin.home_win_rate, 0)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {live && (
        <div className="stat-block">
          <h3>Most recent results</h3>
          <ul className="recent">
            {live.recent.map((g) => (
              <li key={`${g.gameday}-${g.away_team}-${g.home_team}`}>
                <span className={g.correct ? "mark right" : "mark wrong"}>
                  {g.correct ? "✓" : "✗"}
                </span>
                <span className="recent-game">
                  {teamName(g.away_team)} {g.away_score}, {teamName(g.home_team)} {g.home_score}
                </span>
                <span className="muted small">
                  Picked {g.pick} ({percent(g.pick === g.home_team ? g.home_win_prob : 1 - g.home_win_prob, 0)})
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}