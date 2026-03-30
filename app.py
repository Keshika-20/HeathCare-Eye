# =============================================================================
# app.py — Main Application Entry Point & UI Controller
# Eye Health Diagnosis System v2.0
# =============================================================================

import tkinter as tk
from tkinter import ttk, messagebox, font as tkfont
import random
import os
import subprocess
import sys
from datetime import datetime

from core import (
    DiagnosticEngine, PatientDatabase, ReportGenerator,
    SNELLEN_ROWS, CONDITION_TREATMENTS, ISHIHARA_PLATES,
    COLOR_ARRANGEMENT, score_color_blindness, acuity_to_severity
)

# ---------------------------------------------------------------------------
# Colour & Font Tokens
# ---------------------------------------------------------------------------
C = {
    "bg":          "#F0F4F8",   # main background
    "sidebar":     "#1A3A4A",   # dark teal sidebar
    "sidebar_acc": "#2196A6",   # sidebar active item
    "sidebar_txt": "#B0CDD8",   # sidebar inactive text
    "sidebar_atxt":"#FFFFFF",   # sidebar active text
    "primary":     "#1A6B8A",   # headings / buttons
    "accent":      "#2196A6",   # accents
    "card":        "#FFFFFF",   # card background
    "border":      "#D1E0E8",   # card border
    "text":        "#1C2D3A",   # main text
    "sub":         "#5C7A8A",   # secondary text
    "green":       "#27AE60",
    "yellow":      "#F39C12",
    "orange":      "#E67E22",
    "red":         "#E74C3C",
    "darkred":     "#8B0000",
    "input_bg":    "#EAF2F8",
    "hover":       "#1A5270",
    "btn_text":    "#FFFFFF",
    "disabled":    "#9DB5C0",
}

SEVERITY_COLORS = {
    "Normal":   C["green"],
    "None":     C["green"],
    "Mild":     C["yellow"],
    "Moderate": C["orange"],
    "Severe":   C["red"],
    "Critical": C["darkred"],
}


# ---------------------------------------------------------------------------
# Reusable Widget Helpers
# ---------------------------------------------------------------------------

def card(parent, **kwargs) -> tk.Frame:
    """White rounded-looking card frame."""
    kw = dict(bg=C["card"], relief="flat", bd=0,
               highlightthickness=1, highlightbackground=C["border"])
    kw.update(kwargs)
    return tk.Frame(parent, **kw)

def label(parent, text, size=11, bold=False, color=None, **kwargs) -> tk.Label:
    weight = "bold" if bold else "normal"
    fg = color or C["text"]
    return tk.Label(parent, text=text, bg=parent.cget("bg"), fg=fg,
                    font=("Helvetica", size, weight), **kwargs)

def btn(parent, text, command, width=18, bg=None, fg=None) -> tk.Button:
    bg = bg or C["primary"]
    fg = fg or C["btn_text"]
    b = tk.Button(parent, text=text, command=command, width=width,
                  bg=bg, fg=fg, activebackground=C["hover"],
                  activeforeground="#FFFFFF", relief="flat", bd=0,
                  cursor="hand2", font=("Helvetica", 10, "bold"),
                  padx=10, pady=6)
    return b

def entry(parent, **kwargs) -> tk.Entry:
    return tk.Entry(parent, bg=C["input_bg"], relief="flat", bd=0,
                    font=("Helvetica", 11), fg=C["text"],
                    insertbackground=C["text"],
                    highlightthickness=1, highlightcolor=C["accent"],
                    highlightbackground=C["border"], **kwargs)

def separator(parent, orient="horizontal", color=C["border"]):
    f = tk.Frame(parent, bg=color,
                 height=1 if orient == "horizontal" else 0,
                 width=0 if orient == "horizontal" else 1)
    return f

def severity_badge(parent, severity: str) -> tk.Label:
    color = SEVERITY_COLORS.get(severity, C["sub"])
    return tk.Label(parent, text=f"  {severity}  ", bg=color, fg="white",
                    font=("Helvetica", 9, "bold"), padx=4, pady=2)


# ---------------------------------------------------------------------------
# Application Class
# ---------------------------------------------------------------------------

