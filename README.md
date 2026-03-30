# 👁 Eye Health Diagnosis System v2.0

> A production-level simulated ophthalmic diagnostic tool built with Python, Tkinter, SQLite, and ReportLab — designed as a final-year healthcare software project.

---

## ⚠️ Disclaimer

> **This is a simulated educational tool — not a real medical device.**
> It does not provide clinical diagnoses and must not be used to make any healthcare decisions.
> Always consult a licensed ophthalmologist for eye health concerns.

---

## 📸 Overview

The Eye Health Diagnosis System simulates the workflow of an ophthalmic screening session. It guides a patient through:

1. A **login/registration screen** that creates a persistent patient record
2. An **adaptive Snellen-style visual acuity test** (both eyes)
3. **Symptom-based diagnosis** across five condition categories
4. A **color vision assessment** using simulated Ishihara plates
5. A **reports dashboard** with session history and PDF export

---

## ✨ Features

| Feature | Description |
|---|---|
| 🏠 Patient Login | Name / age / gender intake; auto-creates SQLite record |
| 👁 Snellen Eye Test | 11-line adaptive chart (20/200 → 20/10), per-eye, diopter estimation |
| 📈 Trend Tracking | Compares current power against previous visit |
| 🩺 Irritation Diagnosis | 4-symptom binary code → 16 named conditions + medications |
| 🔴 Red Eye Assessment | Priority-ordered rule engine with urgency tiers (Emergency → Routine) |
| 💧 Swelling / Muscle | Look-up table for 12 orbital and systemic conditions |
| 👀 Double Vision | Diplopia condition lookup with treatment plans |
| 🌈 Color Vision Test | Simulated Ishihara plates + shuffled color arrangement test |
| 📋 Session History | SQLite-backed timestamped diagnostic records |
| 📄 PDF Export | Formatted reports via ReportLab (tables, branding, disclaimer) |
| ⚠️ Disclaimer | Embedded on About page and in every exported report |

---

## 🗂 Project Structure

```
eye_health_system/
├── app.py          # UI layer — all 7 page classes, sidebar, colour tokens
├── core.py         # Logic layer — medical KB, DiagnosticEngine, PatientDatabase, ReportGenerator
├── data/
│   └── patients.db # SQLite database (auto-created on first run)
├── exports/
│   └── *.pdf       # Generated diagnostic reports
└── README.md
```

### Architecture

The project follows a lightweight **MVC-style separation**:

- **`core.py`** — Model + business logic: medical knowledge base, `DiagnosticEngine`, `PatientDatabase`, `ReportGenerator`
- **`app.py`** — View + Controller: Tkinter pages, navigation, event handlers

---

## 🚀 Getting Started

### Prerequisites

- Python **3.10 or higher**
- pip

### Install Dependencies

```bash
pip install reportlab pillow
```

### Run the App

```bash
git clone https://github.com/your-username/eye-health-diagnosis-system.git
cd eye-health-diagnosis-system
python app.py
```

---

## 🧠 Diagnostic Logic

### Snellen Eye Test

The test simulates 11 chart rows from `20/200` down to `20/10`. Each row maps to an estimated diopter correction:

| Snellen | Severity | Est. Power |
|---------|----------|------------|
| 20/200  | Critical | 3.00 D     |
| 20/100  | Severe   | 2.00 D     |
| 20/50   | Moderate | 1.25 D     |
| 20/30   | Mild     | 0.75 D     |
| 20/20   | Normal   | 0.00 D     |

Adaptive logic: the test advances when the user passes a row and stops after two consecutive failures. Each eye is tested independently.

### Red Eye Rule Engine

Applies a priority-ordered rule set matching required and forbidden symptom flags:

```
{pain, vision_blur, light_sensitive}  → Acute Angle-Closure Glaucoma  🚨 EMERGENCY
{pain, light_sensitive}               → Uveitis / Iritis               ⚠️  Urgent
{discharge}                           → Bacterial Conjunctivitis        📅 Same-day
{itching}                             → Allergic Conjunctivitis         📅 Routine
```

### Irritation Diagnosis

A 4-bit binary code (dry | watering | pain | itching) maps to one of 16 named conditions, each with a specific medication recommendation.

---

## 📄 Sample PDF Report

Every diagnosis or eye test can be exported as a formatted PDF including:

- Patient name and timestamp
- Findings table (condition, severity, acuity, power, trend)
- Recommended treatment
- Full disclaimer block

Reports are saved to the `exports/` directory.

---

## 🗄 Database Schema

```sql
patients  (id, name, age, gender, created_at)
sessions  (id, patient_id, session_type, findings_json, created_at)
eye_tests (id, patient_id, left_acuity, left_power, left_severity,
           right_acuity, right_power, right_severity,
           prev_left_power, prev_right_power, tested_at)
```

---

## 🛠 Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.12 |
| GUI | Tkinter (standard library) |
| Database | SQLite via `sqlite3` (standard library) |
| PDF Generation | ReportLab |
| Image Support | Pillow |

---

## 🔮 Possible Extensions

- [ ] Doctor mode vs Patient mode with role-based access
- [ ] Matplotlib integration for acuity trend graphs
- [ ] REST API backend (Flask/FastAPI) for web deployment
- [ ] Retinal image upload with basic anomaly flagging
- [ ] Multi-language support

---
## 📜 License

This project is licensed under the MIT License. See `LICENSE` for details.
