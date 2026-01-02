"""
Configuration - Centralized settings for PostureAnalyzer
"""

# =============================================================================
# Gemini LLM Settings
# =============================================================================
GEMINI_MODEL = "gemini-2.5-flash"

# =============================================================================
# Scoring Thresholds (based on running biomechanics research)
# =============================================================================

# Knee angle at ground contact (degrees)
IDEAL_KNEE_ANGLE_MIN = 160
IDEAL_KNEE_ANGLE_MAX = 175

# Torso forward lean (degrees)
IDEAL_TORSO_LEAN_MIN = 5
IDEAL_TORSO_LEAN_MAX = 15

# Foot position relative to hip (normalized units, positive = ahead)
IDEAL_FOOT_POSITION_MIN = -5
IDEAL_FOOT_POSITION_MAX = 5

# =============================================================================
# Score Weights (out of 100 total)
# =============================================================================
SCORE_WEIGHT_KNEE = 25
SCORE_WEIGHT_TORSO = 25
SCORE_WEIGHT_FOOT = 25
SCORE_WEIGHT_CONSISTENCY = 25

# =============================================================================
# Pro Athlete Benchmark (Elite Distance Runner Profile)
# =============================================================================
PRO_ATHLETE_STATS = {
    "knee_angle": 165,      # Optimal flexion for power/efficiency
    "torso_lean": 10,       # Perfect forward drive
    "foot_position": 0,     # Direct center of mass impact
    "consistency": 95       # Extremely consistent form
}

# Normalization ranges for radar chart (min/max reasonable values)
RADAR_RANGES = {
    "knee_angle": (130, 180),
    "torso_lean": (-5, 30),
    "foot_position": (-30, 30)
}
