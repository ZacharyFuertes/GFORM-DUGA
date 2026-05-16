import tkinter as tk
from tkinter import ttk, font
from PIL import Image, ImageTk
import asyncio
import threading
import random
import logging
import os
import sys
import multiprocessing
from datetime import datetime

# ── Import the bot logic directly ──────────────────────────────────────────────
import subprocess
from playwright.async_api import async_playwright
from gform_bot_playwright import (
    MALE_NAMES, FEMALE_NAMES, build_name_pool,
    fill_page1, fill_radiogroups, FORM_URL
)

# ── Color palette ───────────────────────────────────────────────────────────────
BG        = "#0f1117"
CARD      = "#1a1d27"
ACCENT    = "#6c63ff"
ACCENT2   = "#a78bfa"
SUCCESS   = "#22c55e"
FAIL      = "#ef4444"
TEXT      = "#e2e8f0"
MUTED     = "#64748b"
BORDER    = "#2d3148"

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

async def run_bot(count, on_log, on_progress, on_done):
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
                await page.goto(FORM_URL)
                await page.wait_for_load_state("networkidle")

                # Page 1
                await fill_page1(page, name_pool)

                btns = await page.locator('div[role="button"]').all()
                for btn in btns:
                    text = await btn.inner_text()
                    if "Susunod" in text or "Next" in text:
                        await btn.click()
                        break
                await page.wait_for_timeout(1000)

                # Page 2
                await fill_radiogroups(page)
                btns = await page.locator('div[role="button"]').all()
                for btn in btns:
                    text = await btn.inner_text()
                    if "Susunod" in text or "Next" in text:
                        await btn.click()
                        break
                await page.wait_for_timeout(1000)

                # Page 3
                await fill_radiogroups(page)
                btns = await page.locator('div[role="button"]').all()
                for btn in btns:
                    text = await btn.inner_text()
                    if "Isumite" in text or "Submit" in text:
                        await btn.click()
                        break
                await page.wait_for_timeout(2000)

                content = await page.content()
                if "tugon" in content.lower() or "recorded" in content.lower():
                    success += 1
                    on_log(f"✅  [{i}/{count}] Submitted successfully")
                    on_progress(i, count, success, True)
                else:
                    on_log(f"❌  [{i}/{count}] Failed — response not recorded")
                    on_progress(i, count, success, False)

            except Exception as e:
                on_log(f"⚠️  [{i}/{count}] Error: {e}")
                on_progress(i, count, success, False)
            finally:
                await page.close()

            await asyncio.sleep(random.uniform(1.0, 3.0))

        await browser.close()

    on_done(success, count)


