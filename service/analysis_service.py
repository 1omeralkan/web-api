"""
Analysis Service - Performans Analizi ve Optimizasyon Önerileri
===============================================================

Bu modül, toplanan performans verilerini analiz ederek
otomatik optimizasyon önerileri üretir.

YAZILIM KALİTE GÜVENCESİ AÇISINDAN:
-----------------------------------
1. Kural tabanlı analiz: Şeffaf ve açıklanabilir öneriler
2. Genişletilebilir mimari: Yeni kurallar kolayca eklenebilir
3. Threshold-based detection: Config ile ayarlanabilir eşikler
4. Merkezi analiz: Tüm analizler tek noktadan yönetilir

ÜRETİLEN ÖNERİ TİPLERİ:
-----------------------
1. Cache kullanımı önerisi (ortalama response > 500ms)
2. Veritabanı index ekleme önerisi (yavaş sorgular)
3. Sorgu optimizasyonu (5xx hata oranı > %10)
4. Asenkron işlem kullanımı (yüksek latency variance)

MİMARİ:
-------
AnalysisService
├── analyze_endpoint(): Tek endpoint analizi
├── analyze_all_endpoints(): Tüm endpoint'leri analiz et
└── _generate_suggestions(): Kural tabanlı öneri üretimi
    ├── _check_slow_response()
    ├── _check_high_error_rate()
    └── _check_latency_variance()
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from repository.metric_repository import metric_repository
from repository.suggestion_repository import suggestion_repository
from repository.endpoint_repository import endpoint_repository
from models.optimization_suggestion import OptimizationSuggestion, ProblemType, Severity
from core.config import get_settings
from core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class AnalysisRule:
    """
    Analiz kuralı base class.
    
    Yeni kurallar bu class'ı extend ederek eklenebilir.
    Strategy pattern ile genişletilebilirlik sağlanır.
    """
    
    def check(self, stats: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        İstatistikleri kontrol eder ve öneri üretir.
        
        Args:
            stats: Endpoint istatistikleri
            
        Returns:
            Optional[Dict]: Öneri detayları veya None
        """
        raise NotImplementedError


