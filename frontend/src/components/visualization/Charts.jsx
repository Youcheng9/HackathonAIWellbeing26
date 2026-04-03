import { DAYS } from "../../lib/constants";

export function RiskBreakdown({ assessment, getTone, toneClass }) {
  const entries = [
    ["Daily Workload", assessment.metrics.overloaded_days?.length ? 85 : 24],
    ["Deadline Clustering", assessment.reasons.some((reason) => reason.includes("deadlines")) ? 90 : 20],
    ["Break Frequency", assessment.reasons.some((reason) => reason.includes("break")) ? 80 : 18],
    ["Late Night Work", assessment.metrics.late_night_blocks ? 55 : 12],
    ["Recovery Time", assessment.reasons.some((reason) => reason.includes("recovery")) ? 72 : 16],
  ];

  return entries.map(([label, score]) => (
    <div className="risk-row" key={label}>
      <div className="flex-between mb-1">
        <span>{label}</span>
        <span className={`score-mini ${toneClass(getTone(score))}`}>{score}/100</span>
      </div>
      <div className="risk-bar-track small">
        <div className={`risk-bar-fill ${toneClass(getTone(score))}`} style={{ width: `${score}%` }} />
      </div>
    </div>
  ));
}

export function WorkloadChart({ data, getTone, toneClass }) {
  return (
    <div>
      {DAYS.map((day, index) => {
        const hours = data[index] ?? 0;
        const tone = getTone(hours > 9 ? 90 : hours > 6 ? 55 : 20);
        return (
          <div className="workload-bar-row" key={day}>
            <span className="wl-day">{day}</span>
            <div className="wl-track">
              <div className={`wl-fill ${toneClass(tone)}`} style={{ width: `${Math.min((hours / 14) * 100, 100)}%` }} />
            </div>
            <span className="wl-hours">{hours}h</span>
          </div>
        );
      })}
    </div>
  );
}