# ── GUI ──────────────────────────────────────────────────────────────────────────
class BotGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("GFORM DUGA by zekasf")
        self.root.configure(bg=BG)
        self.root.resizable(False, False)
        self.root.geometry("560x680")
        self._center_window()
        self._load_logo()
        self._build_ui()

    def _center_window(self):
        self.root.update_idletasks()
        w, h = 560, 680
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
        tk.Label(text_col, text="by zekasf", bg=BG, fg=ACCENT2,
                 font=("Segoe UI", 9, "italic")).pack(anchor="w")
        tk.Label(header, text="Automated Google Form Submission Tool",
                 bg=BG, fg=MUTED, font=("Segoe UI", 10)).pack(anchor="w", pady=(4, 0))

        # ── Divider ───
        tk.Frame(self.root, bg=BORDER, height=1).pack(fill="x", padx=24, pady=16)

        # ── Config card ───
        card = tk.Frame(self.root, bg=CARD, bd=0, relief="flat")
        card.pack(fill="x", padx=24, pady=(0, 12))
        card.pack_propagate(False)
        card.configure(height=100)

        inner = tk.Frame(card, bg=CARD)
        inner.pack(fill="both", expand=True, padx=20, pady=16)

        tk.Label(inner, text="Number of Submissions", bg=CARD, fg=MUTED,
                 font=("Segoe UI", 9)).grid(row=0, column=0, sticky="w")

        self.count_var = tk.IntVar(value=10)
        spin_frame = tk.Frame(inner, bg=ACCENT, bd=0)
        spin_frame.grid(row=1, column=0, sticky="w", pady=(4, 0))
        self.spin = tk.Spinbox(
            spin_frame, from_=1, to=500, textvariable=self.count_var,
            width=6, font=("Segoe UI", 14, "bold"),
            bg=CARD, fg=TEXT, buttonbackground=CARD,
            relief="flat", bd=0, highlightthickness=0,
            insertbackground=TEXT
        )
        self.spin.pack(padx=2, pady=2)

        tk.Label(inner, text="Ratings: 3 · 4 · 5   |   Names: ~50% filled, no repeats",
                 bg=CARD, fg=MUTED, font=("Segoe UI", 9)).grid(
                     row=1, column=1, sticky="w", padx=(24, 0), pady=(4, 0))

        # ── Progress area ───
        prog_card = tk.Frame(self.root, bg=CARD)
        prog_card.pack(fill="x", padx=24, pady=(0, 12))

        prog_inner = tk.Frame(prog_card, bg=CARD)
        prog_inner.pack(fill="x", padx=20, pady=16)

        top_row = tk.Frame(prog_inner, bg=CARD)
        top_row.pack(fill="x")
        self.prog_label = tk.Label(top_row, text="Ready", bg=CARD, fg=TEXT,
                                   font=("Segoe UI", 10, "bold"))
        self.prog_label.pack(side="left")
        self.pct_label = tk.Label(top_row, text="0%", bg=CARD, fg=ACCENT2,
                                  font=("Segoe UI", 10, "bold"))
        self.pct_label.pack(side="right")

        style = ttk.Style()
        style.theme_use("default")
        style.configure("Custom.Horizontal.TProgressbar",
                         troughcolor=BG, background=ACCENT,
                         thickness=8, borderwidth=0)

        self.progress = ttk.Progressbar(prog_inner, style="Custom.Horizontal.TProgressbar",
                                         orient="horizontal", mode="determinate")
        self.progress.pack(fill="x", pady=(8, 12))

        stats_row = tk.Frame(prog_inner, bg=CARD)
        stats_row.pack(fill="x")

        self.stat_ok  = self._stat_box(stats_row, "✅ Success", "0", SUCCESS)
        self.stat_fail = self._stat_box(stats_row, "❌ Failed", "0", FAIL)
        self.stat_left = self._stat_box(stats_row, "⏳ Remaining", "—", MUTED)

        # ── Log box ───
        log_frame = tk.Frame(self.root, bg=CARD)
        log_frame.pack(fill="both", expand=True, padx=24, pady=(0, 12))

        tk.Label(log_frame, text="Live Log", bg=CARD, fg=MUTED,
                 font=("Segoe UI", 9)).pack(anchor="w", padx=12, pady=(10, 0))

        self.log_text = tk.Text(
            log_frame, bg=BG, fg=TEXT, font=("Consolas", 9),
            relief="flat", bd=0, state="disabled",
            insertbackground=TEXT, wrap="word", height=10
        )
        self.log_text.pack(fill="both", expand=True, padx=12, pady=(4, 12))
        self.log_text.tag_config("ok",   foreground=SUCCESS)
        self.log_text.tag_config("fail", foreground=FAIL)
        self.log_text.tag_config("info", foreground=ACCENT2)

        # ── Button ───
        btn_row = tk.Frame(self.root, bg=BG)
        btn_row.pack(fill="x", padx=24, pady=(0, 24))

        self.run_btn = tk.Button(
            btn_row, text="▶  Start Bot", bg=ACCENT, fg="white",
            font=("Segoe UI", 11, "bold"), relief="flat", bd=0,
            activebackground=ACCENT2, activeforeground="white",
            padx=20, pady=10, cursor="hand2",
            command=self._start
        )
        self.run_btn.pack(side="left", fill="x", expand=True)

        self.stop_btn = tk.Button(
            btn_row, text="■  Stop", bg=CARD, fg=MUTED,
            font=("Segoe UI", 11), relief="flat", bd=0,
            activebackground=BORDER, activeforeground=TEXT,
            padx=20, pady=10, cursor="hand2",
            command=self._stop, state="disabled"
        )
        self.stop_btn.pack(side="left", fill="x", expand=True, padx=(8, 0))

        self._success = 0
        self._failed  = 0
        self._total   = 0
        self._running = False
        self._loop    = None
        self._thread  = None

    def _stat_box(self, parent, label, value, color):
        frame = tk.Frame(parent, bg=BORDER, bd=0)
        frame.pack(side="left", expand=True, fill="x", padx=(0, 6))
        tk.Label(frame, text=label, bg=BORDER, fg=MUTED,
                 font=("Segoe UI", 8)).pack(pady=(8, 0))
        val_lbl = tk.Label(frame, text=value, bg=BORDER, fg=color,
                           font=("Segoe UI", 16, "bold"))
        val_lbl.pack(pady=(0, 8))
        return val_lbl

    def _log(self, msg):
        def _do():
            self.log_text.config(state="normal")
            ts = datetime.now().strftime("%H:%M:%S")
            tag = "ok" if "✅" in msg else ("fail" if ("❌" in msg or "⚠️" in msg) else "info")
            self.log_text.insert("end", f"[{ts}] {msg}\n", tag)
            self.log_text.see("end")
            self.log_text.config(state="disabled")
        self.root.after(0, _do)

    def _update_progress(self, i, total, success, ok):
        def _do():
            self._success = success
            self._failed  = i - success
            pct = int(i / total * 100)
            self.progress["value"] = pct
            self.progress["maximum"] = 100
            self.pct_label.config(text=f"{pct}%")
            self.prog_label.config(text=f"Submission {i} of {total}")
            self.stat_ok.config(text=str(success))
            self.stat_fail.config(text=str(i - success))
            self.stat_left.config(text=str(total - i))
        self.root.after(0, _do)

    def _on_done(self, success, total):
        def _do():
            self._running = False
            self.run_btn.config(state="normal", bg=ACCENT)
            self.stop_btn.config(state="disabled")
            self.spin.config(state="normal")
            self.prog_label.config(text=f"Done! {success}/{total} submitted")
            self.pct_label.config(text="100%")
            self.progress["value"] = 100
            self._log(f"🎉 Finished! {success}/{total} submissions succeeded.")
        self.root.after(0, _do)

    def _start(self):
        if self._running:
            return
        count = self.count_var.get()
        self._total   = count
        self._success = 0
        self._failed  = 0
        self._running = True

        # Reset UI
        self.progress["value"] = 0
        self.pct_label.config(text="0%")
        self.prog_label.config(text="Starting...")
        self.stat_ok.config(text="0")
        self.stat_fail.config(text="0")
        self.stat_left.config(text=str(count))
        self.run_btn.config(state="disabled", bg=MUTED)
        self.stop_btn.config(state="normal")
        self.spin.config(state="disabled")

        self.log_text.config(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.config(state="disabled")
        self._log(f"🚀 Starting {count} submissions...")

        def thread_target():
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            try:
                self._loop.run_until_complete(
                    run_bot(count, self._log, self._update_progress, self._on_done)
                )
            except Exception as e:
                self._log(f"⚠️  Fatal error: {e}")
                self.root.after(0, lambda: self._on_done(self._success, count))
            finally:
                self._loop.close()

        self._thread = threading.Thread(target=thread_target, daemon=True)
        self._thread.start()

    def _stop(self):
        if self._loop and self._running:
            self._running = False
            self._loop.call_soon_threadsafe(self._loop.stop)
            self._log("🛑 Stopped by user.")
            self.run_btn.config(state="normal", bg=ACCENT)
            self.stop_btn.config(state="disabled")
            self.spin.config(state="normal")
            self.prog_label.config(text="Stopped")


if __name__ == "__main__":
    multiprocessing.freeze_support()
    root = tk.Tk()
    app = BotGUI(root)
    root.mainloop()
