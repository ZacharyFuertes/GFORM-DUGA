import tkinter as tk
from tkinter import ttk, font, messagebox
from PIL import Image, ImageTk
import asyncio
import threading
import random
import logging
import os
import sys
import multiprocessing
import time

# ── Playwright EXE Fix ────────────────────────────────────────────────────────
# Force Playwright to look for browsers in the standard system path 
# instead of inside the temporary PyInstaller folder (_MEIPASS).
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "0"
from datetime import datetime

# ── Import the bot logic directly ──────────────────────────────────────────────
import subprocess
from playwright.async_api import async_playwright
from gform_bot_playwright import (
    MALE_NAMES, FEMALE_NAMES, build_name_pool,
    submit_form, summarize_answers, RunStats, FORM_URL
)
from form_schema import AnswerConfig, analyze, make_picker

# ── Gengar glass palette (see glass.py) ───────────────────────────────────────
import glass

BG        = glass.BG_BASE
CARD      = glass.SURFACE
ACCENT    = glass.NEON
ACCENT2   = glass.NEON_SOFT
SUCCESS   = glass.CYAN
FAIL      = glass.MAGENTA
TEXT      = glass.LAVENDER
MUTED     = glass.MUTED
BORDER    = glass.BORDER
INPUT_BG  = glass.INPUT_BG
INPUT_FG  = glass.INPUT_FG
FONT      = glass.FONT
MONO      = glass.MONO

# ── Redirect logging into the GUI ───────────────────────────────────────────────
class GUILogHandler(logging.Handler):
    def __init__(self, callback):
        super().__init__()
        self.callback = callback

    def emit(self, record):
        msg = self.format(record)
        self.callback(msg)


# ── Async bot runner ─────────────────────────────────────────────────────────────
def install_browsers(on_log):
    """Attempt to install Playwright browsers using the internal driver."""
    try:
        on_log("🌐  Browsers missing. Downloading (first time setup)...")
        from playwright._impl._driver import compute_driver_executable, get_driver_env
        driver_executable, driver_cli = compute_driver_executable()
        # Run the driver directly to install chromium
        subprocess.run(
            [driver_executable, driver_cli, "install", "chromium"], 
            env=get_driver_env(), check=True, capture_output=True, text=True
        )
        on_log("✅  Browsers installed successfully.")
        return True
    except Exception as e:
        on_log(f"❌  Install failed: {e}")
        return False

async def run_bot(count, url, on_log, on_progress, on_done, pick=None):
    name_pool = build_name_pool()
    stats = RunStats()
    success = 0

    async with async_playwright() as p:
        try:
            browser = await p.chromium.launch(headless=True)
        except Exception as e:
            msg = str(e).lower()
            if "executable" in msg or "playwright install" in msg:
                if install_browsers(on_log):
                    try:
                        browser = await p.chromium.launch(headless=True)
                    except Exception as retry_err:
                        on_log(f"❌  Launch failed after install: {retry_err}")
                        on_done(0, count, stats)
                        return
                else:
                    on_done(0, count, stats)
                    return
            else:
                on_log(f"⚠️  Browser launch error: {e}")
                on_done(0, count, stats)
                return

        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )

        for i in range(1, count + 1):
            if not name_pool:
                name_pool = build_name_pool()

            page = await context.new_page()
            try:
                res, data = await submit_form(context, i, count, name_pool, url,
                                              pick=pick)
                
                name = data['name'] or (data.get('reason') or 'no name assigned')
                answers = summarize_answers(data.get('answers') or [])
                icon = "✅" if res else "❌"
                if res:
                    success += 1
                stats.record(res, data.get('name'), data.get('answers'))
                on_log(f"{icon}  [{i}/{count}] {name} → {answers}")
                on_progress(i, count, success, bool(res))

            except Exception as e:
                on_log(f"⚠️  [{i}/{count}] Error: {e}")
                stats.record(False, None, None, error=True)
                on_progress(i, count, success, False)
            finally:
                await page.close()

            await asyncio.sleep(random.uniform(1.0, 3.0))

        await browser.close()

    on_done(success, count, stats)


