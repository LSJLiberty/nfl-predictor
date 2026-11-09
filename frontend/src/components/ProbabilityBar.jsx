// ProbabilityBar.jsx
//
// A small reusable "component": a function that returns a piece of the page.
// The curly braces in the parameter list receive "props" -- the inputs the parent
// passes in, like <ProbabilityBar awayLabel="BUF" ... />. A component never changes
// its own props; it just turns them into what you see.

export default function ProbabilityBar({ awayLabel, awayProb, homeLabel, homeProb }) {
  // The API sends probabilities between 0 and 1. Convert to percentages.
  const awayPct = awayProb * 100;
  const homePct = homeProb * 100;
  const awayFavored = awayPct > homePct;

  return (
    <div className="prob">
      {/* The labels above the bar. The favored team gets the "favored" CSS class,
          which the stylesheet makes bold. `.toFixed(1)` keeps one decimal place. */}
      <div className="prob-labels">
        <span className={awayFavored ? "favored" : ""}>
          {awayLabel} <strong>{awayPct.toFixed(1)}%</strong>
        </span>
        <span className={awayFavored ? "" : "favored"}>
          <strong>{homePct.toFixed(1)}%</strong> {homeLabel}
        </span>
      </div>

      {/* The bar itself: two colored boxes side by side. Setting each box's width to
          its percentage makes them fill the bar in the right proportions.
          role="img" + aria-label lets screen readers announce the bar's meaning. */}
      <div
        className="prob-bar"
        role="img"
        aria-label={`${awayLabel} ${awayPct.toFixed(1)} percent, ${homeLabel} ${homePct.toFixed(1)} percent`}
      >
        <div className="prob-away" style={{ width: `${awayPct}%` }} />
        <div className="prob-home" style={{ width: `${homePct}%` }} />
      </div>
    </div>
  );
}