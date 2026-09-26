import tkinter as tk
from tkinter import ttk, font
import requests
import re
from PIL import Image, ImageTk
import asyncio
import threading
import random
import logging
import os
import sys
import multiprocessing
import json
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
    submit_form, FORM_URL
)

# ── Color palette ───────────────────────────────────────────────────────────────
BG        = "#000000"
CARD      = "#0a0a0a"
ACCENT    = "#00ff00"
ACCENT2   = "#00ff00"
SUCCESS   = "#00ff00"
FAIL      = "#ff0000"
TEXT      = "#00ff00"
MUTED     = "#004400"
BORDER    = "#003300"
INPUT_BG  = "#050505"
INPUT_FG  = "#00ff00"

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

async def run_bot(count, url, on_log, on_progress, on_done):
    name_pool = build_name_pool()
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
                        on_done(0, count)
                        return
                else:
                    on_done(0, count)
                    return
            else:
                on_log(f"⚠️  Browser launch error: {e}")
                on_done(0, count)
                return

        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )

        for i in range(1, count + 1):
            if not name_pool:
                name_pool = build_name_pool()

            page = await context.new_page()
            try:
                on_log(f"[{i}/{count}] Opening form...")
                res, data = await submit_form(context, i, count, name_pool, url)
                
                name = data['name'] or (data.get('reason') or 'no name assigned')
                details = f" ({name}{' | ' + data['email'] if data['email'] else ''})"
                answers = data.get('answers') or []
                if res:
                    success += 1
                    on_log(f"✅  [{i}/{count}] Submitted: {details}")
                    for q, a in answers:
                        on_log(f"      {q} → {a}")
                    on_progress(i, count, success, True)
                else:
                    on_log(f"❌  [{i}/{count}] Failed: {details}")
                    on_progress(i, count, success, False)

            except Exception as e:
                on_log(f"⚠️  [{i}/{count}] Error: {e}")
                on_progress(i, count, success, False)
            finally:
                await page.close()

            await asyncio.sleep(random.uniform(1.0, 3.0))

        await browser.close()

    on_done(success, count)


def analyze_gform(url):
    """Parses a Google Form URL and extracts question types, labels, and entry IDs."""
    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            return {"error": f"Failed to fetch form. Status: {response.status_code}"}

        match = re.search(r'var FB_PUBLIC_LOAD_DATA_ = (.*?);</script>', response.text, re.DOTALL)
        if not match:
            return {"error": "Could not find form data. Is this a valid Google Form link?"}

        data = json.loads(match.group(1))
        
        if not data or len(data) < 2 or data[1] is None:
            return {"error": "Form data structure is invalid."}
        
        questions_list = data[1][1] if len(data[1]) > 1 else []
        
        form_info = {
            "title": data[1][8] if len(data[1]) > 8 else "Untitled Form",
            "questions": []
        }

        for q in questions_list:
            if not q or len(q) < 4: continue
            
            label = q[1]
            q_type_code = q[3]
            entry_id = None
            required = False
            
            try:
                if q[4] and len(q[4]) > 0:
                    entry_id = q[4][0][0]
                    required = bool(q[4][0][2]) if len(q[4][0]) > 2 else False
            except: pass

            form_info["questions"].append({
                "label": label,
                "entry_id": f"entry.{entry_id}" if entry_id else "No ID",
                "required": required
            })
        return form_info
    except Exception as e:
        return {"error": str(e)}


