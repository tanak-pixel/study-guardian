#!/usr/bin/env python3
"""
Study Guardian - Phone Detection Alert System
==============================================
Your webcam is watching. Pick up your phone and get roasted.

Stack: Python · OpenCV · Ultralytics YOLO · Pygame · Tkinter
"""

import cv2
import time
import threading
import argparse
from pathlib import Path
from ultralytics import YOLO
import pygame
import tkinter as tk
from tkinter import ttk, messagebox


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
DEFAULT_MODEL = "yolov8n.pt"
PHONE_CLASS_ID = 67                   # COCO "cell phone"
CONFIDENCE_THRESHOLD = 0.45
PHONE_HOLD_SECONDS = 1.5
COOLDOWN_SECONDS = 8.0
ALERT_SOUND = Path(__file__).parent / "assets" / "alert.wav"
WINDOW_NAME = "Study Guardian"

# Savage call-out messages
SAVAGE_MESSAGES = [
    "PUT THE DAMN PHONE DOWN!",
    "BACK TO THE BOOKS, ADDICT!",
    "YOUR GPA IS CRYING RIGHT NOW",
    "SCROLLING WON'T PAY THE BILLS",
    "PHONE DETECTED. DISAPPOINTMENT LOADING...",
    "FOCUS MODE: YOU'RE FAILING IT",
    "THAT NOTIFICATION CAN WAIT. YOUR FUTURE CAN'T.",
    "CAUGHT RED-HANDED. AGAIN.",
    "THE ALGORITHM DOESN'T LOVE YOU BACK",
    "STUDY HARDER. YOUR PHONE ALREADY KNOWS YOU'RE WEAK.",
    "THIS IS WHY YOU'RE STILL SINGLE AND BROKE",
    "DELETE TIKTOK. TOUCH GRASS. OPEN THE TEXTBOOK.",
]


