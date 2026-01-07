"""
Analyze Router - Extended
==========================

Kullanıcının girdiği URL'leri analiz eden API endpoint'leri.

ENDPOINT'LER:
-------------
POST /analyze - URL analizi yapar (performans + güvenlik)
POST /analyze/pdf - URL analizi yapar ve PDF rapor döndürür
GET /analyze/history - Analiz geçmişini listeler
GET /analyze/history/{endpoint_id} - Belirli URL'in geçmiş detayları
"""

from typing import Optional, Any
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from core.database import get_db_session
from service.url_analyzer import url_analyzer
from service.pdf_generator import pdf_generator
from repository.endpoint_repository import endpoint_repository
from repository.metric_repository import metric_repository
from models.performance_metric import PerformanceMetric
from models.api_endpoint import ApiEndpoint

router = APIRouter(prefix="/analyze", tags=["URL Analysis"])


# ============================================================================
# Request/Response Schemas
# ============================================================================

class AnalyzeURLRequest(BaseModel):
    """URL analizi için request şeması."""
    url: str = Field(..., description="Analiz edilecek web sitesi URL'i", example="https://google.com")


# ============================================================================
# Endpoints
# ============================================================================

@router.post(
    "",
    summary="URL Analizi Yap",
    description="""
    Verilen web sitesi URL'ini kapsamlı şekilde analiz eder.
    
    **Analiz içeriği:**
    - Performans: Response süresi, timing breakdown, HTTP status
    - Güvenlik: Security headers, cookie güvenliği, SSL sertifika
    - Öneriler: Optimizasyon ve güvenlik tavsiyeleri
    """
)
async def analyze_url(
    request: AnalyzeURLRequest,
    db: AsyncSession = Depends(get_db_session)
):
    """
    URL analizi yapar - performans ve güvenlik.
    """
    try:
        # URL'i analiz et
        result = await url_analyzer.analyze_url(request.url)
        
        # Sonucu veritabanına kaydet
        if result["status"] == "success":
            performance = result.get("performance", {})
            
            # Endpoint kaydı oluştur
            endpoint = await endpoint_repository.get_or_create(
                session=db,
                path=result["url"],
                method="GET",
                description=f"External URL: {result['domain']}"
            )
            
            # Metrik kaydet
            if performance.get("avg_response_time_ms"):
                await metric_repository.create(
                    session=db,
                    endpoint_id=endpoint.id,
                    response_time_ms=performance["avg_response_time_ms"],
                    status_code=performance.get("status_code", 0)
                )
        
        return result
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analiz hatası: {str(e)}")


@router.post(
    "/pdf",
    summary="PDF Rapor İndir",
    description="URL analizi yapar ve sonucu PDF rapor olarak döndürür."
)
async def analyze_url_pdf(
    request: AnalyzeURLRequest,
    db: AsyncSession = Depends(get_db_session)
):
    """
    URL analizi yapar ve PDF rapor döndürür.
    """
    try:
        # URL'i analiz et
        result = await url_analyzer.analyze_url(request.url)
        
        if result["status"] != "success":
            raise HTTPException(status_code=400, detail=result.get("error", "Analiz başarısız"))
        
        # Veritabanına kaydet
        performance = result.get("performance", {})
        endpoint = await endpoint_repository.get_or_create(
            session=db,
            path=result["url"],
            method="GET",
            description=f"External URL: {result['domain']}"
        )
        
        if performance.get("avg_response_time_ms"):
            await metric_repository.create(
                session=db,
                endpoint_id=endpoint.id,
                response_time_ms=performance["avg_response_time_ms"],
                status_code=performance.get("status_code", 0)
            )
        
        # PDF oluştur
        pdf_bytes = pdf_generator.generate_report(result)
        
        # Domain adını dosya adı için temizle
        domain = result.get("domain", "report").replace(".", "_").replace(":", "_")
        filename = f"api_report_{domain}.pdf"
        
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF oluşturma hatası: {str(e)}")


