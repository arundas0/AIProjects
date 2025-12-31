import os

class Config:
    """Configuration settings for the application"""
    
    # Hardcoded path to Apple Health data
    HEALTH_DATA_FOLDER = "./health_data"
    EXPORT_FILE = os.path.join(HEALTH_DATA_FOLDER, "export.xml")
    AGGREGATIONS_FILE = os.path.join(HEALTH_DATA_FOLDER, "aggregations.json")
    
    # Ollama configuration
    OLLAMA_URL = "http://localhost:11434/api/generate"
    OLLAMA_MODEL = "gemma3:1b"
    OLLAMA_TIMEOUT = 300
    
    # Flask configuration
    FLASK_HOST = "127.0.0.1"
    FLASK_PORT = 5000
    DEBUG = True
    
    @staticmethod
    def ensure_data_folder():
        """Create health data folder if it doesn't exist"""
        os.makedirs(Config.HEALTH_DATA_FOLDER, exist_ok=True)
