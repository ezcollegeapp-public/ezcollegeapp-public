from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from botocore.exceptions import ClientError

from aws_config import DYNAMODB_ORG_INVITATIONS_TABLE, get_dynamodb_resource


class OrgInvitationService:
    """Service for organization ↔ student invitations and relationships.

    We use a single DynamoDB table with composite key (org_id, student_id).
    Records track invitation status and act as the source of truth for
    organization membership when status == "accepted".
    """

    def __init__(self, table_name: str = DYNAMODB_ORG_INVITATIONS_TABLE) -> None:
        self.dynamodb = get_dynamodb_resource()
        self.table = self.dynamodb.Table(table_name)

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def create_invitation(
        self,
        org_id: str,
        student_id: str,
        org_name: Optional[str] = None,
        created_by_user_id: Optional[str] = None,
        message: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create or overwrite an invitation from org → student.

        If a record already exists for (org_id, student_id), its status will be
        reset to "pending" and timestamps updated.
        """

        now = self._utc_now()

        item: Dict[str, Any] = {
            "org_id": org_id,
            "student_id": student_id,
            "status": "pending",
            "created_at": now,
            "updated_at": now,
        }

        if org_name is not None:
            item["org_name"] = org_name
        if created_by_user_id is not None:
            item["created_by_user_id"] = created_by_user_id
        if message is not None:
            item["message"] = message

        try:
            self.table.put_item(Item=item)
            return item
        except ClientError as e:
            print(f"Error creating org invitation: {e}")
            raise

    def update_status(
        self,
        org_id: str,
        student_id: str,
        status: str,
    ) -> Optional[Dict[str, Any]]:
        """Update the status of an invitation.

        Returns the updated item, or None if not found.
        """

        now = self._utc_now()

        try:
            response = self.table.update_item(
                Key={"org_id": org_id, "student_id": student_id},
                UpdateExpression="SET #s = :s, updated_at = :ua",
                ExpressionAttributeNames={"#s": "status"},
                ExpressionAttributeValues={
                    ":s": status,
                    ":ua": now,
                },
                ConditionExpression="attribute_exists(org_id) AND attribute_exists(student_id)",
                ReturnValues="ALL_NEW",
            )
        except ClientError as e:
            # Conditional check failed → item does not exist
            if e.response["Error"].get("Code") == "ConditionalCheckFailedException":
                return None
            print(f"Error updating org invitation status: {e}")
            raise

        return response.get("Attributes")

    def get_invitations_for_student(self, student_id: str) -> List[Dict[str, Any]]:
        """List invitations for a given student (via GSI)."""

        try:
            response = self.table.query(
                IndexName="student-index",
                KeyConditionExpression="student_id = :sid",
                ExpressionAttributeValues={":sid": student_id},
            )
            return response.get("Items", [])
        except ClientError as e:
            print(f"Error querying invitations for student: {e}")
            return []

    def get_invitations_for_org(self, org_id: str) -> List[Dict[str, Any]]:
        """List invitations for a given organization (partition query)."""

        try:
            response = self.table.query(
                KeyConditionExpression="org_id = :oid",
                ExpressionAttributeValues={":oid": org_id},
            )
            return response.get("Items", [])
        except ClientError as e:
            print(f"Error querying invitations for org: {e}")
            return []

    def delete_invitation(self, org_id: str, student_id: str) -> bool:
        """Delete an invitation / relationship record."""

        try:
            self.table.delete_item(Key={"org_id": org_id, "student_id": student_id})
            return True
        except ClientError as e:
            print(f"Error deleting org invitation: {e}")
            return False

    def get_accepted_students_for_org(self, org_id: str) -> List[Dict[str, Any]]:
        """Return all accepted relationships for a given org.

        These represent the students that the org can manage.
        """

        items = self.get_invitations_for_org(org_id)
        return [item for item in items if item.get("status") == "accepted"]

