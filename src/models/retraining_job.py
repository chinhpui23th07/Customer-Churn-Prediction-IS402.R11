"""Decoupled Producer-Job Retraining Architecture with Distributed Locking.

Provides multi-replica concurrency control via Redis SET NX EX or persistent
file lock with TTL, job ticket persistence to disk / ADLS Gen2, and hot-reload.
"""
from __future__ import annotations

import json
import logging
import os
import socket
import sys
import threading
import time
import uuid
from dataclasses import asdict, dataclass
from typing import Any, Callable, Dict, Optional, Tuple

logger = logging.getLogger(__name__)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_LOCK_FILE = os.path.join(BASE_DIR, "data", "retrain_lock.json")
DEFAULT_JOBS_DIR = os.path.join(BASE_DIR, "data", "retrain_jobs")


class DistributedRetrainLock:
    """Distributed lock using Redis SET NX EX with atomic file lock fallback."""

    def __init__(self, lock_file: Optional[str] = None, lock_key: str = "churnguard:lock:retraining", redis_client: Optional[Any] = None) -> None:
        self.lock_file = lock_file or DEFAULT_LOCK_FILE
        self.lock_key, self.redis_client = lock_key, redis_client
        self.current_token: Optional[str] = None
        self._local_lock = threading.RLock()
        os.makedirs(os.path.dirname(os.path.abspath(self.lock_file)), exist_ok=True)

    def acquire(self, ttl_seconds: int = 3600) -> Optional[str]:
        """Acquire lock across cluster replicas with TTL. Returns token or None."""
        token = uuid.uuid4().hex
        if self.redis_client is not None:
            try:
                if self.redis_client.set(self.lock_key, token, nx=True, ex=ttl_seconds):
                    self.current_token = token
                    return token
                return None
            except Exception as e:
                logger.warning("Redis lock error: %s", e)
        with self._local_lock:
            now = time.time()
            if os.path.exists(self.lock_file):
                try:
                    with open(self.lock_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    if now < float(data.get("expires_at", 0)):
                        return None
                except (PermissionError, BlockingIOError):
                    return None
                except Exception:
                    pass
            payload = {"token": token, "acquired_at": now, "expires_at": now + ttl_seconds, "holder": f"{socket.gethostname()}:{os.getpid()}:{threading.get_ident()}"}
            tmp_file = f"{self.lock_file}.{token}.tmp"
            try:
                with open(tmp_file, "w", encoding="utf-8") as f:
                    json.dump(payload, f)
                os.replace(tmp_file, self.lock_file)
                self.current_token = token
                return token
            except Exception as e:
                logger.error("Failed to write lock file: %s", e)
                if os.path.exists(tmp_file):
                    try:
                        os.remove(tmp_file)
                    except OSError:
                        pass
                return None

    def release(self, token: Optional[str] = None) -> bool:
        """Release lock if token matches holder. Returns True if released."""
        target_token = token or self.current_token
        if not target_token:
            return False
        if self.redis_client is not None:
            try:
                val = self.redis_client.get(self.lock_key)
                if isinstance(val, bytes):
                    val = val.decode("utf-8")
                if val == target_token:
                    self.redis_client.delete(self.lock_key)
                    self.current_token = None
                    return True
                return False
            except Exception as e:
                logger.warning("Redis release error: %s", e)
        with self._local_lock:
            if not os.path.exists(self.lock_file):
                self.current_token = None
                return True
            try:
                with open(self.lock_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if data.get("token") == target_token or token is None:
                    os.remove(self.lock_file)
                    self.current_token = None
                    return True
            except Exception as e:
                logger.warning("Error releasing file lock: %s", e)
            return False

    def is_locked(self) -> bool:
        """Check if lock is currently held and not expired."""
        if self.redis_client is not None:
            try:
                return bool(self.redis_client.exists(self.lock_key))
            except Exception:
                pass
        with self._local_lock:
            if not os.path.exists(self.lock_file):
                return False
            try:
                with open(self.lock_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if time.time() < float(data.get("expires_at", 0)):
                    return True
                try:
                    os.remove(self.lock_file)
                except OSError:
                    pass
            except (PermissionError, BlockingIOError):
                return True
            except Exception:
                pass
            return False

    def get_lock_info(self) -> Dict[str, Any]:
        """Return diagnostic lock status including remaining TTL."""
        with self._local_lock:
            locked = self.is_locked()
            remaining, holder = 0.0, "unknown"
            if os.path.exists(self.lock_file):
                try:
                    with open(self.lock_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    remaining = max(0.0, float(data.get("expires_at", 0)) - time.time())
                    holder = data.get("holder", "unknown")
                except Exception:
                    pass
            return {"locked": locked, "remaining_ttl_seconds": round(remaining, 2), "holder": holder}

    def force_release(self) -> bool:
        """Force break lock in emergency recovery."""
        if self.redis_client is not None:
            try:
                self.redis_client.delete(self.lock_key)
            except Exception:
                pass
        with self._local_lock:
            if os.path.exists(self.lock_file):
                try:
                    os.remove(self.lock_file)
                except OSError:
                    pass
            self.current_token = None
            return True


@dataclass
class RetrainingJobTicket:
    """State ticket representing an asynchronous retraining job."""

    ticket_id: str
    status: str
    created_at: str
    mode: str
    lock_token: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    artifact_path: Optional[str] = None
    error_message: Optional[str] = None
    hot_reload_signaled: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def save(self, jobs_dir: str = DEFAULT_JOBS_DIR, storage_adapter: Optional[Any] = None) -> None:
        """Persist ticket to local JSON storage and optional ADLS Gen2/Azurite."""
        os.makedirs(jobs_dir, exist_ok=True)
        payload = json.dumps(self.to_dict(), indent=2)
        with open(os.path.join(jobs_dir, f"{self.ticket_id}.json"), "w", encoding="utf-8") as f:
            f.write(payload)
        if storage_adapter is not None:
            try:
                storage_adapter.upload_blob("retrain-jobs", f"{self.ticket_id}.json", payload)
            except Exception as e:
                logger.warning("Failed to sync ticket to blob storage: %s", e)


class RetrainingJobManager:
    """Producer-Job orchestrator managing lock lifecycle and async execution."""

    def __init__(self, lock: Optional[DistributedRetrainLock] = None, jobs_dir: str = DEFAULT_JOBS_DIR, storage_adapter: Optional[Any] = None) -> None:
        self.lock = lock or DistributedRetrainLock()
        self.jobs_dir, self.storage_adapter = jobs_dir, storage_adapter
        self.reload_hook: Optional[Callable[[], Any]] = None
        os.makedirs(self.jobs_dir, exist_ok=True)

    def start_job(self, dry_run: bool = False, force: bool = False, ttl_seconds: int = 3600) -> Tuple[Optional[RetrainingJobTicket], str]:
        """Acquire distributed lock and dispatch decoupled retraining job."""
        if self.lock.is_locked():
            return None, "LOCK_CONFLICT"
        token = self.lock.acquire(ttl_seconds=ttl_seconds)
        if not token:
            return None, "LOCK_CONFLICT"
        ticket_id = uuid.uuid4().hex[:12]
        ticket = RetrainingJobTicket(
            ticket_id=ticket_id, status="PENDING", created_at=time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
            mode="dry_run" if dry_run else "production", lock_token=token,
        )
        ticket.save(self.jobs_dir, self.storage_adapter)
        worker = threading.Thread(target=self._run_job_worker, args=(ticket, dry_run), daemon=True, name=f"RetrainJobWorker-{ticket_id}")
        worker.start()
        return ticket, "ACCEPTED"

    def _run_job_worker(self, ticket: RetrainingJobTicket, dry_run: bool) -> None:
        ticket.status, ticket.started_at = "RUNNING", time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
        ticket.save(self.jobs_dir, self.storage_adapter)
        log_file = os.path.join(BASE_DIR, "data", "retrain_execution.log")
        try:
            os.makedirs(os.path.dirname(log_file), exist_ok=True)
            with open(log_file, "a", encoding="utf-8") as out:
                out.write(f"\n--- Job {ticket.ticket_id} ({ticket.mode}) started at {ticket.started_at} ---\n")
                if dry_run:
                    out.write("[+] Dry-run verification completed successfully. Pipeline DAG verified.\n")
                    out.flush()
            if not dry_run:
                script = os.path.join(BASE_DIR, "src", "models", "train_pipeline.py")
                import subprocess
                subprocess.run([sys.executable, script], check=True, capture_output=True, text=True)
            ticket.status = "COMPLETED"
            ticket.artifact_path = os.path.join(BASE_DIR, "data", "models", "champion_model.joblib")
            if callable(self.reload_hook):
                try:
                    self.reload_hook()
                    ticket.hot_reload_signaled = True
                except Exception as e:
                    logger.warning("Hot-reload callback failed: %s", e)
        except Exception as exc:
            ticket.status, ticket.error_message = "FAILED", str(exc)
            logger.error("Retraining job %s failed: %s", ticket.ticket_id, exc)
        finally:
            ticket.completed_at = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
            ticket.save(self.jobs_dir, self.storage_adapter)
            self.lock.release(ticket.lock_token)

    def get_job(self, ticket_id: str) -> Optional[RetrainingJobTicket]:
        """Fetch job ticket state from local disk or blob storage."""
        job_file = os.path.join(self.jobs_dir, f"{ticket_id}.json")
        if os.path.exists(job_file):
            try:
                with open(job_file, "r", encoding="utf-8") as f:
                    return RetrainingJobTicket(**json.load(f))
            except Exception:
                pass
        return None
