import { addDays, getWeekStart, toDateInputValue } from "./dateTime";

export function createSamplePayload() {
  const weekStart = getWeekStart(new Date());
  const monday = toDateInputValue(weekStart);
  const tuesday = toDateInputValue(addDays(weekStart, 1));
  const wednesday = toDateInputValue(addDays(weekStart, 2));
  const thursday = toDateInputValue(addDays(weekStart, 3));
  const friday = toDateInputValue(addDays(weekStart, 4));
  const saturday = toDateInputValue(addDays(weekStart, 5));

  return {
    commitments: [
      { title: "CS 101", day: "Mon", commitment_date: monday, start: 9, end: 10.5, category: "class" },
      { title: "Calculus", day: "Thu", commitment_date: thursday, start: 11, end: 12.5, category: "class" },
      { title: "Work Shift", day: "Tue", commitment_date: tuesday, start: 14, end: 20, category: "work" },
      { title: "Work Shift", day: "Thu", commitment_date: thursday, start: 14, end: 20, category: "work" },
    ],
    tasks: [
      { title: "Essay Draft", duration: 3, deadline_day: "Sat", deadline_date: saturday, deadline_time: "18:00" },
      { title: "CS Project", duration: 5, deadline_day: "Wed", deadline_date: wednesday, deadline_time: "23:59" },
      { title: "HW Set 4", duration: 2, deadline_day: "Thu", deadline_date: thursday, deadline_time: "17:00" },
      { title: "Reflection", duration: 1.5, deadline_day: "Fri", deadline_date: friday, deadline_time: "20:00" },
    ],
    sleep_window: { start: 23, end: 7 },
    preferences: {
      max_daily_hours: 8,
      preferred_study_start: 7,
      preferred_study_end: 22,
      slot_step: 0.5,
      buffer_hours: 1,
      weekly_hours_threshold: 50,
      late_night_cutoff: 23,
      max_consecutive_blocks: 3,
      min_breaks_per_day: 1,
      deadline_cluster_days: 2,
    },
  };
}

export function createInitialCommitment(weekStart) {
  return {
    title: "",
    commitment_date: toDateInputValue(weekStart),
    start: "09:00",
    end: "10:30",
    category: "class",
  };
}

export function createInitialTask(weekStart) {
  return {
    title: "",
    duration: 1,
    deadline_day: "Mon",
    deadline_date: toDateInputValue(weekStart),
    deadline_time: "23:59",
  };
}
