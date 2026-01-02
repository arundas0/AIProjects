"""
Form Scorer - Calculate running form score based on biomechanics
"""
from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class ScoreBreakdown:
    """Detailed score breakdown"""
    knee_score: int  # 0-25
    knee_feedback: str
    
    torso_score: int  # 0-25
    torso_feedback: str
    
    foot_strike_score: int  # 0-25
    foot_strike_feedback: str
    
    consistency_score: int  # 0-25
    consistency_feedback: str
    
    total_score: int  # 0-100
    overall_feedback: str
    
    llm_feedback: str = None  # Optional LLM-generated personalized coaching


class FormScorer:
    """
    Score running form based on biomechanical principles.
    
    Scoring rubric (100 points total):
    - Knee angle at impact: 25 pts (ideal: 160-175° slight flexion)
    - Torso lean: 25 pts (ideal: 5-15° forward lean)
    - Foot strike position: 25 pts (ideal: under or slightly ahead of hip)
    - Consistency: 25 pts (low variance in metrics)
    """
    
    def __init__(self):
        from config import (
            IDEAL_KNEE_ANGLE_MIN, IDEAL_KNEE_ANGLE_MAX,
            IDEAL_TORSO_LEAN_MIN, IDEAL_TORSO_LEAN_MAX,
            IDEAL_FOOT_POSITION_MIN, IDEAL_FOOT_POSITION_MAX
        )
        self.IDEAL_KNEE_ANGLE = (IDEAL_KNEE_ANGLE_MIN, IDEAL_KNEE_ANGLE_MAX)
        self.IDEAL_TORSO_LEAN = (IDEAL_TORSO_LEAN_MIN, IDEAL_TORSO_LEAN_MAX)
        self.IDEAL_FOOT_POSITION = (IDEAL_FOOT_POSITION_MIN, IDEAL_FOOT_POSITION_MAX)
    
    def score_knee_angle(self, avg_angle: float) -> Tuple[int, str]:
        """Score knee angle at ground contact"""
        ideal_low, ideal_high = self.IDEAL_KNEE_ANGLE
        ideal_center = (ideal_low + ideal_high) / 2
        
        if ideal_low <= avg_angle <= ideal_high:
            score = 25
            feedback = "✅ Excellent knee flexion at impact. Good shock absorption."
        elif 150 <= avg_angle < ideal_low:
            score = 20
            feedback = "⚠️ Knee slightly more bent than ideal. May indicate over-flexion."
        elif ideal_high < avg_angle <= 180:
            score = 18
            feedback = "⚠️ Knee too straight at impact. Increase flexion for better shock absorption."
        elif 140 <= avg_angle < 150:
            score = 12
            feedback = "⚠️ Significant knee flexion. Check if you're running too slow or overstriding."
        else:
            score = 8
            feedback = "❌ Knee angle outside normal range. Consider gait analysis."
        
        return score, feedback
    
    def score_torso_lean(self, avg_lean: float) -> Tuple[int, str]:
        """Score torso lean angle"""
        ideal_low, ideal_high = self.IDEAL_TORSO_LEAN
        
        if ideal_low <= avg_lean <= ideal_high:
            score = 25
            feedback = "✅ Perfect forward lean. Great running posture!"
        elif 0 <= avg_lean < ideal_low:
            score = 18
            feedback = "⚠️ Too upright. Lean slightly forward from ankles, not waist."
        elif ideal_high < avg_lean <= 25:
            score = 15
            feedback = "⚠️ Leaning too far forward. May cause back strain over time."
        elif -10 <= avg_lean < 0:
            score = 10
            feedback = "⚠️ Leaning backward. This is inefficient and may indicate fatigue."
        else:
            score = 5
            feedback = "❌ Significant postural issue. Focus on core stability."
        
        return score, feedback
    
    def score_foot_strike(self, avg_foot_position: float) -> Tuple[int, str]:
        """Score foot strike position relative to hip"""
        ideal_low, ideal_high = self.IDEAL_FOOT_POSITION
        
        if ideal_low <= avg_foot_position <= ideal_high:
            score = 25
            feedback = "✅ Foot landing under your center of mass. Efficient!"
        elif ideal_high < avg_foot_position <= 15:
            score = 18
            feedback = "⚠️ Slight overstriding. Try increasing cadence to shorten stride."
        elif avg_foot_position > 15:
            score = 10
            feedback = "❌ Significant overstriding. This creates braking forces and injury risk."
        elif -15 <= avg_foot_position < ideal_low:
            score = 15
            feedback = "⚠️ Foot landing behind hip. Unusual - may indicate short stride."
        else:
            score = 8
            feedback = "❌ Foot position very unusual. Review video for accuracy."
        
        return score, feedback
    
    def score_consistency(self, frame_metrics: list) -> Tuple[int, str]:
        """Score consistency of form across frames"""
        if len(frame_metrics) < 5:
            return 15, "⚠️ Not enough frames to assess consistency."
        
        import numpy as np
        
        knee_std = np.std([m.knee_angle for m in frame_metrics])
        lean_std = np.std([m.torso_lean for m in frame_metrics])
        
        # Lower variance = more consistent = better
        avg_std = (knee_std + lean_std) / 2
        
        if avg_std < 5:
            score = 25
            feedback = "✅ Very consistent form throughout. Great control!"
        elif avg_std < 10:
            score = 20
            feedback = "✅ Good consistency. Minor variations are normal."
        elif avg_std < 15:
            score = 15
            feedback = "⚠️ Moderate variability. Focus on maintaining form when tired."
        elif avg_std < 25:
            score = 10
            feedback = "⚠️ Inconsistent form. May indicate fatigue or instability."
        else:
            score = 5
            feedback = "❌ High variability. Work on core stability and form drills."
        
        return score, feedback
    
    def calculate_score(self, running_metrics) -> ScoreBreakdown:
        """Calculate complete form score"""
        knee_score, knee_fb = self.score_knee_angle(running_metrics.avg_knee_angle_at_contact)
        torso_score, torso_fb = self.score_torso_lean(running_metrics.avg_torso_lean)
        foot_score, foot_fb = self.score_foot_strike(running_metrics.avg_foot_position)
        cons_score, cons_fb = self.score_consistency(running_metrics.frame_metrics)
        
        total = knee_score + torso_score + foot_score + cons_score
        
        # Overall feedback
        if total >= 90:
            overall = "🏆 Excellent running form! You're moving efficiently."
        elif total >= 75:
            overall = "👍 Good form with minor areas for improvement."
        elif total >= 60:
            overall = "⚡ Decent form. Focus on the areas marked with ⚠️."
        elif total >= 40:
            overall = "🔧 Several form issues to address. Consider a running coach."
        else:
            overall = "⚠️ Significant form concerns. Start with basic running drills."
        
        return ScoreBreakdown(
            knee_score=knee_score,
            knee_feedback=knee_fb,
            torso_score=torso_score,
            torso_feedback=torso_fb,
            foot_strike_score=foot_score,
            foot_strike_feedback=foot_fb,
            consistency_score=cons_score,
            consistency_feedback=cons_fb,
            total_score=total,
            overall_feedback=overall
        )
