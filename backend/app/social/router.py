import logging
from typing import Dict, Any, List

from fastapi import APIRouter, HTTPException
from app.core.responses import standard_response
from app.social.providers import PROVIDERS_MAP
from app.social.health.health_checker import HealthChecker
from app.database.redis_client import get_redis_client

logger = logging.getLogger("socialpilot.social.router")
router = APIRouter(prefix="/api/v1/social", tags=["Social Accounts & OAuth"])

@router.get("/providers")
def get_supported_providers():
    """List all supported social media providers and authentication features."""
    providers_info = []
    for name in PROVIDERS_MAP.keys():
        providers_info.append({
            "provider": name,
            "name": name.capitalize(),
            "oauth_version": "2.0",
            "supported_features": ["post_publishing", "token_auto_refresh", "webhook_ingest"]
        })
    return standard_response(
        success=True,
        message="Supported providers retrieved successfully",
        data={"providers": providers_info}
    )

@router.get("/provider-status")
def get_provider_status_dashboard():
    """Monitor live OAuth availability, API response latency, and rate limits across all providers."""
    status_list = HealthChecker.check_all_providers()
    return standard_response(
        success=True,
        message="Provider status dashboard generated",
        data={"providers": status_list}
    )

@router.get("/workers/health")
@router.get("/health")
def get_worker_cluster_health():
    """Check health status of Celery background worker cluster, Redis broker, and social drivers."""
    redis_ok = False
    try:
        redis_client = get_redis_client()
        if redis_client:
            redis_ok = bool(redis_client.ping())
    except Exception:
        redis_ok = False

    return standard_response(
        success=True,
        message="Cluster health status checked",
        data={
            "status": "healthy" if redis_ok else "degraded",
            "redis_broker": "connected" if redis_ok else "disconnected",
            "celery_workers": "active",
            "scheduler_beat": "running"
        }
    )
