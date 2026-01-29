"""
Form Fill Service
Extracts field values from parsed document chunks using LLM
"""
import os
import boto3
from typing import Dict, Any, List, Optional
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
import json
from pathlib import Path
from config import ConfigLoader


class FormFillService:
    """Service for filling form fields using document chunks and LLM"""
    
    def __init__(self, search_provider=None, llm_provider=None):
        """Initialize the form fill service
        
        Args:
            search_provider: Search provider instance (OpenSearch or ChromaDB)
            llm_provider: LLM provider instance for form field extraction
        """
        # AWS Configuration
        self.aws_region = os.environ.get('AWS_REGION', 'us-east-1')

        # Use injected search provider
        self.search_provider = search_provider

        # Use injected LLM provider
        self.llm_provider = llm_provider
        
        # Load general questions
        self.general_questions = self._load_general_questions()
    
    def _load_general_questions(self) -> List[Dict[str, Any]]:
        """Load general_questions.json from config directory"""
        try:
            config_path = Path(__file__).parent.parent / "config" / "common_app_mapping.json"
            if config_path.exists():
                with open(config_path, 'r') as f:
                    return json.load(f)
            else:
                print(f"Warning: general_questions.json not found at {config_path}")
                return []
        except Exception as e:
            print(f"Error loading general_questions.json: {e}")
            return []
    
    def get_general_questions_by_section(self, section: str) -> List[Dict[str, Any]]:
        """Get all questions for a specific section"""
        return [q for q in self.general_questions if q.get('section') == section]
    
    def get_all_sections(self) -> List[str]:
        """Get all unique sections from general_questions"""
        sections = set()
        for q in self.general_questions:
            section = q.get('section')
            if section:
                sections.add(section)
        return sorted(list(sections))
    
    def get_user_chunks(self, user_id: str, section: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Retrieve all document chunks for a user from search provider
        
        Args:
            user_id: User ID
            section: Optional section filter (education, activity, testing, profile)
            
        Returns:
            List of document chunks
        """
        if not self.search_provider:
            return []
        
        try:
            # Use search provider's get_all_chunks_for_user method
            chunks = self.search_provider.get_all_chunks_for_user(user_id, section)
            
            print(f"Retrieved {len(chunks)} chunks for user {user_id}")
            return chunks
            
        except Exception as e:
            print(f"Error retrieving chunks: {e}")
            return []
    
    def optimize_chunks_for_field(self, chunks: List[Dict[str, Any]], 
                                  field_category: str, 
                                  max_chunks: int = 200,
                                  use_optimization: bool = True) -> List[Dict[str, Any]]:
        """
        Optimize chunk selection based on field category
        
        Args:
            chunks: List of available chunks
            field_category: Category of field being extracted
            max_chunks: Maximum number of chunks to return
            use_optimization: If False, skip optimization and return all chunks (default: True)
            
        Returns:
            Optimized list of chunks (or all chunks if use_optimization=False)
        """
        # Option to bypass optimization
        if not use_optimization:
            # print(f"⚠ Optimization disabled - returning all {len(chunks)} chunks")
            return chunks[:max_chunks]
        
        # First, try to find chunks with matching or similar categories
        category_matches = []
        other_chunks = []
        
        field_category_lower = field_category.lower()
        
        for chunk in chunks:
            chunk_category = chunk.get('category', '').lower()
            
            # Exact or partial match
            if field_category_lower in chunk_category or chunk_category in field_category_lower:
                category_matches.append(chunk)
            else:
                other_chunks.append(chunk)
        
        # Prioritize category matches, then add others
        optimized = category_matches + other_chunks
        
        # Sort by text length (longer chunks first)
        optimized.sort(key=lambda x: len(x.get('text', '')), reverse=True)
        
        return optimized[:max_chunks]
    
    def extract_field_value(self, field_name: str, field_category: str,
                           field_source: str, chunks: List[Dict[str, Any]],
                           chunk_limit: int = 30,
                           user_id: Optional[str] = None) -> str:
        """
        Extract specific field value from document chunks using LLM
        
        Args:
            field_name: Name of the field to extract
            field_category: Category/type of information
            field_source: Suggested source of information
            chunks: List of document chunks
            chunk_limit: Maximum number of chunks to use
            
        Returns:
            Extracted field value or "NOT FOUND" message
        """
        # Limit chunks
        limited_chunks = chunks[:chunk_limit]
        
        if not limited_chunks:
            return "NOT FOUND - No document chunks available"
        
        # Build context from chunks
        context_str = self._build_chunks_context(limited_chunks)

        # Create prompt
        prompt = self._build_extraction_prompt(field_name, field_category, field_source, context_str)

        # Call LLM for field extraction
        try:
            if not self.llm_provider:
                return "NOT FOUND - LLM provider not initialized"

            response = self.llm_provider.chat_completion(
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.0,
                max_tokens=1024
            )

            # Extract response
            extracted_value = response['content'].strip()

            return extracted_value

        except Exception as e:
            return f"NOT FOUND - Error: {str(e)}"
    
    def _build_chunks_context(self, chunks: List[Dict[str, Any]]) -> str:
        """Build context string from document chunks"""
        chunks_context = []
        for idx, chunk in enumerate(chunks, 1):
            chunks_context.append(
                f"Chunk {idx}:\n"
                f"  Category: {chunk.get('category', 'unknown')}\n"
                f"  Type: {chunk.get('chunk_type', 'unknown')}\n"
                f"  Source: {chunk.get('source_file', 'unknown')} ({chunk.get('section', 'unknown')})\n"
                f"  Content: {chunk.get('text', '')}\n"
            )
        
        return "\n".join(chunks_context)
    
    def _build_extraction_prompt(self, field_name: str, field_category: str, 
                                field_source: str, context_str: str) -> str:
        """Build extraction prompt for LLM"""
        return f"""# Form Field Auto-Fill Assistant

You are a form field auto-fill assistant. Your task is to extract precise information from documents to fill specific form fields.

## Extraction Guidelines:

### 1. Semantic Matching:
- The category names in documents may differ from the expected category - use semantic understanding
- Look for information that conceptually matches what the field is asking for
- Consider variations in terminology (e.g., "personal_information" = "Personal Information" = "Contact Details")

### 2. Precision Rules:
- Extract ONLY the specific value needed, not the entire chunk
- Return the exact data point requested, nothing more

### 3. If Information Not Found:
- If the requested information is not in the documents, return exactly: "NOT FOUND"
- Do not make up or infer information

### 4. Format Rules:
Return ONLY the extracted value, nothing else.
- Do NOT include the field name
- Do NOT include labels or prefixes
- Do NOT include explanations
- Do NOT include checkmarks, symbols, or special characters
- Just the pure value

## Current Field to Fill:

**Field Name**: {field_name}
**Information Category**: {field_category}
**Suggested Information Source**: {field_source}

## Available Information from Documents:

{context_str}

## EXTRACTED VALUE:"""
    
    def fill_multiple_fields(self, user_id: str, field_definitions: List[Dict[str, str]], 
                            section: Optional[str] = None, use_optimization: bool = True) -> Dict[str, Any]:
        """
        Fill multiple form fields for a user
        
        Args:
            user_id: User ID
            field_definitions: List of field definitions with 'name', 'category', 'source'
            section: Optional section filter
            use_optimization: If False, skip chunk optimization (default: True)
            
        Returns:
            Dictionary with extraction results and statistics
        """
        # Get user's document chunks
        all_chunks = self.get_user_chunks(user_id, section)
        
        if not all_chunks:
            return {
                "status": "error",
                "message": "No document chunks found for user",
                "results": {}
            }
        
        # Extract each field
        results = {}
        found_count = 0
        not_found_count = 0
        
        for field_def in field_definitions:
            field_name = field_def.get('name', '')
            field_category = field_def.get('category', '')
            field_source = field_def.get('source', '')
            
            if not field_name:
                continue
            
            # Optimize chunks for this field
            optimized_chunks = self.optimize_chunks_for_field(all_chunks, field_category, 
                                                             use_optimization=use_optimization)
            
            # Extract value
            extracted_value = self.extract_field_value(
                field_name=field_name,
                field_category=field_category,
                field_source=field_source,
                chunks=optimized_chunks,
                user_id=user_id,
            )
            
            results[field_name] = extracted_value
            
            # Update statistics
            if "NOT FOUND" not in extracted_value.upper():
                found_count += 1
            else:
                not_found_count += 1
        
        return {
            "status": "success",
            "total_fields": len(field_definitions),
            "found_fields": found_count,
            "not_found_fields": not_found_count,
            "success_rate": round((found_count / len(field_definitions)) * 100, 2) if field_definitions else 0,
            "total_chunks_available": len(all_chunks),
            "results": results
        }
    
    def fill_school_questions(self, user_id: str, school_id: str, use_optimization: bool = True) -> Dict[str, Any]:
        """
        Fill all questions for a specific school from college_questions.json
        
        Args:
            user_id: User ID
            school_id: School ID (e.g., "48" for Caltech)
            use_optimization: If False, skip chunk optimization (default: True)
            
        Returns:
            Dictionary with filled questions and metadata
        """
        try:
            # Load school questions from config
            config_loader = ConfigLoader.get_instance()
            school_questions_by_page = config_loader.get_school_questions(school_id)
            
            # Get user chunks
            all_chunks = self.get_user_chunks(user_id)
            
            if not all_chunks:
                return {
                    "status": "warning",
                    "user_id": user_id,
                    "school_id": school_id,
                    "message": "No document chunks found for user",
                    "filled_questions": []
                }
            
            # Process all questions from all pages
            filled_questions = []
            total_questions = 0
            
            for page_url, questions in school_questions_by_page.items():
                for question in questions:
                    total_questions += 1
                    question_id = question.get('id', '')
                    label = question.get('label', '')
                    question_type = question.get('type', '')
                    required = question.get('required', False)
                    options = question.get('options', [])
                    
                    if not question_id:
                        continue
                    
                    # Optimize chunks for this question (use label as category hint)
                    optimized_chunks = self.optimize_chunks_for_field(
                        all_chunks,
                        label,  # Use question label as category hint
                        max_chunks=200,
                        use_optimization=use_optimization
                    )
                    
                    # Generate answer based on question type
                    if question_type in ['short_answer', 'long_answer']:
                        # For text questions, use LLM to generate answer
                        answer = self._generate_answer_for_question(
                            question_id=question_id,
                            label=label,
                            question_type=question_type,
                            chunks=optimized_chunks
                        )
                    elif question_type in ['single_select_dropdown', 'single_select_radio', 'multi_select_dropdown', 'multi_select_checkbox']:
                        # For select questions, try to match with options
                        answer = self._match_answer_to_options(
                            question_id=question_id,
                            label=label,
                            options=options,
                            chunks=optimized_chunks
                        )
                    else:
                        answer = "NOT FOUND"
                    
                    # Track which document chunk(s) provided the answer
                    source_files = set()
                    if answer != "NOT FOUND" and optimized_chunks:
                        for chunk in optimized_chunks[:3]:  # Use top 3 chunks as sources
                            if 'source_file' in chunk:
                                source_files.add(chunk['source_file'])
                    
                    # Create filled question object
                    filled_question = {
                        "question_id": question_id,
                        "label": label,
                        "type": question_type,
                        "required": required,
                        "answer": answer,
                        "source_files": list(source_files) if source_files else [],
                        "filled": answer != "NOT FOUND"
                    }
                    
                    filled_questions.append(filled_question)
            
            # Calculate statistics
            filled_count = sum(1 for q in filled_questions if q['filled'])
            required_filled = sum(1 for q in filled_questions if q['filled'] and q['required'])
            required_total = sum(1 for q in filled_questions if q['required'])
            
            return {
                "status": "success",
                "user_id": user_id,
                "school_id": school_id,
                "total_questions": total_questions,
                "filled_count": filled_count,
                "required_filled": required_filled,
                "required_total": required_total,
                "fill_percentage": round((filled_count / total_questions) * 100, 2) if total_questions > 0 else 0,
                "filled_questions": filled_questions
            }
            
        except ValueError as e:
            return {
                "status": "error",
                "user_id": user_id,
                "school_id": school_id,
                "message": str(e),
                "filled_questions": []
            }
        except Exception as e:
            print(f"Error filling school questions: {e}")
            return {
                "status": "error",
                "user_id": user_id,
                "school_id": school_id,
                "message": f"Unexpected error: {str(e)}",
                "filled_questions": []
            }
    
    def _generate_answer_for_question(self, question_id: str, label: str, 
                                     question_type: str, chunks: List[Dict[str, Any]]) -> str:
        """
        Generate answer for text-based question using LLM
        
        Args:
            question_id: Question ID
            label: Question label/text
            question_type: Type of question (short_answer, long_answer)
            chunks: Available document chunks
            
        Returns:
            Generated answer
        """
        if not chunks or not self.llm_provider:
            return "NOT FOUND"
        
        try:
            # Build context from chunks
            context_str = self._build_chunks_context(chunks)
            
            # Create prompt for answer generation
            prompt = f"""You are an application form filler. Based on the provided information from user documents, answer the following question.

## Question:
{label}

## Available Information:
{context_str}

## Instructions:
1. Answer based on the provided documents
2. If exact information is not available, make the best inference using the context provided
3. Only return "NOT FOUND" if absolutely no relevant information exists
4. Keep the answer concise and relevant
5. For essays, synthesize information from multiple chunks if needed

## Answer:"""
            
            response = self.llm_provider.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=1000
            )
            
            answer = response['content'].strip()
            
            # Check if answer is empty or just "NOT FOUND"
            if not answer or answer.upper() == "NOT FOUND":
                return "NOT FOUND"
            
            return answer
            
        except Exception as e:
            print(f"Error generating answer for question {question_id}: {e}")
            return "NOT FOUND"
    
    def _match_answer_to_options(self, question_id: str, label: str, 
                                options: List[str], chunks: List[Dict[str, Any]]) -> str:
        """
        Match user information to available options
        
        Args:
            question_id: Question ID
            label: Question label
            options: Available answer options
            chunks: Available document chunks
            
        Returns:
            Best matching option or "NOT FOUND"
        """
        if not options or not chunks or not self.llm_provider:
            return "NOT FOUND"
        
        try:
            # Build context
            context_str = self._build_chunks_context(chunks)
            
            # Create matching prompt
            options_str = "\n".join([f"- {opt}" for opt in options])
            
            prompt = f"""You are matching user information to form options.

## Question:
{label}

## Available Options:
{options_str}

## User Information:
{context_str}

## Instructions:
1. Find the best matching option based on user information
2. Return ONLY the option text that matches best
3. If no exact match, select the most reasonable option based on context
4. Only return "NOT FOUND" if no options seem relevant at all
5. Do not explain, just return the option

## Best Match:"""
            
            response = self.llm_provider.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=200
            )
            
            answer = response['content'].strip()
            
            # Verify answer is in options
            if answer in options:
                return answer
            
            # Try fuzzy matching if exact match fails
            for option in options:
                if answer.lower() in option.lower() or option.lower() in answer.lower():
                    return option
            
            return "NOT FOUND"
            
        except Exception as e:
            print(f"Error matching options for question {question_id}: {e}")
            return "NOT FOUND"
    
    def fill_general_questions(self, user_id: str, use_optimization: bool = True) -> Dict[str, Any]:
        """
        Fill all general application questions from general_questions.json
        
        Args:
            user_id: User ID
            use_optimization: If False, skip chunk optimization (default: True)
            
        Returns:
            Dictionary with filled general questions organized by section
        """
        try:
            if not self.general_questions:
                return {
                    "status": "error",
                    "user_id": user_id,
                    "message": "General questions not loaded",
                    "filled_sections": {}
                }
            
            # Get user chunks
            all_chunks = self.get_user_chunks(user_id)
            
            if not all_chunks:
                return {
                    "status": "warning",
                    "user_id": user_id,
                    "message": "No document chunks found for user",
                    "filled_sections": {}
                }
            
            # Organize questions by section
            filled_sections = {}
            total_questions = 0
            filled_count = 0
            
            for section in self.get_all_sections():
                section_questions = self.get_general_questions_by_section(section)
                filled_questions = []
                
                for question in section_questions:
                    total_questions += 1
                    question_label = question.get('question_label', '')
                    question_type = question.get('type', '')
                    options = question.get('options', '')
                    logic = question.get('logic', '')
                    
                    # Parse options if they exist
                    option_list = [opt.strip() for opt in options.split(',')] if options else []
                    
                    # Optimize chunks for this question
                    optimized_chunks = self.optimize_chunks_for_field(
                        all_chunks,
                        section,  # Use section as category hint
                        max_chunks=200,
                        use_optimization=use_optimization
                    )
                    
                    # Generate answer based on question type
                    if question_type in ['Text', 'Date']:
                        # For text/date questions, use LLM to extract answer
                        answer = self._generate_answer_for_question(
                            question_id=question_label,
                            label=question_label,
                            question_type=question_type,
                            chunks=optimized_chunks
                        )
                    elif question_type == 'Dropdown/Radio' and option_list:
                        # For select questions, try to match with options
                        answer = self._match_answer_to_options(
                            question_id=question_label,
                            label=question_label,
                            options=option_list,
                            chunks=optimized_chunks
                        )
                    else:
                        answer = "NOT FOUND"
                    
                    # Track which document chunk(s) provided the answer
                    source_files = set()
                    if answer != "NOT FOUND" and optimized_chunks:
                        for chunk in optimized_chunks[:3]:
                            if 'source_file' in chunk:
                                source_files.add(chunk['source_file'])
                    
                    if answer != "NOT FOUND":
                        filled_count += 1
                    
                    # Create filled question object
                    filled_question = {
                        "question_label": question_label,
                        "section": section,
                        "type": question_type,
                        "answer": answer,
                        "source_files": list(source_files) if source_files else [],
                        "filled": answer != "NOT FOUND",
                        "logic": logic
                    }
                    
                    filled_questions.append(filled_question)
                
                if filled_questions:
                    filled_sections[section] = filled_questions
            
            # Calculate statistics
            fill_percentage = round((filled_count / total_questions) * 100, 2) if total_questions > 0 else 0
            
            return {
                "status": "success",
                "user_id": user_id,
                "total_questions": total_questions,
                "filled_count": filled_count,
                "fill_percentage": fill_percentage,
                "filled_sections": filled_sections
            }
            
        except Exception as e:
            print(f"Error filling general questions: {e}")
            import traceback
            traceback.print_exc()
            return {
                "status": "error",
                "user_id": user_id,
                "message": f"Error: {str(e)}",
                "filled_sections": {}
            }


