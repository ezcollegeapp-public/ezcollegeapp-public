"""
Initialize DynamoDB tables for EZ Common Application
Creates the users table with proper indexes
"""
import boto3
from botocore.exceptions import ClientError
from aws_config import (
    AWS_REGION,
    DYNAMODB_USERS_TABLE,
    DYNAMODB_ORGS_TABLE,
    DYNAMODB_ORG_INVITATIONS_TABLE,
    get_dynamodb_client,
)


def create_users_table(table_name: str = DYNAMODB_USERS_TABLE):
    """
    Create DynamoDB users table with the following schema:
    - id (String, Primary Key): UUID for user
    - email (String, GSI): User email (unique)
    - first_name (String): User's first name
    - last_name (String): User's last name
    - password_hash (String): Hashed password
    - created_at (String): ISO timestamp
    - updated_at (String): ISO timestamp
    """
    dynamodb = get_dynamodb_client()

    try:
        # Check if table already exists
        existing_tables = dynamodb.list_tables()['TableNames']
        if table_name in existing_tables:
            print(f"✓ Table '{table_name}' already exists")
            return True

        # Create table
        print(f"Creating DynamoDB table: {table_name}...")

        response = dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {
                    'AttributeName': 'id',
                    'KeyType': 'HASH'  # Partition key
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'id',
                    'AttributeType': 'S'  # String
                },
                {
                    'AttributeName': 'email',
                    'AttributeType': 'S'  # String
                }
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'email-index',
                    'KeySchema': [
                        {
                            'AttributeName': 'email',
                            'KeyType': 'HASH'
                        }
                    ],
                    'Projection': {
                        'ProjectionType': 'ALL'
                    },
                    'ProvisionedThroughput': {
                        'ReadCapacityUnits': 5,
                        'WriteCapacityUnits': 5
                    }
                }
            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5
            },
            Tags=[
                {
                    'Key': 'Application',
                    'Value': 'EZCommon'
                },
                {
                    'Key': 'Environment',
                    'Value': 'Production'
                }
            ]
        )

        print(f"✓ Table '{table_name}' created successfully!")
        print(f"  Status: {response['TableDescription']['TableStatus']}")
        print(f"  ARN: {response['TableDescription']['TableArn']}")

        # Wait for table to be active
        print("Waiting for table to become active...")
        waiter = dynamodb.get_waiter('table_exists')
        waiter.wait(TableName=table_name)
        print("✓ Table is now active!")

        return True

    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'ResourceInUseException':
            print(f"✓ Table '{table_name}' already exists")
            return True
        else:
            print(f"✗ Error creating table: {e}")
            return False

def create_orgs_table(table_name: str = DYNAMODB_ORGS_TABLE):
    """Create DynamoDB table for organizations (simple id-based table)."""
    dynamodb = get_dynamodb_client()

    try:
        existing_tables = dynamodb.list_tables()["TableNames"]
        if table_name in existing_tables:
            print(f"✓ Table '{table_name}' already exists")
            return True

        print(f"Creating DynamoDB table: {table_name}...")
        response = dynamodb.create_table(
            TableName=table_name,
            KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
            ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
            Tags=[
                {"Key": "Application", "Value": "EZCommon"},
                {"Key": "Environment", "Value": "Production"},
            ],
        )
        print(f"✓ Table '{table_name}' created successfully!")
        print(f"  Status: {response['TableDescription']['TableStatus']}")
        print(f"  ARN: {response['TableDescription']['TableArn']}")
        waiter = dynamodb.get_waiter("table_exists")
        waiter.wait(TableName=table_name)
        print("✓ Table is now active!")
        return True
    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        if error_code == "ResourceInUseException":
            print(f"✓ Table '{table_name}' already exists")
            return True
        else:
            print(f"✗ Error creating table: {e}")
            return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False


