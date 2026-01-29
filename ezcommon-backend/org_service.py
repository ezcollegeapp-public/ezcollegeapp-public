from typing import Optional, Dict, Any
from datetime import datetime, timezone

from botocore.exceptions import ClientError

from aws_config import DYNAMODB_ORGS_TABLE, get_dynamodb_resource


class OrgService:
    """Simple service for managing organizations.

    For now we only support creating an organization when an org admin
    registers, and fetching organizations by id.
    """

    def __init__(self, table_name: str = DYNAMODB_ORGS_TABLE) -> None:
        self.dynamodb = get_dynamodb_resource()
        self.table = self.dynamodb.Table(table_name)

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def create_org(
        self,
        org_id: str,
        name: str,
        owner_user_id: str,
        contact_email: str,
    ) -> Dict[str, Any]:
        """Create a new organization record.

        This is idempotent on org_id, later calls will overwrite the record.
        """

        now = self._utc_now()
        item: Dict[str, Any] = {
            "id": org_id,
            "name": name,
            "owner_user_id": owner_user_id,
            "contact_email": contact_email,
            "created_at": now,
            "updated_at": now,
        }

        try:
            self.table.put_item(Item=item)
            return item
        except ClientError as e:
            print(f"Error creating organization: {e}")
            raise

    def get_org_by_id(self, org_id: str) -> Optional[Dict[str, Any]]:
        """Fetch organization by id, returns None if not found."""

        try:
            response = self.table.get_item(Key={"id": org_id})
            return response.get("Item")
        except ClientError as e:
            print(f"Error getting organization by id: {e}")
            return None

