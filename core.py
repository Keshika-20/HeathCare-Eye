# =============================================================================
# core.py — Business Logic, Medical Knowledge Base & Patient Data Layer
# Eye Health Diagnosis System v2.0
# =============================================================================

import json
import sqlite3
import os
import random
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
EXPORTS_DIR = BASE_DIR / "exports"
DB_PATH = DATA_DIR / "patients.db"

DATA_DIR.mkdir(exist_ok=True)
EXPORTS_DIR.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# Medical Knowledge Base
# ---------------------------------------------------------------------------

# Snellen chart rows: (font_size_pt, acuity_label, diopter_estimate)
# Simulates chart lines from 20/200 down to 20/10
SNELLEN_ROWS = [
    (72, "20/200", 3.0),
    (60, "20/160", 2.5),
    (48, "20/100", 2.0),
    (36, "20/70",  1.5),
    (28, "20/50",  1.25),
    (22, "20/40",  1.0),
    (18, "20/30",  0.75),
    (14, "20/25",  0.5),
    (11, "20/20",  0.0),   # Normal vision
    (9,  "20/15",  0.0),
    (8,  "20/10",  0.0),
]

# Severity tiers based on Snellen row reached
def acuity_to_severity(best_row_index: int) -> tuple[str, str]:
    """
    Returns (severity_label, severity_color_key) given the best row passed.
    best_row_index is the index in SNELLEN_ROWS of the lowest line read successfully.
    """
    if best_row_index >= 8:   # 20/20 or better
        return "Normal", "green"
    elif best_row_index >= 6: # 20/30 – 20/40
        return "Mild", "yellow"
    elif best_row_index >= 4: # 20/50 – 20/70
        return "Moderate", "orange"
    elif best_row_index >= 2: # 20/100 – 20/160
        return "Severe", "red"
    else:                      # 20/200
        return "Critical", "darkred"

# Irritation symptom → medication map (binary key: dry|water|pain|itch)
IRRITATION_TREATMENTS = {
    '0000': ('Healthy Eyes', 'No treatment needed. Continue good eye hygiene.', 'None', 'Normal'),
    '0001': ('Allergic Itch', 'Mast cell stabilizers: Alomide, Crolom, Alocril', 'Low', 'Mild'),
    '0010': ('Episcleritis', 'Flurbiprofen Eye Drop, NSAIDs', 'Low', 'Mild'),
    '0011': ('Anterior Uveitis', 'Anti-inflammatory drops + corticosteroid eye drops', 'Moderate', 'Moderate'),
    '0100': ('Conjunctival Congestion', 'Decongestant eye drops (Visine)', 'Low', 'Mild'),
    '0101': ('Allergic Conjunctivitis', 'Visine Allergy Eye Relief, antihistamine drops', 'Low', 'Mild'),
    '0110': ('Chronic Conjunctivitis', 'Pheniramine maleate / naphazoline HCl', 'Moderate', 'Moderate'),
    '0111': ('Vernal Keratoconjunctivitis', 'Antazoline / naphazoline HCl (Vasocon-A)', 'Moderate', 'Moderate'),
    '1000': ('Aqueous Deficient Dry Eye', 'Blink GelTears lubricating drops', 'Low', 'Mild'),
    '1001': ('Mixed Dry Eye + Allergy', 'Artificial tears + antihistamine drops', 'Low', 'Mild'),
    '1010': ('Evaporative Dry Eye', 'Artificial tears, warm compresses, avoid triggers', 'Low', 'Mild'),
    '1011': ('Digital Eye Strain', 'Artificial tears, screen breaks (20-20-20 rule)', 'Low', 'Mild'),
    '1100': ('Meibomian Gland Dysfunction', 'Eyelid hygiene, warm compresses, lubricants', 'Moderate', 'Moderate'),
    '1101': ('Sjögren-Related Dry Eye', 'Omega-3 supplements, env. management, lubricants', 'Moderate', 'Moderate'),
    '1110': ('Lipid-Layer Deficiency', 'Artificial tears for poor-quality tear film', 'Low', 'Mild'),
    '1111': ('Severe Dry Eye Syndrome', 'Comprehensive tear management + env. control', 'High', 'Severe'),
}

