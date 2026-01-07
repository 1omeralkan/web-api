"""
Suggestions Router
==================

Optimizasyon önerilerini sorgulayan router.

ENDPOINT'LER:
-------------
GET /suggestions         - Tüm önerileri listeler
POST /suggestions/analyze - Tüm endpoint'leri analiz eder ve öneri üretir
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db_session
from service.analysis_service import analysis_service
from models.optimization_suggestion import ProblemType, Severity
from api.schemas import (
    SuggestionResponse,
    SuggestionListResponse,
    AnalysisResultResponse,
    SeverityEnum,
    ProblemTypeEnum
)

router = APIRouter(prefix="/suggestions", tags=["Suggestions"])


@router.get(
    "",
    response_model=SuggestionListResponse,
    summary="Optimizasyon Önerilerini Listele",
    description="""
    Performans analizi sonucu üretilen optimizasyon önerilerini listeler.
    
    Öneriler önem seviyesine göre sıralanır (CRITICAL > HIGH > MEDIUM > LOW).
    
    Filtreleme seçenekleri:
    - severity: Önem seviyesi (low, medium, high, critical)
    - problem_type: Problem tipi (slow_response, high_error_rate, vb.)
    """
)
async def list_suggestions(
    skip: int = Query(0, ge=0, description="Atlanacak kayıt sayısı"),
    limit: int = Query(100, ge=1, le=500, description="Maksimum kayıt sayısı"),
    severity: Optional[SeverityEnum] = Query(None, description="Önem seviyesi filtresi"),
    problem_type: Optional[ProblemTypeEnum] = Query(None, description="Problem tipi filtresi"),
    db: AsyncSession = Depends(get_db_session)
) -> SuggestionListResponse:
    """
    Optimizasyon önerilerini listeler.
    """
    # Enum dönüşümü
    severity_filter = Severity(severity.value) if severity else None
    problem_filter = ProblemType(problem_type.value) if problem_type else None
    
    suggestions = await analysis_service.get_suggestions(
        session=db,
        severity=severity_filter,
        problem_type=problem_filter,
        limit=limit
    )
    
    return SuggestionListResponse(
        total=len(suggestions),
        items=[
            SuggestionResponse(
                id=s.id,
                endpoint_id=s.endpoint_id,
                problem_type=ProblemTypeEnum(s.problem_type.value),
                suggestion=s.suggestion,
                severity=SeverityEnum(s.severity.value),
                avg_response_time_ms=s.avg_response_time_ms,
                error_rate_percent=s.error_rate_percent,
                created_at=s.created_at,
                endpoint_path=s.endpoint.path if s.endpoint else None,
                endpoint_method=s.endpoint.method if s.endpoint else None
            )
            for s in suggestions
        ]
    )


@router.post(
    "/analyze",
    response_model=AnalysisResultResponse,
    summary="Performans Analizi Yap",
    description="""
    Tüm endpoint'ler için performans analizi yapar ve optimizasyon önerileri üretir.
    
    Analiz kuralları:
    - **Yavaş Response**: Ortalama response > 500ms → Cache/Index önerisi
    - **Yüksek Hata Oranı**: 5xx hata oranı > %10 → Hata yönetimi önerisi
    - **Yüksek Varyans**: Response süresi tutarsızlığı → Async işlem önerisi
    
    Bu endpoint, tüm endpoint'leri tarar ve mevcut önerileri günceller.
    """
)
async def run_analysis(
    hours_ago: int = Query(24, ge=1, le=720, description="Analiz periyodu (saat)"),
    db: AsyncSession = Depends(get_db_session)
) -> AnalysisResultResponse:
    """
    Tüm endpoint'ler için performans analizi yapar.
    """
    result = await analysis_service.analyze_all_endpoints(
        session=db,
        hours_ago=hours_ago
    )
    
    return AnalysisResultResponse(
        analyzed_endpoints=result["analyzed_endpoints"],
        total_suggestions=result["total_suggestions"],
        analysis_period_hours=result["analysis_period_hours"]
    )
