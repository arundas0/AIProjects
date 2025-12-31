from typing import Optional, Dict

class ChartGenerator:
    """Generate chart configurations based on questions and data"""
    
    @staticmethod
    def generate_chart(question: str, health_summary: Dict) -> Optional[Dict]:
        """Generate appropriate chart based on question and available data"""
        q_lower = question.lower()
        
        if 'step' in q_lower or 'walk' in q_lower:
            return ChartGenerator._generate_steps_chart(health_summary)
        
        elif 'heart' in q_lower or 'hr' in q_lower:
            return ChartGenerator._generate_heart_rate_chart(health_summary)
        
        elif 'workout' in q_lower or 'exercise' in q_lower:
            return ChartGenerator._generate_workout_chart(health_summary)
        
        return None
    
    @staticmethod
    def _generate_steps_chart(health_summary: Dict) -> Optional[Dict]:
        """Generate steps chart configuration"""
        steps = health_summary.get('steps')
        if not steps or not steps.get('daily_data'):
            return None
        
        return {
            'type': 'line',
            'labels': [d['date'] for d in steps['daily_data']],
            'data': [d['value'] for d in steps['daily_data']],
            'label': 'Daily Steps',
            'color': '#667eea'
        }
    
    @staticmethod
    def _generate_heart_rate_chart(health_summary: Dict) -> Optional[Dict]:
        """Generate heart rate chart configuration"""
        heart_rate = health_summary.get('heart_rate')
        if not heart_rate or not heart_rate.get('daily_data'):
            return None
        
        data = heart_rate['daily_data'][-20:]  # Last 20 readings
        
        return {
            'type': 'line',
            'labels': [d['date'] for d in data],
            'data': [d['value'] for d in data],
            'label': 'Heart Rate (bpm)',
            'color': '#dc3545'
        }
    
    @staticmethod
    def _generate_workout_chart(health_summary: Dict) -> Optional[Dict]:
        """Generate workout distribution chart"""
        workouts = health_summary.get('workouts')
        if not workouts or not workouts.get('types'):
            return None
        
        return {
            'type': 'bar',
            'labels': [w['name'] for w in workouts['types']],
            'data': [w['value'] for w in workouts['types']],
            'label': 'Workout Count',
            'colors': ['#667eea', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6']
        }