# Red-eye weighted rule engine
RED_EYE_RULES = [
    # (condition, treatment, severity, required_flags, forbidden_flags, urgency)
    ("Acute Angle-Closure Glaucoma",
     "EMERGENCY: Seek immediate care. IV acetazolamide, pilocarpine, beta-blockers.",
     "Critical", {"pain", "vision_blur", "light_sensitive"}, set(), "🚨 EMERGENCY"),

    ("Uveitis / Iritis",
     "Urgent ophthalmologist referral. Cycloplegics + corticosteroid drops.",
     "Severe", {"pain", "light_sensitive"}, {"discharge"}, "⚠️ Urgent"),

    ("Corneal Ulcer / Keratitis",
     "Urgent care. Topical fortified antibiotics, avoid contact lenses.",
     "Severe", {"pain", "vision_blur"}, {"discharge"}, "⚠️ Urgent"),

    ("Bacterial Conjunctivitis",
     "Topical antibiotic drops (ciprofloxacin, moxifloxacin). Warm compress.",
     "Moderate", {"discharge"}, {"pain"}, "📅 Same-day"),

    ("Viral Conjunctivitis",
     "Supportive care; cold compress, artificial tears. Highly contagious — wash hands.",
     "Mild", {"itching"}, {"discharge", "pain"}, "📅 Routine"),

    ("Allergic Conjunctivitis",
     "Antihistamine drops (olopatadine). Avoid allergens. Cold compress.",
     "Mild", {"itching"}, {"discharge", "pain", "vision_blur"}, "📅 Routine"),

    ("Subconjunctival Hemorrhage",
     "Usually self-resolving in 1–2 weeks. Artificial tears for comfort.",
     "Mild", {"injury"}, set(), "📅 Routine"),

    ("Dry Eye Syndrome",
     "Preservative-free artificial tears, increase water intake, blink exercises.",
     "Mild", set(), set(), "📅 Routine"),  # Fallback
]

# Comprehensive treatment database for non-refraction conditions
CONDITION_TREATMENTS = {
    "pterygium": {
        "description": "Fibrovascular growth on the conjunctiva that may encroach on the cornea.",
        "treatment": "Lubricating drops, anti-inflammatory drops. Surgical excision if vision is affected.",
        "severity": "Mild–Moderate",
        "urgency": "Routine"
    },
    "orbital myositis": {
        "description": "Idiopathic inflammation of one or more extraocular muscles.",
        "treatment": "NSAIDs or systemic steroids (prednisone). Surgery rarely indicated.",
        "severity": "Moderate",
        "urgency": "Urgent"
    },
    "thyroid eye disease": {
        "description": "Autoimmune orbital inflammation associated with thyroid dysfunction.",
        "treatment": "Steroids, radiation, teprotumumab. Orbital decompression if optic nerve compressed.",
        "severity": "Moderate–Severe",
        "urgency": "Urgent"
    },
    "orbital tumor": {
        "description": "Neoplastic mass within the orbit; may be benign or malignant.",
        "treatment": "Imaging (CT/MRI), biopsy, oncology referral. Chemotherapy/radiation/surgery per type.",
        "severity": "Severe",
        "urgency": "Emergency"
    },
    "dermoid cyst": {
        "description": "Benign cystic lesion derived from ectopic skin elements.",
        "treatment": "Observation for asymptomatic lesions. Surgical excision if growing or symptomatic.",
        "severity": "Mild",
        "urgency": "Routine"
    },
    "bacterial conjunctivitis": {
        "description": "Bacterial infection of the conjunctiva with purulent discharge.",
        "treatment": "Topical antibiotics (ciprofloxacin, moxifloxacin). Warm compresses.",
        "severity": "Mild",
        "urgency": "Same-day"
    },
    "orbital cellulitis": {
        "description": "Serious infection of the orbital tissues; vision- and life-threatening.",
        "treatment": "Urgent IV antibiotics (ampicillin-sulbactam). CT scan, possible surgical drainage.",
        "severity": "Critical",
        "urgency": "Emergency"
    },
    "strabismus": {
        "description": "Misalignment of the visual axes; may cause diplopia or amblyopia.",
        "treatment": "Corrective lenses, prism glasses, patching, botulinum toxin, or strabismus surgery.",
        "severity": "Mild–Moderate",
        "urgency": "Routine"
    },
    "cranial nerve palsy": {
        "description": "Weakness of CN III, IV, or VI causing ocular motility defect.",
        "treatment": "Observation (often resolves), systemic workup (MRI/bloods), prism or surgery.",
        "severity": "Moderate",
        "urgency": "Urgent"
    },
    "myasthenia gravis": {
        "description": "Autoimmune NMJ disease causing fatigable ptosis and diplopia.",
        "treatment": "Pyridostigmine, immunosuppressants (azathioprine), possible thymectomy.",
        "severity": "Moderate–Severe",
        "urgency": "Urgent"
    },
    "ischemic stroke": {
        "description": "Cerebrovascular accident causing cranial nerve or visual field defects.",
        "treatment": "Emergency tPA if within window, antiplatelet therapy, neurorehabilitation.",
        "severity": "Critical",
        "urgency": "Emergency"
    },
    "retinal detachment": {
        "description": "Separation of the sensory retina from the RPE; sight-threatening.",
        "treatment": "Urgent surgical repair: pneumatic retinopexy, scleral buckle, or vitrectomy.",
        "severity": "Critical",
        "urgency": "Emergency"
    },
}

