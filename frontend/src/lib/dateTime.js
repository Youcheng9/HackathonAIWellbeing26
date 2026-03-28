import { CALENDAR_START_HOUR, CALENDAR_TOTAL_HOURS } from "./constants";

export function formatHour(value) {
  const safeValue = ((value % 24) + 24) % 24;
  let hour = Math.floor(safeValue);
  let minute = Math.round((safeValue - hour) * 60);
  if (minute === 60) {
    hour = (hour + 1) % 24;
    minute = 0;
  }
  const suffix = hour < 12 ? "AM" : "PM";
  const normalized = hour % 12 || 12;
  return `${normalized}:${String(minute).padStart(2, "0")} ${suffix}`;
}

export function timeToDecimal(rawValue) {
  if (!rawValue || !rawValue.includes(":")) return null;
  const [hoursText, minutesText] = rawValue.split(":");
  const hours = Number(hoursText);
  const minutes = Number(minutesText);
  if (Number.isNaN(hours) || Number.isNaN(minutes)) return null;
  return Number((hours + minutes / 60).toFixed(2));
}

export function dateToDay(rawValue) {
  if (!rawValue) return null;
  const parsed = new Date(`${rawValue}T00:00:00`);
  if (Number.isNaN(parsed.getTime())) return null;
  return ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"][parsed.getDay()] || null;
}

export function dayToDate(day, weekStart) {
  const index = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"].indexOf(day);
  if (index < 0) return "";
  return toDateInputValue(addDays(weekStart, index));
}

export function addDays(date, amount) {
  const next = new Date(date);
  next.setDate(next.getDate() + amount);
  return next;
}

export function getWeekStart(date) {
  const base = new Date(date);
  const day = base.getDay();
  const diff = day === 0 ? -6 : 1 - day;
  base.setHours(0, 0, 0, 0);
  base.setDate(base.getDate() + diff);
  return base;
}

export function toDateInputValue(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function isSameWeek(rawValue, weekStart) {
  if (!rawValue) return false;
  const date = new Date(`${rawValue}T00:00:00`);
  if (Number.isNaN(date.getTime())) return false;
  return toDateInputValue(getWeekStart(date)) === toDateInputValue(weekStart);
}

export function formatDate(rawValue) {
  if (!rawValue) return "No date";
  const [year, month, day] = rawValue.split("-");
  if (!year || !month || !day) return rawValue;
  return `${month}/${day}/${year}`;
}

export function formatShortDate(date) {
  return `${String(date.getMonth() + 1).padStart(2, "0")}/${String(date.getDate()).padStart(2, "0")}`;
}

export function formatWeekRange(weekStart) {
  const weekEnd = addDays(weekStart, 6);
  return `${formatDate(toDateInputValue(weekStart))} - ${formatDate(toDateInputValue(weekEnd))}`;
}

export function buildWeekOptions() {
  const currentWeek = getWeekStart(new Date());
  return Array.from({ length: 25 }, (_, index) => {
    const offset = index - 12;
    const weekStart = addDays(currentWeek, offset * 7);
    const value = toDateInputValue(weekStart);
    const prefix = offset === 0 ? "This Week · " : "";
    return {
      value,
      label: `${prefix}${formatWeekRange(weekStart)}`,
    };
  });
}

export function formatDeadline(task) {
  const dateLabel = task.deadline_date ? formatDate(task.deadline_date) : task.deadline_day;
  const timeLabel = task.deadline_time || "";
  return `${dateLabel}${timeLabel ? ` ${timeLabel}` : ""}`;
}

export function shiftWeek(direction, setSelectedWeekStart, setCommitmentForm, setTaskForm, createInitialCommitment, createInitialTask) {
  setSelectedWeekStart((current) => {
    const next = addDays(current, direction * 7);
    setCommitmentForm(createInitialCommitment(next));
    setTaskForm(createInitialTask(next));
    return next;
  });
}

export function jumpToThisWeek(setSelectedWeekStart, setCommitmentForm, setTaskForm, createInitialCommitment, createInitialTask) {
  const next = getWeekStart(new Date());
  setSelectedWeekStart(next);
  setCommitmentForm(createInitialCommitment(next));
  setTaskForm(createInitialTask(next));
}

export function selectWeek(rawValue, setSelectedWeekStart, setCommitmentForm, setTaskForm, createInitialCommitment, createInitialTask) {
  const next = getWeekStart(new Date(`${rawValue}T00:00:00`));
  setSelectedWeekStart(next);
  setCommitmentForm(createInitialCommitment(next));
  setTaskForm(createInitialTask(next));
}

export function decimalToTime(value) {
  const normalized = ((value % 24) + 24) % 24;
  let hour = Math.floor(normalized);
  let minute = Math.round((normalized - hour) * 60);
  if (minute === 60) {
    hour = (hour + 1) % 24;
    minute = 0;
  }
  return `${String(hour).padStart(2, "0")}:${String(minute).padStart(2, "0")}`;
}

export function hourToTopPercent(hour) {
  return ((hour - CALENDAR_START_HOUR) / CALENDAR_TOTAL_HOURS) * 100;
}

export function capitalize(value) {
  return value.charAt(0).toUpperCase() + value.slice(1);
}
