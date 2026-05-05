import json
import logging
from typing import List, Dict, Any, Optional

from src.strategy.output_strategy import OutputStrategy

logger = logging.getLogger(__name__)


class FirebaseStrategy(OutputStrategy):

    def __init__(self,
                 database_url: str,
                 credentials_path: str,
                 root_node: str = "air_quality_data",
                 write_mode: str = "set",
                 batch_size: int = 100):

        self._database_url = database_url
        self._credentials_path = credentials_path
        self._root_node = root_node
        self._write_mode = write_mode
        self._batch_size = batch_size
        self._count = 0
        self._db = None
        self._root_ref = None

        self._init_firebase()

    def _init_firebase(self) -> None:

        try:
            import firebase_admin
            from firebase_admin import credentials, db

            if not firebase_admin._apps:
                cred = credentials.Certificate(self._credentials_path)
                firebase_admin.initialize_app(cred, {
                    "databaseURL": self._database_url
                })
                logger.info(
                    f"[FirebaseStrategy] Firebase Admin SDK initialized.\n"
                    f"  Database: {self._database_url}\n"
                    f"  Node:     /{self._root_node}"
                )

            self._db = db
            self._root_ref = db.reference(self._root_node)

        except ImportError:
            logger.error(
                "[FirebaseStrategy] 'firebase-admin' library is not installed.\n"
                "  Run: pip install firebase-admin"
            )
        except FileNotFoundError:
            logger.error(
                f"[FirebaseStrategy] Credentials file not found: '{self._credentials_path}'\n"
                "  Download it from Firebase Console -> Project Settings -> "
                "Service Accounts -> Generate new private key"
            )
        except Exception as exc:
            logger.warning(
                f"[FirebaseStrategy] Firebase initialization error: {exc}\n"
                "  Dry-run mode enabled."
            )

    def _get_record_id(self, record: Dict[str, Any]) -> str:
        for field in ("unique_key", "id", "objectid"):
            if field in record:
                return str(record[field])
        return str(self._count)

    def _sanitize(self, record: Dict[str, Any]) -> Dict[str, Any]:

        sanitized = {}
        forbidden = str.maketrans({".": "_", "#": "_", "$": "_",
                                    "[": "_", "]": "_"})
        for key, value in record.items():
            clean_key = key.translate(forbidden)
            if isinstance(value, (str, int, float, bool)) or value is None:
                sanitized[clean_key] = value
            else:
                sanitized[clean_key] = str(value)
        return sanitized

    def write(self, record: Dict[str, Any]) -> None:
        self._count += 1
        clean = self._sanitize(record)

        if not self._root_ref:
            logger.info(
                f"[FirebaseStrategy][DRY-RUN] #{self._count}: "
                f"{json.dumps(clean, ensure_ascii=False)}"
            )
            return

        try:
            if self._write_mode == "push":
                self._root_ref.push(clean)
            else:
                record_id = self._get_record_id(record)
                self._root_ref.child(record_id).set(clean)

        except Exception as exc:
            logger.error(f"[FirebaseStrategy] Write error for record #{self._count}: {exc}")

    def write_batch(self, records: List[Dict[str, Any]]) -> None:

        logger.info(
            f"[FirebaseStrategy] Writing {len(records)} records "
            f"to /{self._root_node} (batch size: {self._batch_size})..."
        )

        if not self._root_ref:
            for record in records:
                self.write(record)
            return

        for chunk_start in range(0, len(records), self._batch_size):
            chunk = records[chunk_start: chunk_start + self._batch_size]
            update_data = {}

            for record in chunk:
                self._count += 1
                clean = self._sanitize(record)

                if self._write_mode == "push":
                    update_data[str(self._count)] = clean
                else:
                    record_id = self._get_record_id(record)
                    update_data[record_id] = clean

            try:
                self._root_ref.update(update_data)
                logger.info(
                    f"[FirebaseStrategy] Batch {chunk_start // self._batch_size + 1}: "
                    f"{len(chunk)} records written."
                )
            except Exception as exc:
                logger.error(
                    f"[FirebaseStrategy] Batch write error "
                    f"(chunk {chunk_start}-{chunk_start + len(chunk)}): {exc}"
                )

    def close(self) -> None:

        logger.info(
            f"[FirebaseStrategy] Completed. "
            f"{self._count} records written to /{self._root_node}."
        )