# ---------------------------------------------------------------------------
# Diagnostic Engine
# ---------------------------------------------------------------------------

class DiagnosticEngine:
    """Applies rule-based + weighted scoring to produce structured diagnoses."""

    @staticmethod
    def diagnose_irritation(dry: bool, watering: bool, pain: bool, itching: bool) -> dict:
        code = f"{int(dry)}{int(watering)}{int(pain)}{int(itching)}"
        name, treatment, urgency, severity = IRRITATION_TREATMENTS.get(
            code, ('Unknown Pattern', 'Please consult an ophthalmologist.', 'Unknown', 'Unknown')
        )
        return {
            "condition": name,
            "treatment": treatment,
            "urgency": urgency,
            "severity": severity,
            "symptom_code": code
        }

    @staticmethod
    def diagnose_red_eye(flags: set) -> dict:
        for rule in RED_EYE_RULES:
            name, treatment, severity, required, forbidden, urgency = rule
            if required.issubset(flags) and not forbidden.intersection(flags):
                return {
                    "condition": name,
                    "treatment": treatment,
                    "severity": severity,
                    "urgency": urgency
                }
        # Fallback
        return {
            "condition": "Non-Specific Red Eye",
            "treatment": "Artificial tears; consult GP if persists beyond 48 hours.",
            "severity": "Mild",
            "urgency": "Routine"
        }

    @staticmethod
    def diagnose_condition(condition_key: str) -> dict:
        info = CONDITION_TREATMENTS.get(condition_key)
        if info:
            return {
                "condition": condition_key.replace("_", " ").title(),
                **info
            }
        return {
            "condition": condition_key,
            "description": "No database entry found.",
            "treatment": "Please consult an ophthalmologist.",
            "severity": "Unknown",
            "urgency": "Routine"
        }

    @staticmethod
    def evaluate_snellen_result(
        left_best: int,   # index in SNELLEN_ROWS of last successful row
        right_best: int,
        prev_left_diopter: float | None,
        prev_right_diopter: float | None
    ) -> dict:
        """Build a structured refraction report."""
        def eye_report(best_idx, prev_diopter, label):
            acuity = SNELLEN_ROWS[best_idx][1]
            diopter = SNELLEN_ROWS[best_idx][2]
            severity, _ = acuity_to_severity(best_idx)

            trend = "N/A"
            if prev_diopter is not None and diopter > 0:
                if diopter > prev_diopter:
                    trend = f"↑ Increased by {diopter - prev_diopter:.2f}D"
                elif diopter < prev_diopter:
                    trend = f"↓ Decreased by {prev_diopter - diopter:.2f}D"
                else:
                    trend = "→ Unchanged"

            return {
                "acuity": acuity,
                "estimated_power": diopter if diopter > 0 else 0.0,
                "severity": severity,
                "trend": trend,
            }

        return {
            "left": eye_report(left_best, prev_left_diopter, "Left"),
            "right": eye_report(right_best, prev_right_diopter, "Right"),
        }


