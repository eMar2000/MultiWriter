"""DynamoDB interface for structured state"""

import json
from typing import Dict, Any, Optional, List
from datetime import datetime
from abc import ABC, abstractmethod
import boto3
from botocore.exceptions import ClientError


class StructuredState(ABC):
    """Abstract interface for structured state storage"""

    @abstractmethod
    async def write(self, table_name: str, item: Dict[str, Any]) -> bool:
        """Write an item to the table"""
        pass

    @abstractmethod
    async def read(self, table_name: str, key: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Read an item from the table"""
        pass

    @abstractmethod
    async def query(
        self,
        table_name: str,
        key_condition: Dict[str, Any],
        **kwargs
    ) -> List[Dict[str, Any]]:
        """Query items from the table"""
        pass

    @abstractmethod
    async def update(
        self,
        table_name: str,
        key: Dict[str, Any],
        updates: Dict[str, Any]
    ) -> bool:
        """Update an item in the table"""
        pass


class DynamoDBState(StructuredState):
    """DynamoDB implementation of structured state"""

    def __init__(
        self,
        region: str = "us-east-1",
        endpoint_url: Optional[str] = None,
        table_prefix: str = ""
    ):
        """
        Initialize DynamoDB client

        Args:
            region: AWS region
            endpoint_url: DynamoDB endpoint (None for production, localstack URL for testing)
            table_prefix: Prefix for table names
        """
        self.region = region
        self.endpoint_url = endpoint_url
        self.table_prefix = table_prefix

        # Initialize boto3 client
        self.client = boto3.client(
            'dynamodb',
            region_name=region,
            endpoint_url=endpoint_url
        )

        # Resource for higher-level operations
        self.resource = boto3.resource(
            'dynamodb',
            region_name=region,
            endpoint_url=endpoint_url
        )

    def _get_table_name(self, table_name: str) -> str:
        """Get full table name with prefix"""
        return f"{self.table_prefix}{table_name}" if self.table_prefix else table_name

    def _serialize_value(self, value: Any) -> Any:
        """Serialize value for DynamoDB"""
        if isinstance(value, str):
            return {"S": value}
        elif isinstance(value, (int, float)):
            return {"N": str(value)}
        elif isinstance(value, bool):
            return {"BOOL": value}
        elif isinstance(value, dict):
            return {"M": {k: self._serialize_value(v) for k, v in value.items()}}
        elif isinstance(value, list):
            return {"L": [self._serialize_value(item) for item in value]}
        elif isinstance(value, datetime):
            return {"S": value.isoformat()}
        elif value is None:
            return {"NULL": True}
        else:
            # Try to serialize as JSON string
            return {"S": json.dumps(value)}

    def _deserialize_value(self, value: Dict[str, Any]) -> Any:
        """Deserialize value from DynamoDB"""
        if "S" in value:
            return value["S"]
        elif "N" in value:
            num_str = value["N"]
            # Try int first, then float
            try:
                if "." in num_str:
                    return float(num_str)
                return int(num_str)
            except ValueError:
                return num_str
        elif "BOOL" in value:
            return value["BOOL"]
        elif "M" in value:
            return {k: self._deserialize_value(v) for k, v in value["M"].items()}
        elif "L" in value:
            return [self._deserialize_value(item) for item in value["L"]]
        elif "NULL" in value:
            return None
        else:
            return value

    def _item_to_dict(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Convert DynamoDB item to regular dict"""
        return {k: self._deserialize_value(v) for k, v in item.items()}

    async def write(self, table_name: str, item: Dict[str, Any]) -> bool:
        """Write an item to DynamoDB"""
        table = self.resource.Table(self._get_table_name(table_name))

        # Convert values to DynamoDB format
        dynamodb_item = {}
        for k, v in item.items():
            dynamodb_item[k] = self._serialize_value(v)

        try:
            table.put_item(Item=dynamodb_item)
            return True
        except ClientError as e:
            raise RuntimeError(f"DynamoDB write error: {str(e)}") from e

    async def read(self, table_name: str, key: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Read an item from DynamoDB"""
        table = self.resource.Table(self._get_table_name(table_name))

        # Convert key to DynamoDB format
        dynamodb_key = {}
        for k, v in key.items():
            dynamodb_key[k] = self._serialize_value(v)

        try:
            response = table.get_item(Key=dynamodb_key)
            if "Item" in response:
                return self._item_to_dict(response["Item"])
            return None
        except ClientError as e:
            raise RuntimeError(f"DynamoDB read error: {str(e)}") from e

    async def query(
        self,
        table_name: str,
        key_condition: Dict[str, Any],
        **kwargs
    ) -> List[Dict[str, Any]]:
        """Query items from DynamoDB"""
        table = self.resource.Table(self._get_table_name(table_name))

        # Build query parameters
        # Note: This is a simplified version; full implementation would support
        # KeyConditionExpression, FilterExpression, etc.
        try:
            # For now, use scan (inefficient but simple)
            # In production, this should use proper query with KeyConditionExpression
            response = table.scan()
            items = response.get("Items", [])
            return [self._item_to_dict(item) for item in items]
        except ClientError as e:
            raise RuntimeError(f"DynamoDB query error: {str(e)}") from e

    async def update(
        self,
        table_name: str,
        key: Dict[str, Any],
        updates: Dict[str, Any]
    ) -> bool:
        """Update an item in DynamoDB"""
        table = self.resource.Table(self._get_table_name(table_name))

        # Convert key
        dynamodb_key = {}
        for k, v in key.items():
            dynamodb_key[k] = self._serialize_value(v)

        # Build update expression
        update_expr = "SET " + ", ".join([f"{k} = :{k}" for k in updates.keys()])
        expr_values = {f":{k}": self._serialize_value(v) for k, v in updates.items()}

        try:
            table.update_item(
                Key=dynamodb_key,
                UpdateExpression=update_expr,
                ExpressionAttributeValues=expr_values
            )
            return True
        except ClientError as e:
            raise RuntimeError(f"DynamoDB update error: {str(e)}") from e
