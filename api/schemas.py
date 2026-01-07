"""
Pydantic Schemas
================

API request/response validasyonu için Pydantic modelleri.

YAZILIM KALİTE GÜVENCESİ AÇISINDAN:
-----------------------------------
1. Input validation: Otomatik tip kontrolü ve hata mesajları
2. Response serialization: Type-safe JSON response
3. Documentation: OpenAPI/Swagger için otomatik şema oluşturma
4. Type hints: IDE desteği ve kod okunabilirliği
"""

from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum


# ============================================================================
# Enums
# ============================================================================

class ProblemTypeEnum(str, Enum):
    """Problem tipleri."""
    SLOW_RESPONSE = "slow_response"
    HIGH_ERROR_RATE = "high_error_rate"
    ANOMALY = "anomaly"
    HIGH_LATENCY_VARIANCE = "high_latency_variance"


class SeverityEnum(str, Enum):
    """Önem seviyeleri."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ============================================================================
# Base Schemas
# ============================================================================

class BaseSchema(BaseModel):
    """Tüm şemaların temel sınıfı."""
    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Endpoint Schemas
# ============================================================================

class EndpointResponse(BaseSchema):
    """API Endpoint response şeması."""
    
    id: int = Field(..., description="Endpoint ID")
    path: str = Field(..., description="API path (ör: /api/users)")
    method: str = Field(..., description="HTTP method (GET, POST vb.)")
    description: Optional[str] = Field(None, description="Endpoint açıklaması")
    created_at: datetime = Field(..., description="Kayıt zamanı")


class EndpointListResponse(BaseSchema):
    """Endpoint listesi response şeması."""
    
    total: int = Field(..., description="Toplam endpoint sayısı")
    items: List[EndpointResponse] = Field(..., description="Endpoint listesi")


# ============================================================================
# Metric Schemas
# ============================================================================

class MetricResponse(BaseSchema):
    """Performans metriği response şeması."""
    
    id: int = Field(..., description="Metrik ID")
    endpoint_id: int = Field(..., description="İlişkili endpoint ID")
    response_time_ms: float = Field(..., description="Response süresi (ms)")
    status_code: int = Field(..., description="HTTP status kodu")
    created_at: datetime = Field(..., description="Metrik zamanı")
    
    # İlişkili endpoint bilgileri (opsiyonel)
    endpoint_path: Optional[str] = Field(None, description="Endpoint path")
    endpoint_method: Optional[str] = Field(None, description="Endpoint method")


class MetricListResponse(BaseSchema):
    """Metrik listesi response şeması."""
    
    total: int = Field(..., description="Dönen kayıt sayısı")
    items: List[MetricResponse] = Field(..., description="Metrik listesi")


class SlowEndpointResponse(BaseSchema):
    """Yavaş endpoint response şeması."""
    
    endpoint_id: int = Field(..., description="Endpoint ID")
    path: str = Field(..., description="Endpoint path")
    method: str = Field(..., description="HTTP method")
    response_time_ms: float = Field(..., description="Response süresi (ms)")
    status_code: int = Field(..., description="HTTP status kodu")
    recorded_at: datetime = Field(..., description="Kayıt zamanı")


class SlowEndpointListResponse(BaseSchema):
    """Yavaş endpoint listesi response şeması."""
    
    threshold_ms: float = Field(..., description="Yavaş kabul edilen eşik (ms)")
    total: int = Field(..., description="Dönen kayıt sayısı")
    items: List[SlowEndpointResponse] = Field(..., description="Yavaş endpoint listesi")


# ============================================================================
# Suggestion Schemas
# ============================================================================

class SuggestionResponse(BaseSchema):
    """Optimizasyon önerisi response şeması."""
    
    id: int = Field(..., description="Öneri ID")
    endpoint_id: int = Field(..., description="İlişkili endpoint ID")
    problem_type: ProblemTypeEnum = Field(..., description="Problem tipi")
    suggestion: str = Field(..., description="Optimizasyon önerisi")
    severity: SeverityEnum = Field(..., description="Önem seviyesi")
    avg_response_time_ms: Optional[float] = Field(None, description="Ortalama response süresi")
    error_rate_percent: Optional[float] = Field(None, description="Hata oranı (%)")
    created_at: datetime = Field(..., description="Öneri oluşturma zamanı")
    
    # İlişkili endpoint bilgileri
    endpoint_path: Optional[str] = Field(None, description="Endpoint path")
    endpoint_method: Optional[str] = Field(None, description="Endpoint method")


class SuggestionListResponse(BaseSchema):
    """Öneri listesi response şeması."""
    
    total: int = Field(..., description="Dönen kayıt sayısı")
    items: List[SuggestionResponse] = Field(..., description="Öneri listesi")


# ============================================================================
# Statistics Schemas
# ============================================================================

class EndpointStatsResponse(BaseSchema):
    """Endpoint istatistikleri response şeması."""
    
    endpoint_id: int = Field(..., description="Endpoint ID")
    path: str = Field(..., description="Endpoint path")
    method: str = Field(..., description="HTTP method")
    request_count: int = Field(..., description="Toplam request sayısı")
    avg_response_time_ms: float = Field(..., description="Ortalama response süresi")
    max_response_time_ms: float = Field(..., description="Maksimum response süresi")


class AnalysisResultResponse(BaseSchema):
    """Analiz sonucu response şeması."""
    
    analyzed_endpoints: int = Field(..., description="Analiz edilen endpoint sayısı")
    total_suggestions: int = Field(..., description="Üretilen öneri sayısı")
    analysis_period_hours: int = Field(..., description="Analiz periyodu (saat)")


# ============================================================================
# Error Schemas
# ============================================================================

class ErrorDetail(BaseSchema):
    """Hata detay şeması."""
    
    code: str = Field(..., description="Hata kodu")
    message: str = Field(..., description="Hata mesajı")
    details: Optional[dict] = Field(None, description="Ek detaylar")


class ErrorResponse(BaseSchema):
    """Hata response şeması."""
    
    error: ErrorDetail = Field(..., description="Hata bilgileri")
