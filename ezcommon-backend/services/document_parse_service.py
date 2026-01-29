"""
Complete Document Parsing Service
Integrates with S3, OpenSearch, and LLM providers for full document processing
"""
import os
import json
import boto3
import tempfile
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
import base64
from .semantic_chunk_former import SemanticChunkFormer


class DocumentParseService:
    """Complete document parsing service with S3, OpenSearch, and LLM integration"""
    
    def __init__(self, search_provider=None, llm_provider=None):
        """Initialize the document parsing service
        
        Args:
            search_provider: Search provider instance (OpenSearch or ChromaDB)
            llm_provider: LLM provider instance for document analysis and vision
        """
        # AWS Configuration
        self.aws_region = os.environ.get('AWS_REGION', 'us-east-1')
        self.s3_bucket = os.environ.get('S3_BUCKET_NAME', 'ezcommon-uploads')
        self.s3_prefix = os.environ.get('S3_UPLOAD_PREFIX', 'user-uploads')

        # Use injected search provider
        self.search_provider = search_provider

        # Use injected LLM provider
        self.llm_provider = llm_provider
        
        # Initialize semantic chunk former
        self.semantic_chunk_former = SemanticChunkFormer(llm_provider) if llm_provider else None

        # Initialize S3 client
        self.s3_client = boto3.client('s3', region_name=self.aws_region)
        
        # Legacy OpenSearch support (if search_provider not used)
        if not search_provider:
            self.opensearch_host = os.environ.get('OPENSEARCH_HOST')
            self.opensearch_region = os.environ.get('OPENSEARCH_REGION', 'us-east-1')
            self.index_name = os.environ.get('OPENSEARCH_INDEX', 'document_chunks')
            self.opensearch_port = int(os.environ.get('OPENSEARCH_PORT', '443'))
            
            if self.opensearch_host:
                self.opensearch_client = self._get_opensearch_client()
                self._create_index_if_not_exists()
            else:
                self.opensearch_client = None
                print("Warning: Search provider not configured")
        else:
            self.opensearch_client = None
    
    def _get_opensearch_client(self):
        """Initialize OpenSearch client with AWS authentication"""
        credentials = boto3.Session().get_credentials()
        try:
            awsauth = AWS4Auth(
                credentials.access_key,
                credentials.secret_key,
                self.opensearch_region,
                'es',
                session_token=credentials.token
            )

            client = OpenSearch(
                hosts=[{'host': self.opensearch_host, 'port': self.opensearch_port}],
                http_auth=awsauth,
                use_ssl=True,
                verify_certs=True,
                connection_class=RequestsHttpConnection,
                timeout=5
            )

            # Test connection
            client.info()
            print(f"✓ OpenSearch connected: {self.opensearch_host}")
            return client
        except Exception as e:
            print(f"⚠ OpenSearch connection failed: {e}")
            print("  Service will continue without OpenSearch storage")
            return None
    
    def list_user_files(self, user_id: str, section: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List all files uploaded by a user from S3
        
        Args:
            user_id: User ID
            section: Optional section filter (education, activity, testing, profile)
            
        Returns:
            List of file information dictionaries
        """
        prefix = f"{self.s3_prefix}/{user_id}/"
        if section:
            prefix += f"{section}/"
        
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.s3_bucket,
                Prefix=prefix
            )
            
            files = []
            if 'Contents' in response:
                for obj in response['Contents']:
                    # Skip directory markers
                    if obj['Key'].endswith('/'):
                        continue
                    
                    # Extract section from path
                    key_parts = obj['Key'].split('/')
                    file_section = key_parts[2] if len(key_parts) > 2 else 'unknown'
                    filename = key_parts[-1]
                    
                    # Determine file type
                    file_ext = Path(filename).suffix.lower()
                    if file_ext == '.pdf':
                        file_type = 'pdf'
                    elif file_ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                        file_type = 'image'
                    else:
                        file_type = 'other'
                    
                    files.append({
                        'key': obj['Key'],
                        'filename': filename,
                        'section': file_section,
                        'file_type': file_type,
                        'size': obj['Size'],
                        'last_modified': obj['LastModified'].isoformat(),
                        'url': self._generate_presigned_url(obj['Key'])
                    })
            
            return files
        except Exception as e:
            print(f"Error listing files: {e}")
            return []
    
    def _generate_presigned_url(self, key: str, expiration: int = 3600) -> str:
        """Generate presigned URL for S3 object"""
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.s3_bucket, 'Key': key},
                ExpiresIn=expiration
            )
            return url
        except Exception as e:
            print(f"Error generating presigned URL: {e}")
            return ""
    
    def download_from_s3(self, s3_key: str) -> str:
        """
        Download file from S3 to temporary location
        
        Args:
            s3_key: S3 object key
            
        Returns:
            Path to downloaded temporary file
        """
        # Get file extension
        file_ext = Path(s3_key).suffix
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
            self.s3_client.download_fileobj(self.s3_bucket, s3_key, tmp_file)
            return tmp_file.name
    
    def process_pdf(self, file_path: str) -> str:
        """
        Extract text from PDF using PyPDF2 first, then OCR if needed

        Args:
            file_path: Path to PDF file

        Returns:
            Extracted text
        """
        try:
            import PyPDF2

            text_parts = []
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page_num in range(len(pdf_reader.pages)):
                    page = pdf_reader.pages[page_num]
                    text = page.extract_text()
                    if text.strip():
                        text_parts.append(f"--- Page {page_num + 1} ---\n{text}")

            extracted_text = "\n\n".join(text_parts)

            # If no text extracted or very little text, try OCR
            if not extracted_text.strip() or len(extracted_text.strip()) < 50:
                print(f"PDF text extraction yielded little content, trying OCR...")
                extracted_text = self._process_pdf_with_ocr(file_path)

            return extracted_text
        except Exception as e:
            # If PyPDF2 fails, try OCR as fallback
            print(f"PyPDF2 failed: {e}, trying OCR...")
            try:
                return self._process_pdf_with_ocr(file_path)
            except Exception as ocr_error:
                raise RuntimeError(f"PDF processing failed: PyPDF2 error: {str(e)}, OCR error: {str(ocr_error)}")

    def _process_pdf_with_ocr(self, file_path: str) -> str:
        """
        Extract text from PDF using OpenAI Vision API (for scanned PDFs or images)

        Args:
            file_path: Path to PDF file

        Returns:
            Extracted text via Vision API
        """
        try:
            from pdf2image import convert_from_path

            # Convert PDF to images
            print(f"Converting PDF to images for Vision API processing...")
            images = convert_from_path(file_path, dpi=200)  # Lower DPI for faster processing

            text_parts = []
            for page_num, image in enumerate(images, start=1):
                print(f"Vision API processing page {page_num}/{len(images)}...")

                # Convert PIL Image to base64
                import io
                buffer = io.BytesIO()
                image.save(buffer, format='PNG')
                image_bytes = buffer.getvalue()
                image_base64 = base64.b64encode(image_bytes).decode('utf-8')

                # Call LLM Vision API
                prompt = """Extract all text from this document image.

Please return the text exactly as it appears, maintaining the original structure and formatting.
If the document contains Chinese text, please extract it accurately.
If there are tables, lists, or structured data, preserve their format."""

                if not self.llm_provider:
                    raise RuntimeError("LLM provider not initialized")

                # Use llm_provider's vision_analysis method
                response = self.llm_provider.vision_analysis(
                    image_base64=image_base64,
                    prompt=prompt
                )

                text = response['content']
                if text.strip():
                    text_parts.append(f"--- Page {page_num} ---\n{text}")

            return "\n\n".join(text_parts)
        except Exception as e:
            raise RuntimeError(f"Vision API processing failed: {str(e)}")
    
    def process_image(self, file_path: str, source_file: str = None) -> Dict[str, Any]:
        """
        Extract information from image using OpenAI GPT-4 Vision

        Args:
            file_path: Path to image file
            source_file: Optional source filename to include in metadata

        Returns:
            Structured data extracted from image
        """
        try:
            # Read image file and encode to base64
            with open(file_path, 'rb') as image_file:
                image_bytes = image_file.read()

            image_base64 = base64.b64encode(image_bytes).decode('utf-8')

            # Determine image format
            file_ext = Path(file_path).suffix.lower()
            format_map = {
                '.jpg': 'jpeg',
                '.jpeg': 'jpeg',
                '.png': 'png',
                '.gif': 'gif',
                '.webp': 'webp'
            }
            image_format = format_map.get(file_ext, 'jpeg')

            # Call OpenAI GPT-4 Vision
            prompt = """Analyze this document image and extract all relevant information.

Return the information as a JSON object with the following structure:
{
    "information_chunks": [
        {
            "text": "extracted text or information",
            "category": "category name (e.g., personal_info, education, activity, test_scores, etc.)",
            "chunk_type": "type of information (e.g., text_field, date, score, etc.)"
        }
    ]
}

Extract as much structured information as possible. Be thorough and accurate."""

            if not self.llm_provider:
                raise RuntimeError("LLM provider not initialized")

            # Use llm_provider's vision_analysis method
            response = self.llm_provider.vision_analysis(
                image_base64=image_base64,
                prompt=prompt
            )

            # Parse response
            content = response['content']
            
            # Extract JSON from response
            try:
                # Try to find JSON in the response
                json_start = content.find('{')
                json_end = content.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = content[json_start:json_end]
                    structured_data = json.loads(json_str)
                else:
                    # Fallback: create simple structure
                    structured_data = {
                        "information_chunks": [{
                            "text": content,
                            "category": "custom_documentation",
                            "chunk_type": "raw_extraction"
                        }]
                    }
            except json.JSONDecodeError:
                # Fallback: create simple structure
                structured_data = {
                    "information_chunks": [{
                        "text": content,
                        "category": "custom_documentation",
                        "chunk_type": "raw_extraction"
                    }]
                }
            
            # Add source_files to all chunks if provided
            if source_file and "information_chunks" in structured_data:
                for chunk in structured_data["information_chunks"]:
                    chunk["source_files"] = [source_file]
            
            return structured_data
            
        except Exception as e:
            raise RuntimeError(f"Image processing failed: {str(e)}")
    
    def _format_structured_data_as_text(self, structured_data: Dict[str, Any]) -> str:
        """
        Convert Vision API structured data to readable text format
        
        Avoids embedding formatted JSON in prompts to prevent JSON parsing issues
        when the text becomes part of the LLM response JSON.
        
        Args:
            structured_data: Structured data from Vision API
            
        Returns:
            Human-readable text representation
        """
        text_parts = []
        
        chunks = structured_data.get('information_chunks', [])
        if chunks:
            for i, chunk in enumerate(chunks, 1):
                text = chunk.get('text', '')
                category = chunk.get('category', 'general')
                
                # Format as readable sections without JSON formatting
                text_parts.append(f"[Section {i} - {category}]\n{text}")
        
        return "\n\n".join(text_parts) if text_parts else str(structured_data)
    
    def _create_text_chunks(self, text: str, source_file: str = None) -> List[Dict[str, Any]]:
        """Create chunks from plain text"""
        if not text.strip():
            return []
        
        # Chunking parameters
        CHUNK_SIZE = 2000  # Characters per chunk
        OVERLAP = 200      # Character overlap between chunks
        
        text = text.strip()
        chunks = []
        
        # If text is smaller than chunk size, return single chunk
        if len(text) <= CHUNK_SIZE:
            chunk = {
                "text": text,
                "category": "custom_documentation",
                "chunk_type": "document_content"
            }
            if source_file:
                chunk["source_files"] = [source_file]  # Store as list
            return [chunk]
        
        # Split text into sentences for better chunk boundaries
        sentences = text.split('. ')
        current_chunk = ""
        chunk_index = 0
        has_overlap = False  # Track if current chunk contains overlap
        
        for i, sentence in enumerate(sentences):
            sentence = sentence.strip() + ('.' if i < len(sentences) - 1 else '')
            
            # Check if adding this sentence would exceed chunk size
            if len(current_chunk) + len(sentence) + 1 > CHUNK_SIZE and current_chunk.strip():
                # Save current chunk
                chunk = {
                    "text": current_chunk.strip(),
                    "category": "custom_documentation",
                    "chunk_type": "document_content"
                }
                if source_file:
                    # If this chunk has overlap from previous chunk, mark both source files
                    if has_overlap and len(chunks) > 0:
                        # This chunk contains overlap, so it has the same source file
                        # but we mark it to indicate it's an overlapping chunk
                        chunk["source_files"] = [source_file]
                        chunk["is_overlap_chunk"] = True
                    else:
                        chunk["source_files"] = [source_file]
                chunks.append(chunk)
                
                # Start new chunk with overlap from previous chunk
                # Include last OVERLAP characters from previous chunk for context
                overlap_text = current_chunk[-OVERLAP:] if len(current_chunk) > OVERLAP else current_chunk
                current_chunk = overlap_text + " " + sentence
                has_overlap = True  # Next chunk will have overlap
                chunk_index += 1
            else:
                current_chunk += " " + sentence if current_chunk else sentence
        
        # Don't forget the last chunk
        if current_chunk.strip():
            chunk = {
                "text": current_chunk.strip(),
                "category": "custom_documentation",
                "chunk_type": "document_content"
            }
            if source_file:
                # If this is the last chunk and has overlap, mark it
                if has_overlap and len(chunks) > 0:
                    chunk["source_files"] = [source_file]
                    chunk["is_overlap_chunk"] = True
                else:
                    chunk["source_files"] = [source_file]
            chunks.append(chunk)
        
        return chunks if chunks else [{"text": text, "category": "custom_documentation", "chunk_type": "document_content", "source_files": [source_file] if source_file else []}]
    
    def _generate_document_id(self, filename: str, user_id: str) -> str:
        """Generate unique document ID"""
        timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f')
        clean_filename = Path(filename).stem.replace(' ', '_')
        return f"doc_{user_id}_{clean_filename}_{timestamp}"

    def _store_document_chunks(self, document_id: str, source_file: str,
                              chunks: List[Dict[str, Any]],
                              processor_name: str,
                              file_type: str,
                              user_id: str,
                              section: str) -> Dict[str, Any]:
        """Store extracted chunks in search provider (ChromaDB)"""
        
        if not self.search_provider:
            return {"stored": False, "reason": "Search provider not configured"}
        
        # Prepare document with information_chunks format
        document = {
            "user_id": user_id,
            "source_file": source_file,
            "section": section,
            "file_type": file_type,
            "information_chunks": chunks
        }
        
        try:
            success = self.search_provider.store_document(document_id, document)
            if success:
                return {"stored": True, "chunks_stored": len(chunks)}
            else:
                return {"stored": False, "reason": "Search provider failed to store"}
        except Exception as e:
            print(f"    ⚠ Error storing in search provider: {e}")
            return {"stored": False, "reason": str(e)}

    def _create_index_if_not_exists(self):
        """Create OpenSearch index if it doesn't exist"""
        if not self.opensearch_client:
            return

        if not self.opensearch_client.indices.exists(index=self.index_name):
            index_body = {
                "mappings": {
                    "properties": {
                        "document_id": {"type": "keyword"},
                        "source_file": {"type": "text"},
                        "file_type": {"type": "keyword"},
                        "user_id": {"type": "keyword"},
                        "section": {"type": "keyword"},
                        "extraction_timestamp": {"type": "date"},
                        "categories_present": {"type": "keyword"},
                        "processor_info": {"type": "object"},
                        "information_chunks": {
                            "type": "nested",
                            "properties": {
                                "text": {"type": "text", "analyzer": "standard"},
                                "category": {"type": "keyword"},
                                "chunk_type": {"type": "keyword"}
                            }
                        }
                    }
                }
            }

            self.opensearch_client.indices.create(index=self.index_name, body=index_body)
            print(f"Created OpenSearch index: {self.index_name}")

    def form_semantic_chunks_for_user(self, 
                                      user_id: str, 
                                      section: str,
                                      raw_texts: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """
        Form semantic chunks from raw extracted texts for a user
        
        Args:
            user_id: User ID
            section: Application section
            raw_texts: List of dicts with 'source_file', 'file_type', 'content'
            
        Returns:
            List of semantic blocks ready for storage
        """
        if not self.semantic_chunk_former:
            print("⚠ Semantic chunk former not initialized, returning raw chunks")
            return []
        
        try:
            print(f"Forming semantic chunks for {user_id} (section: {section})...")
            semantic_blocks = self.semantic_chunk_former.form_semantic_chunks(
                raw_texts=raw_texts,
                user_id=user_id,
                section=section
            )
            
            print(f"✓ Formed {len(semantic_blocks)} semantic blocks")
            return semantic_blocks
            
        except Exception as e:
            print(f"⚠ Semantic chunk formation failed: {e}")
            print("  Continuing with raw chunks")
            return []

    def process_file_from_s3(self, s3_key: str, user_id: str, progress_callback=None) -> Dict[str, Any]:
        """
        Process a file from S3

        Args:
            s3_key: S3 object key
            user_id: User ID
            progress_callback: Optional callback function(progress: int, message: str)

        Returns:
            Processing result dictionary
        """
        def report_progress(progress: int, message: str):
            """Helper to report progress"""
            if progress_callback:
                progress_callback(progress, message)
            print(f"[{progress}%] {message}")

        # Extract section and filename from key
        key_parts = s3_key.split('/')
        section = key_parts[2] if len(key_parts) > 2 else 'unknown'
        filename = key_parts[-1]

        # Determine file type
        file_ext = Path(filename).suffix.lower()
        if file_ext == '.pdf':
            file_type = 'pdf'
            processor_name = 'PyPDF2Processor'
        elif file_ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
            file_type = 'image'
            processor_name = 'OpenAIVisionProcessor'
        else:
            raise ValueError(f"Unsupported file type: {file_ext}")

        # Download file from S3
        report_progress(10, f"Downloading {filename} from S3...")
        local_path = self.download_from_s3(s3_key)

        try:
            # Process based on file type
            report_progress(25, f"Analyzing document structure...")

            if file_type == 'pdf':
                # Extract text from PDF
                report_progress(40, "Extracting text from PDF...")
                extracted_text = self.process_pdf(local_path)
            elif file_type == 'image':
                # Extract information from image using Vision API
                report_progress(40, "Processing image with AI Vision...")
                # process_image returns: {"information_chunks": [{"text": "...", "category": "...", "chunk_type": "...", "source_files": [...]}]}
                structured_data = self.process_image(local_path, source_file=filename)
                # Convert structured data to readable text format for semantic chunking
                # Avoid using json.dumps with indentation to prevent JSON parsing issues
                # when this content is embedded in the LLM response JSON
                extracted_text = self._format_structured_data_as_text(structured_data)
            else:
                raise ValueError(f"Unsupported file type: {file_ext}")

            if not extracted_text.strip():
                raise RuntimeError("No text could be extracted from the document")

            report_progress(60, "Forming semantic blocks from extracted content...")
            
            # NEW: Send raw extracted text directly to semantic chunking (no pre-chunking!)
            # This preserves all context for the LLM to make better decisions
            raw_texts = [{
                'source_file': filename,
                'file_type': file_type,
                'content': extracted_text
            }]
            
            # Form semantic chunks from this file
            semantic_blocks = self.form_semantic_chunks_for_user(user_id, section, raw_texts)
            
            # Use semantic blocks if available, otherwise fall back to raw text chunks
            if semantic_blocks:
                print(f"  ✓ Formed {len(semantic_blocks)} semantic blocks from extracted content")
                # Store semantic blocks
                document_id = self._generate_document_id(filename, user_id)
                for block in semantic_blocks:
                    if self.search_provider:
                        self.search_provider.store_document(block['block_id'], block)
                chunks_to_return = semantic_blocks
            else:
                print(f"  ⚠ Semantic chunking failed, creating fallback text chunks")
                # Fallback: create naive chunks from extracted text
                document_id = self._generate_document_id(filename, user_id)
                fallback_chunks = self._create_text_chunks(extracted_text, source_file=filename)
                # Store fallback chunks in search provider (ChromaDB/OpenSearch)
                self._store_document_chunks(
                    document_id=document_id,
                    source_file=filename,
                    chunks=fallback_chunks,
                    processor_name=processor_name,
                    file_type=file_type,
                    user_id=user_id,
                    section=section
                )
                chunks_to_return = fallback_chunks

            report_progress(95, "Finalizing...")
            print(f"  ✓ Processing complete for {filename}")
            if semantic_blocks:
                print(f"  Document ID: {document_id} ({len(semantic_blocks)} semantic blocks)")

            report_progress(100, "Processing complete!")

            return {
                "status": "success",
                "document_id": document_id,
                "source_file": filename,
                "s3_key": s3_key,
                "section": section,
                "file_type": file_type,
                "chunks_created": len(chunks_to_return),
                "chunks": chunks_to_return,
                "processor_used": processor_name,
                "used_semantic_chunking": bool(semantic_blocks)
            }

        finally:
            # Clean up temporary file
            try:
                os.unlink(local_path)
            except:
                pass

