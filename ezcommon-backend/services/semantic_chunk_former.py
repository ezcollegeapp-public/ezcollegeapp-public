"""
Semantic Chunk Former Service

Reorganizes raw extracted text from documents into semantic blocks using LLM.
This is called AFTER text extraction but BEFORE storage to ChromaDB.
"""

import json
import re
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone


class SemanticChunkFormer:
    """Forms semantic chunks from raw extracted text using LLM"""
    
    def __init__(self, llm_provider):
        """
        Initialize the semantic chunk former
        
        Args:
            llm_provider: LLM provider instance for semantic restructuring
        """
        self.llm_provider = llm_provider
        self._context_limit_tokens = 100000  # Safe threshold for context length
    
    def form_semantic_chunks(self, 
                            raw_texts: List[Dict[str, str]],
                            user_id: str,
                            section: str) -> List[Dict[str, Any]]:
        """
        Transform raw extracted texts into semantic blocks
        
        Args:
            raw_texts: List of dicts with 'source_file', 'file_type', 'content'
            user_id: User ID for context
            section: Application section (education, activity, testing, etc.)
            
        Returns:
            List of semantic block dictionaries ready for storage
        """
        if not raw_texts:
            return []
        
        # Check context length safety
        combined_text = "\n\n".join([t['content'] for t in raw_texts])
        if not self._check_context_length(combined_text):
            raise RuntimeError(
                f"Combined documents exceed safe context length. "
                f"Fall back to Tier 2 processing or split documents."
            )
        
        # Call LLM to restructure into semantic blocks
        semantic_blocks = self._call_llm_for_semantic_formation(
            raw_texts=raw_texts,
            user_id=user_id,
            section=section,
            combined_text=combined_text
        )
        
        return semantic_blocks
    
    def _check_context_length(self, text: str) -> bool:
        """
        Check if text fits within safe context limits
        
        Args:
            text: Combined text content
            
        Returns:
            True if safe, False if exceeds limits
        """
        # Rough estimate: 1 token ≈ 4 characters
        estimated_tokens = len(text) / 4
        
        # Add prompt overhead (2000 tokens for system prompt + instructions)
        prompt_overhead = 2000
        total_tokens = int(estimated_tokens) + prompt_overhead
        
        # Safe threshold: 80% of context window (GPT-4o has 128K)
        safe_threshold = self._context_limit_tokens
        
        if total_tokens > safe_threshold:
            print(f"⚠ Context length warning: {total_tokens:,} tokens (limit: {safe_threshold:,})")
            return False
        
        return True
    
    def _call_llm_for_semantic_formation(self,
                                         raw_texts: List[Dict[str, str]],
                                         user_id: str,
                                         section: str,
                                         combined_text: str) -> List[Dict[str, Any]]:
        """
        Call LLM to restructure texts into semantic blocks
        
        Args:
            raw_texts: Original extracted texts with metadata
            user_id: User ID
            section: Application section
            combined_text: Combined text from all documents
            
        Returns:
            List of semantic blocks
        """
        # Build the LLM prompt
        prompt = self._build_semantic_formation_prompt(raw_texts, combined_text)
        
        try:
            if not self.llm_provider:
                raise RuntimeError("LLM provider not initialized")
            
            # Call LLM
            response = self.llm_provider.chat_completion(
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.0,  # Deterministic output
            )
            
            response_text = response['content']
            
            # Parse text format response
            semantic_blocks = self._parse_llm_response(
                response_text,
                raw_texts,
                user_id,
                section
            )
            
            return semantic_blocks
            
        except Exception as e:
            print(f"Error calling LLM for semantic formation: {e}")
            raise RuntimeError(f"Semantic chunk formation failed: {str(e)}")
    
    def _build_semantic_formation_prompt(self,
                                         raw_texts: List[Dict[str, str]],
                                         combined_text: str) -> str:
        """
        Build the prompt for LLM semantic restructuring
        
        Args:
            raw_texts: Original texts with metadata
            combined_text: Combined text content
            
        Returns:
            Formatted prompt for LLM
        """
        # Create document inventory with source markers
        doc_inventory = "\n".join([
            f"- {t['source_file']} ({t['file_type']}, {len(t['content'])} chars)"
            for t in raw_texts
        ])
        
        # Build document content with clear source markers
        marked_documents = self._create_marked_documents(raw_texts)
        
        prompt = f"""You are an expert at restructuring college application documents into semantic blocks.

TASK: Reorganize the provided documents into meaningful semantic blocks. Each block should represent one complete unit of related information that belongs together.

THE 11 SEMANTIC BLOCK TYPES YOU MUST USE:
1. PERSONAL_PROFILE - Identity, contact info, biographical data (name, DOB, address, etc.)
2. ACADEMIC_PERFORMANCE - Academic standing (GPA, class rank, high school, graduation date)
3. STANDARDIZED_TESTING - Test scores (SAT, ACT, AP exams with dates and scores)
4. RESEARCH_EXPERIENCE - Research projects with mentors, methods, outcomes, publications
5. AWARD_HONOR_RECOGNITION - Individual awards and honors with dates and reasons
6. EXTRACURRICULAR_ACTIVITY - Clubs, activities with roles, time commitment, impact
7. WORK_EXPERIENCE - Jobs and employment with responsibilities and outcomes
8. FAMILY_BACKGROUND - Family information (parents, siblings, household context)
9. ESSAYS_WRITING - Complete essays and writing samples with prompts
10. INSTITUTIONAL_PREFERENCES - College preferences, majors, admission plans
11. APPLICATION_METADATA - Administrative info (submission status, fees, consents)

SOURCE DOCUMENTS:
{doc_inventory}

RESTRUCTURING RULES:
- Group all related information from multiple documents into single blocks
- If a topic is not present in documents, do NOT create an empty block
- Each block should be complete and self-contained
- Preserve exact information but reorganize for clarity
- Track which source files contributed to each block
- Keep original data accuracy - do not infer or add information
- When extracting content, clearly attribute facts to their source files

RESPONSE FORMAT:
Return the blocks in plain text format (NOT JSON). Use this structure for each block:

---BLOCK_START---
BLOCK_TYPE: PERSONAL_PROFILE
SUMMARY: One sentence summary of what this block contains
SOURCES: source_file_1, source_file_2
PRIORITY: high/medium/low
CONTAINS_PERSONAL_DATA: true/false
CONTENT:
The reorganized and grouped content for this block goes here.
Include all relevant information in readable text format.
---BLOCK_END---

---BLOCK_START---
BLOCK_TYPE: ACADEMIC_PERFORMANCE
SUMMARY: Academic information summary
SOURCES: source_file_1
PRIORITY: high
CONTAINS_PERSONAL_DATA: false
CONTENT:
Academic details go here...
---BLOCK_END---

[Continue with more blocks as needed. Only include blocks that have content in the documents.]

DOCUMENTS TO RESTRUCTURE (Each document is marked with its source file name):
{marked_documents}

Now restructure these documents into semantic blocks:"""
        
        return prompt
    
    def _create_marked_documents(self, raw_texts: List[Dict[str, str]]) -> str:
        """
        Create document content with clear source markers so LLM knows which file each content comes from
        
        Args:
            raw_texts: List of dicts with source_file, file_type, content
            
        Returns:
            Marked document string with source attribution
        """
        marked = []
        for idx, text_obj in enumerate(raw_texts, 1):
            source_file = text_obj.get('source_file', 'unknown_file')
            file_type = text_obj.get('file_type', 'unknown_type')
            content = text_obj.get('content', '')
            
            # Create clear source marker block
            marker = f"""
================================================================================
[DOCUMENT {idx}] Source: {source_file} | Type: {file_type}
================================================================================
{content}
================================================================================
[END {source_file}]
================================================================================
"""
            marked.append(marker)
        
        return "\n".join(marked)
    
    def _parse_llm_response(self,
                           response_text: str,
                           raw_texts: List[Dict[str, str]],
                           user_id: str,
                           section: str) -> List[Dict[str, Any]]:
        """
        Parse LLM response in text format and convert to semantic blocks
        
        Args:
            response_text: Raw response from LLM (text format, not JSON)
            raw_texts: Original extracted texts
            user_id: User ID
            section: Application section
            
        Returns:
            List of semantic blocks ready for storage
        """
        try:
            # Parse text-based block format
            blocks = self._extract_blocks_from_text(response_text)
            
            # Transform parsed blocks into storage format
            semantic_blocks = []
            
            for idx, block_data in enumerate(blocks):
                semantic_block = {
                    'block_id': f"{user_id}_{section}_block_{idx}_{int(datetime.now(timezone.utc).timestamp())}",
                    'block_type': block_data.get('block_type', 'UNKNOWN'),
                    'content': block_data.get('content', ''),
                    'summary': block_data.get('summary', ''),
                    'sources': block_data.get('sources', []),
                    'user_id': user_id,
                    'section': section,
                    'category': self._map_block_type_to_category(block_data.get('block_type')),
                    'created_at': datetime.now(timezone.utc).isoformat(),
                    'metadata': {
                        'contains_personal_data': block_data.get('contains_personal_data', False),
                        'priority_for_filing': block_data.get('priority', 'medium')
                    }
                }
                
                semantic_blocks.append(semantic_block)
            
            return semantic_blocks
        
        except Exception as e:
            print(f"Failed to parse LLM response: {e}")
            print(f"Response was: {response_text[:500]}")
            raise RuntimeError(f"Failed to parse semantic blocks: {str(e)}")
    
    def _extract_blocks_from_text(self, response_text: str) -> List[Dict[str, Any]]:
        """
        Extract semantic blocks from text format response.
        Handles variations in LLM output format.
        
        Parses blocks in the format:
        ---BLOCK_START---
        BLOCK_TYPE: NAME
        SUMMARY: summary text
        SOURCES: file1, file2
        PRIORITY: high/medium/low
        CONTAINS_PERSONAL_DATA: true/false
        CONTENT:
        Content text goes here
        ---BLOCK_END---
        
        Also handles variations like:
        - Missing markers (---BLOCK_START---/---BLOCK_END---)
        - Alternate separators (##, ==, --, etc.)
        - Incomplete formatting
        
        Args:
            response_text: LLM response in text format
            
        Returns:
            List of parsed block dictionaries
        """
        blocks = []
        
        # Try primary format first: ---BLOCK_START---(content)---BLOCK_END---
        block_pattern = r'---BLOCK_START---(.*?)---BLOCK_END---'
        block_matches = re.findall(block_pattern, response_text, re.DOTALL)
        
        if block_matches:
            for block_text in block_matches:
                block_data = self._parse_single_block(block_text)
                if block_data and block_data.get('content', '').strip():
                    blocks.append(block_data)
            return blocks
        
        # Fallback 1: Try alternate separators
        alt_separators = [
            (r'#+\s*BLOCK\s*START\s*#+', r'#+\s*BLOCK\s*END\s*#+'),  # ### BLOCK START ###
            (r'==+\s*BLOCK\s*START\s*==+', r'==+\s*BLOCK\s*END\s*==+'),  # === BLOCK START ===
            (r'--+\s*BLOCK\s*START\s*--+', r'--+\s*BLOCK\s*END\s*--+'),  # --- BLOCK START ---
        ]
        
        for start_sep, end_sep in alt_separators:
            pattern = f'({start_sep})(.*?)({end_sep})'
            block_matches = re.findall(pattern, response_text, re.DOTALL | re.IGNORECASE)
            if block_matches:
                for match in block_matches:
                    block_text = match[1] if len(match) > 1 else match[0]
                    block_data = self._parse_single_block(block_text)
                    if block_data and block_data.get('content', '').strip():
                        blocks.append(block_data)
                return blocks
        
        # Fallback 2: Split by BLOCK_TYPE: pattern if no clear separators
        # Look for lines starting with "BLOCK_TYPE:"
        block_starts = [m.start() for m in re.finditer(r'^BLOCK_TYPE:', response_text, re.MULTILINE)]
        
        if block_starts:
            for i, start in enumerate(block_starts):
                # Find end position (start of next block or end of text)
                end = block_starts[i + 1] if i + 1 < len(block_starts) else len(response_text)
                block_text = response_text[start:end]
                block_data = self._parse_single_block(block_text)
                if block_data and block_data.get('content', '').strip():
                    blocks.append(block_data)
            return blocks
        
        # Fallback 3: If response looks like a single block without markers
        # Try to parse the entire response as one block
        if response_text.strip():
            block_data = self._parse_single_block(response_text)
            if block_data and block_data.get('content', '').strip():
                blocks.append(block_data)
        
        return blocks
    
    def _parse_single_block(self, block_text: str) -> Dict[str, Any]:
        """
        Parse a single block from text format.
        Handles missing fields and various formatting variations.
        
        Args:
            block_text: Text content of one block
            
        Returns:
            Dictionary with parsed block data, or None if invalid
        """
        block_data = {
            'block_type': 'UNKNOWN',
            'summary': '',
            'content': '',
            'sources': [],
            'priority': 'medium',
            'contains_personal_data': False
        }
        
        if not block_text or not block_text.strip():
            return None
        
        lines = block_text.split('\n')
        content_started = False
        content_lines = []
        
        for line in lines:
            original_line = line
            line = line.strip()
            
            if not line:
                if content_started:
                    content_lines.append('')
                continue
            
            # Parse metadata fields - handle case insensitive and with/without colons
            line_lower = line.lower()
            
            if line_lower.startswith('block_type'):
                # Extract value after: or =
                block_data['block_type'] = self._extract_field_value(line)
            elif line_lower.startswith('summary'):
                block_data['summary'] = self._extract_field_value(line)
            elif line_lower.startswith('source'):
                sources_str = self._extract_field_value(line)
                block_data['sources'] = [s.strip() for s in sources_str.split(',') if s.strip()]
            elif line_lower.startswith('priority'):
                priority = self._extract_field_value(line).lower()
                if priority in ['high', 'medium', 'low']:
                    block_data['priority'] = priority
            elif line_lower.startswith('contains_personal_data') or line_lower.startswith('personal_data'):
                value = self._extract_field_value(line).lower()
                block_data['contains_personal_data'] = value in ['true', 'yes', '1', 't', 'y']
            elif line_lower.startswith('content'):
                content_started = True
                # Get content after the CONTENT: marker
                content_part = self._extract_field_value(line)
                if content_part:
                    content_lines.append(content_part)
            elif content_started:
                content_lines.append(original_line.rstrip())
        
        # Join content lines and clean up
        block_data['content'] = '\n'.join(content_lines).strip()
        
        # Validate block has required data
        if not block_data['content']:
            return None
        
        # If block type is still UNKNOWN, try to infer from summary or content
        if block_data['block_type'] == 'UNKNOWN':
            block_data['block_type'] = self._infer_block_type(
                block_data['summary'],
                block_data['content']
            )
        
        return block_data
    
    def _extract_field_value(self, line: str) -> str:
        """
        Extract field value from a line like "FIELD_NAME: value" or "FIELD_NAME=value"
        
        Args:
            line: Line to parse
            
        Returns:
            Extracted value
        """
        # Try colon separator first
        if ':' in line:
            parts = line.split(':', 1)
            return parts[1].strip() if len(parts) > 1 else ''
        # Try equals separator
        elif '=' in line:
            parts = line.split('=', 1)
            return parts[1].strip() if len(parts) > 1 else ''
        # If no separator, return empty
        return ''
    
    def _infer_block_type(self, summary: str, content: str) -> str:
        """
        Infer block type from summary and content if not explicitly stated.
        
        Args:
            summary: Block summary
            content: Block content
            
        Returns:
            Inferred block type or 'UNKNOWN'
        """
        combined = f"{summary} {content}".lower()
        
        # Keywords for each block type
        type_keywords = {
            'PERSONAL_PROFILE': ['name', 'contact', 'email', 'phone', 'birthdate', 'address', 'personal'],
            'ACADEMIC_PERFORMANCE': ['gpa', 'grade', 'transcript', 'academic', 'school', 'class rank'],
            'STANDARDIZED_TESTING': ['sat', 'act', 'ap exam', 'test score', 'toefl', 'ielts'],
            'RESEARCH_EXPERIENCE': ['research', 'project', 'experiment', 'publication', 'mentor'],
            'AWARD_HONOR_RECOGNITION': ['award', 'honor', 'recognition', 'scholarship', 'dean\'s list'],
            'EXTRACURRICULAR_ACTIVITY': ['club', 'activity', 'volunteer', 'sport', 'team', 'leadership'],
            'WORK_EXPERIENCE': ['job', 'work', 'employment', 'internship', 'company', 'position'],
            'FAMILY_BACKGROUND': ['family', 'parent', 'sibling', 'household', 'brother', 'sister'],
            'ESSAYS_WRITING': ['essay', 'writing', 'prompt', 'statement', 'personal statement'],
            'INSTITUTIONAL_PREFERENCES': ['college', 'university', 'major', 'program', 'admission'],
            'APPLICATION_METADATA': ['application', 'submission', 'deadline', 'fee', 'status']
        }
        
        # Score each type based on keyword matches
        scores = {}
        for block_type, keywords in type_keywords.items():
            score = sum(1 for kw in keywords if kw in combined)
            if score > 0:
                scores[block_type] = score
        
        # Return type with highest score, or UNKNOWN if no matches
        if scores:
            return max(scores, key=scores.get)
        
        return 'UNKNOWN'
    
    def _map_block_type_to_category(self, block_type: str) -> str:
        """
        Map semantic block type to category for backwards compatibility
        
        Args:
            block_type: Semantic block type name
            
        Returns:
            Category string for storage
        """
        mapping = {
            'PERSONAL_PROFILE': 'personal_info',
            'ACADEMIC_PERFORMANCE': 'academic_performance',
            'STANDARDIZED_TESTING': 'test_scores',
            'RESEARCH_EXPERIENCE': 'research',
            'AWARD_HONOR_RECOGNITION': 'award',
            'EXTRACURRICULAR_ACTIVITY': 'activity',
            'WORK_EXPERIENCE': 'work',
            'FAMILY_BACKGROUND': 'family',
            'ESSAYS_WRITING': 'writing',
            'INSTITUTIONAL_PREFERENCES': 'education',
            'APPLICATION_METADATA': 'metadata'
        }
        return mapping.get(block_type, 'custom_documentation')
