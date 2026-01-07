"""
Metric Repository
=================

PerformanceMetric tablosu için veri erişim katmanı.

YAZILIM KALİTE GÜVENCESİ AÇISINDAN:
-----------------------------------
1. Bulk insert desteği: Yüksek trafik durumunda performans
2. Aggregate queries: İstatistik hesaplamaları veritabanında yapılır
3. Parameterized queries: SQL injection koruması
4. Async write: API response'u engellemeyen metrik yazımı

SORGULAR:
---------
- create: Yeni metrik ekle
- get_all: Tüm metrikleri getir
- get_slow_metrics: Threshold üzerindeki metrikleri getir
- get_stats_by_endpoint: Endpoint bazlı istatistikler
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy import select, func, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.performance_metric import PerformanceMetric
from models.api_endpoint import ApiEndpoint
from core.config import get_settings
from core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class MetricRepository:
    """
    PerformanceMetric tablosu için repository sınıfı.
    """
    
    async def create(
        self,
        session: AsyncSession,
        endpoint_id: int,
        response_time_ms: float,
        status_code: int
    ) -> PerformanceMetric:
        """
        Yeni performans metriği oluşturur.
        
        Bu metod, middleware tarafından her request sonunda çağrılır.
        Minimal overhead için sadece gerekli alanlar yazılır.
        
        Args:
            session: Async database session
            endpoint_id: İlişkili endpoint ID
            response_time_ms: Response süresi (ms)
            status_code: HTTP status kodu
            
        Returns:
            PerformanceMetric: Oluşturulan metrik
        """
        metric = PerformanceMetric(
            endpoint_id=endpoint_id,
            response_time_ms=response_time_ms,
            status_code=status_code
        )
        session.add(metric)
        await session.flush()
        
        logger.debug(
            f"Metrik kaydedildi: endpoint_id={endpoint_id}, "
            f"time={response_time_ms}ms, status={status_code}"
        )
        return metric
    
    async def get_all(
        self,
        session: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        endpoint_id: Optional[int] = None,
        since: Optional[datetime] = None
    ) -> List[PerformanceMetric]:
        """
        Metrikleri listeler.
        
        Filtreleme seçenekleri:
        - endpoint_id: Belirli bir endpoint için
        - since: Belirli bir tarihten sonrası
        
        Args:
            session: Async database session
            skip: Offset
            limit: Maksimum kayıt sayısı
            endpoint_id: Opsiyonel endpoint filtresi
            since: Opsiyonel zaman filtresi
            
        Returns:
            List[PerformanceMetric]: Metrik listesi
        """
        query = select(PerformanceMetric).options(selectinload(PerformanceMetric.endpoint))
        
        conditions = []
        if endpoint_id:
            conditions.append(PerformanceMetric.endpoint_id == endpoint_id)
        if since:
            conditions.append(PerformanceMetric.created_at >= since)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        query = query.order_by(desc(PerformanceMetric.created_at)).offset(skip).limit(limit)
        
        result = await session.execute(query)
        return list(result.scalars().all())
    
    async def get_slow_metrics(
        self,
        session: AsyncSession,
        threshold_ms: Optional[float] = None,
        limit: int = 50
    ) -> List[PerformanceMetric]:
        """
        Threshold üzerindeki yavaş metrikleri getirir.
        
        Bu metod, performance dashboard'da kullanılır.
        
        Args:
            session: Async database session
            threshold_ms: Yavaş kabul edilecek threshold (varsayılan: config'den)
            limit: Maksimum kayıt sayısı
            
        Returns:
            List[PerformanceMetric]: Yavaş metrikler
        """
        threshold = threshold_ms or settings.SLOW_RESPONSE_THRESHOLD_MS
        
        result = await session.execute(
            select(PerformanceMetric)
            .options(selectinload(PerformanceMetric.endpoint))
            .where(PerformanceMetric.response_time_ms > threshold)
            .order_by(desc(PerformanceMetric.response_time_ms))
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def get_stats_by_endpoint(
        self,
        session: AsyncSession,
        endpoint_id: int,
        since: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Endpoint bazlı istatistikleri hesaplar.
        
        Hesaplanan metrikler:
        - count: Toplam request sayısı
        - avg_response_time: Ortalama response süresi
        - min_response_time: Minimum response süresi
        - max_response_time: Maximum response süresi
        - error_count: 5xx hata sayısı
        - error_rate: Hata oranı (%)
        
        Args:
            session: Async database session
            endpoint_id: Endpoint ID
            since: Opsiyonel zaman filtresi
            
        Returns:
            Dict: İstatistik dictionary'si
        """
        # Temel filtre
        conditions = [PerformanceMetric.endpoint_id == endpoint_id]
        if since:
            conditions.append(PerformanceMetric.created_at >= since)
        
        # Ana istatistikler
        result = await session.execute(
            select(
                func.count(PerformanceMetric.id).label("count"),
                func.avg(PerformanceMetric.response_time_ms).label("avg_response_time"),
                func.min(PerformanceMetric.response_time_ms).label("min_response_time"),
                func.max(PerformanceMetric.response_time_ms).label("max_response_time"),
                func.stddev(PerformanceMetric.response_time_ms).label("stddev_response_time"),
            ).where(and_(*conditions))
        )
        row = result.one()
        
        # Hata sayısı (5xx)
        error_result = await session.execute(
            select(func.count(PerformanceMetric.id)).where(
                and_(
                    *conditions,
                    PerformanceMetric.status_code >= 500
                )
            )
        )
        error_count = error_result.scalar_one()
        
        count = row.count or 0
        error_rate = (error_count / count * 100) if count > 0 else 0.0
        
        return {
            "endpoint_id": endpoint_id,
            "count": count,
            "avg_response_time_ms": round(row.avg_response_time or 0, 2),
            "min_response_time_ms": round(row.min_response_time or 0, 2),
            "max_response_time_ms": round(row.max_response_time or 0, 2),
            "stddev_response_time_ms": round(row.stddev_response_time or 0, 2),
            "error_count": error_count,
            "error_rate_percent": round(error_rate, 2),
        }
    
    async def get_all_endpoint_stats(
        self,
        session: AsyncSession,
        since: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Tüm endpoint'ler için istatistikleri hesaplar.
        """
        # Zaman filtresi
        time_filter = []
        if since:
            time_filter.append(PerformanceMetric.created_at >= since)
        
        # GROUP BY ile aggregate
        query = select(
            ApiEndpoint.id,
            ApiEndpoint.path,
            ApiEndpoint.method,
            func.count(PerformanceMetric.id).label("request_count"),
            func.avg(PerformanceMetric.response_time_ms).label("avg_response_time"),
            func.max(PerformanceMetric.response_time_ms).label("max_response_time"),
        ).join(
            PerformanceMetric, ApiEndpoint.id == PerformanceMetric.endpoint_id
        )
        
        if time_filter:
            query = query.where(and_(*time_filter))
        
        query = query.group_by(
            ApiEndpoint.id, ApiEndpoint.path, ApiEndpoint.method
        ).order_by(desc("avg_response_time"))
        
        result = await session.execute(query)
        
        return [
            {
                "endpoint_id": row.id,
                "path": row.path,
                "method": row.method,
                "request_count": row.request_count,
                "avg_response_time_ms": round(row.avg_response_time or 0, 2),
                "max_response_time_ms": round(row.max_response_time or 0, 2),
            }
            for row in result.all()
        ]


# Singleton instance
metric_repository = MetricRepository()
