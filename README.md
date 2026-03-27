# BalanceAI - AI Schedule Arranger and Burnout Alert

## Team Members
- **Freeman Yiu** - Integration / Repo Lead / QA
- **Youcheng Taing** - Scheduler / Optimizer
- **Yen Nguyen** - Frontend / UX (React)
- **Matthew Yeung** - Burnout Detection Engine

---

## Project Overview
BalanceAI is an AI-powered web application designed to help students manage their schedules while avoiding burnout.

Students can input their:
- Classes
- Work shifts
- Tasks and assignments
- Deadlines
- Estimated task durations

The system analyzes the schedule, detects burnout risk, and intelligently rearranges tasks into a healthier, more balanced plan.

---

## Problem Statement
Students often overload their schedules without realizing the long-term impact on their health and productivity.

Current tools such as calendars and planners help organize tasks, but they often:
- Do not detect burnout risk
- Do not provide intelligent scheduling suggestions
- Do not optimize workload distribution

---

## Our Solution
BalanceAI goes beyond basic scheduling.

It:
1. Analyzes workload patterns
2. Detects burnout risk
3. Explains why the schedule is unhealthy
4. Automatically generates a healthier schedule

We are updating the project plan to use:
- A Streamlit frontend for interactive schedule input and visualization
- A Python backend for optimization, burnout logic, and business rules
- A lightweight API layer between the frontend and backend

---

## How AI Is Used
We use a hybrid AI approach combining rules, heuristics, and intelligent scheduling.

### 1. Burnout Detection
- Rule-based scoring system
- Factors include:
  - Daily workload
  - Deadline clustering
  - Lack of breaks
  - Late-night work
  - Consecutive heavy days

### 2. Schedule Optimization
- Constraint-based scheduling
- Heuristic optimization
- Respects:
  - Fixed commitments such as class and work
  - Task deadlines
  - Sleep windows
  - Daily workload limits

### 3. Explainability
- Generates human-readable insights such as:
  - "You have 3 deadlines within 48 hours"
  - "Thursday exceeds safe workload limits"
  - "Your schedule includes too much late-night work"

---

## System Workflow
1. User enters schedule data in the Streamlit frontend
2. Frontend sends the data to the Python backend
3. Backend builds the initial schedule context
4. Burnout engine analyzes risk
5. Optimizer rearranges tasks
6. System compares before vs after
7. Frontend displays improvements and insights

---

## Features

### Core Features
- Input classes, work shifts, and tasks
- Burnout risk scoring (Low / Medium / High)
- Explanation of risk factors
- AI-based schedule optimization
- Before vs After comparison
- Personalized burnout thresholds and scheduling preferences

### Optional or Future Features
- Break recommendations
- Energy-based scheduling
- Export schedule
- Authentication system
- Calendar integrations

---

## Tech Stack

### Frontend
- Streamlit

### Backend
- Python

### Libraries
- Pandas for data handling
- OR-Tools or custom heuristics for optimization

### Data Storage
- JSON / in-memory for hackathon development

---

## Example Use Case

### Input
- 3 classes
- 1 work shift
- 3 assignments due in the same week

### Output
- Burnout Risk: **High**
- Reasons:
  - Heavy workload on Thursday
  - Deadlines clustered within 2 days

### After Optimization
- Tasks redistributed across the week
- Burnout Risk reduced to **Moderate**

---

## Innovation
Unlike traditional planners, BalanceAI:
- Detects burnout before it happens
- Automatically restructures schedules
- Provides explainable AI insights

---

## Impact
- Helps students maintain mental health
- Improves productivity and time management
- Scales as a lightweight student planning tool

---

## Future Improvements
- Machine learning-based personalization
- Mobile app version
- Google Calendar integration
- Long-term burnout prediction

---

## Acknowledgments
Built for AI Hackathon 2026.

---

## License
MIT License
