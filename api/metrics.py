"""
Metrics Router
==============

Performans metriklerini sorgulayan router.

ENDPOINT'LER:
-------------
GET /metrics       - Tüm performans metriklerini listeler
GET /metrics/slow  - Yavaş çalışan endpoint'leri listeler
GET /metrics/stats - Endpoint bazlı istatistikleri getirir
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db_session
from core.config import get_settings
from service.metric_service import metric_service
from api.schemas import (
    MetricResponse,
    MetricListResponse,
    SlowEndpointResponse,
    SlowEndpointListResponse,
    EndpointStatsResponse
)

router = APIRouter(prefix="/metrics", tags=["Metrics"])
settings = get_settings()


@router.get(
    "",
    response_model=MetricListResponse,
    summary="Performans Metriklerini Listele",
    description="""
    Toplanan performans metriklerini listeler.
    
    Filtreleme seçenekleri:
    - endpoint_id: Belirli bir endpoint için
    - hours_ago: Son X saat içindeki metrikler
    
    En son metrikler ilk sırada döner.
    """
)
async def list_metrics(
    skip: int = Query(0, ge=0, description="Atlanacak kayıt sayısı"),
    limit: int = Query(100, ge=1, le=500, description="Maksimum kayıt sayısı"),
    endpoint_id: Optional[int] = Query(None, description="Endpoint ID filtresi"),
    hours_ago: Optional[int] = Query(None, ge=1, le=720, description="Son X saat"),
    db: AsyncSession = Depends(get_db_session)
) -> MetricListResponse:
    """
    Performans metriklerini listeler.
    """
    metrics = await metric_service.list_metrics(
        session=db,
        skip=skip,
        limit=limit,
        endpoint_id=endpoint_id,
        hours_ago=hours_ago
    )
    
    return MetricListResponse(
        total=len(metrics),
        items=[
            MetricResponse(
                id=m.id,
                endpoint_id=m.endpoint_id,
                response_time_ms=m.response_time_ms,
                status_code=m.status_code,
                created_at=m.created_at,
                endpoint_path=m.endpoint.path if m.endpoint else None,
                endpoint_method=m.endpoint.method if m.endpoint else None
            )
            for m in metrics
        ]
    )


@router.get(
    "/slow",
    response_model=SlowEndpointListResponse,
    summary="Yavaş Endpoint'leri Listele",
    description=f"""
    Yavaş çalışan endpoint'lerin metriklerini listeler.
    
    Varsayılan threshold: {settings.SLOW_RESPONSE_THRESHOLD_MS}ms
    
    En yavaş metrikler ilk sırada döner.
    """
)
async def list_slow_endpoints(
    threshold_ms: Optional[float] = Query(
        None,
        description=f"Yavaş kabul edilecek eşik (ms). Varsayılan: {settings.SLOW_RESPONSE_THRESHOLD_MS}"
    ),
    limit: int = Query(50, ge=1, le=200, description="Maksimum kayıt sayısı"),
    db: AsyncSession = Depends(get_db_session)
) -> SlowEndpointListResponse:
    """
    Threshold üzerindeki yavaş endpoint metriklerini getirir.
    """
    threshold = threshold_ms or settings.SLOW_RESPONSE_THRESHOLD_MS
    
    metrics = await metric_service.get_slow_endpoints(
        session=db,
        threshold_ms=threshold,
        limit=limit
    )
    
    return SlowEndpointListResponse(
        threshold_ms=threshold,
        total=len(metrics),
        items=[
            SlowEndpointResponse(
                endpoint_id=m.endpoint_id,
                path=m.endpoint.path if m.endpoint else "Unknown",
                method=m.endpoint.method if m.endpoint else "Unknown",
                response_time_ms=m.response_time_ms,
                status_code=m.status_code,
                recorded_at=m.created_at
            )
            for m in metrics
        ]
    )


@router.get(
    "/stats",
    response_model=list[EndpointStatsResponse],
    summary="Endpoint İstatistiklerini Getir",
    description="""
    Tüm endpoint'ler için aggregate istatistikleri getirir.
    
    Her endpoint için:
    - Toplam request sayısı
    - Ortalama response süresi
    - Maksimum response süresi
    
    Ortalama response süresine göre sıralanır (en yavaş önce).
    """
)
async def get_endpoint_stats(
    hours_ago: int = Query(24, ge=1, le=720, description="Son X saat"),
    db: AsyncSession = Depends(get_db_session)
) -> list[EndpointStatsResponse]:
    """
    Endpoint bazlı istatistikleri getirir.
    """
    stats = await metric_service.get_all_endpoint_statistics(
        session=db,
        hours_ago=hours_ago
    )
    
    return [
        EndpointStatsResponse(
            endpoint_id=s["endpoint_id"],
            path=s["path"],
            method=s["method"],
            request_count=s["request_count"],
            avg_response_time_ms=s["avg_response_time_ms"],
            max_response_time_ms=s["max_response_time_ms"]
        )
        for s in stats
    ]
