import { useEffect, useMemo, useState } from "react";

const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const HOURS = Array.from({ length: 24 }, (_, index) => index);
const CALENDAR_START_HOUR = 0;
const CALENDAR_TOTAL_HOURS = 24;
const API_BASE = "http://127.0.0.1:8000";
const TIME_STEP_MINUTES = 5;

function createSamplePayload() {
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

function createInitialCommitment(weekStart) {
  return {
    title: "",
    commitment_date: toDateInputValue(weekStart),
    start: "09:00",
    end: "10:30",
    category: "class",
  };
}

function createInitialTask(weekStart) {
  return {
    title: "",
    duration: 1,
    deadline_day: "Mon",
    deadline_date: toDateInputValue(weekStart),
    deadline_time: "23:59",
  };
}

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
  const [error, setError] = useState("");

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
    () => ({
      commitments: activeWeekCommitments.map(({ title, day, start, end }) => ({ title, day, start, end })),
      tasks: activeWeekTasks.map(({ title, duration, deadline_day }) => ({ title, duration, deadline_day })),
      sleep_window: sleepWindow,
      preferences,
      max_daily_hours: preferences.max_daily_hours,
      workday_start: preferences.preferred_study_start,
      workday_end: preferences.preferred_study_end,
      slot_step: preferences.slot_step,
      buffer_hours: preferences.buffer_hours,
    }),
    [activeWeekCommitments, activeWeekTasks, sleepWindow, preferences]
  );

  async function analyzeSchedule(nextTab = "insights") {
    const validationError = validateScheduleInputs({
      commitments: activeWeekCommitments,
      tasks: activeWeekTasks,
    });
    if (validationError) {
      setError(validationError);
      return;
    }

    setLoading(true);
    setError("");

    try {
      const response = await fetch(`${API_BASE}/api/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const rawBody = await response.text();
      let parsedBody = null;
      if (rawBody) {
        try {
          parsedBody = JSON.parse(rawBody);
        } catch {
          parsedBody = null;
        }
      }

      if (!response.ok) {
        const message =
          parsedBody?.detail ||
          parsedBody?.message ||
          `Unable to analyze schedule. Backend returned ${response.status}.`;
        throw new Error(message);
      }

      if (!parsedBody) {
        throw new Error("Backend returned an empty response.");
      }

      setAnalysis(parsedBody);
      setTab(nextTab);
    } catch (fetchError) {
      if (fetchError instanceof TypeError) {
        setError("Could not reach the backend. Start the API on http://127.0.0.1:8000 and try again.");
      } else {
        setError(fetchError.message || "Unable to analyze schedule.");
      }
    } finally {
      setLoading(false);
    }
  }

  function addCommitment() {
    if (!commitmentForm.title.trim()) {
      setError("Add a title before saving a class or work block.");
      return;
    }

    const start = timeToDecimal(commitmentForm.start);
    const end = timeToDecimal(commitmentForm.end);
    const commitmentDay = dateToDay(commitmentForm.commitment_date);

    if (start === null || end === null || !commitmentDay) {
      setError("Enter valid start and end times.");
      return;
    }

    if (end <= start) {
      setError("Class or work end time must be later than start time.");
      return;
    }

    setError("");
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
      setError("Add a task title before saving.");
      return;
    }
    if (taskForm.duration <= 0) {
      setError("Task duration must be greater than zero.");
      return;
    }

    if (!taskForm.deadline_date) {
      setError("Choose a deadline date for the task.");
      return;
    }

    if (!taskForm.deadline_time) {
      setError("Choose a deadline time for the task.");
      return;
    }

    const deadlineDay = dateToDay(taskForm.deadline_date);
    if (!deadlineDay) {
      setError("Choose a valid deadline date.");
      return;
    }

    setError("");
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
    setError("");
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
              <StatCard title="Current Burnout Score" value={analysis ? riskScore : "--"} tone={getTone(riskScore)} />
              <StatCard title="After Optimization" value={analysis ? optimizedScore : "--"} tone={getTone(optimizedScore)} />
              <StatCard title="Risk Points Saved" value={analysis ? `-${savedPoints}` : "--"} tone="neutral" />
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
                  <ScoreRing score={analysis ? riskScore : 72} label="Risk score" tone={analysis ? getTone(riskScore) : "danger"} />
                  <ScoreRing score={analysis ? optimizedScore : 34} label="Optimized" tone={analysis ? getTone(optimizedScore) : "safe"} />
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
                    onChange={(event) => selectWeek(event.target.value, setSelectedWeekStart, setCommitmentForm, setTaskForm)}
                  >
                    {buildWeekOptions().map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </Field>
                <button className="btn btn-ghost" type="button" onClick={() => jumpToThisWeek(setSelectedWeekStart, setCommitmentForm, setTaskForm)}>
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
                      <input value={dateToDay(commitmentForm.commitment_date) || ""} readOnly />
                    </Field>
                  </div>
                  <button className="btn btn-primary" type="button" onClick={addCommitment}>
                    Add Class or Work Block
                  </button>
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
                    <DateField label="Deadline date" value={taskForm.deadline_date} onChange={(value) => setTaskForm((current) => ({ ...current, deadline_date: value, deadline_day: dateToDay(value) || current.deadline_day }))} />
                    <TimeField label="Deadline time" value={taskForm.deadline_time} onChange={(value) => setTaskForm((current) => ({ ...current, deadline_time: value }))} />
                    <Field label="Weekday">
                      <input value={dateToDay(taskForm.deadline_date) || taskForm.deadline_day} readOnly />
                    </Field>
                  </div>
                  <button className="btn btn-primary" type="button" onClick={addTask}>
                    Add Movable Task
                  </button>
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
            </article>

            <div className="schedule-actions">
              <button className="btn btn-primary btn-large" type="button" onClick={() => analyzeSchedule("insights")} disabled={loading}>
                {loading ? "Analyzing..." : "Analyze and Optimize"}
              </button>
              <button className="btn btn-ghost" type="button" onClick={resetSample}>
                Reset Sample
              </button>
            </div>

            {error ? <p className="error-banner">{error}</p> : null}
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
                    <RiskBreakdown assessment={beforeAssessment} />
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
                    <WorkloadChart data={beforeLoads} />
                  </article>
                  <article className="card">
                    <div className="compare-label compare-good">Daily Workload After</div>
                    <WorkloadChart data={afterLoads} />
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

function Field({ label, children }) {
  return (
    <div className="input-group">
      <label className="input-label">{label}</label>
      {children}
    </div>
  );
}

function NumberField({ label, value, onChange, step = "0.5", min = "0" }) {
  return (
    <Field label={label}>
      <input type="number" min={min} step={step} value={value} onChange={(event) => onChange(Number(event.target.value))} />
    </Field>
  );
}

function DateField({ label, value, onChange }) {
  return (
    <Field label={label}>
      <input type="date" value={value} onChange={(event) => onChange(event.target.value)} />
    </Field>
  );
}

function TimeField({ label, value, onChange }) {
  return (
    <Field label={label}>
      <input type="time" step={TIME_STEP_MINUTES * 60} value={value} onChange={(event) => onChange(event.target.value)} />
    </Field>
  );
}

function TimePreferenceField({ label, value, onChange }) {
  return (
    <TimeField
      label={label}
      value={decimalToTime(value)}
      onChange={(rawValue) => {
        const parsed = timeToDecimal(rawValue);
        if (parsed !== null) {
          onChange(parsed);
        }
      }}
    />
  );
}

function StepCard({ number, title, text }) {
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

function StatCard({ title, value, tone }) {
  return (
    <article className="stat-card">
      <div className={`stat-value ${toneClass(tone)}`}>{value}</div>
      <div className="stat-label">{title}</div>
    </article>
  );
}

function ScoreRing({ score, label, tone }) {
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

function InsightCard({ tone, text }) {
  return (
    <div className={`insight insight-${tone}`}>
      <span className="insight-icon">{tone === "danger" ? "!" : tone === "warn" ? "~" : "+"}</span>
      <div className="insight-text">{text}</div>
    </div>
  );
}

function RiskBreakdown({ assessment }) {
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

function TimelineCalendar({ blocks, weekStart }) {
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

function WorkloadChart({ data }) {
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

function toDailyBlocks(scheduledTasks, commitments) {
  const days = Object.fromEntries(DAYS.map((day) => [day, []]));

  commitments.forEach((item) => {
    days[item.day]?.push({
      label: item.title,
      type: item.category === "work" || item.title.toLowerCase().includes("work") ? "work" : "class",
      start: item.start,
      end: item.end,
      time: `${formatHour(item.start)}-${formatHour(item.end)}`,
    });
  });

  scheduledTasks.forEach((item) => {
    days[item.day]?.push({
      label: item.title,
      type: "task",
      overload: /deadline|due/i.test(item.title),
      start: item.start,
      end: item.end,
      time: `${formatHour(item.start)}-${formatHour(item.end)}`,
    });
  });

  Object.values(days).forEach((blocks) => {
    blocks.sort((left, right) => {
      const leftStart = typeof left.start === "number" ? left.start : 99;
      const rightStart = typeof right.start === "number" ? right.start : 99;
      return leftStart - rightStart;
    });
  });

  return days;
}

function buildPreviewCalendar(commitments, tasks) {
  const days = Object.fromEntries(DAYS.map((day) => [day, []]));

  commitments.forEach((item) => {
    days[item.day]?.push({
      label: item.title,
      type: item.category === "work" ? "work" : "class",
      start: item.start,
      end: item.end,
      time: `${formatHour(item.start)}-${formatHour(item.end)}`,
    });
  });

  tasks.forEach((task) => {
    days[task.deadline_day]?.push({
      label: `${task.title} due`,
      type: "task",
      time: `${formatDeadline(task)} · ${task.duration}h`,
    });
  });

  Object.values(days).forEach((blocks) => {
    blocks.sort((left, right) => {
      const leftStart = typeof left.start === "number" ? left.start : 99;
      const rightStart = typeof right.start === "number" ? right.start : 99;
      return leftStart - rightStart;
    });
  });

  return days;
}

function filterBlocks(daily, filter) {
  if (filter === "all") return daily;
  return Object.fromEntries(Object.entries(daily).map(([day, blocks]) => [day, blocks.filter((block) => block.type === filter)]));
}

function toDayLoads(dailyHours = {}) {
  return DAYS.map((day) => Number(dailyHours?.[day] || 0));
}

function validateScheduleInputs({ commitments, tasks }) {
  if (!commitments.length && !tasks.length) {
    return "Add at least one class, work block, or task in the currently selected week before analyzing.";
  }
  if (tasks.some((task) => !task.title?.trim())) {
    return "Every task needs a title.";
  }
  if (tasks.some((task) => task.deadline_date && !dateToDay(task.deadline_date))) {
    return "Each task needs a valid deadline date.";
  }
  if (tasks.some((task) => !task.deadline_time)) {
    return "Each task needs a deadline time.";
  }
  if (tasks.some((task) => !DAYS.includes(task.deadline_day))) {
    return "Each task needs a valid deadline day.";
  }
  if (commitments.some((item) => item.end <= item.start)) {
    return "Every class or work block must end after it starts.";
  }
  return "";
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

function formatHour(value) {
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

function timeToDecimal(rawValue) {
  if (!rawValue || !rawValue.includes(":")) return null;
  const [hoursText, minutesText] = rawValue.split(":");
  const hours = Number(hoursText);
  const minutes = Number(minutesText);
  if (Number.isNaN(hours) || Number.isNaN(minutes)) return null;
  return Number((hours + minutes / 60).toFixed(2));
}

function dateToDay(rawValue) {
  if (!rawValue) return null;
  const parsed = new Date(`${rawValue}T00:00:00`);
  if (Number.isNaN(parsed.getTime())) return null;
  return ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"][parsed.getDay()] || null;
}

function addDays(date, amount) {
  const next = new Date(date);
  next.setDate(next.getDate() + amount);
  return next;
}

function getWeekStart(date) {
  const base = new Date(date);
  const day = base.getDay();
  const diff = day === 0 ? -6 : 1 - day;
  base.setHours(0, 0, 0, 0);
  base.setDate(base.getDate() + diff);
  return base;
}

function toDateInputValue(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function isSameWeek(rawValue, weekStart) {
  if (!rawValue) return false;
  const date = new Date(`${rawValue}T00:00:00`);
  if (Number.isNaN(date.getTime())) return false;
  return toDateInputValue(getWeekStart(date)) === toDateInputValue(weekStart);
}

function formatDate(rawValue) {
  if (!rawValue) return "No date";
  const [year, month, day] = rawValue.split("-");
  if (!year || !month || !day) return rawValue;
  return `${month}/${day}/${year}`;
}

function formatShortDate(date) {
  return `${String(date.getMonth() + 1).padStart(2, "0")}/${String(date.getDate()).padStart(2, "0")}`;
}

function formatWeekRange(weekStart) {
  const weekEnd = addDays(weekStart, 6);
  return `${formatDate(toDateInputValue(weekStart))} - ${formatDate(toDateInputValue(weekEnd))}`;
}

function buildWeekOptions() {
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

function formatDeadline(task) {
  const dateLabel = task.deadline_date ? formatDate(task.deadline_date) : task.deadline_day;
  const timeLabel = task.deadline_time || "";
  return `${dateLabel}${timeLabel ? ` ${timeLabel}` : ""}`;
}

function shiftWeek(direction, setSelectedWeekStart, setCommitmentForm, setTaskForm) {
  setSelectedWeekStart((current) => {
    const next = addDays(current, direction * 7);
    setCommitmentForm(createInitialCommitment(next));
    setTaskForm(createInitialTask(next));
    return next;
  });
}

function jumpToThisWeek(setSelectedWeekStart, setCommitmentForm, setTaskForm) {
  const next = getWeekStart(new Date());
  setSelectedWeekStart(next);
  setCommitmentForm(createInitialCommitment(next));
  setTaskForm(createInitialTask(next));
}

function selectWeek(rawValue, setSelectedWeekStart, setCommitmentForm, setTaskForm) {
  const next = getWeekStart(new Date(`${rawValue}T00:00:00`));
  setSelectedWeekStart(next);
  setCommitmentForm(createInitialCommitment(next));
  setTaskForm(createInitialTask(next));
}

function decimalToTime(value) {
  const normalized = ((value % 24) + 24) % 24;
  let hour = Math.floor(normalized);
  let minute = Math.round((normalized - hour) * 60);
  if (minute === 60) {
    hour = (hour + 1) % 24;
    minute = 0;
  }
  return `${String(hour).padStart(2, "0")}:${String(minute).padStart(2, "0")}`;
}

function hourToTopPercent(hour) {
  return ((hour - CALENDAR_START_HOUR) / CALENDAR_TOTAL_HOURS) * 100;
}

function capitalize(value) {
  return value.charAt(0).toUpperCase() + value.slice(1);
}

export default App;
