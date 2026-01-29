#!/usr/bin/env python3
"""
Convert Common App Mapping Markdown to JSON format

Converts the markdown table from common_app_mapping.md to a JSON format
matching the structure of general_questions.json

Usage:
    python convert_md_to_json.py
"""

import json
import re
from pathlib import Path


def parse_markdown_table(md_file_path):
    """
    Parse markdown table and convert to JSON format
    
    Expected markdown format:
    | Section | Subsection | Question Label | Type | Options | Logic / Trigger |
    | :--- | :--- | :--- | :--- | :--- | :--- |
    | ... | ... | ... | ... | ... | ... |
    """
    
    with open(md_file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Split by lines
    lines = content.strip().split('\n')
    
    # Filter out header separators and empty lines
    data_lines = []
    for line in lines:
        # Skip header and separator lines
        if line.startswith('|') and '---' not in line and 'Section' not in line:
            data_lines.append(line)
    
    # Parse each data line
    questions = []
    
    for line in data_lines:
        # Remove leading/trailing pipes and split by pipe
        cells = [cell.strip() for cell in line.split('|')[1:-1]]
        
        if len(cells) >= 6:
            section = cells[0]
            subsection = cells[1]
            question_label = cells[2]
            question_type = cells[3]
            options = cells[4]
            logic = cells[5]
            
            # Create question object
            question = {
                "section": section,
                "subsection": subsection,
                "question_label": question_label,
                "type": question_type,
                "options": options,
                "logic": logic
            }
            
            questions.append(question)
    
    return questions


def save_to_json(questions, output_file_path):
    """Save questions to JSON file"""
    
    with open(output_file_path, 'w', encoding='utf-8') as f:
        json.dump(questions, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Successfully converted! Saved to: {output_file_path}")
    print(f"📊 Total questions: {len(questions)}")


def main():
    """Main function"""
    
    # Set file paths
    current_dir = Path(__file__).parent
    md_file = current_dir / "common_app_mapping.md"
    json_file = current_dir / "common_app_mapping.json"
    
    # Check if markdown file exists
    if not md_file.exists():
        print(f"❌ Error: {md_file} not found!")
        return
    
    print(f"📄 Reading markdown file: {md_file}")
    
    # Parse markdown
    questions = parse_markdown_table(md_file)
    
    if not questions:
        print("❌ Error: No questions found in markdown file!")
        return
    
    # Save to JSON
    print(f"💾 Converting to JSON format...")
    save_to_json(questions, json_file)
    
    # Print sample
    print("\n📋 Sample (first 3 questions):")
    for q in questions[:3]:
        print(json.dumps(q, indent=2, ensure_ascii=False))
        print("---")


if __name__ == "__main__":
    main()
