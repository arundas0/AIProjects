"""
UI Components for PostureAnalyzer (Pro Scout Edition)
Handles all HTML generation and streamlit widget rendering for the visual layer.
"""
import streamlit as st

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def load_css(file_name="style.css"):
    """Inject CSS from a file"""
    import os
    if os.path.exists(file_name):
        with open(file_name) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

def get_score_class(score: int) -> str:
    """Return css class for score color grading"""
    if score >= 90:
        return "score-excellent"
    elif score >= 75:
        return "score-good"
    elif score >= 60:
        return "score-fair"
    return "score-poor"

# =============================================================================
# COMPONENT RENDERERS
# =============================================================================

def render_hero():
    """Render the main Pro Scout hero header"""
    st.markdown("""
    <div class="hero-container">
        <div class="hero-subtitle">NEXT GEN ATHLETE ANALYTICS</div>
        <div class="hero-title">PRO SCOUT</div>
        <p style="color: #94a3b8; margin-top: 10px;">AI-POWERED BIOMECHANICS LAB</p>
    </div>
    """, unsafe_allow_html=True)

def render_stat_block(label, value):
    """Render a single stat block (Label + Value)"""
    st.markdown(f"""
    <div class="stat-block">
        <div class="stat-label">{label}</div>
        <div class="stat-value">{value}</div>
    </div>
    """, unsafe_allow_html=True)

def render_metric_card(title, content):
    """Render a metric card (used in detailed feedback)"""
    st.markdown(f"""
    <div class="metric-card">
        <strong>{title}</strong><br>
        {content}
    </div>
    """, unsafe_allow_html=True)

def render_player_card_frame(title, content_func=None, image_path=None):
    """
    Render a player card container.
    - If image_path is provided, renders an image.
    - If content_func is provided, executes it inside the body.
    """
    st.markdown(f'<div class="player-card"><div class="card-header">{title}</div><div class="card-body">', unsafe_allow_html=True)
    
    if image_path:
        st.image(image_path, use_container_width=True)
    elif content_func:
        content_func()
        
    st.markdown('</div></div>', unsafe_allow_html=True)

def render_ovr_badge(score):
    """Render the FIFA-style Overall Score Badge"""
    st.markdown(f"""
    <div class="ovr-badge">
        <div class="ovr-value">{score}</div>
        <div class="ovr-label">OVR</div>
    </div>
    """, unsafe_allow_html=True)

def render_coach_tablet(feedback_text):
    """Render the digital clipboard feedback"""
    if feedback_text:
        st.markdown(f'<div class="coach-tablet">{feedback_text}</div>', unsafe_allow_html=True)
    else:
        st.info("AI Scout unavailable (Check API Key)")

def render_score_breakdown(score):
    """Render the progress bars for sub-scores"""
    st.markdown("### Score Breakdown")
    st.progress(score.knee_score / 25, text=f"Knee Angle: {score.knee_score}/25")
    st.progress(score.torso_score / 25, text=f"Torso Lean: {score.torso_score}/25")
    st.progress(score.foot_strike_score / 25, text=f"Foot Strike: {score.foot_strike_score}/25")
    st.progress(score.consistency_score / 25, text=f"Consistency: {score.consistency_score}/25")