class SlowResponseRule(AnalysisRule):
    """
    Yavaş response tespiti kuralı.
    
    Eğer ortalama response süresi threshold'u aşıyorsa,
    cache kullanımı veya sorgu optimizasyonu önerilir.
    """
    
    def check(self, stats: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        avg_time = stats.get("avg_response_time_ms", 0)
        max_time = stats.get("max_response_time_ms", 0)
        
        if avg_time > settings.SLOW_RESPONSE_THRESHOLD_MS:
            # Severity hesapla
            if avg_time > settings.SLOW_RESPONSE_THRESHOLD_MS * 4:
                severity = Severity.CRITICAL
            elif avg_time > settings.SLOW_RESPONSE_THRESHOLD_MS * 2:
                severity = Severity.HIGH
            else:
                severity = Severity.MEDIUM
            
            # Öneri metni oluştur
            suggestion = self._generate_suggestion(avg_time, max_time)
            
            return {
                "problem_type": ProblemType.SLOW_RESPONSE,
                "suggestion": suggestion,
                "severity": severity,
                "avg_response_time_ms": avg_time,
            }
        return None
    
    def _generate_suggestion(self, avg_time: float, max_time: float) -> str:
        """Duruma göre özelleştirilmiş öneri metni üretir."""
        suggestions = []
        
        # Temel öneri
        suggestions.append(
            f"📊 Ortalama response süresi {avg_time:.0f}ms ile yüksek "
            f"(Eşik: {settings.SLOW_RESPONSE_THRESHOLD_MS}ms)."
        )
        
        # Cache önerisi
        suggestions.append(
            "💡 **Cache Kullanımı**: Sık değişmeyen veriler için Redis veya "
            "in-memory cache kullanarak response süresi düşürülebilir."
        )
        
        # Veritabanı index önerisi
        if avg_time > 1000:
            suggestions.append(
                "💡 **Veritabanı İndeksi**: WHERE, JOIN ve ORDER BY "
                "sorgularında kullanılan alanlar için index eklenmeli."
            )
        
        # Query optimizasyonu
        if max_time > 2000:
            suggestions.append(
                "💡 **Sorgu Optimizasyonu**: N+1 query problemi kontrol edilmeli, "
                "gerekirse eager loading kullanılmalı."
            )
        
        return "\n".join(suggestions)


class HighErrorRateRule(AnalysisRule):
    """
    Yüksek hata oranı tespiti kuralı.
    
    5xx hata oranı threshold'u aşıyorsa uyarı verilir.
    """
    
    def check(self, stats: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        error_rate = stats.get("error_rate_percent", 0)
        error_count = stats.get("error_count", 0)
        
        if error_rate > settings.ERROR_RATE_THRESHOLD_PERCENT:
            # Severity hesapla
            if error_rate > 50:
                severity = Severity.CRITICAL
            elif error_rate > 25:
                severity = Severity.HIGH
            else:
                severity = Severity.MEDIUM
            
            suggestion = self._generate_suggestion(error_rate, error_count)
            
            return {
                "problem_type": ProblemType.HIGH_ERROR_RATE,
                "suggestion": suggestion,
                "severity": severity,
                "error_rate_percent": error_rate,
            }
        return None
    
    def _generate_suggestion(self, error_rate: float, error_count: int) -> str:
        """Hata oranına göre öneri üretir."""
        suggestions = [
            f"⚠️ Hata oranı %{error_rate:.1f} ile yüksek "
            f"(Toplam {error_count} hata, Eşik: %{settings.ERROR_RATE_THRESHOLD_PERCENT})."
        ]
        
        suggestions.append(
            "💡 **Hata Analizi**: Logları inceleyerek yaygın hata nedenlerini belirleyin."
        )
        
        suggestions.append(
            "💡 **Timeout Kontrolü**: Veritabanı ve external API timeout değerlerini kontrol edin."
        )
        
        if error_rate > 30:
            suggestions.append(
                "💡 **Circuit Breaker**: Yüksek hata oranı için circuit breaker pattern uygulanabilir."
            )
        
        return "\n".join(suggestions)


class LatencyVarianceRule(AnalysisRule):
    """
    Yüksek latency varyansı tespiti kuralı.
    
    Response sürelerinde yüksek varyans, tutarsız performans göstergesidir.
    """
    
    def check(self, stats: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        avg_time = stats.get("avg_response_time_ms", 0)
        stddev = stats.get("stddev_response_time_ms", 0)
        
        # Coefficient of variation kontrolü
        if avg_time > 0 and stddev > avg_time * settings.ANOMALY_STDDEV_MULTIPLIER:
            severity = Severity.MEDIUM
            
            suggestion = self._generate_suggestion(avg_time, stddev)
            
            return {
                "problem_type": ProblemType.HIGH_LATENCY_VARIANCE,
                "suggestion": suggestion,
                "severity": severity,
                "avg_response_time_ms": avg_time,
            }
        return None
    
    def _generate_suggestion(self, avg_time: float, stddev: float) -> str:
        """Latency varyansı için öneri üretir."""
        cv = (stddev / avg_time * 100) if avg_time > 0 else 0
        
        suggestions = [
            f"📈 Response süresinde yüksek varyans tespit edildi "
            f"(Ortalama: {avg_time:.0f}ms, Std Sapma: {stddev:.0f}ms, CV: %{cv:.0f})."
        ]
        
        suggestions.append(
            "💡 **Asenkron İşlem**: Uzun süren işlemleri background task'a taşıyın."
        )
        
        suggestions.append(
            "💡 **Connection Pool**: Veritabanı connection pool boyutunu optimize edin."
        )
        
        suggestions.append(
            "💡 **Kaynak Kullanımı**: CPU/Memory spike'larını monitoring ile takip edin."
        )
        
        return "\n".join(suggestions)


class AnalysisService:
    """
    Performans analizi ve optimizasyon önerisi servisi.
    
    Bu servis, toplanan metrikleri analiz ederek
    kural tabanlı optimizasyon önerileri üretir.
    """
    
    def __init__(self):
        # Analiz kuralları - yeni kurallar buraya eklenir
        self.rules: List[AnalysisRule] = [
            SlowResponseRule(),
            HighErrorRateRule(),
            LatencyVarianceRule(),
        ]
    
    async def analyze_endpoint(
        self,
        session: AsyncSession,
        endpoint_id: int,
        hours_ago: int = 24
    ) -> List[OptimizationSuggestion]:
        """
        Tek bir endpoint için performans analizi yapar.
        
        Args:
            session: Async database session
            endpoint_id: Analiz edilecek endpoint ID
            hours_ago: Son kaç saat analiz edilecek
            
        Returns:
            List[OptimizationSuggestion]: Üretilen öneriler
        """
        since = datetime.utcnow() - timedelta(hours=hours_ago)
        
        # İstatistikleri getir
        stats = await metric_repository.get_stats_by_endpoint(
            session=session,
            endpoint_id=endpoint_id,
            since=since
        )
        
        # Yeterli veri yoksa analiz yapma
        if stats.get("count", 0) < 5:
            logger.debug(f"Endpoint {endpoint_id} için yeterli veri yok")
            return []
        
        # Kuralları çalıştır ve önerileri topla
        suggestions = []
        for rule in self.rules:
            result = rule.check(stats)
            if result:
                suggestion = await suggestion_repository.create_or_update(
                    session=session,
                    endpoint_id=endpoint_id,
                    problem_type=result["problem_type"],
                    suggestion=result["suggestion"],
                    severity=result["severity"],
                    avg_response_time_ms=result.get("avg_response_time_ms"),
                    error_rate_percent=result.get("error_rate_percent"),
                )
                suggestions.append(suggestion)
                
                logger.info(
                    f"Öneri üretildi: endpoint_id={endpoint_id}, "
                    f"type={result['problem_type'].value}, "
                    f"severity={result['severity'].value}"
                )
        
        return suggestions
    
    async def analyze_all_endpoints(
        self,
        session: AsyncSession,
        hours_ago: int = 24
    ) -> Dict[str, Any]:
        """
        Tüm endpoint'leri analiz eder.
        
        Args:
            session: Async database session
            hours_ago: Son kaç saat analiz edilecek
            
        Returns:
            Dict: Analiz sonuç özeti
        """
        endpoints = await endpoint_repository.get_all(session)
        
        total_suggestions = 0
        analyzed_count = 0
        
        for endpoint in endpoints:
            suggestions = await self.analyze_endpoint(
                session=session,
                endpoint_id=endpoint.id,
                hours_ago=hours_ago
            )
            total_suggestions += len(suggestions)
            analyzed_count += 1
        
        logger.info(
            f"Toplu analiz tamamlandı: {analyzed_count} endpoint, "
            f"{total_suggestions} öneri üretildi"
        )
        
        return {
            "analyzed_endpoints": analyzed_count,
            "total_suggestions": total_suggestions,
            "analysis_period_hours": hours_ago,
        }
    
    async def get_suggestions(
        self,
        session: AsyncSession,
        severity: Optional[Severity] = None,
        problem_type: Optional[ProblemType] = None,
        limit: int = 100
    ) -> List[OptimizationSuggestion]:
        """
        Önerileri listeler.
        
        Args:
            session: Async database session
            severity: Opsiyonel severity filtresi
            problem_type: Opsiyonel problem type filtresi
            limit: Maksimum kayıt sayısı
            
        Returns:
            List[OptimizationSuggestion]: Öneri listesi
        """
        return await suggestion_repository.get_all(
            session=session,
            severity=severity,
            problem_type=problem_type,
            limit=limit
        )


# Singleton instance
analysis_service = AnalysisService()
