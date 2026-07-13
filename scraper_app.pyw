#!/usr/bin/env python3
"""Jewels Scraper - desktop app.

Tkinter front-end for catalog_scraper.py: paste a product-category URL,
choose how many products and where to save them, then watch live progress
while photos, DETAILS screenshots and info files land in numbered folders.

Launch with:  pythonw scraper_app.pyw   (or double-click via the desktop
launcher that Setup_Jewels_Scraper.bat creates). catalog_scraper.py must
sit in the same folder.
"""

import os
import queue
import re
import subprocess
import sys
import threading
import json
from pathlib import Path

import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

APP_DIR = Path(__file__).resolve().parent
SCRAPER = APP_DIR / "catalog_scraper.py"
DEFAULT_URL = "https://www.quince.com/women/jewelry/necklaces-all/lab-grown-diamond-necklaces"
SETTINGS_PATH = Path(os.environ.get("APPDATA", str(Path.home()))) / "JewelsScraper" / "settings.json"
CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0


def python_exe():
    """Prefer python.exe over pythonw.exe for child processes so their
    output can be piped normally."""
    exe = Path(sys.executable)
    if exe.name.lower() == "pythonw.exe":
        sibling = exe.with_name("python.exe")
        if sibling.exists():
            return str(sibling)
    return str(exe)


def default_out_folder():
    if os.name == "nt" and os.path.exists("D:\\"):
        return r"D:\jewels\neckless\1"
    return str(Path.home() / "jewels" / "1")


def load_settings():
    try:
        return json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_settings(data):
    try:
        SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
        SETTINGS_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception:
        pass


