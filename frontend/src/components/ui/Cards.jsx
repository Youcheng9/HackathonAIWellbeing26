export function StepCard({ number, title, text }) {
  return (
    <div className="step-card">
      <div className="step-number">{number}</div>
      <div>
        <div className="step-title">{title}</div>
        <div className="step-copy">{text}</div>
      </div>
    </div>
  );
}

export function StatCard({ title, value, tone, toneClass }) {
  return (
    <article className="stat-card">
      <div className={`stat-value ${toneClass(tone)}`}>{value}</div>
      <div className="stat-label">{title}</div>
    </article>
  );
}

export function ScoreRing({ score, label, tone, toneClass }) {
  const radius = 42;
  const circumference = 2 * Math.PI * radius;
  const fill = ((score || 0) / 100) * circumference;
  return (
    <div className="score-ring-wrap">
      <svg width="108" height="108" viewBox="0 0 108 108">
        <circle cx="54" cy="54" r={radius} className="ring-track" />
        <circle
          cx="54"
          cy="54"
          r={radius}
          className={`ring-fill ${toneClass(tone)}`}
          strokeDasharray={`${fill} ${circumference}`}
          transform="rotate(-90 54 54)"
        />
        <text x="54" y="52" textAnchor="middle" className="ring-score">{score || "--"}</text>
        <text x="54" y="69" textAnchor="middle" className="ring-total">/100</text>
      </svg>
      <span>{label}</span>
    </div>
  );
}

export function InsightCard({ tone, text }) {
  return (
    <div className={`insight insight-${tone}`}>
      <span className="insight-icon">{tone === "danger" ? "!" : tone === "warn" ? "~" : "+"}</span>
      <div className="insight-text">{text}</div>
    </div>
  );
}
