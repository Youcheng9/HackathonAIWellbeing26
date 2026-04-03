import { useEffect, useMemo, useState } from "react";

import { DateField, Field, NumberField, TimeField, TimePreferenceField } from "./components/form/FormFields";
import { ScoreRing, InsightCard, StatCard, StepCard } from "./components/ui/Cards";
import { RiskBreakdown, WorkloadChart } from "./components/visualization/Charts";
import { TimelineCalendar } from "./components/visualization/TimelineCalendar";
import {
  addDays,
  buildWeekOptions,
  capitalize,
  dateToDay,
  dayToDate,
  formatDate,
  formatDeadline,
  formatHour,
  formatWeekRange,
  getWeekStart,
  isSameWeek,
  jumpToThisWeek,
  selectWeek,
  timeToDecimal,
  toDateInputValue,
} from "./lib/dateTime";
import { analyzeScheduleRequest } from "./lib/api";
import { createInitialCommitment, createInitialTask, createSamplePayload } from "./lib/sampleData";
import { DAYS } from "./lib/constants";
import { buildApiPayload, buildPreviewCalendar, filterBlocks, toDailyBlocks, toDayLoads, validateScheduleInputs } from "./lib/schedule";

function App() {
  const samplePayload = useMemo(() => createSamplePayload(), []);
  const [selectedWeekStart, setSelectedWeekStart] = useState(() => getWeekStart(new Date()));
  const [theme, setTheme] = useState(() => localStorage.getItem("balanceai-theme") || "dark");
  const [tab, setTab] = useState("dashboard");
  const [commitments, setCommitments] = useState(samplePayload.commitments);
  const [tasks, setTasks] = useState(samplePayload.tasks);
  const [preferences, setPreferences] = useState(samplePayload.preferences);
  const [sleepWindow, setSleepWindow] = useState(samplePayload.sleep_window);
  const [commitmentForm, setCommitmentForm] = useState(() => createInitialCommitment(getWeekStart(new Date())));
  const [taskForm, setTaskForm] = useState(() => createInitialTask(getWeekStart(new Date())));
  const [analysis, setAnalysis] = useState(null);
  const [activeFilter, setActiveFilter] = useState("all");
  const [loading, setLoading] = useState(false);
  const [commitmentError, setCommitmentError] = useState("");
  const [taskError, setTaskError] = useState("");
  const [analysisError, setAnalysisError] = useState("");

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("balanceai-theme", theme);
  }, [theme]);

  const activeWeekCommitments = useMemo(
    () => commitments.filter((item) => isSameWeek(item.commitment_date, selectedWeekStart)),
    [commitments, selectedWeekStart]
  );

  const activeWeekTasks = useMemo(
    () => tasks.filter((item) => isSameWeek(item.deadline_date, selectedWeekStart)),
    [tasks, selectedWeekStart]
  );

  const payload = useMemo(
    () =>
      buildApiPayload({
        commitments: activeWeekCommitments,
        tasks: activeWeekTasks,
        sleepWindow,
        preferences,
      }),
    [activeWeekCommitments, activeWeekTasks, sleepWindow, preferences]
  );

  async function analyzeSchedule(nextTab = "insights") {
    const validationError = validateScheduleInputs({
      commitments: activeWeekCommitments,
      tasks: activeWeekTasks,
    });
    if (validationError) {
      setAnalysisError(validationError);
      return;
    }

    setLoading(true);
    setAnalysisError("");

    try {
      const parsedBody = await analyzeScheduleRequest(payload);
      setAnalysis(parsedBody);
      setTab(nextTab);
    } catch (fetchError) {
      if (fetchError instanceof TypeError) {
        setAnalysisError("Could not reach the backend. Start the API on http://127.0.0.1:8000 and try again.");
      } else {
        setAnalysisError(fetchError.message || "Unable to analyze schedule.");
      }
    } finally {
      setLoading(false);
    }
  }

  function addCommitment() {
    if (!commitmentForm.title.trim()) {
      setCommitmentError("Add a title before saving a class or work block.");
      return;
    }

    const start = timeToDecimal(commitmentForm.start);
    const end = timeToDecimal(commitmentForm.end);
    const commitmentDay = dateToDay(commitmentForm.commitment_date);

    if (start === null || end === null || !commitmentDay) {
      setCommitmentError("Enter valid start and end times.");
      return;
    }

    if (end <= start) {
      setCommitmentError("Class or work end time must be later than start time.");
      return;
    }

    setCommitmentError("");
    setCommitments((current) => [
      ...current,
      {
        title: commitmentForm.title.trim(),
        day: commitmentDay,
        commitment_date: commitmentForm.commitment_date,
        start,
        end,
        category: commitmentForm.category,
      },
    ]);
    setCommitmentForm(createInitialCommitment(selectedWeekStart));
  }

  function addTask() {
    if (!taskForm.title.trim()) {
      setTaskError("Add a task title before saving.");
      return;
    }
    if (taskForm.duration <= 0) {
      setTaskError("Task duration must be greater than zero.");
      return;
    }
    if (!taskForm.deadline_date) {
      setTaskError("Choose a deadline date for the task.");
      return;
    }
    if (!taskForm.deadline_time) {
      setTaskError("Choose a deadline time for the task.");
      return;
    }

    const deadlineDay = dateToDay(taskForm.deadline_date);
    if (!deadlineDay) {
      setTaskError("Choose a valid deadline date.");
      return;
    }

    setTaskError("");
    setTasks((current) => [
      ...current,
      {
        ...taskForm,
        title: taskForm.title.trim(),
        deadline_day: deadlineDay,
      },
    ]);
    setTaskForm(createInitialTask(selectedWeekStart));
  }

  function resetSample() {
    setCommitments(samplePayload.commitments);
    setTasks(samplePayload.tasks);
    setPreferences(samplePayload.preferences);
    setSleepWindow(samplePayload.sleep_window);
    setSelectedWeekStart(getWeekStart(new Date()));
    setCommitmentForm(createInitialCommitment(getWeekStart(new Date())));
    setTaskForm(createInitialTask(getWeekStart(new Date())));
    setAnalysis(null);
    setCommitmentError("");
    setTaskError("");
    setAnalysisError("");
  }

  const beforeAssessment = analysis?.before_assessment;
  const afterAssessment = analysis?.after_assessment;
  const beforePlan = analysis?.before_plan;
  const afterPlan = analysis?.after_plan;

  const riskScore = beforeAssessment?.score ?? 0;
  const optimizedScore = afterAssessment?.score ?? 0;
  const savedPoints = analysis ? Math.max(riskScore - optimizedScore, 0) : 0;

  const beforeDaily = toDailyBlocks(beforePlan?.scheduled_tasks || [], activeWeekCommitments);
  const afterDaily = toDailyBlocks(afterPlan?.scheduled_tasks || [], activeWeekCommitments);
  const beforeLoads = toDayLoads(beforeAssessment?.metrics?.daily_hours);
  const afterLoads = toDayLoads(afterAssessment?.metrics?.daily_hours);
  const schedulePreview = buildPreviewCalendar(activeWeekCommitments, activeWeekTasks);

  const filteredBefore = filterBlocks(beforeDaily, activeFilter);
  const filteredAfter = filterBlocks(afterDaily, activeFilter);

  return (
    <>
      <nav className="nav">
        <div className="logo">
          <div className="logo-mark">
            <div className="logo-dot" />
          </div>
          <div>
            <div className="logo-title">BalanceAI</div>
            <div className="logo-subtitle">Burnout-aware scheduler</div>
          </div>
        </div>
        <div className="nav-tabs">
          {["dashboard", "schedule", "insights", "compare"].map((name) => (
            <button
              key={name}
              className={`nav-tab${tab === name ? " active" : ""}`}
              onClick={() => setTab(name)}
              type="button"
            >
              {capitalize(name)}
            </button>
          ))}
        </div>
        <button
          className="theme-switch"
          type="button"
          onClick={() => setTheme((current) => (current === "dark" ? "light" : "dark"))}
        >
          {theme === "dark" ? "Light mode" : "Dark mode"}
        </button>
      </nav>

      <main className="main">
        {tab === "dashboard" && (
          <div className="page-stack">
            <section className="hero">
              <div className="hero-badge">
                <div className="badge-dot" />
                AI-Powered Schedule Health
              </div>
              <h1>
                Your week,
                <br />
                <span>balanced.</span>
              </h1>
              <p>
                Add class time, work shifts, and deadlines. BalanceAI finds burnout risk, gives alerts,
                and reshapes the week around your personal limits.
              </p>
              <button className="hero-cta" type="button" onClick={() => setTab("schedule")}>
                Build My Schedule
              </button>
            </section>

            <section className="stats-row">
              <StatCard title="Current Burnout Score" value={analysis ? riskScore : "--"} tone={getTone(riskScore)} toneClass={toneClass} />
              <StatCard title="After Optimization" value={analysis ? optimizedScore : "--"} tone={getTone(optimizedScore)} toneClass={toneClass} />
              <StatCard title="Risk Points Saved" value={analysis ? `-${savedPoints}` : "--"} tone="neutral" toneClass={toneClass} />
            </section>

            <section className="grid-2">
              <article className="card">
                <div className="section-title">How it works</div>
                <div className="step-list">
                  <StepCard number="1" title="Add classes and work" text="Enter fixed blocks with real times like 10:30 or 14:45." />
                  <StepCard number="2" title="Add assignment tasks" text="Enter due day and estimated hours. We place them around your week." />
                  <StepCard number="3" title="Analyze and compare" text="You get burnout alerts, workload insight, and a healthier before versus after calendar." />
                </div>
              </article>

              <article className="card">
                <div className="section-title">What you get</div>
                <div className="ring-row">
                  <ScoreRing score={analysis ? riskScore : 72} label="Risk score" tone={analysis ? getTone(riskScore) : "danger"} toneClass={toneClass} />
                  <ScoreRing score={analysis ? optimizedScore : 34} label="Optimized" tone={analysis ? getTone(optimizedScore) : "safe"} toneClass={toneClass} />
                </div>
                <hr className="divider" />
                <button className="btn btn-primary btn-full" type="button" onClick={() => setTab("schedule")}>
                  Go to Schedule Setup
                </button>
              </article>
            </section>
          </div>
        )}

        {tab === "schedule" && (
          <div className="page-stack">
            <section className="page-header">
              <h2>Build Your Schedule</h2>
              <p>
                Add your fixed week first, then your deadlines, then your personal burnout settings.
                The timeline updates live so you can see the week take shape.
              </p>
            </section>

            <section className="card week-toolbar">
              <div>
                <div className="section-title">Calendar Week</div>
                <div className="week-range">{formatWeekRange(selectedWeekStart)}</div>
                <p className="helper-copy">Move between weeks to plan ahead. BalanceAI analyzes the week currently in view.</p>
              </div>
              <div className="week-actions">
                <Field label="Choose week">
                  <select
                    className="week-select"
                    value={toDateInputValue(selectedWeekStart)}
                    onChange={(event) =>
                      selectWeek(
                        event.target.value,
                        setSelectedWeekStart,
                        setCommitmentForm,
                        setTaskForm,
                        createInitialCommitment,
                        createInitialTask
                      )
                    }
                  >
                    {buildWeekOptions().map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </Field>
                <button
                  className="btn btn-ghost"
                  type="button"
                  onClick={() =>
                    jumpToThisWeek(
                      setSelectedWeekStart,
                      setCommitmentForm,
                      setTaskForm,
                      createInitialCommitment,
                      createInitialTask
                    )
                  }
                >
                  This Week
                </button>
              </div>
            </section>

            <section className="workspace">
              <div className="workspace-left page-stack">
                <article className="card">
                  <div className="section-title">1. Classes and Work</div>
                  <p className="helper-copy">Use actual time entry. The fields support times like 10:30, 10:35, or 21:15.</p>
                  <div className="tag-row">
                    {activeWeekCommitments.map((item, index) => (
                      <div className={`tag ${item.category === "work" ? "tag-work" : "tag-class"}`} key={`${item.title}-${index}`}>
                        <span>{item.title} · {formatDate(item.commitment_date)} · {formatHour(item.start)}-{formatHour(item.end)}</span>
                        <button className="tag-remove" type="button" onClick={() => setCommitments((current) => current.filter((entry) => entry !== item))}>
                          ×
                        </button>
                      </div>
                    ))}
                  </div>
                  <div className="form-grid six-up">
                    <Field label="Type">
                      <select value={commitmentForm.category} onChange={(event) => setCommitmentForm((current) => ({ ...current, category: event.target.value }))}>
                        <option value="class">Class</option>
                        <option value="work">Work</option>
                      </select>
                    </Field>
                    <Field label="Title">
                      <input value={commitmentForm.title} placeholder="CS 101 lecture" onChange={(event) => setCommitmentForm((current) => ({ ...current, title: event.target.value }))} />
                    </Field>
                    <DateField label="Date" value={commitmentForm.commitment_date} onChange={(value) => setCommitmentForm((current) => ({ ...current, commitment_date: value }))} />
                    <TimeField label="Start" value={commitmentForm.start} onChange={(value) => setCommitmentForm((current) => ({ ...current, start: value }))} />
                    <TimeField label="End" value={commitmentForm.end} onChange={(value) => setCommitmentForm((current) => ({ ...current, end: value }))} />
                    <Field label="Weekday">
                      <select
                        value={dateToDay(commitmentForm.commitment_date) || "Mon"}
                        onChange={(event) =>
                          setCommitmentForm((current) => ({
                            ...current,
                            commitment_date: dayToDate(event.target.value, selectedWeekStart),
                          }))
                        }
                      >
                        {DAYS.map((day) => (
                          <option key={day} value={day}>
                            {day}
                          </option>
                        ))}
                      </select>
                    </Field>
                  </div>
                  <button className="btn btn-primary" type="button" onClick={addCommitment}>
                    Add Class or Work Block
                  </button>
                  {commitmentError ? <p className="error-banner">{commitmentError}</p> : null}
                </article>

                <article className="card">
                  <div className="section-title">2. Tasks and Deadlines</div>
                  <p className="helper-copy">Tasks stay movable for the optimizer, but you can now enter a real due date and due time in addition to estimated hours.</p>
                  <div className="tag-row">
                    {activeWeekTasks.map((item, index) => (
                      <div className="tag tag-task" key={`${item.title}-${index}`}>
                        <span>{item.title} · due {formatDeadline(item)} · {item.duration}h</span>
                        <button className="tag-remove" type="button" onClick={() => setTasks((current) => current.filter((entry) => entry !== item))}>
                          ×
                        </button>
                      </div>
                    ))}
                  </div>
                  <div className="form-grid five-up">
                    <Field label="Task name">
                      <input value={taskForm.title} placeholder="Essay Draft" onChange={(event) => setTaskForm((current) => ({ ...current, title: event.target.value }))} />
                    </Field>
                    <NumberField label="Est. hours" min="0.25" step="0.25" value={taskForm.duration} onChange={(value) => setTaskForm((current) => ({ ...current, duration: value }))} />
                    <DateField
                      label="Deadline date"
                      value={taskForm.deadline_date}
                      onChange={(value) =>
                        setTaskForm((current) => ({
                          ...current,
                          deadline_date: value,
                          deadline_day: dateToDay(value) || current.deadline_day,
                        }))
                      }
                    />
                    <TimeField label="Deadline time" value={taskForm.deadline_time} onChange={(value) => setTaskForm((current) => ({ ...current, deadline_time: value }))} />
                    <Field label="Weekday">
                      <select
                        value={dateToDay(taskForm.deadline_date) || taskForm.deadline_day}
                        onChange={(event) =>
                          setTaskForm((current) => ({
                            ...current,
                            deadline_day: event.target.value,
                            deadline_date: dayToDate(event.target.value, selectedWeekStart),
                          }))
                        }
                      >
                        {DAYS.map((day) => (
                          <option key={day} value={day}>
                            {day}
                          </option>
                        ))}
                      </select>
                    </Field>
                  </div>
                  <button className="btn btn-primary" type="button" onClick={addTask}>
                    Add Movable Task
                  </button>
                  {taskError ? <p className="error-banner">{taskError}</p> : null}
                  <p className="helper-copy">Deadline date and time define when the task is due. The optimizer can still move the work earlier in the week.</p>
                </article>
              </div>

              <div className="workspace-right page-stack">
                <article className="card card-stretch">
                  <div className="section-title">Live Weekly Preview</div>
                  <p className="helper-copy">Classes and work are placed at exact times. Deadlines appear as due markers in the week.</p>
                  <TimelineCalendar blocks={schedulePreview} weekStart={selectedWeekStart} />
                </article>
              </div>
            </section>

            <article className="card">
              <div className="section-title">3. Personal Burnout Preferences</div>
              <div className="form-grid settings-grid">
                <NumberField label="Max daily hours" value={preferences.max_daily_hours} onChange={(value) => setPreferences((current) => ({ ...current, max_daily_hours: value }))} />
                <NumberField label="Weekly comfort limit" value={preferences.weekly_hours_threshold} onChange={(value) => setPreferences((current) => ({ ...current, weekly_hours_threshold: value }))} />
                <TimePreferenceField label="Late-night cutoff" value={preferences.late_night_cutoff} onChange={(value) => setPreferences((current) => ({ ...current, late_night_cutoff: value }))} />
                <NumberField label="Max consecutive blocks" step="1" value={preferences.max_consecutive_blocks} onChange={(value) => setPreferences((current) => ({ ...current, max_consecutive_blocks: value }))} />
                <NumberField label="Min breaks per day" step="1" value={preferences.min_breaks_per_day} onChange={(value) => setPreferences((current) => ({ ...current, min_breaks_per_day: value }))} />
                <NumberField label="Deadline cluster days" step="1" value={preferences.deadline_cluster_days} onChange={(value) => setPreferences((current) => ({ ...current, deadline_cluster_days: value }))} />
                <TimePreferenceField label="Preferred start" value={preferences.preferred_study_start} onChange={(value) => setPreferences((current) => ({ ...current, preferred_study_start: value }))} />
                <TimePreferenceField label="Preferred end" value={preferences.preferred_study_end} onChange={(value) => setPreferences((current) => ({ ...current, preferred_study_end: value }))} />
                <TimePreferenceField label="Sleep start" value={sleepWindow.start} onChange={(value) => setSleepWindow((current) => ({ ...current, start: value }))} />
                <TimePreferenceField label="Sleep end" value={sleepWindow.end} onChange={(value) => setSleepWindow((current) => ({ ...current, end: value }))} />
              </div>
              {analysisError ? <p className="error-banner">{analysisError}</p> : null}
            </article>

            <div className="schedule-actions">
              <button className="btn btn-primary btn-large" type="button" onClick={() => analyzeSchedule("insights")} disabled={loading}>
                {loading ? "Analyzing..." : "Analyze and Optimize"}
              </button>
              <button className="btn btn-ghost" type="button" onClick={resetSample}>
                Reset Sample
              </button>
            </div>
          </div>
        )}

        {tab === "insights" && (
          <div className="page-stack">
            <section className="page-header">
              <h2>Burnout Analysis</h2>
              <p>See the risk drivers in your current schedule and how much the optimized plan reduces them.</p>
            </section>

            {!analysis ? (
              <div className="empty-state">
                <p>Analyze your schedule from the Schedule tab to unlock insights.</p>
              </div>
            ) : (
              <>
                <section className="grid-2">
                  <article className="card">
                    <div className="section-title">Risk Breakdown</div>
                    <RiskBreakdown assessment={beforeAssessment} getTone={getTone} toneClass={toneClass} />
                  </article>

                  <article className="card">
                    <div className="section-title">Overall Burnout Score</div>
                    <div className="overall-risk">
                      <div className={`risk-label ${toneClass(getTone(riskScore))}`}>{riskScore}</div>
                      <div className={`risk-state ${toneClass(getTone(riskScore))}`}>{beforeAssessment.level} Risk</div>
                      <div className="risk-note">
                        After optimization, your score drops to <strong>{optimizedScore}</strong> ({afterAssessment.level}).
                      </div>
                    </div>
                    <hr className="divider" />
                    <button className="btn btn-primary btn-full" type="button" onClick={() => setTab("compare")}>
                      See Optimized Schedule
                    </button>
                  </article>
                </section>

                <article className="card">
                  <div className="section-title">AI Insights</div>
                  {beforeAssessment.reasons.map((reason, index) => (
                    <InsightCard key={reason} tone={index === 0 ? "danger" : index === beforeAssessment.reasons.length - 1 ? "good" : "warn"} text={reason} />
                  ))}
                </article>
              </>
            )}
          </div>
        )}

        {tab === "compare" && (
          <div className="page-stack">
            <section className="page-header">
              <h2>Before vs After</h2>
              <p>Compare the baseline week with the optimized plan in a real hour-by-hour view.</p>
            </section>

            {!analysis ? (
              <div className="empty-state">
                <p>Analyze a schedule first to compare the two plans.</p>
              </div>
            ) : (
              <>
                <div className="chip-row chips-filter">
                  {[
                    { id: "all", label: "All" },
                    { id: "class", label: "Classes" },
                    { id: "work", label: "Work" },
                    { id: "task", label: "Tasks" },
                  ].map((filter) => (
                    <button
                      key={filter.id}
                      className={`chip chip-filter${activeFilter === filter.id ? " active" : ""}`}
                      type="button"
                      onClick={() => setActiveFilter(filter.id)}
                    >
                      {filter.label}
                    </button>
                  ))}
                </div>

                <section className="comparison comparison-top">
                  <article className="card">
                    <div className={`compare-label ${getTone(riskScore) === "safe" ? "compare-good" : ""}`}>Before · Risk Score {riskScore}</div>
                    <TimelineCalendar blocks={filteredBefore} weekStart={selectedWeekStart} />
                  </article>
                  <article className="card">
                    <div className="compare-label compare-good">After · Risk Score {optimizedScore}</div>
                    <TimelineCalendar blocks={filteredAfter} weekStart={selectedWeekStart} />
                  </article>
                </section>

                <section className="comparison">
                  <article className="card">
                    <div className="compare-label">Daily Workload Before</div>
                    <WorkloadChart data={beforeLoads} getTone={getTone} toneClass={toneClass} />
                  </article>
                  <article className="card">
                    <div className="compare-label compare-good">Daily Workload After</div>
                    <WorkloadChart data={afterLoads} getTone={getTone} toneClass={toneClass} />
                  </article>
                </section>
              </>
            )}
          </div>
        )}
      </main>
    </>
  );
}

function getTone(score) {
  if (score >= 60) return "danger";
  if (score >= 30) return "warn";
  if (score === 0) return "neutral";
  return "safe";
}

function toneClass(tone) {
  if (tone === "warn") return "tone-warn";
  if (tone === "danger") return "tone-danger";
  if (tone === "safe") return "tone-safe";
  return "tone-neutral";
}

export default App;
