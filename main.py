"""
Web API Performance Monitoring System
=====================================

Ana uygulama dosyası - FastAPI uygulamasını yapılandırır ve çalıştırır.

YAZILIM KALİTE GÜVENCESİ AÇISINDAN:
-----------------------------------
1. Merkezi uygulama yapılandırması
2. Startup/shutdown lifecycle yönetimi
3. Global exception handling
4. Modüler router kayıt sistemi
5. Comprehensive API documentation

ÇALIŞTIRMA:
-----------
uvicorn main:app --reload --host 0.0.0.0 --port 8000

SWAGGER DOCS:
-------------
http://localhost:8000/docs
"""

from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from core.config import get_settings
from core.database import init_db, close_db
from core.logging import setup_logging, get_logger
from core.middleware import PerformanceMonitoringMiddleware
from core.exceptions import APIException

# Router imports
from api.endpoints import router as endpoints_router
from api.metrics import router as metrics_router
from api.suggestions import router as suggestions_router
from api.analyze import router as analyze_router

settings = get_settings()
logger = get_logger(__name__)


# ============================================================================
# Application Lifecycle
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Uygulama yaşam döngüsü yönetimi.
    
    Startup:
    - Logging yapılandırması
    - Veritabanı tabloları oluşturma
    
    Shutdown:
    - Veritabanı bağlantılarını kapatma
    """
    # Startup
    setup_logging()
    logger.info("Uygulama başlatılıyor...")
    
    try:
        await init_db()
        logger.info("Veritabanı tabloları hazır")
    except Exception as e:
        logger.error(f"Veritabanı başlatma hatası: {e}")
        raise
    
    logger.info(f"API hazır: {settings.API_TITLE} v{settings.API_VERSION}")
    
    yield  # Uygulama çalışıyor
    
    # Shutdown
    logger.info("Uygulama kapatılıyor...")
    await close_db()
    logger.info("Veritabanı bağlantıları kapatıldı")


# ============================================================================
# FastAPI Application
# ============================================================================

app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    description=settings.API_DESCRIPTION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)


# ============================================================================
# Global Exception Handler
# ============================================================================

@app.exception_handler(APIException)
async def api_exception_handler(request: Request, exc: APIException):
    """
    APIException türevleri için global exception handler.
    
    Tutarlı hata response formatı sağlar.
    """
    logger.warning(
        f"API Hatası: {exc.error_code}",
        extra={
            "path": request.url.path,
            "method": request.method,
            "error_code": exc.error_code,
            "status_code": exc.status_code,
        }
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict()
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """
    Beklenmeyen hatalar için catch-all handler.
    
    Production'da detaylı hata bilgisi gizlenir.
    """
    logger.error(
        f"Beklenmeyen hata: {exc}",
        extra={
            "path": request.url.path,
            "method": request.method,
            "error_type": type(exc).__name__,
        },
        exc_info=True
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "Beklenmeyen bir hata oluştu",
            }
        }
    )


# ============================================================================
# Middleware Registration
# ============================================================================

# CORS (Cross-Origin Resource Sharing)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Production'da kısıtlanmalı
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Performance Monitoring Middleware
app.add_middleware(PerformanceMonitoringMiddleware)


# ============================================================================
# Router Registration
# ============================================================================

app.include_router(endpoints_router)
app.include_router(metrics_router)
app.include_router(suggestions_router)
app.include_router(analyze_router)

# Static Files (CSS, JS)
static_path = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(static_path)), name="static")


# ============================================================================
# Health Check Endpoint
# ============================================================================

@app.get(
    "/health",
    tags=["System"],
    summary="Sağlık Kontrolü",
    description="API'nin çalışır durumda olduğunu doğrular."
)
async def health_check():
    """
    Health check endpoint.
    
    Load balancer ve monitoring sistemleri tarafından kullanılır.
    """
    return {
        "status": "healthy",
        "service": settings.API_TITLE,
        "version": settings.API_VERSION
    }


@app.get(
    "/",
    tags=["System"],
    summary="Dashboard",
    description="Ana dashboard sayfasını döndürür.",
    include_in_schema=False
)
async def root():
    """
    Dashboard - Ana sayfa.
    """
    static_path = Path(__file__).parent / "static" / "index.html"
    return FileResponse(str(static_path))


@app.get(
    "/api",
    tags=["System"],
    summary="API Bilgisi",
    description="API hakkında temel bilgileri döndürür."
)
async def api_info():
    """
    API endpoint - API bilgileri.
    """
    return {
        "message": "Web API Performance Monitoring System",
        "version": settings.API_VERSION,
        "docs": "/docs",
        "dashboard": "/",
        "endpoints": {
            "endpoints": "/endpoints - İzlenen endpoint'leri listeler",
            "metrics": "/metrics - Performans metriklerini listeler",
            "slow": "/metrics/slow - Yavaş endpoint'leri listeler",
            "suggestions": "/suggestions - Optimizasyon önerilerini listeler",
            "analyze": "/suggestions/analyze - Performans analizi yapar (POST)",
        }
    }


# ============================================================================
# Entry Point
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Development için
        log_level="info"
    )
