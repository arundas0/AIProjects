import json
import statistics
from config import Config
from collections import defaultdict
from typing import Dict, List, Optional

try:
    from pandas_aggregator import build_aggregations
except Exception:
    build_aggregations = None

class HealthDataAnalyzer:
    """Analyze parsed health data and generate insights"""
    
    def __init__(self, records: List[Dict], workouts: List[Dict]):
        self.records = records
        self.workouts = workouts
    
    def analyze_metric(self, metric_type: str) -> Optional[Dict]:
        """Get summary statistics for a specific health metric"""
        values = []
        dates = []
        
        for record in self.records:
            if metric_type in record['type']:
                try:
                    values.append(float(record['value']))
                    date_str = self._extract_date(record['start_date'])
                    dates.append(date_str)
                except (ValueError, TypeError):
                    continue
        
        if not values:
            return None
        
        # Group by date for daily metrics
        daily_values = defaultdict(list)
        for date, value in zip(dates, values):
            daily_values[date].append(value)
        
        # Calculate daily averages
        daily_data = [
            {'date': date, 'value': sum(vals) / len(vals)}
            for date, vals in sorted(daily_values.items())
        ]
        
        return {
            'count': len(values),
            'average': statistics.mean(values),
            'median': statistics.median(values),
            'min': min(values),
            'max': max(values),
            'daily_data': daily_data[-365:],  # Last 365 days
            'unit': self._get_unit(metric_type)
        }
    
    def analyze_steps(self) -> Optional[Dict]:
        """Analyze step count data"""
        return self.analyze_metric('StepCount')
    
    def analyze_heart_rate(self) -> Optional[Dict]:
        """Analyze heart rate data"""
        return self.analyze_metric('HeartRate')
    
    def analyze_workouts(self) -> Optional[Dict]:
        """Analyze workout data"""
        if not self.workouts:
            return None
        
        workout_types = defaultdict(int)
        total_duration = 0
        
        for workout in self.workouts:
            workout_types[workout['type']] += 1
            total_duration += workout['duration']
        
        return {
            'total': len(self.workouts),
            'total_minutes': total_duration / 60,
            'types': [{'name': k, 'value': v} for k, v in workout_types.items()]
        }
    
    def get_summary(self) -> Dict:
        """Get complete health data summary"""
        return {
            'steps': self.analyze_steps(),
            'heart_rate': self.analyze_heart_rate(),
            'workouts': self.analyze_workouts(),
            'aggregations': self.get_aggregations()
        }

    def get_aggregations(self) -> Dict:
        """Get pandas-based aggregation tables for model input."""
        if build_aggregations is None:
            aggregations = {'error': 'pandas_not_available'}
            try:
                with open(Config.AGGREGATIONS_FILE, "w", encoding="utf-8") as handle:
                    json.dump(aggregations, handle, ensure_ascii=True, indent=2)
                print(f"[aggregations] wrote {Config.AGGREGATIONS_FILE}")
            except Exception as e:
                print(f"[aggregations] failed to write {Config.AGGREGATIONS_FILE}: {e}")
            return aggregations
        aggregations = build_aggregations(self.records)
        try:
            with open(Config.AGGREGATIONS_FILE, "w", encoding="utf-8") as handle:
                json.dump(aggregations, handle, ensure_ascii=True, indent=2)
            print(f"[aggregations] wrote {Config.AGGREGATIONS_FILE}")
        except Exception as e:
            print(f"[aggregations] failed to write {Config.AGGREGATIONS_FILE}: {e}")
        return aggregations
    
    @staticmethod
    def _extract_date(date_string: str) -> str:
        """Extract date from datetime string"""
        if 'T' in date_string:
            return date_string.split('T')[0]
        return date_string.split(' ')[0]
    
    def _get_unit(self, metric_type: str) -> str:
        """Get unit for a metric type"""
        for record in self.records:
            if metric_type in record['type'] and record['unit']:
                return record['unit']
        return 'N/A'
