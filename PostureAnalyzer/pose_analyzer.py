"""
Pose Analyzer - MediaPipe-based running form analysis
Uses MediaPipe Tasks API (0.10+) with manual landmark drawing
"""
import cv2
import numpy as np
from dataclasses import dataclass
from typing import List, Tuple, Optional
import tempfile
import os
import urllib.request

from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import mediapipe as mp


@dataclass
class FrameMetrics:
    """Metrics for a single frame"""
    frame_number: int
    knee_angle: float
    torso_lean: float
    hip_angle: float
    foot_ahead_of_hip: float
    is_ground_contact: bool


@dataclass
class RunningMetrics:
    """Aggregated metrics for the entire video"""
    avg_knee_angle_at_contact: float
    avg_torso_lean: float
    avg_foot_position: float
    cadence_estimate: Optional[float]
    frame_metrics: List[FrameMetrics]


# Pose connections for drawing skeleton
POSE_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 7),  # Face
    (0, 4), (4, 5), (5, 6), (6, 8),  # Face
    (9, 10),  # Mouth
    (11, 12),  # Shoulders
    (11, 13), (13, 15),  # Left arm
    (12, 14), (14, 16),  # Right arm
    (11, 23), (12, 24),  # Torso
    (23, 24),  # Hips
    (23, 25), (25, 27),  # Left leg
    (24, 26), (26, 28),  # Right leg
    (27, 29), (29, 31),  # Left foot
    (28, 30), (30, 32),  # Right foot
    (15, 17), (15, 19), (15, 21),  # Left hand
    (16, 18), (16, 20), (16, 22),  # Right hand
]


