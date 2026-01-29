"""
User Service for DynamoDB
Handles user CRUD operations with DynamoDB
"""
from typing import Optional, Dict, Any, List, Union
from datetime import datetime, timezone
from uuid import uuid4
from decimal import Decimal
import boto3
from botocore.exceptions import ClientError
from passlib.context import CryptContext
from aws_config import DYNAMODB_USERS_TABLE, get_dynamodb_resource

# Password hashing context (same as backend for compatibility)
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

_UNSET = object()


def _convert_to_dynamo_value(value: Any):
    """Recursively convert floats to Decimal for DynamoDB compatibility."""
    if isinstance(value, float):
        return Decimal(str(value))
    if isinstance(value, list):
        return [_convert_to_dynamo_value(item) for item in value]
    if isinstance(value, dict):
        return {k: _convert_to_dynamo_value(v) for k, v in value.items()}
    return value


def _to_decimal(value: Union[Decimal, float, int, str, None], default: str = "0") -> Decimal:
    """Safely coerce supported numeric inputs into Decimal."""
    if value is None:
        return Decimal(default)
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except Exception:
        return Decimal(default)


class UserService:
    """Service class for user operations with DynamoDB"""
    
    def __init__(self, table_name: str = DYNAMODB_USERS_TABLE):
        self.dynamodb = get_dynamodb_resource()
        self.table = self.dynamodb.Table(table_name)
    
    def hash_password(self, password: str) -> str:
        """Hash a password"""
        return pwd_context.hash(password)
    
    def verify_password(self, password: str, password_hash: str) -> bool:
        """Verify a password against its hash"""
        return pwd_context.verify(password, password_hash)
    
    def create_user(
        self,
        email: str,
        first_name: str,
        last_name: str,
        password: str,
        role: str = "student",
        org_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Create a new user.

        Returns user data (without password_hash) if successful, None if email exists.

        Parameters
        ----------
        email: str
            User email (unique, case-insensitive).
        first_name: str
            First name.
        last_name: str
            Last name.
        password: str
            Plain text password (will be hashed).
        role: str
            User role, e.g. "student", "org_admin", "org_staff". Defaults to "student".
        org_id: Optional[str]
            Optional organization id this user belongs to (for org_* roles).
        """
        email = email.lower().strip()

        # Check if user already exists
        existing_user = self.get_user_by_email(email)
        if existing_user:
            return None

        # Create user
        user_id = str(uuid4())
        now = datetime.now(timezone.utc).isoformat()

        user_data = {
            "id": user_id,
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "password_hash": self.hash_password(password),
            "created_at": now,
            "updated_at": now,
            # Org / role fields (optional for backward-compat)
            "role": role,
            "org_id": org_id,
        }

        try:
            self.table.put_item(Item=user_data)
            return self._sanitize_user(user_data)
        except ClientError as e:
            print(f"Error creating user: {e}")
            return None

    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Get user by email using GSI
        Returns user data if found, None otherwise
        """
        email = email.lower().strip()
        
        try:
            response = self.table.query(
                IndexName='email-index',
                KeyConditionExpression='email = :email',
                ExpressionAttributeValues={
                    ':email': email
                }
            )
            
            items = response.get('Items', [])
            if items:
                return items[0]
            return None
            
        except ClientError as e:
            print(f"Error querying user by email: {e}")
            return None
    
    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user by ID
        Returns user data if found, None otherwise
        """
        try:
            response = self.table.get_item(Key={'id': user_id})
            return response.get('Item')
        except ClientError as e:
            print(f"Error getting user by ID: {e}")
            return None
    
    def authenticate_user(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        """
        Authenticate user with email and password
        Returns user data (without password_hash) if successful, None otherwise
        """
        user = self.get_user_by_email(email)
        
        if not user:
            return None
        
        if not self.verify_password(password, user['password_hash']):
            return None
        
        return self._sanitize_user(user)

    def update_user(
        self,
        user_id: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        password: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Update user information
        Returns updated user data if successful, None otherwise
        """
        # Build update expression
        update_parts = []
        expression_values = {}
        
        if first_name is not None:
            update_parts.append('first_name = :fn')
            expression_values[':fn'] = first_name
        
        if last_name is not None:
            update_parts.append('last_name = :ln')
            expression_values[':ln'] = last_name
        
        if password is not None:
            update_parts.append('password_hash = :ph')
            expression_values[':ph'] = self.hash_password(password)
        
        if not update_parts:
            return self.get_user_by_id(user_id)
        
        # Always update updated_at
        update_parts.append('updated_at = :ua')
        expression_values[':ua'] = datetime.now(timezone.utc).isoformat()
        
        update_expression = 'SET ' + ', '.join(update_parts)
        
        try:
            response = self.table.update_item(
                Key={'id': user_id},
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_values,
                ReturnValues='ALL_NEW'
            )
            
            return self._sanitize_user(response.get('Attributes'))
            
        except ClientError as e:
            print(f"Error updating user: {e}")
            return None
    
    def delete_user(self, user_id: str) -> bool:
        """
        Delete a user
        Returns True if successful, False otherwise
        """
        try:
            self.table.delete_item(Key={'id': user_id})
            return True
        except ClientError as e:
            print(f"Error deleting user: {e}")
            return False
    
    def list_users(self, limit: int = 100) -> list:
        """
        List all users (for admin purposes)
        Returns list of users without password_hash
        """
        try:
            response = self.table.scan(Limit=limit)
            users = response.get('Items', [])
            cleaned: List[Dict[str, Any]] = []
            for raw in users:
                sanitized = self._sanitize_user(raw)
                if sanitized:
                    cleaned.append(sanitized)
            return cleaned
        except ClientError as e:
            print(f"Error listing users: {e}")
            return []

    def _sanitize_user(self, user: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Remove sensitive fields before returning user objects."""
        if not user:
            return None
        user_copy = dict(user)
        user_copy.pop("password_hash", None)
        return user_copy


# Example usage and testing
if __name__ == "__main__":
    print("\n" + "="*60)
    print("USER SERVICE TEST")
    print("="*60 + "\n")
    
    service = UserService()
    
    # Test create user
    print("1. Creating test user...")
    user = service.create_user(
        email="test@example.com",
        first_name="Test",
        last_name="User",
        password="password123"
    )
    if user:
        print(f"✓ User created: {user['email']}")
    else:
        print("✗ User already exists or creation failed")
    
    # Test authenticate
    print("\n2. Testing authentication...")
    auth_user = service.authenticate_user("test@example.com", "password123")
    if auth_user:
        print(f"✓ Authentication successful: {auth_user['email']}")
    else:
        print("✗ Authentication failed")
    
    # Test wrong password
    print("\n3. Testing wrong password...")
    auth_user = service.authenticate_user("test@example.com", "wrongpassword")
    if auth_user:
        print("✗ Authentication should have failed!")
    else:
        print("✓ Authentication correctly rejected")
    
    # Test get user by email
    print("\n4. Getting user by email...")
    user = service.get_user_by_email("test@example.com")
    if user:
        print(f"✓ User found: {user['first_name']} {user['last_name']}")
    else:
        print("✗ User not found")
    
    print("\n" + "="*60 + "\n")
