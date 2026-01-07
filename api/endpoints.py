"""
Endpoints Router
================

İzlenen API endpoint'lerini listeleyen router.

ENDPOINT:
---------
GET /endpoints - Tüm endpoint'leri listeler
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db_session
from service.endpoint_service import endpoint_service
from api.schemas import EndpointResponse, EndpointListResponse

router = APIRouter(prefix="/endpoints", tags=["Endpoints"])


@router.get(
    "",
    response_model=EndpointListResponse,
    summary="İzlenen Endpoint'leri Listele",
    description="""
    Sistem tarafından izlenen tüm API endpoint'lerini listeler.
    
    Her endpoint için:
    - Path bilgisi
    - HTTP method
    - Açıklama (varsa)
    - İlk kayıt zamanı
    
    döndürülür.
    """
)
async def list_endpoints(
    skip: int = Query(0, ge=0, description="Atlanacak kayıt sayısı"),
    limit: int = Query(100, ge=1, le=500, description="Maksimum kayıt sayısı"),
    db: AsyncSession = Depends(get_db_session)
) -> EndpointListResponse:
    """
    İzlenen endpoint'leri listeler.
    
    Pagination parametreleri:
    - skip: Offset değeri
    - limit: Sayfa başına kayıt sayısı
    """
    endpoints = await endpoint_service.list_endpoints(
        session=db,
        skip=skip,
        limit=limit
    )
    
    total = await endpoint_service.get_endpoint_count(db)
    
    return EndpointListResponse(
        total=total,
        items=[
            EndpointResponse(
                id=e.id,
                path=e.path,
                method=e.method,
                description=e.description,
                created_at=e.created_at
            )
            for e in endpoints
        ]
    )
