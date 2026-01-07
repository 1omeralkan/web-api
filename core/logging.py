"""
Logging Modülü
==============

YAZILIM KALİTE GÜVENCESİ AÇISINDAN ÖNEMİ:
-----------------------------------------
1. Structured logging (JSON format) - log analizi ve monitoring için
2. Merkezi log konfigürasyonu - tutarlı log formatı
3. Performans metrikleri için özel logger
4. Context bilgisi (request_id, endpoint vb.) ekleme imkanı

PERFORMANS LOGGING:
-------------------
- Response süreleri
- Slow query uyarıları
- Error rate tracking
- Anormal davranış tespiti
"""

import logging
import sys
from datetime import datetime
from typing import Any, Dict, Optional
from pythonjsonlogger import jsonlogger

from core.config import get_settings

settings = get_settings()


class PerformanceLogFormatter(jsonlogger.JsonFormatter):
    """
    Performans odaklı JSON log formatter.
    
    Her log kaydına otomatik olarak eklenen alanlar:
    - timestamp: ISO format zaman damgası
    - level: Log seviyesi (INFO, WARNING, ERROR vb.)
    - service: Servis adı (monitoring için)
    """
    
    def add_fields(
        self,
        log_record: Dict[str, Any],
        record: logging.LogRecord,
        message_dict: Dict[str, Any]
    ) -> None:
        super().add_fields(log_record, record, message_dict)
        
        # Standart alanlar
        log_record["timestamp"] = datetime.utcnow().isoformat()
        log_record["level"] = record.levelname
        log_record["service"] = "api-performance-monitor"
        log_record["module"] = record.module
        
        # Performans metrikleri için özel alanlar
        if hasattr(record, "response_time_ms"):
            log_record["response_time_ms"] = record.response_time_ms
        if hasattr(record, "endpoint"):
            log_record["endpoint"] = record.endpoint
        if hasattr(record, "method"):
            log_record["method"] = record.method
        if hasattr(record, "status_code"):
            log_record["status_code"] = record.status_code


def setup_logging() -> None:
    """
    Uygulama genelinde logging konfigürasyonunu ayarlar.
    """
    # Root logger konfigürasyonu
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL))
    
    # Mevcut handler'ları temizle
    root_logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    
    if settings.LOG_FORMAT == "json":
        formatter = PerformanceLogFormatter(
            "%(timestamp)s %(level)s %(message)s"
        )
    else:
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
    
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Üçüncü parti kütüphanelerin log seviyesini ayarla
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    İsimlendirilmiş logger döndürür.
    
    Kullanım:
    ---------
    logger = get_logger(__name__)
    logger.info("İşlem başladı", extra={"endpoint": "/metrics"})
    """
    return logging.getLogger(name)


class PerformanceLogger:
    """
    Performans metriklerini loglamak için özel sınıf.
    
    Bu sınıf, response süreleri ve hata oranlarını
    yapılandırılmış formatta loglar.
    """
    
    def __init__(self):
        self.logger = get_logger("performance")
    
    def log_request(
        self,
        endpoint: str,
        method: str,
        status_code: int,
        response_time_ms: float
    ) -> None:
        """
        HTTP request performans metriklerini loglar.
        """
        extra = {
            "endpoint": endpoint,
            "method": method,
            "status_code": status_code,
            "response_time_ms": round(response_time_ms, 2),
        }
        
        # Yavaş response için uyarı
        if response_time_ms > settings.SLOW_RESPONSE_THRESHOLD_MS:
            self.logger.warning(
                f"Yavaş response tespit edildi: {endpoint}",
                extra=extra
            )
        else:
            self.logger.info(
                f"Request tamamlandı: {endpoint}",
                extra=extra
            )
    
    def log_error(
        self,
        endpoint: str,
        method: str,
        error: Exception,
        response_time_ms: Optional[float] = None
    ) -> None:
        """
        Hata durumlarını loglar.
        """
        extra = {
            "endpoint": endpoint,
            "method": method,
            "error_type": type(error).__name__,
            "error_message": str(error),
        }
        if response_time_ms:
            extra["response_time_ms"] = round(response_time_ms, 2)
        
        self.logger.error(
            f"Request hatası: {endpoint}",
            extra=extra,
            exc_info=True
        )


# Singleton performance logger instance
performance_logger = PerformanceLogger()
