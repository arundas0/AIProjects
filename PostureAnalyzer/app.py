"""
PostureAnalyzer - Running Form Analysis App
Upload a video of yourself running (side profile) to get AI-powered form feedback.
"""
import streamlit as st
import tempfile
import os

from pose_analyzer import PoseAnalyzer
from form_scorer import FormScorer
from gemini_feedback import GeminiFeedbackGenerator

# Page config
st.set_page_config(
    page_title="PostureAnalyzer - Running Form Check",
    page_icon="🏃",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
    .score-box {
        padding: 1.5rem;
        border-radius: 12px;
        text-align: center;
        font-size: 1.2rem;
    }
    .score-excellent { background: linear-gradient(135deg, #10b981, #059669); color: white; }
    .score-good { background: linear-gradient(135deg, #3b82f6, #2563eb); color: white; }
    .score-fair { background: linear-gradient(135deg, #f59e0b, #d97706); color: white; }
    .score-poor { background: linear-gradient(135deg, #ef4444, #dc2626); color: white; }
    .metric-card {
        background: #f8fafc;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #667eea;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)


def get_score_class(score: int) -> str:
    if score >= 90:
        return "score-excellent"
    elif score >= 75:
        return "score-good"
    elif score >= 60:
        return "score-fair"
    return "score-poor"


def main():
    st.markdown('<p class="main-header">🏃 PostureAnalyzer</p>', unsafe_allow_html=True)
    st.markdown("### Your $0 Running Coach - Upload a side-view running video for instant form feedback")
    
    st.divider()
    
    # Instructions
    with st.expander("📋 How to get the best results", expanded=False):
        st.markdown("""
        1. **Record from the side** - Position your camera perpendicular to your running direction
        2. **Treadmill works best** - Keeps you in frame consistently  
        3. **10-30 seconds is enough** - Don't need a long clip
        4. **Wear fitted clothes** - Helps AI detect your joints accurately
        5. **Good lighting** - Avoid dark or backlit environments
        """)
    
    # File uploader
    uploaded_file = st.file_uploader(
        "Upload your running video",
        type=["mp4", "mov", "avi", "mkv"],
        help="Side-profile video works best. 10-30 seconds is ideal."
    )
    
    if uploaded_file is not None:
        # Save uploaded file to temp location
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp:
            tmp.write(uploaded_file.read())
            temp_path = tmp.name
        
        st.video(uploaded_file)
        
        if st.button("🔍 Analyze My Form", type="primary", use_container_width=True):
            with st.spinner("Analyzing your running form... This may take a minute."):
                try:
                    # Process video
                    analyzer = PoseAnalyzer()
                    output_video_path, metrics = analyzer.process_video(temp_path)
                    
                    # Calculate score
                    scorer = FormScorer()
                    score = scorer.calculate_score(metrics)
                    
                    # Generate LLM coaching feedback
                    gemini = GeminiFeedbackGenerator()
                    if gemini.is_available:
                        llm_feedback = gemini.generate_feedback(
                            avg_knee_angle=metrics.avg_knee_angle_at_contact,
                            avg_torso_lean=metrics.avg_torso_lean,
                            avg_foot_position=metrics.avg_foot_position,
                            knee_score=score.knee_score,
                            torso_score=score.torso_score,
                            foot_score=score.foot_strike_score,
                            consistency_score=score.consistency_score,
                            total_score=score.total_score
                        )
                        score.llm_feedback = llm_feedback
                    
                    st.success("✅ Analysis complete!")
                    
                    # Display results
                    col1, col2 = st.columns([1, 2])
                    
                    with col1:
                        # Main score
                        score_class = get_score_class(score.total_score)
                        st.markdown(f"""
                        <div class="score-box {score_class}">
                            <div style="font-size: 3rem; font-weight: bold;">{score.total_score}</div>
                            <div>Form Score</div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        st.markdown(f"**{score.overall_feedback}**")
                        
                        # Subscores
                        st.markdown("### Score Breakdown")
                        st.progress(score.knee_score / 25, text=f"Knee Angle: {score.knee_score}/25")
                        st.progress(score.torso_score / 25, text=f"Torso Lean: {score.torso_score}/25")
                        st.progress(score.foot_strike_score / 25, text=f"Foot Strike: {score.foot_strike_score}/25")
                        st.progress(score.consistency_score / 25, text=f"Consistency: {score.consistency_score}/25")
                    
                    with col2:
                        # Processed video with skeleton
                        st.markdown("### Skeleton Overlay")
                        if os.path.exists(output_video_path):
                            st.video(output_video_path)
                        
                        # Detailed metrics
                        st.markdown("### Raw Metrics")
                        metrics_col1, metrics_col2, metrics_col3 = st.columns(3)
                        with metrics_col1:
                            st.metric("Avg Knee Angle", f"{metrics.avg_knee_angle_at_contact:.1f}°")
                        with metrics_col2:
                            st.metric("Avg Torso Lean", f"{metrics.avg_torso_lean:.1f}°")
                        with metrics_col3:
                            if metrics.cadence_estimate:
                                st.metric("Est. Cadence", f"{metrics.cadence_estimate:.0f} spm")
                            else:
                                st.metric("Est. Cadence", "N/A")
                    
                    # Detailed feedback
                    st.divider()
                    st.markdown("### 📝 Detailed Feedback")
                    
                    feedback_col1, feedback_col2 = st.columns(2)
                    with feedback_col1:
                        st.markdown(f"""
                        <div class="metric-card">
                            <strong>🦵 Knee Angle</strong><br>
                            {score.knee_feedback}
                        </div>
                        """, unsafe_allow_html=True)
                        
                        st.markdown(f"""
                        <div class="metric-card">
                            <strong>🧍 Torso Lean</strong><br>
                            {score.torso_feedback}
                        </div>
                        """, unsafe_allow_html=True)
                    
                    with feedback_col2:
                        st.markdown(f"""
                        <div class="metric-card">
                            <strong>👟 Foot Strike</strong><br>
                            {score.foot_strike_feedback}
                        </div>
                        """, unsafe_allow_html=True)
                        
                        st.markdown(f"""
                        <div class="metric-card">
                            <strong>📊 Consistency</strong><br>
                            {score.consistency_feedback}
                        </div>
                        """, unsafe_allow_html=True)
                    
                    # AI Coach feedback section
                    st.divider()
                    st.markdown("### 🤖 AI Coach Says")
                    if score.llm_feedback:
                        st.info(score.llm_feedback)
                    else:
                        if gemini.init_error:
                            st.caption(f"_Gemini init failed: {gemini.init_error}_")
                        elif gemini.call_error:
                            st.caption(f"_Gemini API call failed: {gemini.call_error}_")
                        elif not gemini.is_available:
                            st.caption("_Set GEMINI_API_KEY environment variable to enable personalized AI coaching feedback._")
                        else:
                            st.caption("_AI feedback returned empty. Check console for errors._")
                    
                    # Cleanup
                    try:
                        os.unlink(temp_path)
                        if os.path.exists(output_video_path):
                            os.unlink(output_video_path)
                    except Exception:
                        pass
                        
                except Exception as e:
                    st.error(f"Error analyzing video: {str(e)}")
                    st.info("Make sure the video shows a clear side view of you running.")
    
    # Footer
    st.divider()
    st.markdown("""
    <div style="text-align: center; color: #666; font-size: 0.9rem;">
        Built with MediaPipe Pose Estimation • Not a substitute for professional coaching
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