class EyeHealthApp(tk.Tk):
    """Single-window application with sidebar navigation."""

    def __init__(self):
        super().__init__()
        self.title("Eye Health Diagnosis System v2.0")
        self.geometry("1100x720")
        self.minsize(900, 600)
        self.configure(bg=C["bg"])
        self.resizable(True, True)

        # State
        self.db = PatientDatabase()
        self.engine = DiagnosticEngine()
        self.current_patient_id: int | None = None
        self.current_patient_name: str = ""
        self.last_report: dict | None = None
        self._pages: dict[str, tk.Frame] = {}
        self._nav_buttons: dict[str, tk.Button] = {}
        self._active_page = tk.StringVar(value="home")

        self._build_layout()
        self._show_page("login")

    # ------------------------------------------------------------------
    # Layout skeleton
    # ------------------------------------------------------------------

    def _build_layout(self):
        # Sidebar (left)
        self.sidebar = tk.Frame(self, bg=C["sidebar"], width=210)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        # Main content area (right)
        self.content = tk.Frame(self, bg=C["bg"])
        self.content.pack(side="left", fill="both", expand=True)

        self._build_sidebar()
        self._build_pages()

    def _build_sidebar(self):
        # Logo / title area
        logo_frame = tk.Frame(self.sidebar, bg=C["sidebar"], pady=24)
        logo_frame.pack(fill="x")
        tk.Label(logo_frame, text="👁", font=("Helvetica", 28),
                 bg=C["sidebar"], fg="#2196A6").pack()
        tk.Label(logo_frame, text="EyeHealth", font=("Helvetica", 14, "bold"),
                 bg=C["sidebar"], fg="white").pack()
        tk.Label(logo_frame, text="Diagnosis System", font=("Helvetica", 9),
                 bg=C["sidebar"], fg=C["sidebar_txt"]).pack()

        separator(self.sidebar, color="#2C4A5A").pack(fill="x", padx=16, pady=6)

        # Nav items — shown after login
        self._nav_items = [
            ("home",      "🏠  Home",         self._nav_home),
            ("eyetest",   "👁  Eye Test",      self._nav_eyetest),
            ("diagnosis", "🩺  Diagnosis",     self._nav_diagnosis),
            ("reports",   "📋  Reports",       self._nav_reports),
            ("about",     "ℹ️  About",         self._nav_about),
        ]

        self._nav_area = tk.Frame(self.sidebar, bg=C["sidebar"])
        self._nav_area.pack(fill="x", pady=8)
        self._rebuild_nav()

        # Patient label at bottom
        self._patient_label = tk.Label(
            self.sidebar, text="", bg=C["sidebar"],
            fg=C["sidebar_txt"], font=("Helvetica", 9),
            wraplength=180, justify="center"
        )
        self._patient_label.pack(side="bottom", pady=14)

        tk.Label(self.sidebar, text="v2.0 — Demo Mode", bg=C["sidebar"],
                 fg=C["sidebar_txt"], font=("Helvetica", 8)).pack(side="bottom")

    def _rebuild_nav(self, enabled=False):
        for w in self._nav_area.winfo_children():
            w.destroy()
        self._nav_buttons.clear()

        for key, text, cmd in self._nav_items:
            b = tk.Button(
                self._nav_area, text=text, command=cmd,
                bg=C["sidebar"], fg=C["sidebar_txt"] if not enabled else C["sidebar_txt"],
                activebackground=C["sidebar_acc"], activeforeground="white",
                relief="flat", bd=0, anchor="w", padx=24, pady=10,
                font=("Helvetica", 11),
                state="disabled" if not enabled else "normal",
                cursor="hand2" if enabled else "arrow",
                width=22
            )
            b.pack(fill="x")
            self._nav_buttons[key] = b

    def _set_nav_active(self, key: str):
        for k, b in self._nav_buttons.items():
            if k == key:
                b.configure(bg=C["sidebar_acc"], fg="white")
            else:
                b.configure(bg=C["sidebar"], fg=C["sidebar_txt"])

    # ------------------------------------------------------------------
    # Page management
    # ------------------------------------------------------------------

    def _build_pages(self):
        for name, PageClass in [
            ("login",     LoginPage),
            ("home",      HomePage),
            ("eyetest",   EyeTestPage),
            ("diagnosis", DiagnosisPage),
            ("reports",   ReportsPage),
            ("about",     AboutPage),
        ]:
            page = PageClass(self.content, self)
            page.place(relx=0, rely=0, relwidth=1, relheight=1)
            self._pages[name] = page

    def _show_page(self, name: str):
        for page in self._pages.values():
            page.place_forget()
        self._pages[name].place(relx=0, rely=0, relwidth=1, relheight=1)
        if hasattr(self._pages[name], "on_show"):
            self._pages[name].on_show()
        self._set_nav_active(name)

    # ------------------------------------------------------------------
    # Navigation callbacks
    # ------------------------------------------------------------------

    def _nav_home(self):      self._show_page("home")
    def _nav_eyetest(self):   self._show_page("eyetest")
    def _nav_diagnosis(self): self._show_page("diagnosis")
    def _nav_reports(self):   self._show_page("reports")
    def _nav_about(self):     self._show_page("about")

    def on_login_success(self, patient_id: int, name: str):
        self.current_patient_id = patient_id
        self.current_patient_name = name
        self._patient_label.configure(text=f"Patient:\n{name}")
        self._rebuild_nav(enabled=True)
        self._show_page("home")

    def save_and_set_report(self, report_data: dict):
        self.last_report = report_data
        self.db.save_diagnosis_session(
            self.current_patient_id,
            report_data.get("type", "General"),
            report_data
        )

    def on_destroy(self):
        self.db.close()
        self.destroy()


# ---------------------------------------------------------------------------
# Login Page
# ---------------------------------------------------------------------------

class LoginPage(tk.Frame):
    def __init__(self, parent, app: EyeHealthApp):
        super().__init__(parent, bg=C["bg"])
        self.app = app
        self._build()

    def _build(self):
        # Center column
        col = tk.Frame(self, bg=C["bg"])
        col.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(col, text="👁", font=("Helvetica", 48),
                 bg=C["bg"], fg=C["primary"]).pack()
        label(col, "Eye Health Diagnosis System", 20, bold=True,
              color=C["primary"]).pack(pady=(4, 2))
        label(col, "Simulated Healthcare Tool — Not for Medical Use",
              9, color=C["sub"]).pack(pady=(0, 24))

        frm = card(col)
        frm.pack(ipadx=30, ipady=20)

        label(frm, "Patient Name", 10, bold=True).pack(anchor="w", padx=20, pady=(16,2))
        self._name = entry(frm, width=30)
        self._name.pack(padx=20, pady=(0,8), ipady=5)

        label(frm, "Age (optional)", 10, bold=True).pack(anchor="w", padx=20, pady=(4,2))
        self._age = entry(frm, width=30)
        self._age.pack(padx=20, pady=(0,8), ipady=5)

        label(frm, "Gender", 10, bold=True).pack(anchor="w", padx=20, pady=(4,2))
        self._gender = ttk.Combobox(frm, values=["Prefer not to say", "Male", "Female", "Other"],
                                    state="readonly", width=27)
        self._gender.current(0)
        self._gender.pack(padx=20, pady=(0,16))

        btn(frm, "Continue  →", self._login, width=30).pack(padx=20, pady=(0,16))

        label(col, "⚠ This tool is for educational/demo purposes only.",
              8, color=C["red"]).pack(pady=(12,0))

        self._name.bind("<Return>", lambda e: self._login())

    def _login(self):
        name = self._name.get().strip()
        if not name:
            messagebox.showwarning("Name Required", "Please enter a patient name to continue.")
            return
        try:
            age = int(self._age.get().strip()) if self._age.get().strip() else None
        except ValueError:
            age = None
        gender = self._gender.get()
        pid = self.app.db.get_or_create_patient(name, age, gender)
        self.app.on_login_success(pid, name)