class StudyGuardianApp:
    def __init__(self, args):
        self.args = args
        self.running = False
        self.sound_enabled = not args.no_sound
        self.hold_seconds = args.hold
        self.conf = args.conf
        self.cooldown = args.cooldown

        self.model = None
        self.cap = None
        self.alert_sound = None
        self.phone_visible_since = None
        self.last_alert_time = 0.0
        self.showing_callout = False
        self.callout_until = 0.0
        self.msg_idx = 0
        self.current_status = "Ready"
        self.phone_detected = False
        self.phone_timer = 0.0

        self._build_gui()
        self._init_audio()

    # ------------------------------------------------------------------
    # GUI
    # ------------------------------------------------------------------
    def _build_gui(self):
        self.root = tk.Tk()
        self.root.title("Study Guardian 📚")
        self.root.geometry("380x520")
        self.root.resizable(False, False)
        self.root.configure(bg="#1a1a2e")

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TLabel", background="#1a1a2e", foreground="#eaeaea", font=("Segoe UI", 10))
        style.configure("Title.TLabel", font=("Segoe UI", 16, "bold"), foreground="#00ffb3")
        style.configure("Status.TLabel", font=("Segoe UI", 11, "bold"))
        style.configure("TButton", font=("Segoe UI", 11, "bold"), padding=8)
        style.configure("TCheckbutton", background="#1a1a2e", foreground="#eaeaea", font=("Segoe UI", 10))
        style.configure("TScale", background="#1a1a2e")

        # Title
        ttk.Label(self.root, text="STUDY GUARDIAN", style="Title.TLabel").pack(pady=(20, 5))
        ttk.Label(self.root, text="Your webcam is watching...").pack(pady=(0, 15))

        # Status frame
        status_frame = tk.Frame(self.root, bg="#16213e", padx=15, pady=12)
        status_frame.pack(fill="x", padx=20, pady=5)
        self.status_var = tk.StringVar(value="● Idle – press Start")
        self.status_label = ttk.Label(status_frame, textvariable=self.status_var, style="Status.TLabel")
        self.status_label.pack()

        # Controls
        ctrl = tk.Frame(self.root, bg="#1a1a2e")
        ctrl.pack(fill="x", padx=25, pady=15)

        # Hold time
        ttk.Label(ctrl, text="Hold time before alert (seconds)").pack(anchor="w")
        self.hold_var = tk.DoubleVar(value=self.hold_seconds)
        hold_scale = ttk.Scale(ctrl, from_=0.5, to=5.0, variable=self.hold_var, orient="horizontal")
        hold_scale.pack(fill="x", pady=(2, 8))
        self.hold_label = ttk.Label(ctrl, text=f"{self.hold_seconds:.1f}s")
        self.hold_label.pack(anchor="e")
        hold_scale.configure(command=lambda v: self.hold_label.config(text=f"{float(v):.1f}s"))

        # Confidence
        ttk.Label(ctrl, text="Detection confidence").pack(anchor="w", pady=(8, 0))
        self.conf_var = tk.DoubleVar(value=self.conf)
        conf_scale = ttk.Scale(ctrl, from_=0.2, to=0.9, variable=self.conf_var, orient="horizontal")
        conf_scale.pack(fill="x", pady=(2, 8))
        self.conf_label = ttk.Label(ctrl, text=f"{self.conf:.2f}")
        self.conf_label.pack(anchor="e")
        conf_scale.configure(command=lambda v: self.conf_label.config(text=f"{float(v):.2f}"))

        # Sound toggle
        self.sound_var = tk.BooleanVar(value=self.sound_enabled)
        ttk.Checkbutton(
            ctrl, text="🔊 Sound alerts", variable=self.sound_var,
            command=self._toggle_sound
        ).pack(anchor="w", pady=10)

        # Buttons
        btn_frame = tk.Frame(self.root, bg="#1a1a2e")
        btn_frame.pack(pady=10)

        self.start_btn = tk.Button(
            btn_frame, text="▶  START WATCHING", width=18, height=2,
            bg="#00b894", fg="white", activebackground="#00a381",
            font=("Segoe UI", 11, "bold"), relief="flat", cursor="hand2",
            command=self.start
        )
        self.start_btn.pack(side="left", padx=6)

        self.stop_btn = tk.Button(
            btn_frame, text="■  STOP", width=10, height=2,
            bg="#e17055", fg="white", activebackground="#d63031",
            font=("Segoe UI", 11, "bold"), relief="flat", cursor="hand2",
            command=self.stop, state="disabled"
        )
        self.stop_btn.pack(side="left", padx=6)

        # Tips
        tip = tk.Label(
            self.root,
            text="Tip: Keep the phone out of frame while studying.\nPress Q in the video window to quit.",
            bg="#1a1a2e", fg="#888", font=("Segoe UI", 9), justify="center"
        )
        tip.pack(pady=15)

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def _toggle_sound(self):
        self.sound_enabled = self.sound_var.get()

    def _init_audio(self):
        try:
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            if ALERT_SOUND.exists():
                self.alert_sound = pygame.mixer.Sound(str(ALERT_SOUND))
        except Exception as e:
            print(f"[WARN] Audio init failed: {e}")
            self.alert_sound = None

    # ------------------------------------------------------------------
    # Start / Stop
    # ------------------------------------------------------------------
    def start(self):
        if self.running:
            return
        self.hold_seconds = self.hold_var.get()
        self.conf = self.conf_var.get()

        self.status_var.set("● Loading YOLO model...")
        self.root.update()

        try:
            self.model = YOLO(self.args.model)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load model:\n{e}")
            self.status_var.set("● Error loading model")
            return

        self.cap = cv2.VideoCapture(self.args.camera)
        if not self.cap.isOpened():
            messagebox.showerror("Error", f"Cannot open camera {self.args.camera}")
            self.status_var.set("● Camera error")
            return

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

        self.running = True
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.status_var.set("● Watching... no phone detected")

        self.thread = threading.Thread(target=self._video_loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.cap:
            self.cap.release()
            self.cap = None
        cv2.destroyAllWindows()
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self.status_var.set("● Stopped")
        self.current_status = "Stopped"

    def on_close(self):
        self.stop()
        if pygame.mixer.get_init():
            pygame.mixer.quit()
        self.root.destroy()

    # ------------------------------------------------------------------
    # Video + Detection loop
    # ------------------------------------------------------------------
    def _video_loop(self):
        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                break

            frame = cv2.flip(frame, 1)  # mirror

            results = self.model(frame, conf=self.conf, verbose=False)[0]

            self.phone_detected = False
            for box in results.boxes:
                cls_id = int(box.cls[0])
                conf = float(box.conf[0])
                if cls_id == PHONE_CLASS_ID:
                    self.phone_detected = True
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 60, 255), 3)
                    cv2.putText(
                        frame, f"phone {conf:.2f}", (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 60, 255), 2, cv2.LINE_AA
                    )

            now = time.time()

            if self.phone_detected:
                if self.phone_visible_since is None:
                    self.phone_visible_since = now
                self.phone_timer = now - self.phone_visible_since
            else:
                self.phone_visible_since = None
                self.phone_timer = 0.0

            # Trigger alert
            if (
                self.phone_detected
                and self.phone_timer >= self.hold_seconds
                and (now - self.last_alert_time) >= self.cooldown
            ):
                self.last_alert_time = now
                self.showing_callout = True
                self.callout_until = now + 3.5
                self.msg_idx = (self.msg_idx + 1) % len(SAVAGE_MESSAGES)

                if self.alert_sound and self.sound_enabled:
                    self.alert_sound.play()

                print(f"[ALERT] {SAVAGE_MESSAGES[self.msg_idx]}")

            # Status text for GUI + HUD
            if self.showing_callout and now < self.callout_until:
                status = "🚨 ALERT – YOU GOT CAUGHT"
                self._draw_callout(frame, SAVAGE_MESSAGES[self.msg_idx])
            elif self.phone_detected:
                status = f"📱 Phone visible ({self.phone_timer:.1f}s)"
            else:
                status = "✅ Focus mode – no phone"
                self.showing_callout = False

            self.current_status = status
            # Update GUI status from this thread safely
            try:
                self.root.after(0, lambda s=status: self.status_var.set("● " + s))
            except Exception:
                pass

            self._draw_hud(frame, status)
            cv2.imshow(WINDOW_NAME, frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                self.root.after(0, self.stop)
                break

        self.running = False

    # ------------------------------------------------------------------
    # Drawing helpers
    # ------------------------------------------------------------------
    def _draw_hud(self, frame, status: str):
        h, w = frame.shape[:2]
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, 70), (15, 15, 25), -1)
        cv2.addWeighted(overlay, 0.65, frame, 0.35, 0, frame)

        cv2.putText(frame, "STUDY GUARDIAN", (15, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.85, (0, 255, 180), 2, cv2.LINE_AA)

        color = (0, 60, 255) if self.phone_detected else (80, 255, 120)
        cv2.putText(frame, status, (15, 55),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2, cv2.LINE_AA)

        if self.phone_detected and self.phone_timer > 0:
            bar_w = int(min(self.phone_timer / self.hold_seconds, 1.0) * 200)
            cv2.rectangle(frame, (w - 220, 20), (w - 20, 40), (40, 40, 50), -1)
            cv2.rectangle(frame, (w - 220, 20), (w - 220 + bar_w, 40), (0, 80, 255), -1)
            cv2.putText(frame, f"{self.phone_timer:.1f}s", (w - 210, 55),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1, cv2.LINE_AA)

    def _draw_callout(self, frame, message: str):
        h, w = frame.shape[:2]
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, h // 2 - 70), (w, h // 2 + 70), (0, 0, 160), -1)
        cv2.addWeighted(overlay, 0.8, frame, 0.2, 0, frame)

        font = cv2.FONT_HERSHEY_SIMPLEX
        scale = 1.15
        thickness = 3
        (tw, th), _ = cv2.getTextSize(message, font, scale, thickness)
        x = (w - tw) // 2
        y = h // 2 + th // 2
        cv2.putText(frame, message, (x, y), font, scale, (255, 255, 255), thickness, cv2.LINE_AA)

    def run(self):
        self.root.mainloop()


def parse_args():
    parser = argparse.ArgumentParser(description="Study Guardian – YOLO phone detector")
    parser.add_argument("--model", type=str, default=DEFAULT_MODEL)
    parser.add_argument("--camera", type=int, default=0)
    parser.add_argument("--conf", type=float, default=CONFIDENCE_THRESHOLD)
    parser.add_argument("--hold", type=float, default=PHONE_HOLD_SECONDS)
    parser.add_argument("--cooldown", type=float, default=COOLDOWN_SECONDS)
    parser.add_argument("--no-sound", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    print("=" * 50)
    print("  Study Guardian – Phone Detection Alert")
    print("  GUI control panel + live webcam feed")
    print("=" * 50)
    app = StudyGuardianApp(args)
    app.run()