# ── Matrix Animation ─────────────────────────────────────────────────────────────
class MatrixAnimation:
    def __init__(self, canvas):
        self.canvas = canvas
        self.columns = []
        self.chars = "ｱｲｳｴｵｶｷｸｹｺｻｼｽｾｿﾀﾁﾂﾃﾄﾅﾆﾇﾈﾉﾊﾋﾌﾍﾎﾏﾐﾑﾒﾓﾔﾕﾖﾗﾘﾙﾚﾛﾜﾝ1234567890ABCDEF"
        self.running = False
        self.font_size = 15

    def start(self):
        if self.running: return
        self.running = True
        width = self.canvas.winfo_width()
        if width < 10: width = 560
        col_count = width // self.font_size
        self.columns = [random.randint(-30, 0) for _ in range(col_count)]
        self._animate()

    def _animate(self):
        if not self.running: return
        self.canvas.delete("matrix")
        height = self.canvas.winfo_height()
        if height < 10: height = 850
        
        for i, y in enumerate(self.columns):
            char = random.choice(self.chars)
            x = i * self.font_size
            # Draw the leading character (bright)
            self.canvas.create_text(x, y * self.font_size, text=char, 
                                   fill="#00ff00", font=("Consolas", self.font_size), 
                                   tags="matrix", anchor="nw")
            # Draw a few trailing characters (dimmer)
            for tail in range(1, 5):
                if y - tail >= 0:
                    t_char = random.choice(self.chars)
                    alpha = ["#00cc00", "#009900", "#006600", "#003300"][tail-1]
                    self.canvas.create_text(x, (y - tail) * self.font_size, text=t_char, 
                                           fill=alpha, font=("Consolas", self.font_size), 
                                           tags="matrix", anchor="nw")

            self.columns[i] += 1
            if self.columns[i] * self.font_size > height:
                if random.random() > 0.9:
                    self.columns[i] = 0

        self.canvas.after(60, self._animate)

    def stop(self):
        self.running = False
        self.canvas.delete("matrix")