# ---------------------------------------------------------------------------
# Database Layer
# ---------------------------------------------------------------------------

class PatientDatabase:
    """SQLite-backed patient and session storage."""

    def __init__(self):
        self.conn = sqlite3.connect(str(DB_PATH))
        self._init_schema()

    def _init_schema(self):
        cur = self.conn.cursor()
        cur.executescript("""
            CREATE TABLE IF NOT EXISTS patients (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT    NOT NULL,
                age         INTEGER,
                gender      TEXT,
                created_at  TEXT    DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS sessions (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id      INTEGER REFERENCES patients(id),
                session_type    TEXT,
                findings_json   TEXT,
                created_at      TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS eye_tests (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id          INTEGER REFERENCES patients(id),
                left_acuity         TEXT,
                left_power          REAL,
                left_severity       TEXT,
                right_acuity        TEXT,
                right_power         REAL,
                right_severity      TEXT,
                prev_left_power     REAL,
                prev_right_power    REAL,
                tested_at           TEXT DEFAULT (datetime('now'))
            );
        """)
        self.conn.commit()

    def get_or_create_patient(self, name: str, age: int = None, gender: str = None) -> int:
        cur = self.conn.cursor()
        cur.execute("SELECT id FROM patients WHERE LOWER(name)=LOWER(?)", (name,))
        row = cur.fetchone()
        if row:
            return row[0]
        cur.execute(
            "INSERT INTO patients (name, age, gender) VALUES (?,?,?)",
            (name, age, gender)
        )
        self.conn.commit()
        return cur.lastrowid

    def save_eye_test(self, patient_id: int, result: dict,
                      prev_left: float = None, prev_right: float = None) -> int:
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO eye_tests
            (patient_id, left_acuity, left_power, left_severity,
             right_acuity, right_power, right_severity,
             prev_left_power, prev_right_power)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, (
            patient_id,
            result["left"]["acuity"],  result["left"]["estimated_power"],  result["left"]["severity"],
            result["right"]["acuity"], result["right"]["estimated_power"], result["right"]["severity"],
            prev_left, prev_right
        ))
        self.conn.commit()
        return cur.lastrowid

    def save_diagnosis_session(self, patient_id: int, session_type: str, findings: dict) -> int:
        cur = self.conn.cursor()
        cur.execute(
            "INSERT INTO sessions (patient_id, session_type, findings_json) VALUES (?,?,?)",
            (patient_id, session_type, json.dumps(findings))
        )
        self.conn.commit()
        return cur.lastrowid

    def get_patient_history(self, patient_id: int) -> list[dict]:
        cur = self.conn.cursor()
        cur.execute("""
            SELECT session_type, findings_json, created_at
            FROM sessions WHERE patient_id=? ORDER BY created_at DESC LIMIT 20
        """, (patient_id,))
        rows = cur.fetchall()
        return [{"type": r[0], "findings": json.loads(r[1]), "date": r[2]} for r in rows]

    def get_all_patients(self) -> list[tuple]:
        cur = self.conn.cursor()
        cur.execute("SELECT id, name, age, gender, created_at FROM patients ORDER BY name")
        return cur.fetchall()

    def get_latest_eye_test(self, patient_id: int) -> dict | None:
        cur = self.conn.cursor()
        cur.execute("""
            SELECT left_acuity, left_power, left_severity,
                   right_acuity, right_power, right_severity, tested_at
            FROM eye_tests WHERE patient_id=? ORDER BY tested_at DESC LIMIT 1
        """, (patient_id,))
        row = cur.fetchone()
        if row:
            return {
                "left": {"acuity": row[0], "power": row[1], "severity": row[2]},
                "right": {"acuity": row[3], "power": row[4], "severity": row[5]},
                "date": row[6]
            }
        return None

    def close(self):
        self.conn.close()


