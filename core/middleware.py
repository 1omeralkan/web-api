"""
Performance Monitoring Middleware
=================================

Her HTTP request'i otomatik olarak izleyen ve performans metriklerini
toplayan FastAPI middleware.

YAZILIM KALİTE GÜVENCESİ AÇISINDAN:
-----------------------------------
1. Non-intrusive monitoring: Uygulama koduna müdahale etmeden izleme
2. Minimal overhead: Async write ile API performansını minimum etkiler
3. Automatic endpoint discovery: Yeni endpoint'ler otomatik kaydedilir
4. Comprehensive metrics: Response time, status code, path, method

TOPLANAN METRİKLER:
-------------------
- Endpoint path ve HTTP method
- Response süresi (milisaniye)
- HTTP status code
- Timestamp

MİMARİ KARAR:
-------------
Middleware, request başlangıcında zaman alır ve response sonunda
hesaplama yaparak veritabanına async yazar. Write işlemi, API
response'unu bekletmemek için background'da yapılır.
"""

import time
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from core.database import async_session_factory
from core.logging import performance_logger, get_logger
from repository.endpoint_repository import endpoint_repository
from repository.metric_repository import metric_repository

logger = get_logger(__name__)

# İzleme dışında bırakılacak path'ler
EXCLUDED_PATHS = {
    "/docs",
    "/redoc",
    "/openapi.json",
    "/favicon.ico",
    "/health",
}


class PerformanceMonitoringMiddleware(BaseHTTPMiddleware):
    """
    Performans izleme middleware'i.
    
    Her HTTP request için:
    1. Başlangıç zamanı kaydedilir
    2. Request işlenir
    3. Response süresi hesaplanır
    4. Metrik veritabanına yazılır
    
    Örnek:
    ------
    app.add_middleware(PerformanceMonitoringMiddleware)
    """
    
    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint
    ) -> Response:
        """
        Request'i işler ve performans metriklerini toplar.
        
        Args:
            request: Gelen HTTP request
            call_next: Sonraki middleware/handler
            
        Returns:
            Response: HTTP response
        """
        path = request.url.path
        method = request.method
        
        # Hariç tutulan path'leri atla
        if self._should_skip(path):
            return await call_next(request)
        
        # Zamanlama başlat
        start_time = time.perf_counter()
        
        try:
            # Request'i işle
            response = await call_next(request)
            status_code = response.status_code
            
        except Exception as e:
            # Hata durumunda da metrik kaydet
            status_code = 500
            end_time = time.perf_counter()
            response_time_ms = (end_time - start_time) * 1000
            
            await self._record_metric(path, method, response_time_ms, status_code)
            performance_logger.log_error(path, method, e, response_time_ms)
            raise
        
        # Response süresini hesapla
        end_time = time.perf_counter()
        response_time_ms = (end_time - start_time) * 1000
        
        # Metriği kaydet (async, response'u bekletmez)
        await self._record_metric(path, method, response_time_ms, status_code)
        
        # Performance log
        performance_logger.log_request(path, method, status_code, response_time_ms)
        
        # Response header'a timing bilgisi ekle (opsiyonel, debug için)
        response.headers["X-Response-Time"] = f"{response_time_ms:.2f}ms"
        
        return response
    
    def _should_skip(self, path: str) -> bool:
        """
        Path'in izleme dışında olup olmadığını kontrol eder.
        
        Aşağıdaki durumlar atlanır:
        - Swagger docs
        - Health check
        - Static files
        """
        if path in EXCLUDED_PATHS:
            return True
        
        # /static/ ile başlayan path'ler
        if path.startswith("/static"):
            return True
        
        return False
    
    async def _record_metric(
        self,
        path: str,
        method: str,
        response_time_ms: float,
        status_code: int
    ) -> None:
        """
        Performans metriğini veritabanına kaydeder.
        
        Yeni bir session kullanır (middleware'in kendi transaction'ı).
        Hata durumunda sessizce log'lar (API response'u etkilemez).
        """
        try:
            async with async_session_factory() as session:
                # Endpoint'i getir veya oluştur
                endpoint = await endpoint_repository.get_or_create(
                    session=session,
                    path=path,
                    method=method
                )
                
                # Metriği kaydet
                await metric_repository.create(
                    session=session,
                    endpoint_id=endpoint.id,
                    response_time_ms=response_time_ms,
                    status_code=status_code
                )
                
                await session.commit()
                
        except Exception as e:
            # Metrik kaydetme hatası API'yi etkilememeli
            logger.error(
                f"Metrik kaydetme hatası: {e}",
                extra={"path": path, "method": method}
            )