# ---------------------------------------------------------------------------
# Home Page
# ---------------------------------------------------------------------------

class HomePage(tk.Frame):
    def __init__(self, parent, app: EyeHealthApp):
        super().__init__(parent, bg=C["bg"])
        self.app = app

    def on_show(self):
        for w in self.winfo_children():
            w.destroy()
        self._build()

    def _build(self):
        # Header
        hdr = tk.Frame(self, bg=C["primary"], padx=30, pady=18)
        hdr.pack(fill="x")
        label(hdr, f"Welcome, {self.app.current_patient_name}", 18, bold=True,
              color="white").pack(anchor="w")
        label(hdr, datetime.now().strftime("%A, %d %B %Y"), 10,
              color="#A8D4E0").pack(anchor="w")

        body = tk.Frame(self, bg=C["bg"], padx=30, pady=20)
        body.pack(fill="both", expand=True)

        label(body, "Quick Actions", 13, bold=True, color=C["primary"]).pack(anchor="w", pady=(0,12))

        tiles_row = tk.Frame(body, bg=C["bg"])
        tiles_row.pack(fill="x")

        tiles = [
            ("👁", "Eye Test",  "Snellen chart\nacuity assessment", self.app._nav_eyetest, C["primary"]),
            ("🩺", "Diagnose", "Symptom-based\ndiagnosis", self.app._nav_diagnosis, "#27788A"),
            ("📋", "Reports",  "View & export\npast records",   self.app._nav_reports, "#1E6E5A"),
            ("ℹ️", "About",    "System info\n& disclaimer",     self.app._nav_about,   "#6B5A8A"),
        ]

        for icon, title, sub, cmd, color in tiles:
            c = card(tiles_row)
            c.pack(side="left", padx=8, pady=4, ipadx=16, ipady=12, expand=True, fill="x")
            tk.Label(c, text=icon, font=("Helvetica", 26), bg=C["card"]).pack(pady=(12,4))
            label(c, title, 12, bold=True, color=color).pack()
            label(c, sub, 9, color=C["sub"]).pack(pady=(2,8))
            btn(c, "Open", cmd, width=12, bg=color).pack(pady=(0,12))

        # Latest record
        separator(body).pack(fill="x", pady=16)
        label(body, "Last Test Result", 12, bold=True, color=C["primary"]).pack(anchor="w")
        rec = self.app.db.get_latest_eye_test(self.app.current_patient_id)
        if rec:
            row = tk.Frame(body, bg=C["bg"])
            row.pack(fill="x", pady=6)
            for eye_label, eye_data in [("Left Eye", rec["left"]), ("Right Eye", rec["right"])]:
                c = card(row)
                c.pack(side="left", padx=6, ipadx=14, ipady=8, expand=True, fill="x")
                label(c, eye_label, 11, bold=True, color=C["primary"]).pack(anchor="w", padx=10, pady=(8,2))
                label(c, f"Acuity: {eye_data['acuity']}", 10, color=C["text"]).pack(anchor="w", padx=10)
                label(c, f"Power : {eye_data['power']:.2f}D", 10, color=C["text"]).pack(anchor="w", padx=10)
                severity_badge(c, eye_data['severity']).pack(anchor="w", padx=10, pady=(4,8))
            label(body, f"Tested: {rec['date']}", 8, color=C["sub"]).pack(anchor="w", pady=(2,0))
        else:
            label(body, "No previous test on record. Start an Eye Test to begin.", 10,
                  color=C["sub"]).pack(anchor="w", pady=6)


# ---------------------------------------------------------------------------
# Eye Test Page  (Snellen-style adaptive chart)
# ---------------------------------------------------------------------------

