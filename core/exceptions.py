"""
Merkezi Hata Yönetimi Modülü
============================

YAZILIM KALİTE GÜVENCESİ AÇISINDAN ÖNEMİ:
-----------------------------------------
1. Tutarlı hata response formatı - API kullanıcıları için öngörülebilirlik
2. Hata kategorileri ile anlamlı HTTP status kodları
3. Detaylı hata mesajları (development) vs güvenli mesajlar (production)
4. Exception hierarchy ile tip güvenli hata yönetimi

Bu yaklaşım şunları sağlar:
- Debug kolaylığı
- Client tarafında tutarlı hata işleme
- Güvenlik (hassas bilgilerin sızmasını engelleme)
"""

from typing import Any, Dict, Optional


class APIException(Exception):
    """
    Tüm API hatalarının temel sınıfı.
    
    Attributes:
        status_code: HTTP status kodu
        error_code: Uygulama içi hata kodu (ör: "ENDPOINT_NOT_FOUND")
        message: Kullanıcıya gösterilecek mesaj
        details: Ek hata detayları (opsiyonel)
    """
    
    def __init__(
        self,
        status_code: int = 500,
        error_code: str = "INTERNAL_ERROR",
        message: str = "Beklenmeyen bir hata oluştu",
        details: Optional[Dict[str, Any]] = None
    ):
        self.status_code = status_code
        self.error_code = error_code
        self.message = message
        self.details = details or {}
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Hata bilgilerini JSON response için dict formatına çevirir.
        """
        response = {
            "error": {
                "code": self.error_code,
                "message": self.message,
            }
        }
        if self.details:
            response["error"]["details"] = self.details
        return response


# ============================================================================
# 4xx Client Errors
# ============================================================================

class BadRequestException(APIException):
    """400 Bad Request - Geçersiz istek formatı veya parametreleri"""
    
    def __init__(
        self,
        message: str = "Geçersiz istek",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            status_code=400,
            error_code="BAD_REQUEST",
            message=message,
            details=details
        )


class NotFoundException(APIException):
    """404 Not Found - Kaynak bulunamadı"""
    
    def __init__(
        self,
        resource: str = "Kaynak",
        resource_id: Optional[Any] = None
    ):
        message = f"{resource} bulunamadı"
        if resource_id:
            message = f"{resource} bulunamadı: {resource_id}"
        
        super().__init__(
            status_code=404,
            error_code="NOT_FOUND",
            message=message,
            details={"resource": resource, "id": resource_id}
        )


class ValidationException(APIException):
    """422 Unprocessable Entity - Validation hatası"""
    
    def __init__(
        self,
        message: str = "Validation hatası",
        errors: Optional[list] = None
    ):
        super().__init__(
            status_code=422,
            error_code="VALIDATION_ERROR",
            message=message,
            details={"validation_errors": errors or []}
        )


# ============================================================================
# 5xx Server Errors
# ============================================================================

class DatabaseException(APIException):
    """500 Internal Server Error - Veritabanı hatası"""
    
    def __init__(
        self,
        message: str = "Veritabanı hatası",
        original_error: Optional[Exception] = None
    ):
        details = {}
        if original_error:
            # Production'da bu bilgiyi gizle
            details["error_type"] = type(original_error).__name__
        
        super().__init__(
            status_code=500,
            error_code="DATABASE_ERROR",
            message=message,
            details=details
        )


class ServiceException(APIException):
    """500 Internal Server Error - Servis katmanı hatası"""
    
    def __init__(
        self,
        message: str = "Servis hatası",
        service_name: Optional[str] = None
    ):
        super().__init__(
            status_code=500,
            error_code="SERVICE_ERROR",
            message=message,
            details={"service": service_name} if service_name else {}
        )


# ============================================================================
# Performans İzleme Özel Hataları
# ============================================================================

class MetricCollectionException(APIException):
    """Metrik toplama sırasında oluşan hata"""
    
    def __init__(
        self,
        endpoint: str,
        original_error: Optional[Exception] = None
    ):
        super().__init__(
            status_code=500,
            error_code="METRIC_COLLECTION_ERROR",
            message=f"Metrik toplanamadı: {endpoint}",
            details={
                "endpoint": endpoint,
                "error_type": type(original_error).__name__ if original_error else None
            }
        )


class AnalysisException(APIException):
    """Performans analizi sırasında oluşan hata"""
    
    def __init__(
        self,
        message: str = "Analiz hatası",
        analysis_type: Optional[str] = None
    ):
        super().__init__(
            status_code=500,
            error_code="ANALYSIS_ERROR",
            message=message,
            details={"analysis_type": analysis_type} if analysis_type else {}
        )
