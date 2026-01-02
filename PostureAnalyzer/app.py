"""
PostureAnalyzer - Pro Scout Edition
High-performance running form analysis for the next generation of athletes.
"""
import streamlit as st
import tempfile
import os
import plotly.graph_objects as go
from config import PRO_ATHLETE_STATS, RADAR_RANGES

from pose_analyzer import PoseAnalyzer
from form_scorer import FormScorer
from gemini_feedback import GeminiFeedbackGenerator
import ui

# Page config with Dark Theme assumption
st.set_page_config(
    page_title="PRO SCOUT // PostureAnalyzer",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Load styling
ui.load_css()

def get_radar_chart(metrics, score, pro_stats):
    categories = ['KNEE DRIVE', 'LEAN', 'FOOT STRIKE', 'CONSISTENCY']
    
    # Simple normalization logic for visual
    # 0-100 scale where 100 is "Pro Standard"
    
    def calc_vis_score(val, target, tolerance=5):
        # 100 points if within tolerance, drop off linearly
        diff = abs(val - target)
        if diff <= tolerance: return 100
        return max(20, 100 - (diff - tolerance) * 3)

    user_values = [
        calc_vis_score(metrics.avg_knee_angle_at_contact, pro_stats['knee_angle'], 5),
        calc_vis_score(metrics.avg_torso_lean, pro_stats['torso_lean'], 3),
        calc_vis_score(metrics.avg_foot_position, pro_stats['foot_position'], 2),
        score.consistency_score * 4
    ]
    
    pro_values = [100, 100, 100, 100] # Pro is perfection

    fig = go.Figure()
    
    # Pro Layer
    fig.add_trace(go.Scatterpolar(
        r=pro_values,
        theta=categories,
        fill='toself',
        name='PRO ELITE',
        line=dict(color='#FFD700', width=1, dash='dot'),
        fillcolor='rgba(255, 215, 0, 0.1)',
        hoverinfo='skip'
    ))
    
    # User Layer
    fig.add_trace(go.Scatterpolar(
        r=user_values,
        theta=categories,
        fill='toself',
        name='YOU',
        line=dict(color='#00F0FF', width=3),
        fillcolor='rgba(0, 240, 255, 0.3)'
    ))

    fig.update_layout(
        polar=dict(
            bgcolor='rgba(0,0,0,0)',
            radialaxis=dict(visible=False, range=[0, 100]),
            angularaxis=dict(
                tickfont=dict(size=12, color='#94a3b8', family='Rajdhani'),
                rotation=90,
                direction='clockwise'
            )
        ),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        showlegend=False,
        margin=dict(l=30, r=30, t=30, b=30),
        height=300
    )
    return fig

def main():
    ui.render_hero()
    
    # Input Section
    col_upload, col_tips = st.columns([2, 1])
    with col_upload:
        uploaded_file = st.file_uploader("DROP GAME FOOTAGE", type=["mp4", "mov", "avi"])
    with col_tips:
        st.info("💡 **PRO TIP:** Film from the side (90°) for best accuracy. Use slow-mo if possible.")

    if uploaded_file is not None:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp:
            tmp.write(uploaded_file.read())
            temp_path = tmp.name

        if st.button("🚀 LAUNCH ANALYSIS", type="primary", use_container_width=True):
            with st.spinner("AI SCOUT ANALYZING BIOMECHANICS..."):
                try:
                    # 1. ANALYSIS
                    analyzer = PoseAnalyzer()
                    output_video_path, metrics, key_frame_path = analyzer.process_video(temp_path)
                    
                    scorer = FormScorer()
                    score = scorer.calculate_score(metrics)
                    
                    gemini = GeminiFeedbackGenerator()
                    gpt_feedback = None
                    if gemini.is_available:
                        gpt_feedback = gemini.generate_feedback(
                            metrics.avg_knee_angle_at_contact, metrics.avg_torso_lean, metrics.avg_foot_position,
                            score.knee_score, score.torso_score, score.foot_strike_score, score.consistency_score,
                            score.total_score, key_frame_path
                        )
                    
                    # 2. DASHBOARD UI
                    st.divider()
                    
                    # --- TOP SECTION: PLAYER CARD ---
                    card_col1, card_col2, card_col3 = st.columns([1, 2, 1])
                    
                    # Left: Photo
                    with card_col1:
                        # Use a lambda to render content inside the card if needed, or pass image path
                        st.markdown('<div class="player-card"><div class="card-header">KEY FRAME</div><div class="card-body" style="padding:0;">', unsafe_allow_html=True)
                        if key_frame_path:
                            st.image(key_frame_path, use_container_width=True)
                        else:
                            st.caption("No clear frame detected")
                        st.markdown('</div></div>', unsafe_allow_html=True)
                        
                        st.markdown('<div style="margin-top:10px;"></div>', unsafe_allow_html=True)
                        ui.render_ovr_badge(score.total_score)

                    # Center: Radar & Feedback
                    with card_col2:
                         st.markdown('<div class="player-card"><div class="card-header">BIOMECHANIC PROFILE</div><div class="card-body">', unsafe_allow_html=True)
                         radar_fig = get_radar_chart(metrics, score, PRO_ATHLETE_STATS)
                         st.plotly_chart(radar_fig, use_container_width=True)
                         st.markdown('</div></div>', unsafe_allow_html=True)

                    # Right: Stats
                    with card_col3:
                        st.markdown('<div class="player-card"><div class="card-header">METRICS</div><div class="card-body">', unsafe_allow_html=True)
                        ui.render_stat_block("KNEE ANGLE", f"{metrics.avg_knee_angle_at_contact:.1f}°")
                        ui.render_stat_block("TORSO LEAN", f"{metrics.avg_torso_lean:.1f}°")
                        ui.render_stat_block("CADENCE", f"{metrics.cadence_estimate:.0f} SPM" if metrics.cadence_estimate else "N/A")
                        st.markdown('</div></div>', unsafe_allow_html=True)

                    # --- MIDDLE SECTION: VIDEO & CHARTS ---
                    st.markdown("### 🎥 TAPE BREAKDOWN")
                    vid_col, chart_col = st.columns([3, 2])
                    
                    with vid_col:
                        st.video(output_video_path)
                    
                    with chart_col:
                        st.markdown('<div class="player-card"><div class="card-header">CONSISTENCY CHECK</div><div class="card-body">', unsafe_allow_html=True)
                        # Knee Trend
                        contact_metrics = [m for m in metrics.frame_metrics if m.is_ground_contact]
                        if contact_metrics:
                            chart_data = {"Step": range(len(contact_metrics)), "Knee Angle": [m.knee_angle for m in contact_metrics]}
                            st.line_chart(chart_data, x="Step", y="Knee Angle", color="#CCFF00")
                            st.caption("Lower variances = Pro Consistency")
                        st.markdown('</div></div>', unsafe_allow_html=True)

                    # --- BOTTOM SECTION: COACH FEEDBACK ---
                    st.markdown("### 📋 SCOUT REPORT")
                    ui.render_coach_tablet(gpt_feedback)

                except Exception as e:
                    st.error(f"Analysis Failed: {e}")

if __name__ == "__main__":
    main()