def create_org_invitations_table(
    table_name: str = DYNAMODB_ORG_INVITATIONS_TABLE,
):
    """Create DynamoDB table for organization ↔ student invitations.

    Schema:
    - org_id (HASH): organization identifier
    - student_id (RANGE): student user id
    GSI:
    - student-index on (student_id)
    """
    dynamodb = get_dynamodb_client()

    try:
        existing_tables = dynamodb.list_tables()["TableNames"]
        if table_name in existing_tables:
            print(f"✓ Table '{table_name}' already exists")
            return True

        print(f"Creating DynamoDB table: {table_name}...")
        response = dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {"AttributeName": "org_id", "KeyType": "HASH"},
                {"AttributeName": "student_id", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "org_id", "AttributeType": "S"},
                {"AttributeName": "student_id", "AttributeType": "S"},
            ],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "student-index",
                    "KeySchema": [
                        {"AttributeName": "student_id", "KeyType": "HASH"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                    "ProvisionedThroughput": {
                        "ReadCapacityUnits": 5,
                        "WriteCapacityUnits": 5,
                    },
                }
            ],
            ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
            Tags=[
                {"Key": "Application", "Value": "EZCommon"},
                {"Key": "Environment", "Value": "Production"},
            ],
        )
        print(f"✓ Table '{table_name}' created successfully!")
        print(f"  Status: {response['TableDescription']['TableStatus']}")
        print(f"  ARN: {response['TableDescription']['TableArn']}")
        waiter = dynamodb.get_waiter("table_exists")
        waiter.wait(TableName=table_name)
        print("✓ Table is now active!")
        return True
    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        if error_code == "ResourceInUseException":
            print(f"✓ Table '{table_name}' already exists")
            return True
        else:
            print(f"✗ Error creating table: {e}")
            return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False



def describe_table(table_name: str = DYNAMODB_USERS_TABLE):
    """Describe the users table"""
    dynamodb = get_dynamodb_client()

    try:
        response = dynamodb.describe_table(TableName=table_name)
        table = response['Table']

        print(f"\n{'='*60}")
        print(f"Table: {table['TableName']}")
        print(f"{'='*60}")
        print(f"Status: {table['TableStatus']}")
        print(f"Item Count: {table['ItemCount']}")
        print(f"Size: {table['TableSizeBytes']} bytes")
        print(f"Created: {table['CreationDateTime']}")
        print(f"\nKey Schema:")
        for key in table['KeySchema']:
            print(f"  - {key['AttributeName']} ({key['KeyType']})")

        if 'GlobalSecondaryIndexes' in table:
            print(f"\nGlobal Secondary Indexes:")
            for gsi in table['GlobalSecondaryIndexes']:
                print(f"  - {gsi['IndexName']}")
                print(f"    Status: {gsi['IndexStatus']}")
                for key in gsi['KeySchema']:
                    print(f"    Key: {key['AttributeName']} ({key['KeyType']})")

        print(f"{'='*60}\n")
        return True

    except ClientError as e:
        print(f"✗ Error describing table: {e}")
        return False


def delete_table(table_name: str = DYNAMODB_USERS_TABLE):
    """Delete the users table (use with caution!)"""
    dynamodb = get_dynamodb_client()

    try:
        print(f"⚠️  Deleting table: {table_name}...")
        response = dynamodb.delete_table(TableName=table_name)
        print(f"✓ Table deletion initiated")

        # Wait for table to be deleted
        print("Waiting for table to be deleted...")
        waiter = dynamodb.get_waiter('table_not_exists')
        waiter.wait(TableName=table_name)
        print("✓ Table deleted successfully!")

        return True

    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'ResourceNotFoundException':
            print(f"✓ Table '{table_name}' does not exist")
            return True
        else:
            print(f"✗ Error deleting table: {e}")
            return False


def main():
    """Main function to initialize DynamoDB"""
    print("\n" + "=" * 60)
    print("EZ COMMON - DYNAMODB INITIALIZATION")
    print("=" * 60 + "\n")
    print(f"Region: {AWS_REGION}")
    print(f"Users Table: {DYNAMODB_USERS_TABLE}")
    print(f"Orgs Table: {DYNAMODB_ORGS_TABLE}")
    print(f"Org Invitations Table: {DYNAMODB_ORG_INVITATIONS_TABLE}\n")

    # Create users table
    success_users = create_users_table()
    # Create organizations table (optional)
    success_orgs = create_orgs_table()
    # Create org invitations table
    success_invites = create_org_invitations_table()

    if success_users and success_orgs and success_invites:
        # Describe the users table as a sanity check
        describe_table()
        print("✓ DynamoDB initialization completed successfully!\n")
    else:
        print("✗ DynamoDB initialization failed for one or more tables!\n")


if __name__ == "__main__":
    main()

