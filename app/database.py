import os
import uuid
import json
from datetime import datetime
from google.cloud import firestore

from google.auth.exceptions import DefaultCredentialsError

try:
    db = firestore.Client()
except DefaultCredentialsError:
    print("WARNING: Default credentials not found. Firestore will be disabled.")
    db = None

class Job:
    def __init__(self, id=None, status="PENDING", result_json=None, created_at=None, updated_at=None):
        self.id = id or str(uuid.uuid4())
        self.status = status
        self.result_json = result_json
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()

    def to_dict(self):
        return {
            "id": self.id,
            "status": self.status,
            "result_json": self.result_json,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }

    @staticmethod
    def from_dict(source):
        return Job(
            id=source.get("id"),
            status=source.get("status"),
            result_json=source.get("result_json"),
            created_at=source.get("created_at"),
            updated_at=source.get("updated_at")
        )

# Mock dependency for FastAPI that returns the Firestore client
def get_db():
    yield db
