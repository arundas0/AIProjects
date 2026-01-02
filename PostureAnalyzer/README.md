# PostureAnalyzer - Running Form Check

A **$0 AI running coach** that analyzes your form from video using pose estimation.

## Quick Start

```bash
cd PostureAnalyzer
source venv/bin/activate
streamlit run app.py
# Open http://localhost:8501
```

---

## How It Works (End-to-End)

### 🎬 Stage 1: Video Upload
Upload a 10-30 second clip of yourself running (side profile). Treadmill works best.

### 🤖 Stage 2: AI Model
**MediaPipe PoseLandmarker** (neural network) detects 33 body landmarks per frame:
- Shoulders, elbows, wrists
- Hips, knees, ankles
- Hands and feet

### 📐 Stage 3: Biomechanics

From landmarks, we calculate:

| Metric | How It's Measured | Ideal |
|--------|-------------------|-------|
| **Knee Angle** | Hip→Knee→Ankle angle at impact | 160-175° |
| **Torso Lean** | Shoulder vs Hip from vertical | 5-15° forward |
| **Foot Strike** | Ankle position relative to hip | Under hip |

### 🎯 Stage 4: Scoring

Each metric = 25 points max, **Total = 100 points**

| Score | Grade |
|-------|-------|
| 90+ | 🏆 Excellent |
| 75-89 | 👍 Good |
| 60-74 | ⚡ Fair |
| <60 | 🔧 Needs work |

### 🎨 Stage 5: Output
- Skeleton overlay video
- Metrics dashboard
- Actionable feedback

---

## Project Structure

```
PostureAnalyzer/
├── app.py              # Streamlit UI
├── pose_analyzer.py    # MediaPipe processing
├── form_scorer.py      # Scoring algorithm
├── requirements.txt    # Dependencies
└── README.md           # This file
```

---

## Dependencies

- `streamlit` - Web UI
- `mediapipe` - Pose estimation AI
- `opencv-python` - Video processing
- `numpy` - Math operations

---

## Tips for Best Results

1. **Side view** - Camera perpendicular to running direction
2. **Good lighting** - Avoid dark or backlit
3. **Fitted clothes** - Helps AI detect joints
4. **Treadmill preferred** - Keeps you in frame