# ── Ambient background: floating ghostly particles ─────────────────────────────
class AmbientBackground:
    """Slow purple/lavender motes drifting up over the baked backdrop."""

    TINTS = (glass.NEON, glass.LAVENDER, glass.MAGENTA, glass.CYAN,
             glass.PURPLE_RICH)

    def __init__(self, canvas, count=46):
        self.canvas = canvas
        self.count = count
        self.running = False
        self._motes = []

    def start(self):
        if self.running:
            return
        self.running = True
        self.canvas.delete("mote")
        w = self.canvas.winfo_width() or 1400
        h = self.canvas.winfo_height() or 900
        self._motes = []
        for _ in range(self.count):
            x = random.uniform(0, w)
            y = random.uniform(0, h)
            r = random.uniform(1.1, 3.2)
            mote = [x, y, r,
                    random.uniform(0.22, 0.85),      # rise
                    random.uniform(-0.30, 0.30),     # drift
                    random.choice(self.TINTS)]
            mote.append(self.canvas.create_oval(
                x - r, y - r, x + r, y + r, fill=mote[5], outline="",
                tags="mote"))
            self._motes.append(mote)
        self._animate()

    def _animate(self):
        if not self.running:
            return
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        for mote in self._motes:
            mote[0] += mote[4]
            mote[1] -= mote[3]
            if mote[1] < -8:
                mote[1] = h + 8
                mote[0] = random.uniform(0, w)
            if mote[0] < -8:
                mote[0] = w + 8
            elif mote[0] > w + 8:
                mote[0] = -8
            x, y, r = mote[0], mote[1], mote[2]
            self.canvas.coords(mote[6], x - r, y - r, x + r, y + r)
        self.canvas.after(45, self._animate)

    def stop(self):
        self.running = False
        self._motes = []
        try:
            self.canvas.delete("mote")
        except tk.TclError:
            pass


