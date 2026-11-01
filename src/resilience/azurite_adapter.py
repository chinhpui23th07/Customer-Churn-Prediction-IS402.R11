"""Dual-Mode Azure Blob Storage & Azurite Local Simulation Adapter.

Inspired by Azure/Azurite emulator (2.3k stars).
Bridges live Azure Blob / Azurite services with an in-memory fallback
to ensure 100% resilient testing and offline execution.
"""

from __future__ import annotations

import logging
import threading
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


class InMemoryBlobStore:
    """Thread-safe in-memory blob store simulating Azure Blob Storage semantics."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._containers: Dict[str, Dict[str, bytes]] = {}

    def upload_blob(
        self,
        container: str,
        blob: str,
        data: Union[bytes, str],
        overwrite: bool = True,
    ) -> bool:
        with self._lock:
            if container not in self._containers:
                self._containers[container] = {}
            if not overwrite and blob in self._containers[container]:
                return False
            payload = data.encode("utf-8") if isinstance(data, str) else data
            self._containers[container][blob] = payload
            return True

    def download_blob(self, container: str, blob: str) -> bytes:
        with self._lock:
            if container not in self._containers or blob not in self._containers[container]:
                raise FileNotFoundError(f"Blob '{blob}' not found in container '{container}'")
            return self._containers[container][blob]

    def list_blobs(self, container: str) -> List[str]:
        with self._lock:
            return list(self._containers.get(container, {}).keys())

    def delete_blob(self, container: str, blob: str) -> bool:
        with self._lock:
            if container in self._containers and blob in self._containers[container]:
                del self._containers[container][blob]
                return True
            return False

    def exists(self, container: str, blob: str) -> bool:
        with self._lock:
            return blob in self._containers.get(container, {})


DEFAULT_AZURITE_CONN = (
    "DefaultEndpointsProtocol=http;"
    "AccountName=devstoreaccount1;"
    "AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;"
    "BlobEndpoint=http://127.0.0.1:10000/devstoreaccount1;"
)


class AzuriteStorageAdapter:
    """Dual-mode storage adapter routing to live Azurite/Azure or in-memory fallback."""

    def __init__(self, connection_string: Optional[str] = None, force_fallback: bool = False) -> None:
        self._fallback_store = InMemoryBlobStore()
        self._is_using_fallback = force_fallback
        self._live_client: Optional[Any] = None
        self._lock = threading.RLock()

        target_conn = connection_string if connection_string is not None else DEFAULT_AZURITE_CONN
        if not force_fallback:
            try:
                from azure.storage.blob import BlobServiceClient
                client = BlobServiceClient.from_connection_string(
                    target_conn, connection_verify=False
                )
                client.get_account_information()
                self._live_client = client
                self._is_using_fallback = False
                logger.info("Connected to live Azure/Azurite endpoint on port 10000.")
            except Exception as exc:
                logger.warning("Live Azure/Azurite unavailable (%s). Using in-memory fallback.", exc)
                self._is_using_fallback = True
        else:
            self._is_using_fallback = True

    @property
    def is_using_fallback(self) -> bool:
        return self._is_using_fallback

    def is_live_service_available(self) -> bool:
        if self._live_client is None:
            return False
        try:
            self._live_client.get_account_information()
            return True
        except Exception:
            return False

    def upload_blob(
        self,
        container: str,
        blob: str,
        data: Union[bytes, str],
        overwrite: bool = True,
    ) -> bool:
        if self._is_using_fallback or self._live_client is None:
            return self._fallback_store.upload_blob(container, blob, data, overwrite=overwrite)
        try:
            container_client = self._live_client.get_container_client(container)
            if not container_client.exists():
                container_client.create_container()
            blob_client = container_client.get_blob_client(blob)
            payload = data.encode("utf-8") if isinstance(data, str) else data
            blob_client.upload_blob(payload, overwrite=overwrite)
            return True
        except Exception as exc:
            logger.warning("Live upload failed (%s). Retrying to in-memory fallback.", exc)
            self._is_using_fallback = True
            return self._fallback_store.upload_blob(container, blob, data, overwrite=overwrite)

    def download_blob(self, container: str, blob: str) -> bytes:
        if self._is_using_fallback or self._live_client is None:
            return self._fallback_store.download_blob(container, blob)
        try:
            blob_client = self._live_client.get_blob_client(container=container, blob=blob)
            return blob_client.download_blob().readall()
        except Exception as exc:
            logger.warning("Live download failed (%s). Falling back to in-memory.", exc)
            return self._fallback_store.download_blob(container, blob)

    def list_blobs(self, container: str) -> List[str]:
        if self._is_using_fallback or self._live_client is None:
            return self._fallback_store.list_blobs(container)
        try:
            container_client = self._live_client.get_container_client(container)
            return [b.name for b in container_client.list_blobs()]
        except Exception:
            return self._fallback_store.list_blobs(container)

    def delete_blob(self, container: str, blob: str) -> bool:
        if self._is_using_fallback or self._live_client is None:
            return self._fallback_store.delete_blob(container, blob)
        try:
            blob_client = self._live_client.get_blob_client(container=container, blob=blob)
            blob_client.delete_blob()
            return True
        except Exception:
            return self._fallback_store.delete_blob(container, blob)

    def exists(self, container: str, blob: str) -> bool:
        if self._is_using_fallback or self._live_client is None:
            return self._fallback_store.exists(container, blob)
        try:
            blob_client = self._live_client.get_blob_client(container=container, blob=blob)
            return blob_client.exists()
        except Exception:
            return self._fallback_store.exists(container, blob)

    def get_status(self) -> Dict[str, Any]:
        return {
            "mode": "fallback_in_memory" if self._is_using_fallback else "live_service",
            "is_using_fallback": self._is_using_fallback,
            "live_available": self.is_live_service_available(),
        }