# ---------------------------------------------------------------------------
# Report Generator
# ---------------------------------------------------------------------------

class ReportGenerator:
    """Generates text and PDF diagnostic reports."""

    @staticmethod
    def build_text_report(patient_name: str, report_data: dict) -> str:
        now = datetime.now().strftime("%d %B %Y, %I:%M %p")
        lines = [
            "=" * 60,
            "      EYE HEALTH DIAGNOSIS SYSTEM — DIAGNOSTIC REPORT",
            "=" * 60,
            "",
            f"  Patient Name : {patient_name}",
            f"  Date & Time  : {now}",
            f"  Report Type  : {report_data.get('type', 'General')}",
            "",
            "  ⚠  DISCLAIMER: This is a simulated diagnostic tool.",
            "  It does NOT replace a qualified ophthalmologist.",
            "",
            "-" * 60,
            "  FINDINGS",
            "-" * 60,
        ]

        findings = report_data.get("findings", {})
        for key, val in findings.items():
            lines.append(f"  {key:<22}: {val}")

        lines += [
            "",
            "-" * 60,
            "  RECOMMENDED ACTION",
            "-" * 60,
            f"  {report_data.get('treatment', 'Consult an ophthalmologist.')}",
            "",
            "=" * 60,
            "  Generated by Eye Health Diagnosis System v2.0",
            "=" * 60,
        ]
        return "\n".join(lines)

    @staticmethod
    def export_text(patient_name: str, report_data: dict) -> str:
        content = ReportGenerator.build_text_report(patient_name, report_data)
        safe_name = "".join(c for c in patient_name if c.isalnum() or c in "_ ")
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = EXPORTS_DIR / f"report_{safe_name}_{ts}.txt"
        path.write_text(content, encoding="utf-8")
        return str(path)

    @staticmethod
    def export_pdf(patient_name: str, report_data: dict) -> str:
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib import colors
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import cm
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable

            safe_name = "".join(c for c in patient_name if c.isalnum() or c in "_ ")
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = str(EXPORTS_DIR / f"report_{safe_name}_{ts}.pdf")

            doc = SimpleDocTemplate(path, pagesize=A4,
                                    rightMargin=2*cm, leftMargin=2*cm,
                                    topMargin=2*cm, bottomMargin=2*cm)
            styles = getSampleStyleSheet()
            PRIMARY = colors.HexColor("#1A6B8A")
            LIGHT   = colors.HexColor("#E8F4F8")

            title_style = ParagraphStyle("title", parent=styles["Title"],
                                         fontName="Helvetica-Bold", fontSize=18,
                                         textColor=PRIMARY, spaceAfter=6)
            head_style  = ParagraphStyle("head", parent=styles["Heading2"],
                                         fontName="Helvetica-Bold", fontSize=13,
                                         textColor=PRIMARY, spaceBefore=12, spaceAfter=4)
            normal_style = ParagraphStyle("normal", parent=styles["Normal"],
                                          fontName="Helvetica", fontSize=10, leading=14)
            warn_style  = ParagraphStyle("warn", parent=styles["Normal"],
                                         fontName="Helvetica-Oblique", fontSize=9,
                                         textColor=colors.HexColor("#CC4400"))

            story = []

            # Header
            story.append(Paragraph("Eye Health Diagnosis System", title_style))
            story.append(Paragraph("Diagnostic Report", styles["Heading2"]))
            story.append(HRFlowable(width="100%", thickness=2, color=PRIMARY))
            story.append(Spacer(1, 10))

            # Patient info table
            now = datetime.now().strftime("%d %B %Y, %I:%M %p")
            info = [
                ["Patient Name", patient_name],
                ["Date & Time", now],
                ["Report Type", report_data.get("type", "General")],
            ]
            t = Table(info, colWidths=[5*cm, 12*cm])
            t.setStyle(TableStyle([
                ("BACKGROUND", (0,0), (0,-1), LIGHT),
                ("FONTNAME", (0,0), (0,-1), "Helvetica-Bold"),
                ("FONTSIZE", (0,0), (-1,-1), 10),
                ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
                ("PADDING", (0,0), (-1,-1), 6),
            ]))
            story.append(t)
            story.append(Spacer(1, 12))

            # Disclaimer
            story.append(Paragraph(
                "⚠ DISCLAIMER: This is a simulated diagnostic tool. "
                "It does NOT replace a qualified ophthalmologist. "
                "Please seek professional medical advice for any eye condition.",
                warn_style
            ))
            story.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey))
            story.append(Spacer(1, 8))

            # Findings
            story.append(Paragraph("Findings", head_style))
            findings = report_data.get("findings", {})
            findings_data = [[k, str(v)] for k, v in findings.items()]
            if findings_data:
                ft = Table(findings_data, colWidths=[6*cm, 11*cm])
                ft.setStyle(TableStyle([
                    ("BACKGROUND", (0,0), (0,-1), LIGHT),
                    ("FONTNAME", (0,0), (0,-1), "Helvetica-Bold"),
                    ("FONTSIZE", (0,0), (-1,-1), 10),
                    ("GRID", (0,0), (-1,-1), 0.5, colors.lightgrey),
                    ("ROWBACKGROUNDS", (0,0), (-1,-1), [colors.white, colors.HexColor("#F5FBFD")]),
                    ("PADDING", (0,0), (-1,-1), 6),
                    ("VALIGN", (0,0), (-1,-1), "TOP"),
                ]))
                story.append(ft)

            story.append(Spacer(1, 12))

            # Treatment
            story.append(Paragraph("Recommended Action", head_style))
            story.append(Paragraph(report_data.get("treatment", "Consult an ophthalmologist."), normal_style))
            story.append(Spacer(1, 20))
            story.append(HRFlowable(width="100%", thickness=1, color=PRIMARY))
            story.append(Spacer(1, 4))
            story.append(Paragraph("Generated by Eye Health Diagnosis System v2.0", warn_style))

            doc.build(story)
            return path

        except ImportError:
            # Fallback to text report if reportlab not installed
            return ReportGenerator.export_text(patient_name, report_data)


