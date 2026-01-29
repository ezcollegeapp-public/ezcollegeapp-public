"""
Configuration loader for school form questions
Loads college_questions.json from config directory
"""
import json
import os
from pathlib import Path
from typing import Dict, Any, Optional


class ConfigLoader:
    """Loads and manages configuration files"""
    
    _instance = None
    _config_cache = {}
    
    def __new__(cls):
        """Singleton pattern - only one instance"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize config loader"""
        self.config_dir = Path(__file__).parent
        self.school_questions = None
    
    def load_college_questions(self) -> Dict[str, Any]:
        """
        Load college questions from JSON file
        
        Returns:
            Dictionary mapping school_id to form questions
        """
        if self.school_questions is not None:
            return self.school_questions
        
        questions_file = self.config_dir / "college_questions.json"
        
        if not questions_file.exists():
            raise FileNotFoundError(
                f"college_questions.json not found at {questions_file}"
            )
        
        try:
            with open(questions_file, 'r', encoding='utf-8') as f:
                self.school_questions = json.load(f)
            print(f"✓ Loaded college questions for {len(self.school_questions)} schools")
            return self.school_questions
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in college_questions.json: {e}")
        except Exception as e:
            raise RuntimeError(f"Failed to load college_questions.json: {e}")
    
    def get_school_questions(self, school_id: str) -> Dict[str, Any]:
        """
        Get all questions for a specific school
        
        Args:
            school_id: School ID (e.g., "48" for Caltech)
            
        Returns:
            Dictionary mapping form page URLs to question lists
        """
        questions = self.load_college_questions()
        
        if school_id not in questions:
            raise ValueError(f"School ID '{school_id}' not found in configuration")
        
        return questions[school_id]
    
    def get_all_questions_for_school(self, school_id: str) -> list:
        """
        Get all questions for a school as a flat list
        
        Args:
            school_id: School ID
            
        Returns:
            Flattened list of all questions for the school
        """
        school_questions = self.get_school_questions(school_id)
        all_questions = []
        
        for page_url, questions in school_questions.items():
            all_questions.extend(questions)
        
        return all_questions
    
    def get_required_questions(self, school_id: str) -> list:
        """
        Get only required questions for a school
        
        Args:
            school_id: School ID
            
        Returns:
            List of required questions
        """
        all_questions = self.get_all_questions_for_school(school_id)
        return [q for q in all_questions if q.get('required', False)]
    
    @staticmethod
    def get_instance() -> "ConfigLoader":
        """Get singleton instance"""
        return ConfigLoader()


# Convenience function for easy access
def load_college_questions() -> Dict[str, Any]:
    """Load college questions configuration"""
    return ConfigLoader.get_instance().load_college_questions()


def get_school_questions(school_id: str) -> Dict[str, Any]:
    """Get questions for a specific school"""
    return ConfigLoader.get_instance().get_school_questions(school_id)
