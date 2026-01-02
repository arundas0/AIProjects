"""
Gemini Feedback Generator - Generate personalized running form feedback using LLM
"""
import os
from typing import Optional


class GeminiFeedbackGenerator:
    """
    Uses Google Gemini to generate personalized running form coaching feedback.
    Reads API key from GEMINI_API_KEY environment variable or Streamlit secrets.
    """
    
    def __init__(self):
        # Try environment variable first, then Streamlit secrets
        self.api_key = os.environ.get("GEMINI_API_KEY")
        
        if not self.api_key:
            try:
                import streamlit as st
                self.api_key = st.secrets.get("GEMINI_API_KEY")
            except Exception:
                pass
        
        self.client = None
        self.init_error = None
        self.call_error = None  # Stores error from generate_feedback call
        
        if self.api_key:
            try:
                from google import genai
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                self.init_error = str(e)
                print(f"Warning: Could not initialize Gemini: {e}")
                self.client = None
        else:
            self.init_error = "No API key found"
    
    @property
    def is_available(self) -> bool:
        """Check if Gemini is configured and available"""
        return self.client is not None
    
    def generate_feedback(
        self,
        avg_knee_angle: float,
        avg_torso_lean: float,
        avg_foot_position: float,
        knee_score: int,
        torso_score: int,
        foot_score: int,
        consistency_score: int,
        total_score: int,
        image_path: Optional[str] = None
    ) -> Optional[str]:
        """
        Generate personalized coaching feedback based on running metrics and visual analysis.
        
        Returns None if Gemini is not available.
        """
        if not self.is_available:
            return None
        
        prompt = f"""You are an expert running coach providing personalized feedback.

Analyze this runner's form based on the provided metrics and the visual snapshot of their running stride (if available).

**Measurements:**
- Knee angle at ground contact: {avg_knee_angle:.1f}° (ideal: 160-175°)
- Torso forward lean: {avg_torso_lean:.1f}° (ideal: 5-15°)
- Foot position relative to hip: {avg_foot_position:.1f} units (ideal: -5 to +5, positive = ahead of hip)

**Scores (out of 25 each):**
- Knee angle: {knee_score}/25
- Torso lean: {torso_score}/25
- Foot strike: {foot_score}/25
- Consistency: {consistency_score}/25
- **Total: {total_score}/100**

**Visual Analysis (from image):**
Look at the provided image (which captures the ground contact phase) and also analyze:
- **Arm Carriage:** Are arms relaxed? Elbows driving back?
- **Head Position:** Looking forward? Neck relaxed?
- **Facial Tension:** Is the runner straining?

Provide bulleted personalized, actionable coaching advice to the runner (age 10-12, focusing on 1500m-3000m distances). Focus on:
1. The most important area to improve (metrics or visual)
2. A specific drill or cue they can use
3. Positive reinforcement for what they're doing well

Be encouraging but honest. Speak directly to the runner using "you/your"."""

        try:
            from config import GEMINI_MODEL
            from PIL import Image
            
            contents = [prompt]
            if image_path and os.path.exists(image_path):
                image = Image.open(image_path)
                contents.append(image)
                
            response = self.client.models.generate_content(
                model=GEMINI_MODEL,
                contents=contents
            )
            return response.text.strip()
        except Exception as e:
            self.call_error = str(e)
            print(f"Warning: Gemini API call failed: {e}")
            return None
