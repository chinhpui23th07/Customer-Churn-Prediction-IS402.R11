"""Feast FeatureStore configuration helper supporting local SQLite and Azure Redis."""

from __future__ import annotations

import os
from pathlib import Path

from feast import FeatureStore
from feast.infra.online_stores.redis import RedisOnlineStoreConfig
from feast.repo_config import load_repo_config


def build_redis_connection_string() -> str | None:
    """Build Feast Redis connection string from environment variables if configured."""
    host = os.getenv("REDIS_HOST", "").strip()
    if not host:
        return None
    port = os.getenv("REDIS_PORT", "6379").strip() or "6379"
    parts = [f"{host}:{port}"]
    if os.getenv("REDIS_SSL", "").strip().lower() in ("1", "true", "yes"):
        parts.append("ssl=true")
    password = (os.getenv("AZURE_REDIS_PASSWORD") or os.getenv("REDIS_PASSWORD") or "").strip()
    if password:
        parts.append(f"password={password}")
    return ",".join(parts)


def build_feature_store(repo_path: str | Path) -> FeatureStore:
    """Return a Feast FeatureStore backed by Azure Managed Redis when configured, else SQLite."""
    repo_dir = Path(repo_path).resolve()
    conn_str = build_redis_connection_string()
    if conn_str:
        cfg = load_repo_config(repo_dir, repo_dir / "feature_store.yaml")
        cfg.online_config = RedisOnlineStoreConfig(connection_string=conn_str)
        return FeatureStore(config=cfg)
    return FeatureStore(repo_path=str(repo_dir))
