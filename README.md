# 📚 Study Guardian

**Your webcam is watching. Pick up your phone and get roasted.**

Real-time computer vision project that detects when you grab your phone while studying and immediately calls you out with a loud alert + savage on-screen messages.

Built with **Python · OpenCV · Ultralytics YOLO · Pygame · Tkinter**.

![Python](https://img.shields.io/badge/Python-3.9%2B-blue) ![YOLO](https://img.shields.io/badge/YOLO-v8-orange) ![License](https://img.shields.io/badge/License-MIT-green)

---

## ✨ Features

- Real-time webcam object detection (YOLOv8)
- Detects **cell phones**
- Dark-themed control GUI (start/stop, hold time, confidence, sound toggle)
- Live video window with HUD + progress bar
- **Savage rotating call-out messages**
- Loud multi-beep alert sound
- Configurable hold time & cooldown
- Works on CPU (GPU recommended)

---

## 🚀 Quick Start

```bash
git clone https://github.com/YOUR_USERNAME/study-guardian.git
cd study-guardian

python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

pip install -r requirements.txt
python main.py
```

A control panel window will open. Click **START WATCHING**.  
A separate video window shows the live feed. Press **Q** in the video window (or Stop in the GUI) to quit.

---

## ⚙️ Options

You can still use command-line flags:

```bash
python main.py --model yolov8s.pt --conf 0.55 --hold 2.0 --camera 0
```

| Flag | Default | Description |
|------|---------|-------------|
| `--model` | `yolov8n.pt` | YOLO weights |
| `--camera` | `0` | Webcam index |
| `--conf` | `0.45` | Confidence threshold |
| `--hold` | `1.5` | Seconds phone must be visible |
| `--cooldown` | `8.0` | Seconds between alerts |
| `--no-sound` | off | Disable audio |

---

## 📁 Project Structure

```
study-guardian/
├── assets/
│   └── alert.wav
├── main.py
├── requirements.txt
├── README.md
├── LICENSE
└── .gitignore
```

---

## 🧠 What you'll learn

- Real-time YOLO inference with Ultralytics
- OpenCV drawing (boxes, HUD, overlays)
- Temporal state tracking (how long an object is visible)
- Pygame audio
- Tkinter GUI + threading with OpenCV

---

## 🔥 Example savage messages

- "PUT THE DAMN PHONE DOWN!"
- "YOUR GPA IS CRYING RIGHT NOW"
- "SCROLLING WON'T PAY THE BILLS"
- "THE ALGORITHM DOESN'T LOVE YOU BACK"
- "THIS IS WHY YOU'RE STILL SINGLE AND BROKE"
- ...and more

Edit the `SAVAGE_MESSAGES` list in `main.py` to make them as mean (or motivational) as you want.

---

## 📜 License

MIT

---

Stay focused.  
**Put the phone down.**
