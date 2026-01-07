"""
OptimizationSuggestion Model
============================

Performans analizi sonucu üretilen optimizasyon önerilerini saklar.

TABLO YAPISI:
-------------
- id: Primary key
- endpoint_id: Foreign key (ApiEndpoint tablosuna)
- problem_type: Problem tipi (enum)
- suggestion: Optimizasyon önerisi metni
- severity: Önem seviyesi (enum)
- created_at: Öneri oluşturma zamanı

ENUM TİPLERİ:
-------------
ProblemType:
- SLOW_RESPONSE: Yavaş response süresi
- HIGH_ERROR_RATE: Yüksek hata oranı (5xx)
- ANOMALY: Anormal performans davranışı
- HIGH_LATENCY_VARIANCE: Response süresinde yüksek varyans

Severity:
- LOW: Düşük öncelik
- MEDIUM: Orta öncelik
- HIGH: Yüksek öncelik
- CRITICAL: Kritik - acil müdahale gerekli
"""

import enum
from sqlalchemy import String, Enum, ForeignKey, Index, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TimestampMixin


class ProblemType(str, enum.Enum):
    """
    Tespit edilen problem tipleri.
    
    str'den miras alması, JSON serialization'ı kolaylaştırır.
    """
    SLOW_RESPONSE = "slow_response"
    HIGH_ERROR_RATE = "high_error_rate"
    ANOMALY = "anomaly"
    HIGH_LATENCY_VARIANCE = "high_latency_variance"
    
    @property
    def description(self) -> str:
        """Problem tipinin Türkçe açıklaması."""
        descriptions = {
            ProblemType.SLOW_RESPONSE: "Yavaş response süresi",
            ProblemType.HIGH_ERROR_RATE: "Yüksek hata oranı",
            ProblemType.ANOMALY: "Anormal davranış",
            ProblemType.HIGH_LATENCY_VARIANCE: "Yüksek gecikme varyansı",
        }
        return descriptions.get(self, "Bilinmeyen problem")


class Severity(str, enum.Enum):
    """
    Önem seviyeleri.
    
    Endpoint'lerin önceliklendirilmesinde kullanılır.
    """
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    
    @property
    def priority_order(self) -> int:
        """Sıralama için öncelik değeri (yüksek = daha öncelikli)."""
        orders = {
            Severity.LOW: 1,
            Severity.MEDIUM: 2,
            Severity.HIGH: 3,
            Severity.CRITICAL: 4,
        }
        return orders.get(self, 0)


class OptimizationSuggestion(Base, TimestampMixin):
    """
    Optimizasyon Önerisi modeli.
    
    Performans analizi sonucunda üretilen öneriler burada saklanır.
    Her öneri, belirli bir endpoint için ve belirli bir problem tipine yöneliktir.
    """
    
    __tablename__ = "optimization_suggestions"
    
    # Primary Key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    
    # Foreign Key: Hangi endpoint için
    endpoint_id: Mapped[int] = mapped_column(
        ForeignKey("api_endpoints.id", ondelete="CASCADE"),
        nullable=False,
        comment="İlişkili endpoint ID"
    )
    
    # Problem bilgileri
    problem_type: Mapped[ProblemType] = mapped_column(
        Enum(ProblemType),
        nullable=False,
        comment="Tespit edilen problem tipi"
    )
    
    suggestion: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Optimizasyon önerisi metni"
    )
    
    severity: Mapped[Severity] = mapped_column(
        Enum(Severity),
        nullable=False,
        default=Severity.MEDIUM,
        comment="Önem seviyesi"
    )
    
    # Ek metrikler (analiz sonuçları)
    avg_response_time_ms: Mapped[float] = mapped_column(
        nullable=True,
        comment="Ortalama response süresi (ms)"
    )
    
    error_rate_percent: Mapped[float] = mapped_column(
        nullable=True,
        comment="Hata oranı (%)"
    )
    
    # İlişki (Relationship)
    endpoint: Mapped["ApiEndpoint"] = relationship(
        "ApiEndpoint",
        back_populates="suggestions"
    )
    
    # Index tanımları
    __table_args__ = (
        # FK index
        Index("ix_optimization_suggestions_endpoint_id", "endpoint_id"),
        
        # Severity bazlı sorgular (kritik önerileri bul)
        Index("ix_optimization_suggestions_severity", "severity"),
        
        # Problem tipi bazlı sorgular
        Index("ix_optimization_suggestions_problem_type", "problem_type"),
        
        {"comment": "Optimizasyon önerileri"}
    )
    
    def __repr__(self) -> str:
        return (
            f"<OptimizationSuggestion(id={self.id}, endpoint_id={self.endpoint_id}, "
            f"problem_type={self.problem_type.value}, severity={self.severity.value})>"
        )


# Forward reference için import
from models.api_endpoint import ApiEndpoint
