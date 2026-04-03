import { CALENDAR_START_HOUR, CALENDAR_TOTAL_HOURS, DAYS, HOURS } from "../../lib/constants";
import { addDays, formatHour, formatShortDate, hourToTopPercent } from "../../lib/dateTime";

export function TimelineCalendar({ blocks, weekStart }) {
  return (
    <div className="timeline-calendar">
      <div className="timeline-grid">
        <div className="timeline-corner" />
        {DAYS.map((day, index) => (
          <div className="timeline-day-header" key={day}>
            <strong>{day}</strong>
            <span>{formatShortDate(addDays(weekStart, index))}</span>
          </div>
        ))}
        <div className="timeline-time-column">
          {HOURS.map((hour) => (
            <div className="timeline-time-label" key={hour} style={{ top: `${hourToTopPercent(hour)}%` }}>
              {formatHour(hour)}
            </div>
          ))}
        </div>
        {DAYS.map((day) => (
          <div className="timeline-day-column" key={day}>
            {HOURS.map((hour) => (
              <div key={`${day}-${hour}`} className="timeline-hour-line" style={{ top: `${hourToTopPercent(hour)}%` }} />
            ))}
            {(blocks[day] || []).map((block, index) => (
              <TimelineBlock key={`${day}-${block.label}-${index}`} block={block} />
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}

function TimelineBlock({ block }) {
  if (typeof block.start !== "number" || typeof block.end !== "number") {
    return (
      <div className={`timeline-task-pill timeline-${block.type}`}>
        <strong>{block.label}</strong>
        {block.time ? <span>{block.time}</span> : null}
      </div>
    );
  }

  const clippedStart = Math.max(block.start, CALENDAR_START_HOUR);
  const clippedEnd = Math.min(block.end, CALENDAR_START_HOUR + CALENDAR_TOTAL_HOURS);
  if (clippedEnd <= clippedStart) return null;

  return (
    <div
      className={`timeline-block timeline-${block.type}${block.overload ? " timeline-overload" : ""}`}
      style={{
        top: `${hourToTopPercent(clippedStart)}%`,
        height: `${Math.max(((clippedEnd - clippedStart) / CALENDAR_TOTAL_HOURS) * 100, 2.2)}%`,
      }}
    >
      <strong>{block.label}</strong>
      <span>{formatHour(block.start)}-{formatHour(block.end)}</span>
    </div>
  );
}
