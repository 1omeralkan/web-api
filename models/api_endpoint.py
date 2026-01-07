"""
ApiEndpoint Model
=================

İzlenen API endpoint'lerinin bilgilerini saklar.

TABLO YAPISI:
-------------
- id: Primary key
- path: API path (ör: "/users", "/metrics")
- method: HTTP method (GET, POST, PUT, DELETE vb.)
- description: Endpoint açıklaması
- created_at: Kayıt zamanı

INDEX'LER:
----------
- (path, method) üzerinde unique index: Aynı endpoint tekrar eklenmesini engeller
- path üzerinde index: Path bazlı sorgular için performans

FOREIGN KEY İLİŞKİLERİ:
-----------------------
- PerformanceMetric -> ApiEndpoint (one-to-many)
- OptimizationSuggestion -> ApiEndpoint (one-to-many)
"""

from sqlalchemy import String, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List, Optional

from models.base import Base, TimestampMixin


class ApiEndpoint(Base, TimestampMixin):
    """
    API Endpoint modeli.
    
    Her benzersiz (path, method) kombinasyonu için bir kayıt tutulur.
    Bu sayede performans metrikleri endpoint bazında gruplandırılabilir.
    """
    
    __tablename__ = "api_endpoints"
    
    # Primary Key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    
    # Endpoint bilgileri
    path: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="API endpoint path (ör: /api/v1/users)"
    )
    
    method: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        comment="HTTP method (GET, POST, PUT, DELETE vb.)"
    )
    
    description: Mapped[Optional[str]] = mapped_column(
        String(1000),
        nullable=True,
        comment="Endpoint açıklaması"
    )
    
    # İlişkiler (Relationships)
    # --------------------------
    # lazy="selectin": N+1 sorgu problemini önler, tek sorguda yükler
    # cascade="all, delete-orphan": Parent silindiğinde child'lar da silinir
    
    metrics: Mapped[List["PerformanceMetric"]] = relationship(
        "PerformanceMetric",
        back_populates="endpoint",
        lazy="selectin",
        cascade="all, delete-orphan"
    )
    
    suggestions: Mapped[List["OptimizationSuggestion"]] = relationship(
        "OptimizationSuggestion",
        back_populates="endpoint",
        lazy="selectin",
        cascade="all, delete-orphan"
    )
    
    # Index tanımları
    __table_args__ = (
        # Unique constraint: Aynı path+method kombinasyonu tekrar eklenemez
        Index(
            "ix_api_endpoints_path_method",
            "path", "method",
            unique=True
        ),
        # Path üzerinde index: Filtreleme performansı için
        Index("ix_api_endpoints_path", "path"),
        
        {"comment": "İzlenen API endpoint'leri"}
    )
    
    def __repr__(self) -> str:
        return f"<ApiEndpoint(id={self.id}, method={self.method}, path={self.path})>"


# Circular import çözümü için forward reference
from models.performance_metric import PerformanceMetric
from models.optimization_suggestion import OptimizationSuggestion