# ── Analyzed data + randomness config (embedded left card) ─────────────────────
class AnswerConfigPanel(glass.GlassPanel):
    """'Analyzed Form Data' card — part of the single window, not a popup.

    Per question the user picks an answer with a radio button instead of
    typing weights. Every row starts on "Random", which stores an empty
    weight string, so nothing picked keeps that question on the global
    setting and an untouched panel still yields AnswerConfig().is_untouched
    (the bot's original random behaviour).

    Selecting an answer stores [0, ..., 100, ..., 0] for that question, i.e.
    that answer is always the one submitted.
    """

    MODES = (
        ("default",  "Default (random)"),
        ("uniform",  "Uniform (equal chance)"),
        ("weighted", "Custom weights"),
    )

    def __init__(self, parent, theme, on_apply=None):
        super().__init__(parent, theme)
        self.on_apply = on_apply
        self.form_info = {}
        self.units = []
        self.reference = []
        self.weight_vars = {}
        self.mode_var = tk.StringVar(value="default")
        self.global_var = tk.StringVar(value="")
        self._build_static()
        self._sync_mode()
        self._render_empty()

    # ── fixed chrome ──
    def _build_static(self):
        body = self.body

        tk.Label(body, text="Analyzed Form Data", bg=CARD, fg=ACCENT2,
                 font=(FONT, 15, "bold")).pack(anchor="w")
        self.summary = tk.Label(body, text="", bg=CARD, fg=MUTED,
                                font=(FONT, 9), justify="left", wraplength=640)
        self.summary.pack(anchor="w", pady=(4, 12))

        # ── global ──
        card = tk.Frame(body, bg=glass.SURFACE_ALT, bd=0,
                        highlightthickness=1,
                        highlightbackground=glass.BORDER_SOFT)
        card.pack(fill="x", pady=(0, 12))
        inner = tk.Frame(card, bg=glass.SURFACE_ALT)
        inner.pack(fill="x", padx=16, pady=14)

        tk.Label(inner, text="GLOBAL DEFAULT", bg=glass.SURFACE_ALT, fg=ACCENT2,
                 font=(FONT, 10, "bold")).pack(anchor="w")

        modes = tk.Frame(inner, bg=glass.SURFACE_ALT)
        modes.pack(anchor="w", pady=(8, 0))
        for value, text in self.MODES:
            tk.Radiobutton(
                modes, text=text, variable=self.mode_var, value=value,
                bg=glass.SURFACE_ALT, fg=TEXT, selectcolor=INPUT_BG, bd=0,
                highlightthickness=0, activebackground=glass.SURFACE_ALT,
                activeforeground=ACCENT2, font=(FONT, 9),
                command=self._sync_mode,
            ).pack(side="left", padx=(0, 16))

        tk.Label(inner,
                 text="Global weights, comma separated, in option order "
                      "(empty = uniform). Per-question picks below override this.",
                 bg=glass.SURFACE_ALT, fg=MUTED, font=(FONT, 8),
                 justify="left", wraplength=640).pack(anchor="w", pady=(8, 0))
        self.global_entry = tk.Entry(
            inner, textvariable=self.global_var, width=60,
            bg=INPUT_BG, fg=INPUT_FG, font=(MONO, 10), relief="flat",
            insertbackground=INPUT_FG, bd=0, highlightthickness=1,
            highlightbackground=glass.BORDER_SOFT, highlightcolor=ACCENT,
        )
        self.global_entry.pack(fill="x", pady=(5, 0))

        # ── per-question list ──
        box = tk.Frame(body, bg=glass.SURFACE_ALT, bd=0,
                       highlightthickness=1,
                       highlightbackground=glass.BORDER_SOFT)
        box.pack(fill="both", expand=True)

        head = tk.Frame(box, bg=glass.SURFACE_ALT)
        head.pack(fill="x", padx=14, pady=(10, 0))
        tk.Label(head, text="PER-QUESTION PICKS", bg=glass.SURFACE_ALT,
                 fg=ACCENT2, font=(FONT, 10, "bold")).pack(anchor="w")
        tk.Label(head,
                 text="Pick the answer the bot should submit. "
                      "'Random' (default) leaves the question on the global setting.",
                 bg=glass.SURFACE_ALT, fg=MUTED, font=(FONT, 8),
                 justify="left", wraplength=640).pack(anchor="w", pady=(2, 0))

        body2 = tk.Frame(box, bg=glass.SURFACE_ALT)
        body2.pack(fill="both", expand=True, padx=8, pady=(8, 10))

        self.canvas = tk.Canvas(body2, bg=glass.SURFACE_ALT,
                                highlightthickness=0, bd=0)
        scroll = ttk.Scrollbar(body2, orient="vertical",
                               command=self.canvas.yview)
        self.rows = tk.Frame(self.canvas, bg=glass.SURFACE_ALT)
        self.rows.bind("<Configure>", lambda e: self.canvas.configure(
            scrollregion=self.canvas.bbox("all")))
        holder = self.canvas.create_window((0, 0), window=self.rows, anchor="nw",
                                           tags="rows")
        self.canvas.configure(yscrollcommand=scroll.set)
        self.canvas.bind("<Configure>",
                         lambda e: self.canvas.itemconfig(holder, width=e.width))
        self.canvas.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        self._bind_wheel(self.canvas)

        # ── actions ──
        actions = tk.Frame(body, bg=CARD)
        actions.pack(fill="x", pady=(12, 0))
        btn = dict(bg=INPUT_BG, fg=INPUT_FG, font=(FONT, 10, "bold"),
                   relief="flat", bd=0, padx=16, pady=7, cursor="hand2",
                   activebackground=ACCENT, activeforeground="#12061F",
                   highlightthickness=0)
        tk.Button(actions, text="Reset to random",
                  command=self._reset, **btn).pack(side="left")
        tk.Button(actions, text="Apply", command=self._save,
                  **btn).pack(side="right")

    def _render_empty(self):
        if getattr(self, "_empty_label", None) is not None:
            self._empty_label.pack_forget()
        if self.units:
            return
        self._empty_label = tk.Label(
            self.rows, bg=glass.SURFACE_ALT, fg=MUTED, font=(FONT, 10),
            justify="left", wraplength=620, pady=26,
            text="No form analyzed yet.\n\n"
                 "Enter a Google Form URL in the sidebar and press "
                 "ANALYZE URL to list its questions here.")
        self._empty_label.pack(fill="x", padx=14, pady=10)

    def _radio(self, parent, text, variable, value, muted=False):
        return tk.Radiobutton(
            parent, text=text, variable=variable, value=value,
            bg=CARD, fg=(MUTED if muted else TEXT),
            selectcolor=glass.mix(CARD, ACCENT, 0.5), bd=0,
            highlightthickness=0, activebackground=CARD,
            activeforeground=ACCENT2, indicatoron=True,
            font=(FONT, 9), padx=5, pady=1, cursor="hand2")

    # ── filling it from an analysis ──
    def load(self, form_info, config=None):
        self.form_info = form_info or {}
        self.units = self.form_info.get("units") or []
        self.reference = self.form_info.get("reference_options") or []
        config = config or AnswerConfig()

        self.mode_var.set(config.mode)
        self.global_var.set(", ".join(str(w) for w in config.weights))

        for child in self.rows.winfo_children():
            child.destroy()
        self._empty_label = None

        self.weight_vars = {}
        for unit in self.units:
            override = config.overrides.get(unit["index"])
            self.weight_vars[unit["index"]] = tk.StringVar(
                value=", ".join(str(w) for w in override) if override else "")

        for unit in self.units:
            # Bind each fresh row subtree; self.rows keeps its single
            # binding from _build_static (a panel is reused across loads).
            self._bind_wheel(self._build_row(unit))

        if self.units:
            title = self.form_info.get("title") or "Untitled form"
            questions = self.form_info.get("questions") or []
            self.summary.configure(
                text=f"{title}\n{len(self.units)} answerable of "
                     f"{len(questions)} questions  •  option order: "
                     f"{', '.join(self.reference) or 'n/a'}")
        else:
            self.summary.configure(text="")
        self._render_empty()
        return self


    # ── rows ──
    def _build_row(self, unit):
        row = tk.Frame(self.rows, bg=CARD, bd=0,
                       highlightthickness=1,
                       highlightbackground=glass.BORDER_SOFT)
        row.pack(fill="x", padx=8, pady=(0, 6))

        idx = unit["index"]
        label = " ".join(str(unit.get("label") or unit.get("question") or "").split())
        options = list(unit.get("options") or [])

        top = tk.Frame(row, bg=CARD)
        top.pack(fill="x", padx=10, pady=(7, 0))
        tk.Label(top, text=f"#{idx}", bg=CARD, fg=ACCENT,
                 font=(MONO, 9, "bold"), width=4, anchor="w").pack(side="left")
        tk.Label(top, text=label, bg=CARD, fg=TEXT, font=(FONT, 9),
                 anchor="w", wraplength=620, justify="left").pack(side="left")

        picks = tk.Frame(row, bg=CARD)
        picks.pack(fill="x", padx=(44, 10), pady=(3, 8))

        var = self.weight_vars[idx]
        # "Random" stores "" -> inherit the global setting (default state).
        self._radio(picks, "🎲 Random", var, "", muted=True).pack(
            side="left", padx=(0, 8))

        if not options:
            tk.Label(picks, text="(no options found)", bg=CARD, fg=MUTED,
                     font=(FONT, 8)).pack(side="left")
            return row

        # Each answer stores [0, ..., 100, ..., 0] -> always this answer.
        for i, option in enumerate(options):
            weights = ", ".join("100" if j == i else "0"
                                for j in range(len(options)))
            self._radio(picks, str(option), var, weights).pack(
                side="left", padx=(0, 8))

        return row

    def _bind_wheel(self, widget):
        """Scroll rows with the mouse wheel. Rows must be bound exactly once."""
        for w in (widget if isinstance(widget, (list, tuple)) else [widget]):
            if not hasattr(w, "bind"):
                continue
            w.bind("<MouseWheel>",
                   lambda e: self.canvas.yview_scroll(
                       int(-1 * (e.delta / 120)), "units"), add="+")
            for child in w.winfo_children():
                self._bind_wheel(child)

    def _sync_mode(self):
        state = "normal" if self.mode_var.get() == "weighted" else "disabled"
        self.global_entry.config(state=state,
                                 fg=INPUT_FG if state == "normal" else MUTED)

    # ── reading the form back ──
    @staticmethod
    def _parse(text, limit=None):
        """Return (weights, bad_tokens). Empty list means 'not set'.

        limit is the number of options the weights must describe; a mismatch
        is reported so a mis-sized list never gets silently resampled.
        """
        text = (text or "").strip().rstrip(",")
        if not text:
            return [], []
        weights, bad = [], []
        for token in text.replace(";", ",").split(","):
            token = token.strip()
            if not token:
                continue
            try:
                weights.append(max(0.0, float(token)))
            except ValueError:
                bad.append(token)
        if not bad and limit and len(weights) != limit:
            bad.append(f"expected {limit} values, got {len(weights)}")
        return weights, bad

    def collect(self):
        """Read current fields -> (AnswerConfig, problems)."""
        bad = []
        mode = self.mode_var.get()
        global_weights, errs = self._parse(
            self.global_var.get() if mode == "weighted" else "",
            limit=len(self.reference) or None,
        )
        bad += [f"global: {e}" for e in errs]

        options_by_index = {u["index"]: len(u["options"]) for u in self.units}
        overrides = {}
        for idx, var in self.weight_vars.items():
            weights, errs = self._parse(var.get(),
                                        limit=options_by_index.get(idx) or None)
            if errs:
                bad += [f"#{idx}: {e}" for e in errs]
            elif weights:
                overrides[idx] = weights

        return AnswerConfig(mode, global_weights, overrides), bad


    # ── actions ──
    def _save(self):
        """Apply the current picks. The card stays put — single-window design."""
        config, problems = self.collect()
        if problems:
            messagebox.showwarning(
                "Check the weights",
                "These entries look wrong:\n\n" + "\n".join(problems[:12])
                + ("\n..." if len(problems) > 12 else ""),
                parent=self,
            )
            return False
        if self.on_apply:
            self.on_apply(config)
        return True

    def _reset(self):
        """Send every question back to 'Random' (inherit the global setting)."""
        self.mode_var.set("default")
        self.global_var.set("")
        for var in self.weight_vars.values():
            var.set("")
        self._sync_mode()

    def _close(self):
        """Drop the analyzed data and return the card to its empty state."""
        self.load({}, AnswerConfig())