# ── GUI ──────────────────────────────────────────────────────────────────────────
class BotGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("GFORM DUGA by zekasf")
        self.root.configure(bg=BG)
        self.root.resizable(False, False)
        self.root.geometry("560x850")
        self._center_window()
        
        # Background Matrix Canvas
        self.bg_canvas = tk.Canvas(self.root, bg=BG, highlightthickness=0, bd=0)
        self.bg_canvas.place(x=0, y=0, relwidth=1, relheight=1)
        self.matrix = MatrixAnimation(self.bg_canvas)
        
        self._load_logo()
        self._build_ui()

    def _center_window(self):
        self.root.update_idletasks()
        w, h = 560, 850
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.root.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

    def _load_logo(self):
        logo_path = os.path.join(os.path.dirname(__file__), "logo.png.png")
        try:
            img = Image.open(logo_path)
            # Window icon (32x32)
            icon_img = img.resize((32, 32), Image.LANCZOS)
            self._icon = ImageTk.PhotoImage(icon_img)
            self.root.iconphoto(True, self._icon)
            # Header logo (48x48)
            header_img = img.resize((48, 48), Image.LANCZOS)
            self._logo = ImageTk.PhotoImage(header_img)
        except Exception as e:
            self._logo = None
            print(f"Logo load error: {e}")

    def _build_ui(self):
        # ── Header ────
        header = tk.Frame(self.root, bg=BG)
        header.pack(fill="x", padx=24, pady=(28, 0))

        title_row = tk.Frame(header, bg=BG)
        title_row.pack(anchor="w")

        if self._logo:
            tk.Label(title_row, image=self._logo, bg=BG).pack(side="left", padx=(0, 12))

        text_col = tk.Frame(title_row, bg=BG)
        text_col.pack(side="left")
        tk.Label(text_col, text="GFORM DUGA", bg=BG, fg=TEXT,
                 font=("Segoe UI", 20, "bold")).pack(anchor="w")
        tk.Label(text_col, text="by zekasf", bg=BG, fg=MUTED,
                 font=("Segoe UI", 9, "italic")).pack(anchor="w")
        
        # Status Indicator
        self.status_frame = tk.Frame(header, bg=BG)
        self.status_frame.pack(side="right", pady=5)
        self.status_dot = tk.Label(self.status_frame, text="●", fg="#555555", bg=BG, font=("Segoe UI", 12))
        self.status_dot.pack(side="left")
        self.status_text = tk.Label(self.status_frame, text="IDLE", fg=MUTED, bg=BG, font=("Segoe UI", 9, "bold"))
        self.status_text.pack(side="left", padx=(5, 0))

        tk.Label(header, text="Automated Google Form Submission Tool",
                 bg=BG, fg=MUTED, font=("Segoe UI", 10)).pack(anchor="w", pady=(15, 0))

        # ── Divider ───
        tk.Frame(self.root, bg=BORDER, height=1).pack(fill="x", padx=24, pady=16)

        # ── Config card ───
        config_card = tk.Frame(self.root, bg=CARD, bd=0, relief="flat")
        config_card.pack(fill="x", padx=24, pady=(0, 20))
        
        inner_config = tk.Frame(config_card, bg=CARD)
        inner_config.pack(fill="both", expand=True, padx=25, pady=25)

        # Number of Submissions
        tk.Label(inner_config, text="Number of Submissions", bg=CARD, fg=TEXT,
                 font=("Segoe UI", 11)).pack(anchor="w")
        
        self.count_var = tk.IntVar(value=10)
        self.spin = tk.Spinbox(
            inner_config, from_=1, to=500, textvariable=self.count_var,
            width=15, font=("Segoe UI", 12, "bold"),
            bg=INPUT_BG, fg=INPUT_FG, buttonbackground=INPUT_BG,
            relief="flat", bd=0, highlightthickness=10,
            highlightbackground=INPUT_BG, highlightcolor=INPUT_BG,
            insertbackground=INPUT_FG
        )
        self.spin.pack(anchor="w", pady=(5, 15))

        # URL Entry
        tk.Label(inner_config, text="Google Form URL", bg=CARD, fg=TEXT,
                 font=("Segoe UI", 11)).pack(anchor="w")
        self.url_var = tk.StringVar(value=FORM_URL)
        self.url_entry = tk.Entry(
            inner_config, textvariable=self.url_var, bg=INPUT_BG, fg=INPUT_FG,
            font=("Segoe UI", 10), relief="flat", insertbackground=INPUT_FG,
            highlightthickness=10, highlightbackground=INPUT_BG, highlightcolor=INPUT_BG
        )
        self.url_entry.pack(fill="x", pady=(5, 0))

        # ── Log card ───
        log_card = tk.Frame(self.root, bg=CARD)
        log_card.pack(fill="x", padx=24, pady=(0, 25))
        log_card.configure(height=300)
        log_card.pack_propagate(False)

        inner_log = tk.Frame(log_card, bg=CARD)
        inner_log.pack(fill="both", expand=True, padx=20, pady=(20, 20))

        tk.Label(inner_log, text="Live Log", bg=CARD, fg=TEXT,
                 font=("Segoe UI", 11)).pack(anchor="w", pady=(0, 10))

        self.log_text = tk.Text(
            inner_log, bg=BG, fg=TEXT, font=("Consolas", 10),
            relief="flat", bd=0, state="disabled",
            insertbackground=TEXT, wrap="word"
        )
        self.log_text.pack(fill="both", expand=True)
        self.log_text.tag_config("ok",   foreground=SUCCESS)
        self.log_text.tag_config("fail", foreground=FAIL)
        self.log_text.tag_config("info", foreground=MUTED)
        self.log_text.tag_config("hacker", foreground=SUCCESS, font=("Consolas", 10, "bold"))

        # ── Button Row (Pills) ────
        btn_row = tk.Frame(self.root, bg=BG)
        btn_row.pack(fill="x", padx=24, pady=(0, 30))

        btn_style = {
            "bg": INPUT_BG, "fg": INPUT_FG,
            "font": ("Segoe UI", 11, "bold"),
            "relief": "flat", "bd": 0,
            "activebackground": TEXT, "activeforeground": INPUT_FG,
            "padx": 20, "pady": 12, "cursor": "hand2"
        }

        self.run_btn = tk.Button(btn_row, text="Start Bot", command=self._start, **btn_style)
        self.run_btn.pack(side="left", fill="x", expand=True)

        self.analyze_btn = tk.Button(btn_row, text="Analyze URL", command=self._analyze, **btn_style)
        self.analyze_btn.pack(side="left", fill="x", expand=True, padx=10)

        self.stop_btn = tk.Button(btn_row, text="Stop Bot", command=self._stop, state="disabled", **btn_style)
        self.stop_btn.pack(side="left", fill="x", expand=True)

        self._success = 0
        self._failed  = 0
        self._total   = 0
        self._running = False
        self._loop    = None
        self._thread  = None

    def _log(self, msg, tag=None):
        def _do():
            self.log_text.config(state="normal")
            ts = datetime.now().strftime("%H:%M:%S")
            if not tag:
                use_tag = "ok" if "✅" in msg else ("fail" if ("❌" in msg or "⚠️" in msg) else "info")
            else:
                use_tag = tag
            self.log_text.insert("end", f"[{ts}] {msg}\n", use_tag)
            self.log_text.see("end")
            self.log_text.config(state="disabled")
            
            # Update status dot on success/fail
            if "✅" in msg: self.status_dot.config(fg=SUCCESS)
            elif "❌" in msg or "⚠️" in msg: self.status_dot.config(fg=FAIL)
        self.root.after(0, _do)

    def _update_progress(self, i, total, success, ok):
        # UI simplified - stats removed
        pass

    def _on_done(self, success, total):
        def _do():
            self._running = False
            self.spin.config(state="normal")
            self.analyze_btn.config(state="normal")
            self.url_entry.config(state="normal")
            self.status_dot.config(fg="#555555")
            self.status_text.config(text="IDLE", fg=MUTED)
            self._log(f"🎉 Finished! {success}/{total} submissions succeeded.")
        self.root.after(0, _do)

    def _start(self):
        if self._running:
            return
        try:
            count = self.count_var.get()
        except:
            count = 1
            
        url = self.url_var.get()
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
        
        self.status_dot.config(fg=SUCCESS)
        self.status_text.config(text="RUNNING", fg=SUCCESS)

        self.log_text.config(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.config(state="disabled")
        
        # Start Matrix animation
        self.matrix.start()
        
        def run_hacker_intro():
            intros = [
                "INITIALIZING GFORM.DUGA CORE...",
                "ESTABLISHING STEALTH SOCKET CONNECTION...",
                "BYPASSING GOOGLE ANTI-BOT PROTOCOLS...",
                "INJECTING PAYLOAD INTO TARGET SCHEMA...",
                "ACCESS GRANTED. STARTING AUTOMATION..."
            ]
            for msg in intros:
                self._log(f"> {msg}", "hacker")
                time.sleep(random.uniform(0.1, 0.4))
                
            self._log(f"🚀 Starting {count} submissions...")

            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            try:
                self._loop.run_until_complete(
                    run_bot(count, url, self._log, self._update_progress, self._on_done)
                )
            except Exception as e:
                self._log(f"⚠️  Fatal error: {e}")
                self.root.after(0, lambda: self._on_done(self._success, count))
            finally:
                self._loop.close()
                self.root.after(0, self.matrix.stop)

        def run_warning():
            # Big red warning flash
            warning_text = self.bg_canvas.create_text(
                280, 425, text="⚠️ WARNING: SYSTEM BREACH ⚠️",
                fill="red", font=("Segoe UI", 24, "bold"), tags="warning"
            )
            for _ in range(6):
                color = "red" if _ % 2 == 0 else "black"
                self.bg_canvas.itemconfig(warning_text, fill=color)
                self.bg_canvas.config(bg="red" if _ % 2 == 0 else BG)
                time.sleep(0.15)
            
            self.bg_canvas.delete("warning")
            self.bg_canvas.config(bg=BG)
            run_hacker_intro()

        self._thread = threading.Thread(target=run_warning, daemon=True)
        self._thread.start()

    def _stop(self):
        if self._loop and self._running:
            self._running = False
            self._loop.call_soon_threadsafe(self._loop.stop)
            self._log("🛑 Stopped by user.")
            self.matrix.stop()
            self.run_btn.config(state="normal")
            self.stop_btn.config(state="disabled")
            self.spin.config(state="normal")
            self.analyze_btn.config(state="normal")
            self.url_entry.config(state="normal")
            self.status_dot.config(fg=FAIL)
            self.status_text.config(text="STOPPED", fg=FAIL)

    def _analyze(self):
        url = self.url_var.get()
        self._log(f"🔍  Analyzing: {url}...")
        
        def run_analysis():
            res = analyze_gform(url)
            if "error" in res:
                self._log(f"❌  Analysis Error: {res['error']}")
            else:
                self._log(f"📋  Form: {res['title']}")
                for i, q in enumerate(res['questions'], 1):
                    req = " (Required)" if q['required'] else ""
                    self._log(f"  Q{i}: {q['label']} -> {q['entry_id']}{req}")
                self._log("✅  Analysis complete.")

        threading.Thread(target=run_analysis, daemon=True).start()


if __name__ == "__main__":
    multiprocessing.freeze_support()
    root = tk.Tk()
    app = BotGUI(root)
    root.mainloop()