class EyeTestPage(tk.Frame):
    def __init__(self, parent, app: EyeHealthApp):
        super().__init__(parent, bg=C["bg"])
        self.app = app
        self._reset_state()
        self._build_shell()

    def _reset_state(self):
        self.phase = "intro"          # intro | left | right | done
        self.current_eye = "left"
        self.row_index = 0            # current SNELLEN_ROWS index being tested
        self.best_passed = -1         # best index passed for current eye
        self.fails_in_row = 0
        self.left_result_idx = -1
        self.right_result_idx = -1
        self.prev_left = None
        self.prev_right = None
        self.current_numbers = ""

    def on_show(self):
        self._reset_state()
        self._show_intro()

    def _build_shell(self):
        # Header bar
        self._header = tk.Frame(self, bg=C["primary"], padx=30, pady=14)
        self._header.pack(fill="x")
        label(self._header, "👁  Eye Test", 16, bold=True, color="white").pack(anchor="w")
        label(self._header, "Snellen-style visual acuity assessment", 10,
              color="#A8D4E0").pack(anchor="w")

        self._body = tk.Frame(self, bg=C["bg"], padx=40, pady=20)
        self._body.pack(fill="both", expand=True)

    def _clear_body(self):
        for w in self._body.winfo_children():
            w.destroy()

    # --- Phases ---

    def _show_intro(self):
        self._clear_body()

        c = card(self._body)
        c.pack(expand=True, fill="both", ipadx=30, ipady=20)

        label(c, "Before we begin", 14, bold=True, color=C["primary"]).pack(pady=(20,8))
        label(c, "This test simulates a Snellen visual acuity chart.\n"
                 "Numbers will be displayed at decreasing sizes.\n"
                 "Please close one eye as instructed and read the numbers aloud or in your head.\n"
                 "Click 'Yes' if you can read them clearly, 'No' if you cannot.",
              10, color=C["text"]).pack(padx=30, pady=8)

        separator(c).pack(fill="x", padx=30, pady=10)
        label(c, "Do you have a previously measured eye power?", 11, bold=True).pack(pady=(8,4))

        row = tk.Frame(c, bg=C["card"])
        row.pack(pady=4)

        btn(row, "Yes — Enter It", self._ask_prev_power, width=16, bg=C["accent"]).pack(side="left", padx=8)
        btn(row, "No — Start Test", self._start_left_eye, width=16).pack(side="left", padx=8)

    def _ask_prev_power(self):
        self._clear_body()
        c = card(self._body)
        c.pack(expand=True, fill="both", ipadx=30, ipady=20)

        label(c, "Enter Previous Power (Diopters)", 14, bold=True, color=C["primary"]).pack(pady=(20,8))
        label(c, "Leave blank if no previous prescription for that eye.", 10, color=C["sub"]).pack()

        frm = tk.Frame(c, bg=C["card"])
        frm.pack(pady=16)

        label(frm, "Left Eye (D):", 11).grid(row=0, column=0, padx=10, pady=6, sticky="e")
        self._prev_l_entry = entry(frm, width=10)
        self._prev_l_entry.grid(row=0, column=1, padx=10, pady=6)

        label(frm, "Right Eye (D):", 11).grid(row=1, column=0, padx=10, pady=6, sticky="e")
        self._prev_r_entry = entry(frm, width=10)
        self._prev_r_entry.grid(row=1, column=1, padx=10, pady=6)

        btn(c, "Save & Start Test", self._save_prev_and_start, width=20).pack(pady=12)

    def _save_prev_and_start(self):
        try:
            lv = self._prev_l_entry.get().strip()
            rv = self._prev_r_entry.get().strip()
            self.prev_left  = float(lv) if lv else None
            self.prev_right = float(rv) if rv else None
        except ValueError:
            messagebox.showwarning("Input Error", "Please enter valid numbers (e.g. 1.5) or leave blank.")
            return
        self._start_left_eye()

    def _start_left_eye(self):
        self.current_eye = "left"
        self.row_index = 0
        self.best_passed = -1
        self.fails_in_row = 0
        self._show_chart_row()

    def _show_chart_row(self):
        self._clear_body()

        eye_label = "LEFT Eye" if self.current_eye == "left" else "RIGHT Eye"
        eye_icon  = "👁‍🗨" if self.current_eye == "left" else "👁"
        font_size, acuity, _ = SNELLEN_ROWS[self.row_index]

        # Progress bar simulation
        progress = tk.Frame(self._body, bg=C["bg"])
        progress.pack(fill="x", pady=(0,8))
        label(progress, f"{eye_icon}  Testing: {eye_label}", 12, bold=True,
              color=C["primary"]).pack(side="left")
        label(progress, f"Line {self.row_index + 1} of {len(SNELLEN_ROWS)}  |  {acuity}",
              10, color=C["sub"]).pack(side="right")

        c = card(self._body)
        c.pack(expand=True, fill="both", ipadx=20, ipady=10)

        instruction = ("CLOSE your RIGHT eye. Read with LEFT eye only."
                       if self.current_eye == "left"
                       else "CLOSE your LEFT eye. Read with RIGHT eye only.")
        label(c, instruction, 11, bold=True, color=C["accent"]).pack(pady=(16,4))

        # Generate random digit string
        digits = random.sample(range(10), 5)
        self.current_numbers = ''.join(map(str, digits))

        # Display with Snellen font size
        chart_frame = tk.Frame(c, bg=C["card"], pady=20)
        chart_frame.pack(expand=True, fill="both")
        tk.Label(chart_frame, text=self.current_numbers,
                 font=("Courier", font_size, "bold"),
                 bg=C["card"], fg=C["text"]).pack(expand=True)

        label(c, "Can you read all the numbers clearly?", 11).pack(pady=(8,4))

        btn_row = tk.Frame(c, bg=C["card"])
        btn_row.pack(pady=12)
        btn(btn_row, "✓  Yes, clearly", lambda: self._respond(True),
            width=16, bg=C["green"]).pack(side="left", padx=10)
        btn(btn_row, "✗  No, cannot read", lambda: self._respond(False),
            width=16, bg=C["red"]).pack(side="left", padx=10)

    def _respond(self, can_read: bool):
        if can_read:
            self.best_passed = self.row_index
            self.fails_in_row = 0
            next_idx = self.row_index + 1
            if next_idx >= len(SNELLEN_ROWS):
                # Passed all rows
                self._finish_eye()
            else:
                self.row_index = next_idx
                self._show_chart_row()
        else:
            self.fails_in_row += 1
            if self.fails_in_row >= 2:
                # Failed twice — stop this eye
                self._finish_eye()
            else:
                # One more attempt at same row
                self._show_chart_row()

    def _finish_eye(self):
        if self.best_passed < 0:
            self.best_passed = 0  # Couldn't pass even the first row

        if self.current_eye == "left":
            self.left_result_idx = self.best_passed
            # Switch to right eye
            self.current_eye = "right"
            self.row_index = 0
            self.best_passed = -1
            self.fails_in_row = 0
            self._show_switch_eye_screen()
        else:
            self.right_result_idx = self.best_passed
            self._show_results()

    def _show_switch_eye_screen(self):
        self._clear_body()
        c = card(self._body)
        c.pack(expand=True, fill="both", ipadx=30, ipady=20)

        label(c, "Left Eye — Complete ✓", 14, bold=True, color=C["green"]).pack(pady=(20,8))
        label(c, "Now let's test your RIGHT eye.\nPlease close your LEFT eye.", 11).pack()

        btn(c, "Start Right Eye Test  →", self._show_chart_row, width=22).pack(pady=20)

    def _show_results(self):
        self._clear_body()

        # Build result dict
        result = self.app.engine.evaluate_snellen_result(
            self.left_result_idx, self.right_result_idx,
            self.prev_left, self.prev_right
        )

        # Save to DB
        self.app.db.save_eye_test(
            self.app.current_patient_id, result,
            self.prev_left, self.prev_right
        )

        # Build report for session
        report = {
            "type": "Eye Test (Snellen)",
            "findings": {
                "Left Acuity":       result["left"]["acuity"],
                "Left Est. Power":   f"{result['left']['estimated_power']:.2f}D",
                "Left Severity":     result["left"]["severity"],
                "Left Trend":        result["left"]["trend"],
                "Right Acuity":      result["right"]["acuity"],
                "Right Est. Power":  f"{result['right']['estimated_power']:.2f}D",
                "Right Severity":    result["right"]["severity"],
                "Right Trend":       result["right"]["trend"],
            },
            "treatment": (
                "Both eyes within normal range. Continue regular eye check-ups."
                if result["left"]["severity"] == "Normal" and result["right"]["severity"] == "Normal"
                else "Consult an ophthalmologist for a comprehensive refraction assessment and prescription."
            )
        }
        self.app.save_and_set_report(report)

        # Display results
        label(self._body, "Test Complete — Results", 14, bold=True, color=C["primary"]).pack(pady=(0,12))

        for eye, eye_label in [("left", "Left Eye"), ("right", "Right Eye")]:
            r = result[eye]
            c = card(self._body)
            c.pack(fill="x", pady=6, ipadx=16, ipady=8)
            header_row = tk.Frame(c, bg=C["card"])
            header_row.pack(fill="x", padx=12, pady=(10,4))
            label(header_row, eye_label, 12, bold=True, color=C["primary"]).pack(side="left")
            severity_badge(header_row, r["severity"]).pack(side="right")

            info_row = tk.Frame(c, bg=C["card"])
            info_row.pack(fill="x", padx=12, pady=4)
            for k, v in [("Visual Acuity", r["acuity"]),
                         ("Estimated Power", f"{r['estimated_power']:.2f}D"),
                         ("Trend vs Previous", r["trend"])]:
                label(info_row, f"{k}:", 10, bold=True).pack(side="left", padx=(0,4))
                label(info_row, v, 10).pack(side="left", padx=(0,20))

        separator(self._body).pack(fill="x", pady=12)
        label(self._body, report["treatment"], 10, color=C["sub"]).pack(anchor="w")

        btn_row = tk.Frame(self._body, bg=C["bg"])
        btn_row.pack(pady=12)
        btn(btn_row, "📄 Export Report", self._export_report, width=16).pack(side="left", padx=8)
        btn(btn_row, "🔄 Retest", self.on_show, width=12, bg=C["accent"]).pack(side="left", padx=8)
        btn(btn_row, "🏠 Home", self.app._nav_home, width=12, bg=C["sub"]).pack(side="left", padx=8)

    def _export_report(self):
        if self.app.last_report:
            path = ReportGenerator.export_pdf(self.app.current_patient_name, self.app.last_report)
            messagebox.showinfo("Report Saved", f"Report exported to:\n{path}")
            try:
                if sys.platform.startswith("linux"):
                    subprocess.Popen(["xdg-open", os.path.dirname(path)])
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Diagnosis Page
# ---------------------------------------------------------------------------

