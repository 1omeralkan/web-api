"""
Merkezi Konfigürasyon Modülü
============================

YAZILIM KALİTE GÜVENCESİ AÇISINDAN ÖNEMİ:
-----------------------------------------
1. Tüm konfigürasyon tek bir yerden yönetilir (Single Source of Truth)
2. Environment variable desteği ile farklı ortamlarda (dev/prod) çalışabilirlik
3. Pydantic Settings ile tip güvenliği ve validation
4. Hassas bilgiler (şifre vb.) kod içinde değil, environment'ta tutulur

Bu yaklaşım, test edilebilirliği artırır çünkü:
- Mock konfigürasyonlar kolayca enjekte edilebilir
- Farklı test senaryoları için farklı threshold değerleri kullanılabilir
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """
    Uygulama ayarları.
    Environment variable'lardan veya .env dosyasından okunur.
    """
    
    # Veritabanı Ayarları
    DATABASE_HOST: str = "localhost"
    DATABASE_PORT: int = 5432
    DATABASE_NAME: str = "web-api"
    DATABASE_USER: str = "postgres"
    DATABASE_PASSWORD: str = "1Sjklmn90."
    
    # Performans Eşik Değerleri (Threshold)
    # Bu değerler, optimizasyon önerilerinin üretilmesinde kullanılır
    SLOW_RESPONSE_THRESHOLD_MS: int = 500  # 500ms üzeri "yavaş" kabul edilir
    ERROR_RATE_THRESHOLD_PERCENT: float = 10.0  # %10 üzeri hata oranı kritik
    ANOMALY_STDDEV_MULTIPLIER: float = 2.0  # Standart sapmanın 2 katı anormal
    
    # API Ayarları
    API_TITLE: str = "Web API Performance Monitor"
    API_VERSION: str = "1.0.0"
    API_DESCRIPTION: str = "REST API performans izleme ve optimizasyon öneri sistemi"
    
    # Logging Ayarları
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"  # json veya text
    
    @property
    def database_url(self) -> str:
        """
        Async SQLAlchemy için veritabanı bağlantı URL'i.
        asyncpg driver'ı kullanılır (PostgreSQL için yüksek performanslı async driver).
        """
        return (
            f"postgresql+asyncpg://{self.DATABASE_USER}:{self.DATABASE_PASSWORD}"
            f"@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"
        )
    
    @property
    def database_url_sync(self) -> str:
        """
        Senkron işlemler için veritabanı URL'i (migration vb.)
        """
        return (
            f"postgresql://{self.DATABASE_USER}:{self.DATABASE_PASSWORD}"
            f"@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"
        )
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """
    Singleton pattern ile settings instance döndürür.
    
    LRU cache kullanımı:
    - Her çağrıda yeni instance oluşturulmasını engeller
    - Performans optimizasyonu sağlar
    - Test sırasında cache temizlenebilir
    """
    return Settings()