@router.get(
    "/history",
    summary="Analiz Geçmişi",
    description="Daha önce analiz edilen URL'lerin listesini döndürür."
)
async def get_analysis_history(
    limit: int = 50,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Analiz geçmişini listeler.
    """
    # Endpoint'leri metrikleriyle birlikte getir
    result = await db.execute(
        select(
            ApiEndpoint.id,
            ApiEndpoint.path,
            ApiEndpoint.description,
            ApiEndpoint.created_at,
            func.count(PerformanceMetric.id).label("analysis_count"),
            func.avg(PerformanceMetric.response_time_ms).label("avg_response_time"),
            func.max(PerformanceMetric.created_at).label("last_analyzed")
        )
        .outerjoin(PerformanceMetric)
        .where(ApiEndpoint.path.like("http%"))  # Sadece external URL'ler
        .group_by(ApiEndpoint.id)
        .order_by(func.max(PerformanceMetric.created_at).desc())
        .limit(limit)
    )
    
    rows = result.all()
    
    return {
        "total": len(rows),
        "items": [
            {
                "id": row.id,
                "url": row.path,
                "description": row.description,
                "analysis_count": row.analysis_count,
                "avg_response_time_ms": round(row.avg_response_time or 0, 2),
                "last_analyzed": row.last_analyzed.isoformat() if row.last_analyzed else None,
                "first_analyzed": row.created_at.isoformat()
            }
            for row in rows
        ]
    }


@router.get(
    "/history/{endpoint_id}",
    summary="URL Detay Geçmişi",
    description="Belirli bir URL'in tüm analiz geçmişini detaylı gösterir."
)
async def get_url_history_detail(
    endpoint_id: int,
    limit: int = 100,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Belirli URL'in detaylı geçmişini listeler.
    """
    # Endpoint bilgisi
    endpoint_result = await db.execute(
        select(ApiEndpoint).where(ApiEndpoint.id == endpoint_id)
    )
    endpoint = endpoint_result.scalar_one_or_none()
    
    if not endpoint:
        raise HTTPException(status_code=404, detail="URL bulunamadı")
    
    # Bu URL'in tüm metrikleri
    metrics_result = await db.execute(
        select(PerformanceMetric)
        .where(PerformanceMetric.endpoint_id == endpoint_id)
        .order_by(PerformanceMetric.created_at.desc())
        .limit(limit)
    )
    metrics = metrics_result.scalars().all()
    
    # İstatistikler
    if metrics:
        response_times = [m.response_time_ms for m in metrics]
        stats = {
            "total_analyses": len(metrics),
            "avg_response_time_ms": round(sum(response_times) / len(response_times), 2),
            "min_response_time_ms": round(min(response_times), 2),
            "max_response_time_ms": round(max(response_times), 2),
            "success_count": sum(1 for m in metrics if 200 <= m.status_code < 400),
            "error_count": sum(1 for m in metrics if m.status_code >= 400 or m.status_code == 0),
        }
    else:
        stats = {
            "total_analyses": 0,
            "avg_response_time_ms": 0,
            "min_response_time_ms": 0,
            "max_response_time_ms": 0,
            "success_count": 0,
            "error_count": 0
        }
    
    # Chart data için son 20 analiz
    chart_data = [
        {
            "timestamp": m.created_at.isoformat(),
            "response_time_ms": m.response_time_ms,
            "status_code": m.status_code
        }
        for m in reversed(metrics[:20])  # Kronolojik sıra
    ]
    
    return {
        "endpoint": {
            "id": endpoint.id,
            "url": endpoint.path,
            "description": endpoint.description,
            "created_at": endpoint.created_at.isoformat()
        },
        "stats": stats,
        "chart_data": chart_data,
        "history": [
            {
                "id": m.id,
                "response_time_ms": m.response_time_ms,
                "status_code": m.status_code,
                "analyzed_at": m.created_at.isoformat()
            }
            for m in metrics
        ]
    }
