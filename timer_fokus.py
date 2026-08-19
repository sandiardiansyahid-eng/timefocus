"""
Timer Fokus - aplikasi desktop sederhana untuk mengerjakan tugas dengan batas waktu.
Bunyi alarm otomatis saat waktu habis.

Cara jalankan langsung: python timer_fokus.py
Cara jadikan .exe: lihat instruksi yang diberikan bersama file ini (pakai PyInstaller).
"""

import time
import threading
import tkinter as tk
from tkinter import ttk

try:
    import winsound
    HAS_WINSOUND = True
except ImportError:
    HAS_WINSOUND = False

# ---------- Warna & tema ----------
BG = "#1b1e1c"
BG_SOFT = "#22261f"
ACCENT = "#e8a33d"
TEXT = "#f1ede4"
TEXT_DIM = "#9a9d93"
TRACK = "#34392f"
ALARM = "#e2574c"
ALARM_BG = "#2a1815"


class TimerFokus:
    def __init__(self, root):
        self.root = root
        self.root.title("Timer Fokus")
        self.root.geometry("380x560")
        self.root.resizable(False, False)
        self.root.configure(bg=BG)

        self.total_seconds = 25 * 60
        self.remaining_seconds = self.total_seconds
        self.end_time = None
        self.running = False
        self.after_id = None

        self.alarm_active = False
        self.alarm_after_id = None
        self.flash_after_id = None
        self.alarm_window = None

        self._build_ui()
        self._update_display()

    # ---------- UI ----------
    def _build_ui(self):
        eyebrow = tk.Label(
            self.root, text="TIMER FOKUS", font=("Segoe UI", 10, "bold"),
            fg=ACCENT, bg=BG,
        )
        eyebrow.pack(pady=(22, 6))

        self.task_var = tk.StringVar()
        task_entry = tk.Entry(
            self.root, textvariable=self.task_var, font=("Segoe UI", 11),
            fg=TEXT, bg=BG, insertbackground=TEXT, relief="flat",
            justify="center", highlightthickness=1,
            highlightbackground=TRACK, highlightcolor=ACCENT,
        )
        task_entry.insert(0, "")
        task_entry.pack(fill="x", padx=40, pady=(0, 22), ipady=6)
        self._task_placeholder(task_entry)

        # Countdown display
        self.time_label = tk.Label(
            self.root, text="25:00", font=("Consolas", 46, "bold"),
            fg=ACCENT, bg=BG,
        )
        self.time_label.pack(pady=(4, 2))

        self.status_label = tk.Label(
            self.root, text="siap", font=("Segoe UI", 9),
            fg=TEXT_DIM, bg=BG,
        )
        self.status_label.pack(pady=(0, 12))

        style = ttk.Style()
        style.theme_use("default")
        style.configure(
            "Fokus.Horizontal.TProgressbar",
            troughcolor=TRACK, background=ACCENT, thickness=6,
        )
        self.progress = ttk.Progressbar(
            self.root, style="Fokus.Horizontal.TProgressbar",
            orient="horizontal", length=280, mode="determinate", maximum=100,
        )
        self.progress.pack(pady=(0, 20))

        # Presets
        preset_frame = tk.Frame(self.root, bg=BG)
        preset_frame.pack(pady=(0, 14))
        self.preset_buttons = []
        for minutes in (5, 10, 15, 25, 45):
            b = tk.Button(
                preset_frame, text=f"{minutes} mnt", font=("Segoe UI", 9),
                fg=TEXT_DIM, bg=BG_SOFT, activebackground=BG_SOFT,
                activeforeground=ACCENT, relief="flat", padx=10, pady=6,
                bd=0, cursor="hand2",
                command=lambda m=minutes: self.set_preset(m),
            )
            b.pack(side="left", padx=4)
            self.preset_buttons.append((b, minutes))
        self._highlight_preset(25)

        # Custom time
        custom_frame = tk.Frame(self.root, bg=BG)
        custom_frame.pack(pady=(0, 22))
        tk.Label(custom_frame, text="Kustom:", font=("Segoe UI", 9), fg=TEXT_DIM, bg=BG).pack(side="left", padx=(0, 6))
        self.custom_min = tk.Spinbox(custom_frame, from_=0, to=180, width=4, font=("Consolas", 10))
        self.custom_min.pack(side="left")
        tk.Label(custom_frame, text=":", font=("Segoe UI", 9), fg=TEXT_DIM, bg=BG).pack(side="left", padx=2)
        self.custom_sec = tk.Spinbox(custom_frame, from_=0, to=59, width=4, font=("Consolas", 10))
        self.custom_sec.pack(side="left")
        tk.Button(
            custom_frame, text="Atur", font=("Segoe UI", 9), fg=BG, bg=ACCENT,
            relief="flat", bd=0, padx=10, pady=4, cursor="hand2",
            command=self.set_custom,
        ).pack(side="left", padx=(8, 0))

        # Controls
        control_frame = tk.Frame(self.root, bg=BG)
        control_frame.pack(pady=(4, 10), fill="x", padx=40)
        self.start_btn = tk.Button(
            control_frame, text="Mulai", font=("Segoe UI", 11, "bold"),
            fg="#241a08", bg=ACCENT, activebackground=ACCENT, relief="flat",
            bd=0, padx=10, pady=12, cursor="hand2", command=self.toggle_start_pause,
        )
        self.start_btn.pack(side="left", expand=True, fill="x", padx=(0, 8))

        reset_btn = tk.Button(
            control_frame, text="Reset", font=("Segoe UI", 11), fg=TEXT_DIM,
            bg=BG_SOFT, activebackground=BG_SOFT, relief="flat", bd=0,
            padx=10, pady=12, cursor="hand2", command=self.reset,
        )
        reset_btn.pack(side="left", expand=True, fill="x")

    def _task_placeholder(self, entry):
        placeholder = "Nama tugas (opsional)"
        entry.insert(0, placeholder)
        entry.config(fg=TEXT_DIM)

        def on_focus_in(_):
            if entry.get() == placeholder:
                entry.delete(0, "end")
                entry.config(fg=TEXT)

        def on_focus_out(_):
            if not entry.get():
                entry.insert(0, placeholder)
                entry.config(fg=TEXT_DIM)

        entry.bind("<FocusIn>", on_focus_in)
        entry.bind("<FocusOut>", on_focus_out)
        self._task_placeholder_text = placeholder
        self._task_entry = entry

    def get_task_name(self):
        val = self._task_entry.get().strip()
        return "" if val == self._task_placeholder_text else val

    def _highlight_preset(self, active_minutes):
        for b, minutes in self.preset_buttons:
            if minutes == active_minutes:
                b.config(bg="#3a3221", fg=ACCENT)
            else:
                b.config(bg=BG_SOFT, fg=TEXT_DIM)

    # ---------- Waktu ----------
    def _format(self, seconds):
        m, s = divmod(max(0, seconds), 60)
        return f"{m:02d}:{s:02d}"

    def _update_display(self):
        self.time_label.config(text=self._format(self.remaining_seconds))
        pct = (self.remaining_seconds / self.total_seconds * 100) if self.total_seconds else 0
        self.progress["value"] = pct

    def set_preset(self, minutes):
        self.stop_timer()
        self.total_seconds = minutes * 60
        self.remaining_seconds = self.total_seconds
        self._update_display()
        self._highlight_preset(minutes)
        self.status_label.config(text="siap")
        self.start_btn.config(text="Mulai")

    def set_custom(self):
        try:
            m = max(0, min(180, int(self.custom_min.get())))
            s = max(0, min(59, int(self.custom_sec.get())))
        except ValueError:
            return
        if m == 0 and s == 0:
            return
        self.stop_timer()
        self.total_seconds = m * 60 + s
        self.remaining_seconds = self.total_seconds
        self._update_display()
        self._highlight_preset(-1)
        self.status_label.config(text="siap")
        self.start_btn.config(text="Mulai")

    def toggle_start_pause(self):
        if self.running:
            self.pause_timer()
        else:
            self.start_timer()

    def start_timer(self):
        if self.remaining_seconds <= 0:
            self.remaining_seconds = self.total_seconds
        self.end_time = time.time() + self.remaining_seconds
        self.running = True
        self.start_btn.config(text="Jeda")
        self.status_label.config(text="berjalan")
        self._tick()

    def pause_timer(self):
        if self.after_id:
            self.root.after_cancel(self.after_id)
            self.after_id = None
        self.remaining_seconds = max(0, round(self.end_time - time.time()))
        self.running = False
        self.start_btn.config(text="Lanjutkan")
        self.status_label.config(text="jeda")

    def stop_timer(self):
        if self.after_id:
            self.root.after_cancel(self.after_id)
            self.after_id = None
        self.running = False

    def reset(self):
        self.stop_timer()
        self.remaining_seconds = self.total_seconds
        self._update_display()
        self.start_btn.config(text="Mulai")
        self.status_label.config(text="siap")
        self.stop_alarm()

    def _tick(self):
        self.remaining_seconds = round(self.end_time - time.time())
        if self.remaining_seconds <= 0:
            self.remaining_seconds = 0
            self._update_display()
            self.finish()
            return
        self._update_display()
        self.after_id = self.root.after(250, self._tick)

    # ---------- Alarm ----------
    def _play_beep_async(self):
        def run():
            if HAS_WINSOUND:
                winsound.Beep(880, 180)
                time.sleep(0.05)
                winsound.Beep(660, 220)
            else:
                print("\a", end="", flush=True)
        threading.Thread(target=run, daemon=True).start()

    def finish(self):
        self.running = False
        self.start_btn.config(text="Mulai")
        self.status_label.config(text="selesai")
        self.alarm_active = True
        self._play_beep_async()
        self._alarm_loop()
        self._flash_loop(True)
        self._show_alarm_window()

    def _alarm_loop(self):
        if not self.alarm_active:
            return
        self._play_beep_async()
        self.alarm_after_id = self.root.after(1400, self._alarm_loop)

    def _flash_loop(self, on):
        if not self.alarm_active:
            self.root.configure(bg=BG)
            return
        self.root.configure(bg=ALARM_BG if on else BG)
        self.flash_after_id = self.root.after(500, self._flash_loop, not on)

    def _show_alarm_window(self):
        task = self.get_task_name()
        win = tk.Toplevel(self.root)
        win.title("Waktu Habis")
        win.configure(bg="#1e1614")
        win.geometry("320x220")
        win.resizable(False, False)
        win.attributes("-topmost", True)
        win.protocol("WM_DELETE_WINDOW", self.stop_alarm)
        self.alarm_window = win

        tk.Label(
            win, text="WAKTU HABIS", font=("Consolas", 22, "bold"),
            fg=ALARM, bg="#1e1614",
        ).pack(pady=(28, 10))

        msg = f'Tugas: "{task}"' if task else "Waktu kerja kamu sudah selesai."
        tk.Label(
            win, text=msg, font=("Segoe UI", 10), fg=TEXT, bg="#1e1614",
            wraplength=260, justify="center",
        ).pack(pady=(0, 20))

        tk.Button(
            win, text="Matikan Alarm", font=("Segoe UI", 10, "bold"),
            fg="#241a08", bg=ACCENT, relief="flat", bd=0, padx=14, pady=8,
            cursor="hand2", command=self.stop_alarm,
        ).pack()

    def stop_alarm(self):
        self.alarm_active = False
        if self.alarm_after_id:
            self.root.after_cancel(self.alarm_after_id)
            self.alarm_after_id = None
        if self.flash_after_id:
            self.root.after_cancel(self.flash_after_id)
            self.flash_after_id = None
        self.root.configure(bg=BG)
        if self.alarm_window is not None:
            try:
                self.alarm_window.destroy()
            except tk.TclError:
                pass
            self.alarm_window = None
        self.remaining_seconds = self.total_seconds
        self._update_display()
        self.status_label.config(text="siap")


def main():
    root = tk.Tk()
    TimerFokus(root)
    root.mainloop()


if __name__ == "__main__":
    main()
