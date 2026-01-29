"""
AWS Configuration for EZ Common Application
Handles DynamoDB, OpenSearch, and other AWS service configurations
"""
import os
import boto3
from typing import Optional

# AWS Region Configuration
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
AWS_REGION_BEDROCK = os.environ.get("AWS_REGION_BEDROCK", "us-east-2")

# DynamoDB Configuration
DYNAMODB_USERS_TABLE = os.environ.get("DYNAMODB_USERS_TABLE", "ezcommon-users")
# Table for storing organizations (optional, for future expansion)
DYNAMODB_ORGS_TABLE = os.environ.get("DYNAMODB_ORGS_TABLE", "ezcommon-orgs")
# Table for organization ↔ student invitations and relationships
DYNAMODB_ORG_INVITATIONS_TABLE = os.environ.get(
    "DYNAMODB_ORG_INVITATIONS_TABLE",
    "ezcommon-org-invitations",
)

# OpenSearch Configuration
OPENSEARCH_HOST = os.environ.get(
    "OPENSEARCH_HOST",
    "search-eiai-a3k4rgdcysqgg7y45x4dcdu7hy.us-east-1.es.amazonaws.com"
)
OPENSEARCH_INDEX = os.environ.get("OPENSEARCH_INDEX", "document_chunks")

# Bedrock Configuration
BEDROCK_MODEL_ARN = os.environ.get(
    "BEDROCK_MODEL_ARN",
    "arn:aws:bedrock:us-east-2:540764878694:inference-profile/us.anthropic.claude-3-5-sonnet-20241022-v2:0"
)


def get_dynamodb_client():
    """Get DynamoDB client"""
    return boto3.client('dynamodb', region_name=AWS_REGION)


def get_dynamodb_resource():
    """Get DynamoDB resource (higher-level interface)"""
    return boto3.resource('dynamodb', region_name=AWS_REGION)


def get_bedrock_client():
    """Get Bedrock runtime client"""
    return boto3.client('bedrock-runtime', region_name=AWS_REGION_BEDROCK)


def get_s3_client():
    """Get S3 client"""
    return boto3.client('s3', region_name=AWS_REGION)