class DiagnosisPage(tk.Frame):
    def __init__(self, parent, app: EyeHealthApp):
        super().__init__(parent, bg=C["bg"])
        self.app = app
        self._active_section = tk.StringVar(value="")
        self._build()

    def on_show(self):
        pass

    def _build(self):
        hdr = tk.Frame(self, bg=C["primary"], padx=30, pady=14)
        hdr.pack(fill="x")
        label(hdr, "🩺  Diagnosis", 16, bold=True, color="white").pack(anchor="w")
        label(hdr, "Select a category to begin symptom-based assessment", 10,
              color="#A8D4E0").pack(anchor="w")

        # Category selector
        cat_bar = tk.Frame(self, bg=C["border"], pady=2)
        cat_bar.pack(fill="x")

        self._tab_frame = tk.Frame(cat_bar, bg=C["card"])
        self._tab_frame.pack(fill="x", padx=0)

        self._sections: dict[str, tk.Frame] = {}
        self._tab_buttons: dict[str, tk.Button] = {}

        sections = [
            ("irritation",  "👁 Irritation",    self._build_irritation),
            ("redeye",      "🔴 Red Eye",        self._build_red_eye),
            ("swelling",    "💧 Swelling",       self._build_swelling),
            ("double",      "👀 Double Vision",  self._build_double_vision),
            ("color",       "🌈 Color Blindness",self._build_color_blindness),
        ]

        for key, label_text, builder in sections:
            b = tk.Button(self._tab_frame, text=label_text,
                          command=lambda k=key: self._switch_section(k),
                          bg=C["card"], fg=C["sub"],
                          relief="flat", bd=0, padx=16, pady=10,
                          font=("Helvetica", 10), cursor="hand2")
            b.pack(side="left")
            self._tab_buttons[key] = b

        self._content_area = tk.Frame(self, bg=C["bg"], padx=30, pady=16)
        self._content_area.pack(fill="both", expand=True)

        # Build all section frames (hidden initially)
        for key, _, builder in sections:
            frm = tk.Frame(self._content_area, bg=C["bg"])
            builder(frm)
            self._sections[key] = frm

        self._switch_section("irritation")

    def _switch_section(self, key: str):
        for k, frm in self._sections.items():
            frm.pack_forget()
        self._sections[key].pack(fill="both", expand=True)
        for k, b in self._tab_buttons.items():
            b.configure(bg=C["primary"] if k == key else C["card"],
                        fg="white" if k == key else C["sub"])

    # --- Irritation ---
    def _build_irritation(self, parent):
        label(parent, "Irritation / Dry Eye Symptoms", 13, bold=True,
              color=C["primary"]).pack(anchor="w", pady=(0,10))

        c = card(parent)
        c.pack(fill="x", ipadx=20, ipady=10)

        label(c, "Select all symptoms you are experiencing:", 11).pack(anchor="w", padx=16, pady=(12,6))

        self._irr_dry   = tk.BooleanVar()
        self._irr_water = tk.BooleanVar()
        self._irr_pain  = tk.BooleanVar()
        self._irr_itch  = tk.BooleanVar()

        for text, var in [
            ("Dry / gritty sensation", self._irr_dry),
            ("Excessive watering / tearing", self._irr_water),
            ("Eye pain or aching", self._irr_pain),
            ("Itching or burning", self._irr_itch),
        ]:
            tk.Checkbutton(c, text=text, variable=var,
                           bg=C["card"], fg=C["text"],
                           font=("Helvetica", 11),
                           activebackground=C["card"],
                           selectcolor=C["accent"]).pack(anchor="w", padx=24, pady=3)

        btn(c, "Get Diagnosis", self._diagnose_irritation, width=18).pack(pady=14, padx=20)

        self._irr_result = tk.Frame(parent, bg=C["bg"])
        self._irr_result.pack(fill="x", pady=8)

    def _diagnose_irritation(self):
        result = self.app.engine.diagnose_irritation(
            self._irr_dry.get(), self._irr_water.get(),
            self._irr_pain.get(), self._irr_itch.get()
        )
        report = {
            "type": "Irritation Diagnosis",
            "findings": {
                "Condition":   result["condition"],
                "Severity":    result["severity"],
                "Urgency":     result["urgency"],
                "Symptom Code":result["symptom_code"],
            },
            "treatment": result["treatment"]
        }
        self.app.save_and_set_report(report)
        self._show_result_card(self._irr_result, result["condition"],
                               result["severity"], result["treatment"], result["urgency"])

    # --- Red Eye ---
    def _build_red_eye(self, parent):
        label(parent, "Red Eye Assessment", 13, bold=True, color=C["primary"]).pack(anchor="w", pady=(0,10))

        c = card(parent)
        c.pack(fill="x", ipadx=20, ipady=10)

        label(c, "Check all that apply:", 11).pack(anchor="w", padx=16, pady=(12,6))

        self._re_vars = {}
        flags_labels = [
            ("pain",           "Eye pain or aching"),
            ("discharge",      "Discharge (pus or sticky secretion)"),
            ("itching",        "Itching"),
            ("vision_blur",    "Blurred vision"),
            ("light_sensitive","Sensitivity to light (photophobia)"),
            ("injury",         "Recent eye injury or trauma"),
        ]
        for key, text in flags_labels:
            v = tk.BooleanVar()
            self._re_vars[key] = v
            tk.Checkbutton(c, text=text, variable=v, bg=C["card"], fg=C["text"],
                           font=("Helvetica", 11), activebackground=C["card"],
                           selectcolor=C["accent"]).pack(anchor="w", padx=24, pady=3)

        btn(c, "Diagnose", self._diagnose_red_eye, width=18).pack(pady=14, padx=20)
        self._re_result = tk.Frame(parent, bg=C["bg"])
        self._re_result.pack(fill="x", pady=8)

    def _diagnose_red_eye(self):
        flags = {k for k, v in self._re_vars.items() if v.get()}
        result = self.app.engine.diagnose_red_eye(flags)
        report = {
            "type": "Red Eye Diagnosis",
            "findings": {
                "Condition": result["condition"],
                "Severity":  result["severity"],
                "Urgency":   result["urgency"],
                "Flags":     ", ".join(flags) or "None selected",
            },
            "treatment": result["treatment"]
        }
        self.app.save_and_set_report(report)
        self._show_result_card(self._re_result, result["condition"],
                               result["severity"], result["treatment"], result["urgency"])

    # --- Swelling ---
    def _build_swelling(self, parent):
        label(parent, "Swelling / Muscle Growth — Condition Look-up", 13,
              bold=True, color=C["primary"]).pack(anchor="w", pady=(0,10))

        c = card(parent)
        c.pack(fill="x", ipadx=20, ipady=10)

        label(c, "Select the closest matching condition:", 11).pack(anchor="w", padx=16, pady=(12,6))

        self._sw_var = tk.StringVar()
        conditions = list(CONDITION_TREATMENTS.keys())
        cb = ttk.Combobox(c, textvariable=self._sw_var, values=conditions,
                          state="readonly", width=40, font=("Helvetica", 11))
        cb.pack(padx=16, pady=8)
        cb.current(0)

        btn(c, "Get Treatment Plan", self._diagnose_swelling, width=20).pack(pady=12, padx=16)
        self._sw_result = tk.Frame(parent, bg=C["bg"])
        self._sw_result.pack(fill="x", pady=8)

    def _diagnose_swelling(self):
        result = self.app.engine.diagnose_condition(self._sw_var.get())
        report = {
            "type": "Condition Look-up",
            "findings": {
                "Condition":   result.get("condition", ""),
                "Description": result.get("description", ""),
                "Severity":    result.get("severity", ""),
                "Urgency":     result.get("urgency", ""),
            },
            "treatment": result.get("treatment", "")
        }
        self.app.save_and_set_report(report)
        self._show_result_card(self._sw_result,
                               result.get("condition",""),
                               result.get("severity",""),
                               result.get("treatment",""),
                               result.get("urgency",""))

    # --- Double Vision ---
    def _build_double_vision(self, parent):
        label(parent, "Double Vision (Diplopia) — Condition Lookup", 13,
              bold=True, color=C["primary"]).pack(anchor="w", pady=(0,10))

        c = card(parent)
        c.pack(fill="x", ipadx=20, ipady=10)
        label(c, "Select suspected cause:", 11).pack(anchor="w", padx=16, pady=(12,6))

        self._dv_var = tk.StringVar()
        conditions = ["strabismus", "cranial nerve palsy", "myasthenia gravis", "ischemic stroke",
                      "thyroid eye disease", "orbital myositis", "orbital tumor"]
        cb = ttk.Combobox(c, textvariable=self._dv_var, values=conditions,
                          state="readonly", width=40, font=("Helvetica", 11))
        cb.pack(padx=16, pady=8)
        cb.current(0)
        btn(c, "Get Diagnosis", self._diagnose_dv, width=20).pack(pady=12, padx=16)

        self._dv_result = tk.Frame(parent, bg=C["bg"])
        self._dv_result.pack(fill="x", pady=8)

    def _diagnose_dv(self):
        result = self.app.engine.diagnose_condition(self._dv_var.get())
        report = {
            "type": "Double Vision Diagnosis",
            "findings": {
                "Condition": result.get("condition",""),
                "Severity":  result.get("severity",""),
                "Urgency":   result.get("urgency",""),
            },
            "treatment": result.get("treatment","")
        }
        self.app.save_and_set_report(report)
        self._show_result_card(self._dv_result,
                               result.get("condition",""),
                               result.get("severity",""),
                               result.get("treatment",""),
                               result.get("urgency",""))

    # --- Color Blindness ---
    def _build_color_blindness(self, parent):
        label(parent, "Color Vision Assessment", 13, bold=True,
              color=C["primary"]).pack(anchor="w", pady=(0,10))

        row = tk.Frame(parent, bg=C["bg"])
        row.pack(fill="x")

        # Ishihara simulation
        c1 = card(row)
        c1.pack(side="left", fill="both", expand=True, padx=(0,8), ipadx=14, ipady=10)
        label(c1, "Simulated Ishihara Plates", 12, bold=True, color=C["primary"]).pack(pady=(12,4))
        label(c1, "Answer what number you see in each plate:", 10).pack()
        self._ishihara_answers: list[tk.Entry] = []
        self._ishi_vars: list[tk.StringVar] = []

        for plate in ISHIHARA_PLATES:
            pf = tk.Frame(c1, bg=C["card"])
            pf.pack(fill="x", padx=16, pady=4)
            # Simulate plate with coloured label
            plate_lbl = tk.Label(pf, text=plate["display"], font=("Courier", 22, "bold"),
                                 bg="#2E8B57", fg="#DEB887", width=4, height=1,
                                 relief="solid", bd=2)
            plate_lbl.pack(side="left", padx=(0,10))
            v = tk.StringVar()
            e = entry(pf, textvariable=v, width=6)
            e.pack(side="left")
            self._ishi_vars.append(v)

        btn(c1, "Score Ishihara Test", self._score_ishihara, width=20).pack(pady=12)
        self._ishi_result = tk.Frame(parent, bg=C["bg"])
        self._ishi_result.pack(fill="x", pady=8)

        # Color arrangement test
        c2 = card(row)
        c2.pack(side="left", fill="both", expand=True, padx=(8,0), ipadx=14, ipady=10)
        label(c2, "Color Arrangement Test", 12, bold=True, color=C["primary"]).pack(pady=(12,4))
        label(c2, "Click colors in correct spectral order\n(Red → Violet)", 10).pack(pady=4)

        self._color_order: list[str] = []
        self._color_btn_frame = tk.Frame(c2, bg=C["card"])
        self._color_btn_frame.pack(pady=8)
        self._reset_color_test(c2)

    def _reset_color_test(self, parent_card):
        for w in self._color_btn_frame.winfo_children():
            w.destroy()
        self._color_order.clear()
        shuffled = COLOR_ARRANGEMENT[:]
        random.shuffle(shuffled)
        self._color_correct = COLOR_ARRANGEMENT[:]

        COLOR_HEX = {
            "Red":"#E74C3C","Orange":"#E67E22","Yellow":"#F1C40F",
            "Green":"#27AE60","Blue":"#2980B9","Indigo":"#4B0082","Violet":"#8E44AD"
        }
        for color in shuffled:
            tk.Button(self._color_btn_frame, text=color, width=8,
                      bg=COLOR_HEX.get(color,"#999"), fg="white",
                      relief="flat", font=("Helvetica", 9, "bold"),
                      command=lambda c=color: self._select_color(c),
                      cursor="hand2").pack(side="left", padx=3, pady=4)

        btn(parent_card, "Check Order", self._check_color_order, width=18,
            bg=C["accent"]).pack(pady=8)

    def _select_color(self, color: str):
        self._color_order.append(color)

    def _check_color_order(self):
        if len(self._color_order) < len(self._color_correct):
            messagebox.showwarning("Incomplete", f"Please click all {len(self._color_correct)} colors first.")
            return
        used = self._color_order[:len(self._color_correct)]
        if used == self._color_correct:
            messagebox.showinfo("✓ Correct", "Colors arranged in correct spectral order. "
                                              "Normal color vision indicated.")
        else:
            messagebox.showinfo("✗ Incorrect",
                                f"Incorrect order.\nExpected: {' → '.join(self._color_correct)}\n"
                                f"Your order: {' → '.join(used)}\n\n"
                                "Color arrangement difficulty may indicate color vision deficiency.")
        self._color_order.clear()

    def _score_ishihara(self):
        correct = 0
        for i, v in enumerate(self._ishi_vars):
            if v.get().strip() == ISHIHARA_PLATES[i]["answer"]:
                correct += 1
        result = score_color_blindness(correct, len(ISHIHARA_PLATES))
        report = {
            "type": "Color Blindness Test",
            "findings": {
                "Correct Plates": f"{correct} / {len(ISHIHARA_PLATES)}",
                "Result":         result["result"],
                "Severity":       result["severity"],
            },
            "treatment": result["recommendation"]
        }
        self.app.save_and_set_report(report)
        self._show_result_card(self._ishi_result, result["result"],
                               result["severity"], result["recommendation"], "Routine")

    # --- Shared result display ---
    def _show_result_card(self, container: tk.Frame, condition: str,
                          severity: str, treatment: str, urgency: str):
        for w in container.winfo_children():
            w.destroy()

        c = card(container)
        c.pack(fill="x", ipadx=16, ipady=12, pady=6)

        header = tk.Frame(c, bg=C["card"])
        header.pack(fill="x", padx=16, pady=(12,4))
        label(header, condition, 13, bold=True, color=C["primary"]).pack(side="left")
        severity_badge(header, severity).pack(side="right")

        separator(c).pack(fill="x", padx=16, pady=4)

        label(c, f"Urgency: {urgency}", 10, color=C["sub"]).pack(anchor="w", padx=16)
        label(c, "Recommended Treatment:", 10, bold=True).pack(anchor="w", padx=16, pady=(8,2))
        tk.Label(c, text=treatment, bg=C["card"], fg=C["text"],
                 font=("Helvetica", 10), wraplength=600, justify="left").pack(
                     anchor="w", padx=16, pady=(0,12))

        btn_row = tk.Frame(c, bg=C["card"])
        btn_row.pack(anchor="w", padx=16, pady=(0,12))
        btn(btn_row, "📄 Export Report", self._export_report, width=16).pack(side="left", padx=(0,8))

    def _export_report(self):
        if self.app.last_report:
            path = ReportGenerator.export_pdf(self.app.current_patient_name, self.app.last_report)
            messagebox.showinfo("Report Saved", f"PDF report exported to:\n{path}")