# ── GUI ──────────────────────────────────────────────────────────────────────────
class BotGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("GFORM DUGA by zekasf")
        self.root.configure(bg=BG)
        self.root.geometry("1400x900")
        self._center_window()
        self.root.minsize(1180, 780)

        # Baked gradient + haze backdrop; every glass panel crops a blurred
        # slice of it, so the cards really are see-through frosted glass.
        self.bg_canvas = tk.Canvas(self.root, bg=BG, highlightthickness=0, bd=0)
        self.bg_canvas.place(x=0, y=0, relwidth=1, relheight=1)
        self._backdrop_photo = None

        self.theme = glass.Theme(self.root)
        self.theme.build(*self._window_size())
        self.theme.on_refresh = self._paint_backdrop
        self._paint_backdrop()

        self.ambient = AmbientBackground(self.bg_canvas)
        self._load_logo()
        self._build_ui()
        self.ambient.start()

    def _window_size(self):
        w, h = self.root.winfo_width(), self.root.winfo_height()
        return (w if w > 200 else 1400, h if h > 200 else 900)

    def _paint_backdrop(self):
        if not hasattr(self, "bg_canvas") or not self.bg_canvas.winfo_exists():
            return
        self._backdrop_photo = ImageTk.PhotoImage(self.theme.backdrop)
        self.bg_canvas.delete("backdrop")
        self.bg_canvas.create_image(0, 0, image=self._backdrop_photo,
                                    anchor="nw", tags="backdrop")
        self.bg_canvas.tag_lower("backdrop")

    def _center_window(self):
        self.root.update_idletasks()
        w, h = 1400, 900
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.root.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

    def _load_logo(self):
        logo_path = os.path.join(os.path.dirname(__file__), "logo.png.png")
        try:
            img = Image.open(logo_path)
            icon_img = img.resize((32, 32), Image.LANCZOS)
            self._icon = ImageTk.PhotoImage(icon_img)
            self.root.iconphoto(True, self._icon)
            header_img = img.resize((48, 48), Image.LANCZOS)
            self._logo = ImageTk.PhotoImage(header_img)
        except Exception as e:
            self._logo = None
            print(f"Logo load error: {e}")

    def _build_ui(self):
        # ── Header glass bar ──────────────────────────────────────────────
        header = glass.GlassPanel(self.root, self.theme)
        header.place(relx=0.011, rely=0.016, relwidth=0.978, relheight=0.088)
        head = header.body

        brand = tk.Frame(head, bg=CARD)
        brand.pack(side="left", fill="y", padx=(14, 0), pady=8)
        if self._logo:
            tk.Label(brand, image=self._logo, bg=CARD).pack(
                side="left", padx=(0, 12))
        text_col = tk.Frame(brand, bg=CARD)
        text_col.pack(side="left")
        tk.Label(text_col, text="GFORM DUGA", bg=CARD, fg=ACCENT2,
                 font=(FONT, 21, "bold")).pack(anchor="w")
        tk.Label(text_col, text="Automated Google Form Submission Tool",
                 bg=CARD, fg=MUTED, font=(FONT, 9)).pack(anchor="w")

        tools = tk.Frame(head, bg=CARD)
        tools.pack(side="right", fill="y", padx=(0, 14), pady=8)

        self.status_pill = glass.Pill(tools, "IDLE", MUTED)
        self.status_pill.pack(side="right", padx=(10, 0), pady=3)

        glass.GlassButton(tools, "Clear log", self._clear_log,
                          width=104, height=30,
                          font=(FONT, 9, "bold")).pack(side="right", padx=6)
        glass.GlassButton(tools, "Save preset", self._save_preset,
                          width=112, height=30,
                          font=(FONT, 9, "bold")).pack(side="right", padx=6)

        # ── Sidebar ───────────────────────────────────────────────────────
        sidebar = glass.GlassPanel(self.root, self.theme)
        sidebar.place(relx=0.011, rely=0.118, relwidth=0.200, relheight=0.866)
        side = sidebar.body

        tk.Label(side, text="RUN SETTINGS", bg=CARD, fg=ACCENT2,
                 font=(FONT, 10, "bold")).pack(anchor="w", pady=(4, 14))

        tk.Label(side, text="Number of Submissions", bg=CARD, fg=TEXT,
                 font=(FONT, 10)).pack(anchor="w")
        self.count_var = tk.IntVar(value=10)
        self.spin = tk.Spinbox(
            side, from_=1, to=500, textvariable=self.count_var,
            width=10, font=(FONT, 20, "bold"), justify="left",
            bg=INPUT_BG, fg=INPUT_FG, buttonbackground=INPUT_BG,
            relief="flat", bd=0, highlightthickness=1,
            highlightbackground=glass.BORDER_SOFT, highlightcolor=ACCENT,
            insertbackground=INPUT_FG)
        self.spin.pack(fill="x", pady=(6, 20))

        tk.Label(side, text="Google Form URL", bg=CARD, fg=TEXT,
                 font=(FONT, 10)).pack(anchor="w")
        self.url_var = tk.StringVar(value=FORM_URL)
        self.url_entry = tk.Entry(
            side, textvariable=self.url_var, bg=INPUT_BG, fg=INPUT_FG,
            font=(FONT, 9), relief="flat", insertbackground=INPUT_FG,
            highlightthickness=1, highlightbackground=glass.BORDER_SOFT,
            highlightcolor=ACCENT)
        self.url_entry.pack(fill="x", pady=(6, 0))

        tk.Frame(side, bg=CARD, height=1).pack(fill="x", pady=(22, 16))

        self.run_btn = glass.GlassButton(
            side, "Start Bot", self._start, variant="primary",
            font=(FONT, 12, "bold"), height=46)
        self.run_btn.pack(fill="x", pady=5)

        self.analyze_btn = glass.GlassButton(
            side, "Analyze URL", self._analyze, variant="ghost",
            font=(FONT, 11, "bold"), height=42)
        self.analyze_btn.pack(fill="x", pady=5)

        self.stop_btn = glass.GlassButton(
            side, "Stop Bot", self._stop, variant="danger", state="disabled",
            font=(FONT, 11, "bold"), height=42)
        self.stop_btn.pack(fill="x", pady=5)

        tk.Label(side, text="Picks are read from the Analyzed Form Data card. "
                            "Nothing picked = random, exactly as before.",
                 bg=CARD, fg=MUTED, font=(FONT, 8), justify="left",
                 wraplength=230).pack(anchor="w", side="bottom", pady=(16, 6))

        # ── Analyzed form data (left card) ────────────────────────────────
        self._config_win = AnswerConfigPanel(
            self.root, self.theme, self._apply_answer_config)
        self._config_win.place(relx=0.2225, rely=0.118,
                               relwidth=0.375, relheight=0.866)

        # ── Live log (right card) ─────────────────────────────────────────
        log_card = glass.GlassPanel(self.root, self.theme)
        log_card.place(relx=0.6105, rely=0.118,
                       relwidth=0.3785, relheight=0.866)
        log_body = log_card.body

        log_head = tk.Frame(log_body, bg=CARD)
        log_head.pack(fill="x")
        tk.Label(log_head, text="Live Log", bg=CARD, fg=ACCENT2,
                 font=(FONT, 11, "bold")).pack(side="left")
        tk.Label(log_head, text="one line per submission", bg=CARD, fg=MUTED,
                 font=(FONT, 8)).pack(side="left", padx=(10, 0))

        log_bg = glass.darken(glass.SURFACE, 0.42)
        log_area = tk.Frame(log_body, bg=log_bg, highlightthickness=1,
                            highlightbackground=glass.BORDER_SOFT)
        log_area.pack(fill="both", expand=True, pady=(8, 0))

        self.log_text = tk.Text(
            log_area, bg=log_bg, fg=TEXT, font=(MONO, 10),
            relief="flat", bd=0, state="disabled", wrap="word",
            insertbackground=TEXT, highlightthickness=0,
            selectbackground=glass.mix(ACCENT, log_bg, 0.45))
        self.log_text.pack(fill="both", expand=True, padx=2, pady=2)
        self.log_text.tag_config("ok", foreground=SUCCESS)
        self.log_text.tag_config("fail", foreground=FAIL)
        self.log_text.tag_config("info", foreground=MUTED)
        self.log_text.tag_config("hacker", foreground=ACCENT2,
                                 font=(MONO, 10, "bold"))

        # soft scan line sweeping the terminal
        self._scan_y = 0.0
        self._scan = tk.Frame(log_area, height=2,
                              bg=glass.mix(log_bg, ACCENT, 0.55))
        self._scan.place(relx=0, rely=0.0, relwidth=1)
        self.root.after(70, self._animate_scan)

        self._success = 0
        self._failed = 0
        self._total = 0
        self._running = False
        self._loop = None
        self._thread = None
        # Answer randomness: untouched AnswerConfig() keeps the original
        # random rule. Populated by the Analyzed Form Data card.
        self.answer_config = AnswerConfig()
        self._analyzed_url = None

    def _animate_scan(self):
        if not self._scan.winfo_exists():
            return
        self._scan_y = (self._scan_y + 0.005) % 1.0
        self._scan.place(relx=0, rely=self._scan_y, relwidth=1)
        self.root.after(70, self._animate_scan)

    def _clear_log(self):
        self.log_text.config(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.config(state="disabled")

    def _save_preset(self):
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "answers.json")
        try:
            self.answer_config.save(path)
        except Exception as exc:
            self._log(f"❌  Could not save preset: {exc}")
            return
        self._log(f"💾  Preset saved -> {path} "
                  f"(use with --config)")

    def _log(self, msg, tag=None, raw=False):
        def _do():
            self.log_text.config(state="normal")
            ts = datetime.now().strftime("%H:%M:%S")
            if not tag:
                use_tag = "ok" if "✅" in msg else ("fail" if ("❌" in msg or "⚠️" in msg) else "info")
            else:
                use_tag = tag
            prefix = "" if raw else f"[{ts}] "
            self.log_text.insert("end", f"{prefix}{msg}\n", use_tag)
            self.log_text.see("end")
            self.log_text.config(state="disabled")
            
            # Nudge the indicator without disturbing the RUNNING label
            if "✅" in msg:
                self.status_pill.set_dot(SUCCESS)
            elif "❌" in msg or "⚠️" in msg:
                self.status_pill.set_dot(FAIL)
        self.root.after(0, _do)

    def _update_progress(self, i, total, success, ok):
        # UI simplified - stats removed
        pass

    def _on_done(self, success, total, stats=None):
        def _do():
            self._running = False
            self.spin.config(state="normal")
            self.analyze_btn.config(state="normal")
            self.url_entry.config(state="normal")
            self.status_pill.set("IDLE", MUTED)
            self._log(f"🎉 Finished! {success}/{total} submissions succeeded.")
            if stats is not None:
                for line, is_head in stats.table():
                    self._log(line, tag="hacker" if is_head else "ok", raw=True)
        self.root.after(0, _do)

    def _start(self):
        if self._running:
            return
        try:
            count = self.count_var.get()
        except:
            count = 1
            
        url = self.url_var.get()

        # Overrides are keyed by position, so a config from a different form
        # must never be applied to this one.
        url_changed = (self._analyzed_url is not None and url != self._analyzed_url)
        if url_changed:
            self.answer_config = AnswerConfig()
            self._analyzed_url = None

        self._total   = count
        self._success = 0
        self._failed  = 0
        self._running = True

        # Reset UI
        self.run_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.analyze_btn.config(state="disabled")
        self.spin.config(state="disabled")
        self.url_entry.config(state="disabled")
        
        self.status_pill.set("RUNNING", SUCCESS)

        self.log_text.config(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.config(state="disabled")

        # The log was just cleared, so restate the active randomness here.
        if url_changed:
            self._log("⚠️  URL changed since analysis - randomness reset to default.")
        if self.answer_config.is_untouched:
            self._log("⚙️  Randomness: Default (random)")
        else:
            self._log(f"⚙️  Randomness: {self.answer_config.mode} "
                      f"({len(self.answer_config.overrides)} override(s))")

        picker = make_picker(self.answer_config)


        
        def run_hacker_intro():
            intros = [
                "INITIALIZING GFORM.DUGA CORE...",
                "ESTABLISHING STEALTH SOCKET CONNECTION...",
                "BYPASSING GOOGLE ANTI-BOT PROTOCOLS...",
                "INJECTING PAYLOAD INTO TARGET SCHEMA...",
                "ACCESS GRANTED. STARTING AUTOMATION..."
            ]
            for msg in intros:
                if not self._running:
                    return
                self._log(f"> {msg}", "hacker")
                time.sleep(random.uniform(0.1, 0.4))
                
            self._log(f"🚀 Starting {count} submissions...")

            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            try:
                self._loop.run_until_complete(
                    run_bot(count, url, self._log, self._update_progress,
                            self._on_done, pick=picker)
                )
            except Exception as e:
                self._log(f"⚠️  Fatal error: {e}")
                self.root.after(0, lambda: self._on_done(self._success, count))
            finally:
                self._loop.close()

        def start_flash(step=0):
            # Canvas calls must stay on the main thread: drive the blink with
            # after() and only hand the actual run to the worker.
            if not self._running:
                try:
                    self.bg_canvas.delete("warning")
                except tk.TclError:
                    pass
                return
            if step >= 6:
                try:
                    self.bg_canvas.delete("warning")
                except tk.TclError:
                    pass
                self._thread = threading.Thread(target=run_hacker_intro,
                                                daemon=True)
                self._thread.start()
                return
            try:
                if step % 2 == 0:
                    w = self.root.winfo_width() or 1400
                    h = self.root.winfo_height() or 900
                    self.bg_canvas.create_text(
                        w // 2, h // 2,
                        text="⚠️ WARNING: SYSTEM BREACH ⚠️",
                        fill=ACCENT, font=(FONT, 24, "bold"), tags="warning")
                else:
                    self.bg_canvas.delete("warning")
            except tk.TclError:
                return
            self.root.after(150, start_flash, step + 1)

        self.root.after(0, start_flash, 0)

    def _stop(self):
        if self._loop and self._running:
            self._running = False
            self._loop.call_soon_threadsafe(self._loop.stop)
            self._log("🛑 Stopped by user.")

            self.run_btn.config(state="normal")
            self.stop_btn.config(state="disabled")
            self.spin.config(state="normal")
            self.analyze_btn.config(state="normal")
            self.url_entry.config(state="normal")
            self.status_pill.set("STOPPED", FAIL)

    def _analyze(self):
        url = self.url_var.get()
        self._log(f"🔍  Analyzing: {url}...")
        self.analyze_btn.config(state="disabled")

        def run_analysis():
            res = analyze(url)

            def show():
                self.analyze_btn.config(state="normal")
                if "error" in res:
                    self._log(f"❌  Analysis Error: {res['error']}")
                    return
                self._analyzed_url = url
                units = res.get("units") or []
                self._log(f"📋  Form: {res['title']}")
                self._log(f"    {len(res.get('questions') or [])} questions | "
                          f"{len(units)} answerable | "
                          f"options: {', '.join(res.get('reference_options') or [])}")
                self._log("✅  Analysis complete. Review it below.")
                self._open_config(res)

            self.root.after(0, show)

        threading.Thread(target=run_analysis, daemon=True).start()

    def _open_config(self, form_info):
        self._config_win.load(form_info, self.answer_config)

    def _apply_answer_config(self, config):
        self.answer_config = config
        if config.is_untouched:
            self._log("⚙️  Randomness: Default (random)")
        else:
            self._log(f"⚙️  Randomness: {config.mode} "
                      f"({len(config.overrides)} override(s))")


if __name__ == "__main__":
    multiprocessing.freeze_support()
    root = tk.Tk()
    app = BotGUI(root)
    root.mainloop()
