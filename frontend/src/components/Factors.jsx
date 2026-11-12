// Factors.jsx
//
// "Why did the model pick that team?" Shows each reason as a bar that pushes the odds
// toward the away team (left, orange) or the home team (right, blue), measured in
// percentage points away from a 50/50 coin flip.

export default function Factors({ factors, awayLabel, homeLabel }) {
  // Scale every bar against the biggest reason (but never less than 10 points, so a
  // matchup where everything is tiny doesn't blow small bars up to full width).
  const biggest = Math.max(10, ...factors.map((f) => Math.abs(f.points)));

  return (
    <div className="factors">
      <h3>What drove this pick</h3>
      <p className="muted small">
        Starting from a 50/50 coin flip, how far each reason moves the odds toward{" "}
        {awayLabel} (left) or {homeLabel} (right).
      </p>
      <ul>
        {factors.map((factor) => {
          const towardHome = factor.points > 0;
          // Each bar grows outward from the center line, up to half the track width.
          const halfWidth = (Math.abs(factor.points) / biggest) * 50;
          const sign = towardHome ? "+" : "";
          return (
            <li key={factor.name} className="factor">
              <div className="factor-header">
                <span>{factor.name}</span>
                <strong>
                  {sign}
                  {factor.points.toFixed(1)} pts
                </strong>
              </div>
              <div className="factor-track" aria-hidden="true">
                <div className="factor-center" />
                <div
                  className={towardHome ? "factor-fill home" : "factor-fill away"}
                  style={
                    towardHome
                      ? { left: "50%", width: `${halfWidth}%` }
                      : { right: "50%", width: `${halfWidth}%` }
                  }
                />
              </div>
              <p className="muted small">{factor.detail}</p>
            </li>
          );
        })}
      </ul>
    </div>
  );
}