# ---------------------------------------------------------------------------
# Reports Page
# ---------------------------------------------------------------------------

class ReportsPage(tk.Frame):
    def __init__(self, parent, app: EyeHealthApp):
        super().__init__(parent, bg=C["bg"])
        self.app = app
        self._build_shell()

    def _build_shell(self):
        hdr = tk.Frame(self, bg=C["primary"], padx=30, pady=14)
        hdr.pack(fill="x")
        label(hdr, "📋  Reports & History", 16, bold=True, color="white").pack(anchor="w")
        label(hdr, "Past diagnostic sessions and test records", 10, color="#A8D4E0").pack(anchor="w")

        ctrl = tk.Frame(self, bg=C["card"], padx=20, pady=10)
        ctrl.pack(fill="x")
        btn(ctrl, "🔄 Refresh", self.on_show, width=12).pack(side="left")
        btn(ctrl, "📄 Export Last Report as PDF",
            self._export_last, width=24, bg=C["accent"]).pack(side="left", padx=10)

        self._list_area = tk.Frame(self, bg=C["bg"], padx=24, pady=16)
        self._list_area.pack(fill="both", expand=True)

    def on_show(self):
        for w in self._list_area.winfo_children():
            w.destroy()
        self._populate()

    def _populate(self):
        history = self.app.db.get_patient_history(self.app.current_patient_id)
        if not history:
            label(self._list_area, "No records found. Complete a test or diagnosis to see results here.",
                  10, color=C["sub"]).pack(pady=20)
            return

        for rec in history:
            c = card(self._list_area)
            c.pack(fill="x", pady=5, ipadx=14, ipady=8)

            hrow = tk.Frame(c, bg=C["card"])
            hrow.pack(fill="x", padx=12, pady=(8,2))
            label(hrow, rec["type"], 11, bold=True, color=C["primary"]).pack(side="left")
            label(hrow, rec["date"], 9, color=C["sub"]).pack(side="right")

            findings = rec.get("findings", {})
            for k, v in list(findings.items())[:4]:
                frow = tk.Frame(c, bg=C["card"])
                frow.pack(fill="x", padx=24, pady=1)
                label(frow, f"{k}:", 9, bold=True, color=C["sub"]).pack(side="left")
                label(frow, str(v), 9).pack(side="left", padx=6)

            if len(findings) > 4:
                label(c, f"  + {len(findings)-4} more fields...", 8, color=C["sub"]).pack(anchor="w", padx=24)

    def _export_last(self):
        if not self.app.last_report:
            messagebox.showinfo("No Report", "No report available to export. "
                                              "Complete a test or diagnosis first.")
            return
        path = ReportGenerator.export_pdf(self.app.current_patient_name, self.app.last_report)
        messagebox.showinfo("Exported", f"PDF saved:\n{path}")


