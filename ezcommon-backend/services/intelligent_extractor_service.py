"""
Intelligent Document Extractor Service
使用 LLM 智能提取文档中的结构化信息（成绩、论文、获奖等）
"""

import os
import boto3
import PyPDF2
from io import BytesIO
from typing import List, Dict, Any, Optional
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class IntelligentExtractorService:
    def __init__(self, search_provider=None, llm_provider=None):
        """Initialize the intelligent extractor service
        
        Args:
            search_provider: Search provider instance (OpenSearch or ChromaDB)
            llm_provider: LLM provider instance for intelligent extraction
        """
        # AWS Configuration
        self.aws_region = os.getenv('AWS_REGION', 'us-east-1')
        self.aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')
        self.aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
        self.s3_bucket = os.getenv('S3_BUCKET_NAME', 'ezcommon-uploads')
        
        # OpenSearch Configuration
        self.opensearch_host = os.getenv('OPENSEARCH_HOST')
        self.opensearch_index = os.getenv('OPENSEARCH_INDEX', 'document_chunks')
        
        # Use injected LLM provider
        self.llm_provider = llm_provider
        
        # Initialize clients
        self.s3_client = boto3.client(
            's3',
            region_name=self.aws_region,
            aws_access_key_id=self.aws_access_key,
            aws_secret_access_key=self.aws_secret_key
        )
        
        # Use injected search provider
        self.search_provider = search_provider
        
        print("✓ Intelligent Extractor Service initialized")
    
    def list_user_files(self, user_id: str, section: Optional[str] = None) -> List[Dict[str, Any]]:
        """列出用户上传的文件"""
        try:
            files = []
            
            if section and section != 'all':
                # List files in specific section
                prefix = f"user-uploads/{user_id}/{section}/"
                response = self.s3_client.list_objects_v2(
                    Bucket=self.s3_bucket,
                    Prefix=prefix
                )
                
                if 'Contents' in response:
                    for obj in response['Contents']:
                        key = obj['Key']
                        filename = key.split('/')[-1]
                        if filename:  # Skip directory markers
                            files.append({
                                'filename': filename,
                                'section': section,
                                'size': obj['Size'],
                                'last_modified': obj['LastModified'].isoformat()
                            })
            else:
                # List files in all sections
                sections = ['education', 'activity', 'testing', 'profile']
                for sec in sections:
                    prefix = f"user-uploads/{user_id}/{sec}/"
                    response = self.s3_client.list_objects_v2(
                        Bucket=self.s3_bucket,
                        Prefix=prefix
                    )
                    
                    if 'Contents' in response:
                        for obj in response['Contents']:
                            key = obj['Key']
                            filename = key.split('/')[-1]
                            if filename:
                                files.append({
                                    'filename': filename,
                                    'section': sec,
                                    'size': obj['Size'],
                                    'last_modified': obj['LastModified'].isoformat()
                                })
            
            return files
        except Exception as e:
            print(f"Error listing files: {e}")
            raise
    
    def extract_text_from_pdf(self, file_content: bytes) -> str:
        """从 PDF 提取文本"""
        try:
            pdf_file = BytesIO(file_content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            
            return text.strip()
        except Exception as e:
            print(f"Error extracting PDF text: {e}")
            return ""
    
    def intelligent_extract(self, text: str, source_file: str, user_id: Optional[str] = None) -> List[Dict[str, str]]:
        """使用 GPT 智能提取文档中的结构化信息"""
        try:
            system_prompt = """你是一个专业的文档信息提取助手。你的任务是从给定的文档文本中提取结构化信息。

请仔细分析文档内容，识别并提取以下类型的信息：
1. **个人信息** (personal_info): 姓名、邮箱、电话、地址、出生日期等
2. **教育背景** (education): 学校名称、专业、学位、GPA、排名、课程等
3. **考试成绩** (test_scores): SAT、ACT、托福、雅思、AP、IB 等标准化考试成绩
4. **获奖荣誉** (awards): 各类奖项、荣誉称号、竞赛获奖等
5. **课外活动** (activities): 社团、志愿者、实习、工作经历等
6. **论文发表** (publications): 论文标题、期刊、会议、发表时间等
7. **项目经历** (projects): 项目名称、描述、技能、成果等
8. **技能特长** (skills): 编程语言、工具、语言能力、其他技能等
9. **推荐信息** (recommendations): 推荐人信息、推荐内容等
10. **其他** (other): 其他重要信息

对于每条提取的信息，请返回 JSON 格式：
{
  "category": "类别名称",
  "information": "具体信息内容"
}

要求：
- 每条信息应该是独立、完整的
- 信息内容要准确、简洁
- 如果某个类别有多条信息，请分别提取
- 只提取文档中明确存在的信息，不要推测或编造
- 返回 JSON 数组格式

示例输出：
[
  {"category": "personal_info", "information": "姓名: 张三"},
  {"category": "personal_info", "information": "邮箱: zhangsan@example.com"},
  {"category": "education", "information": "北京大学 计算机科学与技术 本科 GPA: 3.8/4.0"},
  {"category": "test_scores", "information": "SAT: 1520 (Math: 800, Reading: 720)"},
  {"category": "awards", "information": "2023年全国大学生数学建模竞赛一等奖"}
]
"""
            
            user_prompt = f"""请从以下文档中提取结构化信息：

文档内容：
{text[:8000]}  # 限制长度避免超过 token 限制

请返回 JSON 数组格式的提取结果。"""
            
            if not self.llm_provider:
                print("Error: LLM provider not initialized")
                return []
            
            response = self.llm_provider.chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.0,
                max_tokens=2048
            )
            
            result_text = response['content'].strip()
            
            # Parse JSON response
            import json
            try:
                # Try to parse as JSON object first
                result_obj = json.loads(result_text)
                
                # If it's a dict with a key containing array, extract it
                if isinstance(result_obj, dict):
                    for key in result_obj:
                        if isinstance(result_obj[key], list):
                            extracted_items = result_obj[key]
                            break
                    else:
                        # If no array found, wrap the dict
                        extracted_items = [result_obj]
                else:
                    extracted_items = result_obj
                
            except json.JSONDecodeError:
                print(f"Failed to parse GPT response as JSON: {result_text}")
                extracted_items = []

            # Add source file to each item
            for item in extracted_items:
                item['source_file'] = source_file
            
            return extracted_items
            
        except Exception as e:
            print(f"Error in intelligent extraction: {e}")
            return []
    
    def extract_from_files(self, user_id: str, files: List[Dict[str, str]]) -> Dict[str, Any]:
        """从多个文件中提取信息"""
        try:
            all_chunks = []
            
            for file_info in files:
                filename = file_info['filename']
                section = file_info['section']
                
                # Download file from S3
                s3_key = f"user-uploads/{user_id}/{section}/{filename}"
                
                try:
                    response = self.s3_client.get_object(
                        Bucket=self.s3_bucket,
                        Key=s3_key
                    )
                    file_content = response['Body'].read()
                    
                    # Extract text based on file type
                    if filename.lower().endswith('.pdf'):
                        text = self.extract_text_from_pdf(file_content)
                    else:
                        # For other file types, try to decode as text
                        try:
                            text = file_content.decode('utf-8')
                        except:
                            text = file_content.decode('latin-1', errors='ignore')
                    
                    if not text:
                        print(f"No text extracted from {filename}")
                        continue
                    
                    # Use GPT to extract structured information
                    chunks = self.intelligent_extract(text, filename, user_id=user_id)
                    
                    # Add section info
                    for chunk in chunks:
                        chunk['section'] = section
                    
                    all_chunks.extend(chunks)
                    
                except Exception as e:
                    print(f"Error processing file {filename}: {e}")
                    continue
            
            return {
                'status': 'success',
                'total_chunks': len(all_chunks),
                'chunks': all_chunks,
                'source_file': files[0]['filename'] if files else 'unknown'
            }
            
        except Exception as e:
            print(f"Error extracting from files: {e}")
            raise
    
    def store_chunks_to_opensearch(self, user_id: str, chunks: List[Dict[str, str]], source_file: str) -> Dict[str, Any]:
        """将提取的 chunks 存储到搜索提供程序（OpenSearch 或 ChromaDB）"""
        try:
            document_id = f"{user_id}_{source_file}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Prepare document
            document = {
                'document_id': document_id,
                'user_id': user_id,
                'source_file': source_file,
                'extraction_timestamp': datetime.now().isoformat(),
                'total_chunks': len(chunks),
                'chunks': chunks,
                'processor_info': {
                    'name': 'intelligent_extractor',
                    'version': '1.0',
                    'model': self.llm_provider.get_provider_info() if self.llm_provider else 'unknown'
                }
            }
            
            # Store using search_provider (supports OpenSearch, ChromaDB, etc.)
            if self.search_provider:
                # Use the abstract search provider interface
                success = self.search_provider.store_document(
                    document_id=document_id,
                    document=document
                )
                return {
                    'status': 'success' if success else 'failed',
                    'document_id': document_id,
                    'stored_chunks': len(chunks),
                    'provider': 'search_provider',
                    'response': {'stored': success}
                }
            else:
                return {
                    'status': 'warning',
                    'document_id': document_id,
                    'stored_chunks': len(chunks),
                    'provider': 'none',
                    'message': 'No search provider configured - data not stored'
                }
            
        except Exception as e:
            print(f"Error storing to search provider: {e}")
            raise