class PoseAnalyzer:
    """Analyze running form using MediaPipe Pose"""
    
    # Landmark indices
    LEFT_HIP = 23
    RIGHT_HIP = 24
    LEFT_KNEE = 25
    RIGHT_KNEE = 26
    LEFT_ANKLE = 27
    RIGHT_ANKLE = 28
    LEFT_HEEL = 29
    RIGHT_HEEL = 30
    LEFT_SHOULDER = 11
    RIGHT_SHOULDER = 12
    
    def __init__(self, min_detection_confidence=0.5, min_tracking_confidence=0.5):
        self.model_path = self._ensure_model()
        self.min_detection_confidence = min_detection_confidence
        self.min_tracking_confidence = min_tracking_confidence
    
    def _ensure_model(self) -> str:
        """Download pose landmarker model if needed"""
        import ssl
        
        model_path = os.path.join(tempfile.gettempdir(), "pose_landmarker_lite.task")
        if not os.path.exists(model_path):
            print("Downloading pose model...")
            url = "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task"
            
            # Workaround for macOS SSL certificate issues
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            with urllib.request.urlopen(url, context=ssl_context) as response:
                with open(model_path, 'wb') as f:
                    f.write(response.read())
            print("Model downloaded.")
        return model_path
    
    def calculate_angle(self, p1: Tuple[float, float], p2: Tuple[float, float], p3: Tuple[float, float]) -> float:
        """Calculate angle at p2 formed by p1-p2-p3"""
        a = np.array(p1)
        b = np.array(p2)
        c = np.array(p3)
        
        ba = a - b
        bc = c - b
        
        cosine_angle = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc) + 1e-6)
        cosine_angle = np.clip(cosine_angle, -1.0, 1.0)
        return np.degrees(np.arccos(cosine_angle))
    
    def calculate_torso_lean(self, shoulder: Tuple[float, float], hip: Tuple[float, float]) -> float:
        """Calculate torso lean from vertical"""
        dx = shoulder[0] - hip[0]
        dy = hip[1] - shoulder[1]
        return np.degrees(np.arctan2(dx, dy))
    
    def get_landmark_xy(self, landmarks, idx: int) -> Tuple[float, float]:
        """Extract x, y from landmark"""
        lm = landmarks[idx]
        return (lm.x, lm.y)
    
    def analyze_frame(self, landmarks, frame_number: int) -> Optional[FrameMetrics]:
        """Analyze a single frame's pose landmarks"""
        try:
            hip = self.get_landmark_xy(landmarks, self.RIGHT_HIP)
            knee = self.get_landmark_xy(landmarks, self.RIGHT_KNEE)
            ankle = self.get_landmark_xy(landmarks, self.RIGHT_ANKLE)
            shoulder = self.get_landmark_xy(landmarks, self.RIGHT_SHOULDER)
            
            knee_angle = self.calculate_angle(hip, knee, ankle)
            hip_angle = self.calculate_angle(shoulder, hip, knee)
            torso_lean = self.calculate_torso_lean(shoulder, hip)
            foot_ahead = (ankle[0] - hip[0]) * 100
            is_contact = ankle[1] > 0.8
            
            return FrameMetrics(
                frame_number=frame_number,
                knee_angle=knee_angle,
                torso_lean=torso_lean,
                hip_angle=hip_angle,
                foot_ahead_of_hip=foot_ahead,
                is_ground_contact=is_contact
            )
        except Exception:
            return None
    
    def draw_landmarks(self, image, landmarks, width, height):
        """Draw pose landmarks on image manually"""
        # Draw connections
        for start_idx, end_idx in POSE_CONNECTIONS:
            if start_idx < len(landmarks) and end_idx < len(landmarks):
                start = landmarks[start_idx]
                end = landmarks[end_idx]
                
                start_point = (int(start.x * width), int(start.y * height))
                end_point = (int(end.x * width), int(end.y * height))
                
                cv2.line(image, start_point, end_point, (0, 255, 0), 2)
        
        # Draw landmarks as circles
        for lm in landmarks:
            x = int(lm.x * width)
            y = int(lm.y * height)
            cv2.circle(image, (x, y), 4, (255, 0, 0), -1)
        
        return image
    
    def process_video(self, video_path: str) -> Tuple[str, RunningMetrics]:
        """Process video and return annotated video path and metrics"""
        
        base_options = python.BaseOptions(model_asset_path=self.model_path)
        options = vision.PoseLandmarkerOptions(
            base_options=base_options,
            output_segmentation_masks=False,
            min_pose_detection_confidence=self.min_detection_confidence,
            min_tracking_confidence=self.min_tracking_confidence
        )
        detector = vision.PoseLandmarker.create_from_options(options)
        
        cap = cv2.VideoCapture(video_path)
        
        fps = cap.get(cv2.CAP_PROP_FPS) or 30
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        output_path = tempfile.mktemp(suffix='.mp4')
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        
        frame_metrics_list = []
        frame_number = 0
        
        while cap.isOpened():
            success, frame = cap.read()
            if not success:
                break
            
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
            
            detection_result = detector.detect(mp_image)
            
            if detection_result.pose_landmarks and len(detection_result.pose_landmarks) > 0:
                landmarks = detection_result.pose_landmarks[0]
                
                # Draw skeleton
                annotated_frame = self.draw_landmarks(frame.copy(), landmarks, width, height)
                
                # Analyze
                metrics = self.analyze_frame(landmarks, frame_number)
                if metrics:
                    frame_metrics_list.append(metrics)
                    cv2.putText(annotated_frame, f"Knee: {metrics.knee_angle:.1f} deg", (10, 30),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                    cv2.putText(annotated_frame, f"Lean: {metrics.torso_lean:.1f} deg", (10, 60),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                
                out.write(annotated_frame)
            else:
                out.write(frame)
            
            frame_number += 1
        
        cap.release()
        out.release()
        detector.close()
        
        # Convert to H.264 for browser compatibility
        final_output_path = self._convert_to_h264(output_path)
        
        # Aggregate metrics
        key_frame_path = None
        
        if frame_metrics_list:
            contact_frames = [m for m in frame_metrics_list if m.is_ground_contact] or frame_metrics_list
            
            # Find the "best" contact frame (e.g. middle of the first contact phase) to save as key image
            best_frame_idx = contact_frames[0].frame_number # Default to first
            if len(contact_frames) > 2:
                 # Simple heuristic: take the 3rd contact frame if available to avoid blur/transition
                 best_frame_idx = contact_frames[min(len(contact_frames)-1, 2)].frame_number
            
            # Extract and save key frame
            cap = cv2.VideoCapture(video_path)
            cap.set(cv2.CAP_PROP_POS_FRAMES, best_frame_idx)
            ret, frame = cap.read()
            if ret:
                key_frame_path = tempfile.mktemp(suffix='.jpg')
                cv2.imwrite(key_frame_path, frame)
            cap.release()

            avg_knee = np.mean([m.knee_angle for m in contact_frames])
            avg_lean = np.mean([m.torso_lean for m in frame_metrics_list])
            avg_foot = np.mean([m.foot_ahead_of_hip for m in contact_frames])
            
            cadence = None
            if len(contact_frames) > 2 and fps > 0:
                duration_s = frame_number / fps
                steps = len(contact_frames) / 2
                cadence = (steps / duration_s) * 60
            
            running_metrics = RunningMetrics(
                avg_knee_angle_at_contact=avg_knee,
                avg_torso_lean=avg_lean,
                avg_foot_position=avg_foot,
                cadence_estimate=cadence,
                frame_metrics=frame_metrics_list
            )
        else:
            running_metrics = RunningMetrics(
                avg_knee_angle_at_contact=0,
                avg_torso_lean=0,
                avg_foot_position=0,
                cadence_estimate=None,
                frame_metrics=[]
            )
        
        return final_output_path, running_metrics, key_frame_path

    def _convert_to_h264(self, input_path: str) -> str:
        """Convert video to H.264 using ffmpeg for browser compatibility"""
        import subprocess
        
        output_path = tempfile.mktemp(suffix='.mp4')
        try:
            subprocess.run([
                'ffmpeg', '-y',
                '-i', input_path,
                '-vcodec', 'libx264',
                '-f', 'mp4',
                output_path
            ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return output_path
        except Exception as e:
            print(f"Warning: ffmpeg conversion failed: {e}")
            return input_path
