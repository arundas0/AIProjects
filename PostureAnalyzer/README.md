# PostureAnalyzer - Running Form Check

A **$0 AI running coach** that analyzes your form from video using pose estimation and provides personalized feedback powered by Gemini AI.

## Quick Start

```bash
cd PostureAnalyzer
source venv/bin/activate

# Set your Gemini API key (get free at https://makersuite.google.com/app/apikey)
export GEMINI_API_KEY="your-key-here"

pip install -r requirements.txt
streamlit run app.py
# Open http://localhost:8501
```

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              PostureAnalyzer                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌──────────┐     ┌───────────────┐     ┌─────────────┐     ┌──────────┐  │
│   │  User    │────▶│  app.py       │────▶│pose_analyzer│────▶│  form_   │  │
│   │  Upload  │     │  (Streamlit)  │     │    .py      │     │ scorer.py│  │
│   └──────────┘     └───────────────┘     └─────────────┘     └──────────┘  │
│                            │                                       │        │
│                            │                                       ▼        │
│                            │                              ┌──────────────┐  │
│                            │                              │   gemini_    │  │
│                            │◀─────────────────────────────│  feedback.py │  │
│                            │                              └──────────────┘  │
│                            ▼                                       │        │
│                    ┌───────────────┐                               ▼        │
│                    │   Results     │◀────────────────────  ┌──────────────┐ │
│                    │   Display     │                       │ config.py    │ │
│                    └───────────────┘                       └──────────────┘ │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## End-to-End Request Flow

### Step 1: Video Upload (app.py)

```
User clicks "Upload" → Streamlit file_uploader → Temp file saved
```

- User uploads video (MP4, MOV, AVI, MKV supported)
- File saved to temporary location
- Video preview displayed

**Code path:** `app.py` → `st.file_uploader()` → `tempfile.NamedTemporaryFile()`

---

### Step 2: Pose Estimation (pose_analyzer.py)

```
Video frames → MediaPipe PoseLandmarker → 33 landmarks per frame
```

- `PoseAnalyzer.process_video()` reads video frame-by-frame
- MediaPipe neural network detects 33 body landmarks:
  - **Upper body:** shoulders, elbows, wrists, hips
  - **Lower body:** knees, ankles, heels, toes
- Skeleton overlay drawn on each frame
- Metrics calculated:
  - **Knee angle:** `calculate_angle(hip, knee, ankle)`
  - **Torso lean:** shoulder-hip line vs vertical
  - **Foot position:** ankle X relative to hip X

**Code path:** `app.py` → `PoseAnalyzer().process_video(temp_path)` → Returns `(output_video, RunningMetrics)`

---

### Step 3: Rule-Based Scoring (form_scorer.py)

```
RunningMetrics → FormScorer → ScoreBreakdown (0-100 score)
```

Each metric scored out of 25 points:

| Metric | Ideal Range | Scoring Logic |
|--------|-------------|---------------|
| Knee Angle | 160-175° | In range = 25pts, outside = reduced |
| Torso Lean | 5-15° forward | In range = 25pts, outside = reduced |
| Foot Strike | ±5 units from hip | Centered = 25pts, overstriding = reduced |
| Consistency | Low std deviation | Low variance = 25pts |

Thresholds loaded from `config.py`.

**Code path:** `app.py` → `FormScorer().calculate_score(metrics)` → Returns `ScoreBreakdown`

---

### Step 4: LLM Feedback (gemini_feedback.py)

```
ScoreBreakdown + Metrics → Gemini API → Personalized coaching text
```

- `GeminiFeedbackGenerator` reads API key from `GEMINI_API_KEY` env var
- Constructs prompt with all metrics and scores
- Calls Gemini model (configurable in `config.py`)
- Returns 2-3 sentences of personalized coaching advice

**Code path:** 
```python
gemini = GeminiFeedbackGenerator()
if gemini.is_available:
    llm_feedback = gemini.generate_feedback(
        avg_knee_angle=metrics.avg_knee_angle_at_contact,
        avg_torso_lean=metrics.avg_torso_lean,
        ...
    )
    score.llm_feedback = llm_feedback
```

**Fallback:** If API key missing or call fails, rule-based feedback is shown instead.

---

### Step 5: Results Display (app.py)

```
All data → Streamlit widgets → Interactive UI
```

Displayed components:
- **Score card:** Total score with color coding (green/blue/orange/red)
- **Progress bars:** Individual metric scores
- **Video player:** Skeleton overlay video
- **Metrics:** Raw measurements (angles, cadence)
- **Feedback cards:** Per-metric advice with emojis
- **AI Coach Says:** Gemini-generated personalized feedback

---

## Project Structure

```
PostureAnalyzer/
├── app.py              # Streamlit UI & orchestration
├── pose_analyzer.py    # MediaPipe pose estimation
├── form_scorer.py      # Rule-based scoring logic
├── gemini_feedback.py  # LLM feedback generation
├── config.py           # Centralized configuration
├── requirements.txt    # Dependencies
└── README.md           # This file
```

---

## Configuration (config.py)

All tunable parameters in one file:

```python
# LLM Settings
GEMINI_MODEL = "gemini-2.5-flash"

# Scoring Thresholds
IDEAL_KNEE_ANGLE_MIN = 160
IDEAL_KNEE_ANGLE_MAX = 175
IDEAL_TORSO_LEAN_MIN = 5
IDEAL_TORSO_LEAN_MAX = 15
IDEAL_FOOT_POSITION_MIN = -5
IDEAL_FOOT_POSITION_MAX = 5
```

---

## Dependencies

| Package | Purpose |
|---------|---------|
| `streamlit` | Web UI framework |
| `mediapipe` | Pose estimation AI |
| `opencv-python` | Video processing |
| `numpy` | Math operations |
| `google-genai` | Gemini API client |

---

## Tips for Best Results

1. **Side view** - Camera perpendicular to running direction
2. **Good lighting** - Avoid dark or backlit environments
3. **Fitted clothes** - Helps AI detect joints accurately
4. **Treadmill preferred** - Keeps you in frame consistently
5. **10-30 seconds** - Enough for consistent analysis
