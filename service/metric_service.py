"""
Metric Service
==============

PerformanceMetric için iş mantığı katmanı.

YAZILIM KALİTE GÜVENCESİ AÇISINDAN:
-----------------------------------
1. Metrik kaydetme: Minimal overhead ile async yazım
2. Yavaş endpoint tespiti: Configurable threshold
3. İstatistik agregasyonu: Performans dashboard için
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from repository.metric_repository import metric_repository
from models.performance_metric import PerformanceMetric
from core.config import get_settings
from core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class MetricService:
    """
    PerformanceMetric iş mantığı servisi.
    """
    
    async def record_metric(
        self,
        session: AsyncSession,
        endpoint_id: int,
        response_time_ms: float,
        status_code: int
    ) -> PerformanceMetric:
        """
        Yeni performans metriği kaydeder.
        
        Middleware tarafından her request sonunda çağrılır.
        
        Args:
            session: Async database session
            endpoint_id: İlişkili endpoint ID
            response_time_ms: Response süresi (ms)
            status_code: HTTP status kodu
            
        Returns:
            PerformanceMetric: Oluşturulan metrik
        """
        return await metric_repository.create(
            session=session,
            endpoint_id=endpoint_id,
            response_time_ms=response_time_ms,
            status_code=status_code
        )
    
    async def list_metrics(
        self,
        session: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        endpoint_id: Optional[int] = None,
        hours_ago: Optional[int] = None
    ) -> List[PerformanceMetric]:
        """
        Metrikleri listeler.
        
        Args:
            session: Async database session
            skip: Offset
            limit: Maksimum kayıt sayısı
            endpoint_id: Opsiyonel endpoint filtresi
            hours_ago: Son X saat içindeki metrikler
            
        Returns:
            List[PerformanceMetric]: Metrik listesi
        """
        since = None
        if hours_ago:
            since = datetime.utcnow() - timedelta(hours=hours_ago)
        
        return await metric_repository.get_all(
            session=session,
            skip=skip,
            limit=limit,
            endpoint_id=endpoint_id,
            since=since
        )
    
    async def get_slow_endpoints(
        self,
        session: AsyncSession,
        threshold_ms: Optional[float] = None,
        limit: int = 50
    ) -> List[PerformanceMetric]:
        """
        Yavaş çalışan endpoint metriklerini getirir.
        
        Threshold değeri config'den alınır veya parametre ile override edilebilir.
        
        Args:
            session: Async database session
            threshold_ms: Yavaş kabul edilecek eşik değeri (ms)
            limit: Maksimum kayıt sayısı
            
        Returns:
            List[PerformanceMetric]: Yavaş metrikler
        """
        return await metric_repository.get_slow_metrics(
            session=session,
            threshold_ms=threshold_ms or settings.SLOW_RESPONSE_THRESHOLD_MS,
            limit=limit
        )
    
    async def get_endpoint_statistics(
        self,
        session: AsyncSession,
        endpoint_id: int,
        hours_ago: Optional[int] = 24
    ) -> Dict[str, Any]:
        """
        Endpoint bazlı istatistikleri hesaplar.
        
        Hesaplanan metrikler:
        - Toplam request sayısı
        - Ortalama/min/max response süresi
        - Hata oranı
        - Standart sapma
        
        Args:
            session: Async database session
            endpoint_id: Endpoint ID
            hours_ago: Son X saat (varsayılan: 24)
            
        Returns:
            Dict: İstatistik verileri
        """
        since = None
        if hours_ago:
            since = datetime.utcnow() - timedelta(hours=hours_ago)
        
        return await metric_repository.get_stats_by_endpoint(
            session=session,
            endpoint_id=endpoint_id,
            since=since
        )
    
    async def get_all_endpoint_statistics(
        self,
        session: AsyncSession,
        hours_ago: Optional[int] = 24
    ) -> List[Dict[str, Any]]:
        """
        Tüm endpoint'ler için istatistikleri getirir.
        """
        since = None
        if hours_ago:
            since = datetime.utcnow() - timedelta(hours=hours_ago)
        
        return await metric_repository.get_all_endpoint_stats(
            session=session,
            since=since
        )


# Singleton instance
metric_service = MetricService()
