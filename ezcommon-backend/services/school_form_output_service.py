"""
School Form Output Service
Saves and retrieves filled school form data as JSON files
"""
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional


class SchoolFormOutputService:
    """Service for saving and managing filled school form JSON outputs"""
    
    def __init__(self):
        """Initialize service with output directory configuration"""
        # Create output directory if it doesn't exist
        self.output_dir = Path(__file__).parent.parent / "config" / "outputs"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        print(f"✓ School form output directory: {self.output_dir}")
    
    def save_or_return_json(self, user_id: str, school_id: str, 
                           filled_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Save filled school form to JSON file and return file info + contents
        
        Args:
            user_id: User ID
            school_id: School ID
            filled_data: Dictionary with filled form data from FormFillService
            
        Returns:
            Dictionary with file path, timestamp, and filled data
        """
        try:
            # Generate filename
            filename = f"filled_form_user_{user_id}_school_{school_id}.json"
            filepath = self.output_dir / filename
            
            # Prepare output data with metadata
            output_data = {
                "metadata": {
                    "user_id": user_id,
                    "school_id": school_id,
                    "generated_at": datetime.now().isoformat(),
                    "file_path": str(filepath),
                    "version": "1.0"
                },
                "form_data": filled_data
            }
            
            # Write to JSON file
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            
            print(f"✓ Saved filled form to: {filepath}")
            
            return {
                "status": "success",
                "file_saved": True,
                "file_path": str(filepath),
                "file_size_kb": round(filepath.stat().st_size / 1024, 2),
                "saved_at": datetime.now().isoformat(),
                "user_id": user_id,
                "school_id": school_id,
                "filled_data": filled_data
            }
            
        except Exception as e:
            print(f"✗ Error saving form to JSON: {e}")
            return {
                "status": "error",
                "file_saved": False,
                "error": str(e),
                "user_id": user_id,
                "school_id": school_id,
                "filled_data": filled_data
            }
    
    def load_filled_form(self, user_id: str, school_id: str) -> Optional[Dict[str, Any]]:
        """
        Load previously saved filled form JSON
        
        Args:
            user_id: User ID
            school_id: School ID
            
        Returns:
            Dictionary with filled form data or None if not found
        """
        try:
            filename = f"filled_form_user_{user_id}_school_{school_id}.json"
            filepath = self.output_dir / filename
            
            if not filepath.exists():
                return None
            
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return data
            
        except Exception as e:
            print(f"Error loading filled form: {e}")
            return None
    
    def get_filled_form_for_schools(self, user_id: str, 
                                   school_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Get filled forms for multiple schools
        
        Args:
            user_id: User ID
            school_ids: List of school IDs
            
        Returns:
            Dictionary mapping school_id to filled form data
        """
        results = {}
        
        for school_id in school_ids:
            filled_form = self.load_filled_form(user_id, school_id)
            if filled_form:
                results[school_id] = filled_form
        
        return results
    
    def delete_filled_form(self, user_id: str, school_id: str) -> bool:
        """
        Delete a saved filled form JSON
        
        Args:
            user_id: User ID
            school_id: School ID
            
        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            filename = f"filled_form_user_{user_id}_school_{school_id}.json"
            filepath = self.output_dir / filename
            
            if filepath.exists():
                filepath.unlink()
                print(f"✓ Deleted: {filepath}")
                return True
            
            return False
            
        except Exception as e:
            print(f"Error deleting filled form: {e}")
            return False
    
    def list_filled_forms_for_user(self, user_id: str) -> List[Dict[str, str]]:
        """
        List all filled forms for a user
        
        Args:
            user_id: User ID
            
        Returns:
            List of form metadata dicts
        """
        results = []
        
        try:
            pattern = f"filled_form_user_{user_id}_school_*.json"
            
            for filepath in self.output_dir.glob(pattern):
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    metadata = data.get('metadata', {})
                    results.append({
                        "school_id": metadata.get('school_id', ''),
                        "generated_at": metadata.get('generated_at', ''),
                        "file_path": metadata.get('file_path', ''),
                        "file_size_kb": round(filepath.stat().st_size / 1024, 2)
                    })
                except Exception as e:
                    print(f"Error reading {filepath}: {e}")
                    continue
            
            return sorted(results, key=lambda x: x['generated_at'], reverse=True)
            
        except Exception as e:
            print(f"Error listing filled forms: {e}")
            return []
    
    def save_general_questions(self, user_id: str, 
                              filled_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Save filled general application questions to JSON file
        
        Args:
            user_id: User ID
            filled_data: Dictionary with filled general questions from FormFillService
            
        Returns:
            Dictionary with file path and metadata
        """
        try:
            # Generate filename
            filename = f"general_questions_user_{user_id}.json"
            filepath = self.output_dir / filename
            
            # Prepare output data with metadata
            output_data = {
                "metadata": {
                    "user_id": user_id,
                    "form_type": "general_application",
                    "generated_at": datetime.now().isoformat(),
                    "file_path": str(filepath),
                    "version": "1.0"
                },
                "form_data": filled_data
            }
            
            # Write to JSON file
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            
            print(f"✓ Saved general questions to: {filepath}")
            
            return {
                "status": "success",
                "file_saved": True,
                "file_path": str(filepath),
                "file_size_kb": round(filepath.stat().st_size / 1024, 2),
                "saved_at": datetime.now().isoformat(),
                "user_id": user_id,
                "filled_data": filled_data
            }
            
        except Exception as e:
            print(f"✗ Error saving general questions to JSON: {e}")
            return {
                "status": "error",
                "file_saved": False,
                "error": str(e),
                "user_id": user_id,
                "filled_data": filled_data
            }
    
    def load_general_questions(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Load previously saved general application questions
        
        Args:
            user_id: User ID
            
        Returns:
            Dictionary with filled general questions or None if not found
        """
        try:
            filename = f"general_questions_user_{user_id}.json"
            filepath = self.output_dir / filename
            
            if not filepath.exists():
                return None
            
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return data
            
        except Exception as e:
            print(f"Error loading general questions: {e}")
            return None


# Singleton instance
_instance = None


def get_service() -> SchoolFormOutputService:
    """Get singleton instance of SchoolFormOutputService"""
    global _instance
    if _instance is None:
        _instance = SchoolFormOutputService()
    return _instance
