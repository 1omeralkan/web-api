"""
Veritabanı Bağlantı Modülü
==========================

YAZILIM KALİTE GÜVENCESİ AÇISINDAN ÖNEMİ:
-----------------------------------------
1. Async SQLAlchemy ile non-blocking I/O - yüksek eşzamanlılık
2. Connection pooling ile verimli kaynak kullanımı
3. Session yönetimi dependency injection ile - test edilebilirlik
4. Context manager pattern ile güvenli kaynak temizliği

PERFORMANS AÇISINDAN:
---------------------
- asyncpg: Python'un en hızlı PostgreSQL driver'ı
- Pool size ayarlanabilir (varsayılan: 5-20 connection)
- Bağlantı timeout'ları ile deadlock önleme
"""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
from typing import AsyncGenerator

from core.config import get_settings

settings = get_settings()

# Async Engine oluşturma
# ----------------------
# echo=False: SQL loglarını kapatır (production için önerilir)
# pool_pre_ping=True: Bağlantı sağlığını kontrol eder
engine = create_async_engine(
    settings.database_url,
    echo=False,  # Debug için True yapılabilir
    pool_pre_ping=True,  # Bağlantı kopmuşsa yeniden bağlan
    pool_size=10,  # Havuzdaki minimum bağlantı sayısı
    max_overflow=20,  # Maksimum ek bağlantı sayısı
)

# Session Factory
# ---------------
# expire_on_commit=False: Commit sonrası objelerin geçerliliğini korur
# autoflush=False: Manuel flush kontrolü sağlar
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency olarak kullanılacak async session generator.
    
    Kullanım:
    ---------
    @router.get("/example")
    async def example(db: AsyncSession = Depends(get_db_session)):
        # db kullanımı
        pass
    
    Bu pattern'in avantajları:
    1. Her request için izole session
    2. Otomatik rollback (hata durumunda)
    3. Otomatik session kapatma (finally bloğu)
    4. Test sırasında mock session enjekte edilebilir
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """
    Veritabanı tablolarını oluşturur.
    Uygulama başlangıcında çağrılır (startup event).
    
    NOT: Production'da Alembic migration tercih edilir.
    Bu fonksiyon development kolaylığı için sunulmuştur.
    """
    from models.base import Base
    
    async with engine.begin() as conn:
        # Tüm modelleri import et (foreign key ilişkileri için gerekli)
        from models import api_endpoint, performance_metric, optimization_suggestion
        
        # Tabloları oluştur
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """
    Veritabanı bağlantılarını kapatır.
    Uygulama kapanışında çağrılır (shutdown event).
    """
    await engine.dispose()
