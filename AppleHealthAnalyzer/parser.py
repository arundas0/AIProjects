import xml.etree.ElementTree as ET
from typing import Dict, List, Optional

class HealthDataParser:
    """Parse Apple Health XML export files"""
    
    def __init__(self, xml_file_path: str):
        self.xml_file_path = xml_file_path
    
    def parse(self) -> Dict:
        """Parse the XML file and return structured data"""
        print(f"Parsing health data from {self.xml_file_path}...")
        
        tree = ET.parse(self.xml_file_path)
        root = tree.getroot()
        
        records = self._parse_records(root)
        workouts = self._parse_workouts(root)
        
        print(f"Loaded {len(records)} records and {len(workouts)} workouts")
        
        return {
            'records': records,
            'workouts': workouts
        }
    
    def _parse_records(self, root) -> List[Dict]:
        """Parse health record elements"""
        records = []
        for record in root.findall('.//Record'):
            records.append({
                'type': record.get('type'),
                'value': record.get('value'),
                'unit': record.get('unit'),
                'start_date': record.get('startDate'),
                'end_date': record.get('endDate'),
            })
        return records
    
    def _parse_workouts(self, root) -> List[Dict]:
        """Parse workout elements"""
        workouts = []
        for workout in root.findall('.//Workout'):
            workouts.append({
                'type': workout.get('workoutActivityType'),
                'duration': float(workout.get('duration', 0)),
                'start_date': workout.get('startDate'),
            })
        return workouts
