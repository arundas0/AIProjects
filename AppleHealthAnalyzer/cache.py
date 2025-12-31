import os
from typing import Optional, Dict

class DataCache:
    """Cache parsed health data to avoid re-parsing on every request"""
    
    def __init__(self, parser, analyzer_class):
        self.parser = parser
        self.analyzer_class = analyzer_class
        self.data = None
        self.analyzer = None
        self.last_modified = None
    
    def get_data(self) -> Optional[Dict]:
        """Get cached data or parse if needed"""
        xml_path = self.parser.xml_file_path
        
        if not os.path.exists(xml_path):
            return None
        
        current_modified = os.path.getmtime(xml_path)
        
        if self.data is None or self.last_modified != current_modified:
            self.data = self.parser.parse()
            self.analyzer = self.analyzer_class(
                self.data['records'],
                self.data['workouts']
            )
            self.last_modified = current_modified
        
        return self.data
    
    def get_analyzer(self):
        """Get the analyzer instance (ensures data is loaded first)"""
        if self.analyzer is None:
            self.get_data()
        return self.analyzer