# ---------------------------------------------------------------------------
# Color Blindness Test Utilities
# ---------------------------------------------------------------------------

ISHIHARA_PLATES = [
    {"display": "25", "answer": "25", "detail": "Plate 1 — Normal trichromats see 25"},
    {"display": "45", "answer": "45", "detail": "Plate 2 — Deuteranopes may see 35"},
    {"display": "6",  "answer": "6",  "detail": "Plate 3 — Protanopes may miss this"},
    {"display": "29", "answer": "29", "detail": "Plate 4 — All should see 29"},
    {"display": "57", "answer": "57", "detail": "Plate 5 — Red-green deficient may see 35"},
]

COLOR_ARRANGEMENT = ["Red", "Orange", "Yellow", "Green", "Blue", "Indigo", "Violet"]

def score_color_blindness(ishihara_correct: int, total: int) -> dict:
    pct = ishihara_correct / total * 100
    if pct >= 80:
        return {"result": "Normal Color Vision", "severity": "None", "recommendation":
                "No signs of color vision deficiency detected."}
    elif pct >= 60:
        return {"result": "Mild Color Deficiency", "severity": "Mild", "recommendation":
                "Mild red-green confusion possible. Consult an optometrist for confirmation."}
    elif pct >= 40:
        return {"result": "Moderate Deficiency", "severity": "Moderate", "recommendation":
                "Significant color confusion detected. Referral to ophthalmologist advised."}
    else:
        return {"result": "Severe Deficiency / Achromatopsia", "severity": "Severe", "recommendation":
                "Severe color vision impairment. Immediate specialist consultation recommended."}