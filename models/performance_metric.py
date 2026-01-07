"""
PerformanceMetric Model
=======================

Her HTTP request için toplanan performans metriklerini saklar.

TABLO YAPISI:
-------------
- id: Primary key
- endpoint_id: Foreign key (ApiEndpoint tablosuna)
- response_time_ms: Response süresi (milisaniye)
- status_code: HTTP status kodu
- created_at: Metrik toplama zamanı

INDEX'LER:
----------
- endpoint_id: FK index (join performansı)
- created_at: Zaman bazlı sorgular için
- (endpoint_id, created_at): Endpoint bazlı zaman serisi sorguları
- response_time_ms: Yavaş sorguları bulmak için

YAZILIM KALİTE GÜVENCESİ NOTU:
------------------------------
Bu tablo, sistemin "kalbi" niteliğindedir. Doğru index'leme:
- Yavaş endpoint tespitini hızlandırır
- Trend analizini mümkün kılar
- Anomali tespitini kolaylaştırır
"""

from sqlalchemy import Integer, Float, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TimestampMixin


class PerformanceMetric(Base, TimestampMixin):
    """
    Performans Metrik modeli.
    
    Her HTTP request için bir kayıt oluşturulur.
    Bu veriler, performans analizi ve optimizasyon önerileri için kullanılır.
    """
    
    __tablename__ = "performance_metrics"
    
    # Primary Key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    
    # Foreign Key: Hangi endpoint'e ait
    endpoint_id: Mapped[int] = mapped_column(
        ForeignKey("api_endpoints.id", ondelete="CASCADE"),
        nullable=False,
        comment="İlişkili endpoint ID"
    )
    
    # Performans metrikleri
    response_time_ms: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="Response süresi (milisaniye)"
    )
    
    status_code: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="HTTP status kodu (200, 404, 500 vb.)"
    )
    
    # İlişki (Relationship)
    endpoint: Mapped["ApiEndpoint"] = relationship(
        "ApiEndpoint",
        back_populates="metrics"
    )
    
    # Index tanımları
    __table_args__ = (
        # FK index: Join performansı için
        Index("ix_performance_metrics_endpoint_id", "endpoint_id"),
        
        # Zaman bazlı sorgular için
        Index("ix_performance_metrics_created_at", "created_at"),
        
        # Endpoint bazlı zaman serisi sorguları için composite index
        Index(
            "ix_performance_metrics_endpoint_time",
            "endpoint_id", "created_at"
        ),
        
        # Yavaş response'ları bulmak için
        Index("ix_performance_metrics_response_time", "response_time_ms"),
        
        # Status code bazlı sorgular (hata oranı hesaplama)
        Index("ix_performance_metrics_status_code", "status_code"),
        
        {"comment": "HTTP request performans metrikleri"}
    )
    
    def __repr__(self) -> str:
        return (
            f"<PerformanceMetric(id={self.id}, endpoint_id={self.endpoint_id}, "
            f"response_time_ms={self.response_time_ms}, status_code={self.status_code})>"
        )
    
    @property
    def is_success(self) -> bool:
        """Status kodu 2xx mi kontrol eder."""
        return 200 <= self.status_code < 300
    
    @property
    def is_client_error(self) -> bool:
        """Status kodu 4xx mi kontrol eder."""
        return 400 <= self.status_code < 500
    
    @property
    def is_server_error(self) -> bool:
        """Status kodu 5xx mi kontrol eder."""
        return 500 <= self.status_code < 600


# Forward reference için import
from models.api_endpoint import ApiEndpoint