class App:
    def __init__(self, root):
        self.root = root
        self.proc = None
        self.worker = None
        self.q = queue.Queue()
        self.photos_done = 0
        self.summary_line = ""
        saved = load_settings()

        root.title("Jewels Scraper")
        root.minsize(760, 560)
        frm = ttk.Frame(root, padding=12)
        frm.pack(fill="both", expand=True)
        frm.columnconfigure(1, weight=1)

        ttk.Label(frm, text="Product category (or single product) URL:").grid(
            row=0, column=0, columnspan=3, sticky="w")
        self.url_var = tk.StringVar(value=saved.get("url", DEFAULT_URL))
        ttk.Entry(frm, textvariable=self.url_var).grid(
            row=1, column=0, columnspan=3, sticky="ew", pady=(2, 10))

        ttk.Label(frm, text="How many products:").grid(row=2, column=0, sticky="w")
        self.limit_var = tk.StringVar(value=str(saved.get("limit", 15)))
        ttk.Spinbox(frm, from_=1, to=200, textvariable=self.limit_var, width=6).grid(
            row=2, column=1, sticky="w")
        self.headed_var = tk.BooleanVar(value=bool(saved.get("headed", True)))
        ttk.Checkbutton(frm, text="Show the browser while it works",
                        variable=self.headed_var).grid(row=2, column=2, sticky="e")

        ttk.Label(frm, text="Save into folder:").grid(row=3, column=0, sticky="w", pady=(10, 0))
        self.out_var = tk.StringVar(value=saved.get("out", default_out_folder()))
        ttk.Entry(frm, textvariable=self.out_var).grid(
            row=4, column=0, columnspan=2, sticky="ew")
        ttk.Button(frm, text="Browse...", command=self.pick_folder).grid(
            row=4, column=2, sticky="e", padx=(8, 0))

        btns = ttk.Frame(frm)
        btns.grid(row=5, column=0, columnspan=3, sticky="ew", pady=12)
        self.start_btn = ttk.Button(btns, text="Start scraping", command=self.start)
        self.start_btn.pack(side="left")
        self.stop_btn = ttk.Button(btns, text="Stop", command=self.stop, state="disabled")
        self.stop_btn.pack(side="left", padx=8)
        self.open_btn = ttk.Button(btns, text="Open output folder",
                                   command=self.open_folder, state="disabled")
        self.open_btn.pack(side="left")

        self.bar = ttk.Progressbar(frm, mode="determinate")
        self.bar.grid(row=6, column=0, columnspan=3, sticky="ew")
        self.status_var = tk.StringVar(value="Ready.")
        ttk.Label(frm, textvariable=self.status_var).grid(
            row=7, column=0, columnspan=3, sticky="w", pady=(4, 8))

        self.log = scrolledtext.ScrolledText(frm, height=18, state="disabled",
                                             font=("Consolas", 9))
        self.log.grid(row=8, column=0, columnspan=3, sticky="nsew")
        frm.rowconfigure(8, weight=1)

        root.protocol("WM_DELETE_WINDOW", self.on_close)
        root.after(100, self.poll_queue)

    # ------------------------------------------------------------------ UI

    def pick_folder(self):
        chosen = filedialog.askdirectory(title="Choose where to save the products")
        if chosen:
            self.out_var.set(os.path.normpath(chosen))

    def post(self, line):
        self.q.put(("line", line.rstrip("\n")))

    def append_log(self, text):
        self.log.configure(state="normal")
        self.log.insert("end", text + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def set_running(self, running):
        state = "disabled" if running else "normal"
        self.start_btn.configure(state=state)
        self.stop_btn.configure(state="normal" if running else "disabled")

    def open_folder(self):
        out = self.out_var.get().strip()
        if not out:
            return
        try:
            if os.name == "nt":
                os.startfile(out)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", out])
            else:
                subprocess.Popen(["xdg-open", out])
        except Exception as exc:
            messagebox.showerror("Jewels Scraper", f"Could not open folder:\n{exc}")

    # ------------------------------------------------------------ scraping

    def start(self):
        url = self.url_var.get().strip()
        out = self.out_var.get().strip()
        try:
            limit = max(1, int(self.limit_var.get()))
        except ValueError:
            messagebox.showerror("Jewels Scraper", "'How many products' must be a number.")
            return
        if not url.lower().startswith(("http://", "https://")):
            messagebox.showerror("Jewels Scraper", "Please paste a full URL starting with https://")
            return
        if not out:
            messagebox.showerror("Jewels Scraper", "Please choose an output folder.")
            return
        if not SCRAPER.exists():
            messagebox.showerror("Jewels Scraper",
                                 f"catalog_scraper.py was not found next to this app:\n{SCRAPER}")
            return
        save_settings({"url": url, "out": out, "limit": limit,
                       "headed": self.headed_var.get()})
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")
        self.photos_done = 0
        self.summary_line = ""
        self.blocked = False
        self.bar.configure(value=0, maximum=100)
        self.status_var.set("Starting...")
        self.open_btn.configure(state="disabled")
        self.set_running(True)
        self.worker = threading.Thread(
            target=self.run_job, args=(url, out, limit, self.headed_var.get()), daemon=True)
        self.worker.start()

    def run_job(self, url, out, limit, headed):
        py = python_exe()
        try:
            self.post("Checking setup (fast after the first time)...")
            for cmd in ([py, "-m", "pip", "install", "--quiet",
                         "playwright", "requests", "pillow"],
                        [py, "-m", "playwright", "install", "chromium"]):
                r = subprocess.run(cmd, capture_output=True, text=True,
                                   creationflags=CREATE_NO_WINDOW)
                tail = (r.stdout or "") + (r.stderr or "")
                for ln in tail.strip().splitlines()[-3:]:
                    self.post("  " + ln)
                if r.returncode != 0:
                    self.post(f"Setup step failed ({' '.join(cmd[2:4])}). "
                              "Check your internet connection and try again.")
                    self.q.put(("done", 1))
                    return
            self.post("Setup OK. Starting the scrape...\n")
            cmd = [py, "-u", str(SCRAPER),
                   "--category-url", url, "--limit", str(limit), "--out", out,
                   "--headed" if headed else "--headless"]
            self.proc = subprocess.Popen(
                cmd, cwd=str(APP_DIR), stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, text=True, bufsize=1,
                creationflags=CREATE_NO_WINDOW)
            for line in self.proc.stdout:
                self.q.put(("line", line.rstrip("\n")))
            rc = self.proc.wait()
            self.q.put(("done", rc))
        except Exception as exc:
            self.q.put(("line", f"Unexpected error: {exc}"))
            self.q.put(("done", 1))

    def stop(self):
        if self.proc and self.proc.poll() is None:
            self.post("Stopping...")
            try:
                if os.name == "nt":
                    subprocess.run(["taskkill", "/F", "/T", "/PID", str(self.proc.pid)],
                                   capture_output=True, creationflags=CREATE_NO_WINDOW)
                else:
                    self.proc.terminate()
            except Exception:
                pass

    # ------------------------------------------------------------- updates

    def poll_queue(self):
        try:
            while True:
                kind, payload = self.q.get_nowait()
                if kind == "line":
                    self.append_log(payload)
                    self.digest(payload)
                elif kind == "done":
                    self.finish(payload)
        except queue.Empty:
            pass
        self.root.after(100, self.poll_queue)

    def digest(self, line):
        s = line.strip()
        m = re.match(r"\[(\d+)/(\d+)\]", s)
        if m:
            cur, total = int(m.group(1)), int(m.group(2))
            self.bar.configure(maximum=total, value=cur - 1)
            self.status_var.set(f"Product {cur} of {total}  "
                                f"({self.photos_done} photos so far)")
            return
        if s.startswith("photo_"):
            self.photos_done += 1
            base = self.status_var.get().split("(")[0].strip()
            if base:
                self.status_var.set(f"{base}  ({self.photos_done} photos so far)")
            return
        if s.startswith("Done:"):
            self.summary_line = s
        if "COULD NOT SCRAPE THIS SITE" in s or "protected by anti-bot" in s:
            self.blocked = True

    def finish(self, rc):
        self.proc = None
        self.set_running(False)
        self.bar.configure(value=self.bar["maximum"])
        self.open_btn.configure(state="normal")
        if self.blocked or rc == 3:
            self.status_var.set("This site blocked the scraper (anti-bot protection).")
            messagebox.showwarning(
                "Jewels Scraper",
                "This website is protected by anti-bot software and blocked "
                "the browser, so nothing could be downloaded.\n\n"
                "Big retailers and marketplaces (Brilliant Earth, Amazon, Etsy...) "
                "usually can't be scraped. Smaller brand shops — especially "
                "Shopify stores — normally work. See the log for tips.")
        elif self.summary_line:
            self.status_var.set(self.summary_line)
            messagebox.showinfo("Jewels Scraper", self.summary_line +
                                "\n\nOpening the output folder now.")
            self.open_folder()
        elif rc == 0:
            self.status_var.set("Finished.")
        else:
            self.status_var.set("Stopped or failed - see the log above.")

    def on_close(self):
        if self.proc and self.proc.poll() is None:
            if not messagebox.askyesno("Jewels Scraper",
                                       "A scrape is still running. Stop it and exit?"):
                return
            self.stop()
        self.root.destroy()


def main():
    root = tk.Tk()
    try:
        ttk.Style().theme_use("vista" if os.name == "nt" else "clam")
    except tk.TclError:
        pass
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