# ---------------------------------------------------------------------------
# About Page
# ---------------------------------------------------------------------------

class AboutPage(tk.Frame):
    def __init__(self, parent, app: EyeHealthApp):
        super().__init__(parent, bg=C["bg"])
        self.app = app
        self._build()

    def _build(self):
        hdr = tk.Frame(self, bg=C["primary"], padx=30, pady=14)
        hdr.pack(fill="x")
        label(hdr, "ℹ️  About This System", 16, bold=True, color="white").pack(anchor="w")

        body = tk.Frame(self, bg=C["bg"], padx=40, pady=24)
        body.pack(fill="both", expand=True)

        c = card(body)
        c.pack(fill="x", ipadx=24, ipady=16)

        label(c, "Eye Health Diagnosis System v2.0", 16, bold=True,
              color=C["primary"]).pack(pady=(16,4))
        label(c, "A simulated ophthalmic diagnostic assistant for educational use.",
              11, color=C["sub"]).pack(pady=(0,16))

        disclaimer = (
            "⚠  IMPORTANT DISCLAIMER\n\n"
            "This application is a SIMULATED diagnostic tool created for academic "
            "and demonstration purposes ONLY.\n\n"
            "• It does NOT provide real medical diagnoses.\n"
            "• It CANNOT replace a licensed ophthalmologist or optometrist.\n"
            "• Results should NOT be used to make any clinical decisions.\n"
            "• Always consult a qualified healthcare professional for eye concerns.\n\n"
            "If you are experiencing severe eye pain, sudden vision loss, or any "
            "eye emergency, please seek IMMEDIATE medical attention."
        )
        tk.Label(c, text=disclaimer, bg="#FFF8E1", fg="#5D4037",
                 font=("Helvetica", 10), justify="left",
                 wraplength=600, padx=16, pady=12,
                 relief="flat", bd=0).pack(padx=16, pady=(0,16), fill="x")

        separator(c).pack(fill="x", padx=16, pady=8)

        features = [
            ("🗄 Patient Database", "SQLite-backed patient records with timestamped sessions"),
            ("👁 Snellen Eye Test", "Adaptive 11-line acuity chart with diopter estimation"),
            ("🩺 Symptom Diagnosis", "Weighted rule engine for 5 condition categories"),
            ("🌈 Color Vision Test", "Simulated Ishihara plates + color arrangement test"),
            ("📄 PDF Reports", "Export formatted diagnostic summaries via ReportLab"),
        ]
        for icon_title, desc in features:
            row = tk.Frame(c, bg=C["card"])
            row.pack(fill="x", padx=16, pady=3)
            label(row, icon_title, 11, bold=True, color=C["primary"]).pack(side="left", padx=(0,12))
            label(row, desc, 10, color=C["sub"]).pack(side="left")

        separator(c).pack(fill="x", padx=16, pady=8)
        label(c, "Built with Python 3.12 · Tkinter · SQLite · ReportLab",
              9, color=C["sub"]).pack(pady=(0,16))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app = EyeHealthApp()
    app.protocol("WM_DELETE_WINDOW", app.on_destroy)
    app.mainloop()