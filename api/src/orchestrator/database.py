import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from api.src.config import settings
from api.src.db.models import Base, ResearchRun, ListingSnapshot

logger = logging.getLogger(__name__)

engine = create_engine(
    settings.DATABASE_URL, 
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")

# Inicializa ao importar
init_db()

def save_research_run(summary, listings):
    """Salva a execução de pesquisa de mercado (ML)"""
    session = SessionLocal()
    try:
        db_run = ResearchRun(
            keyword=summary.keyword,
            marketplace=summary.marketplace,
            total_listings=summary.total_listings,
            price_min=summary.price_stats.min,
            price_max=summary.price_stats.max,
            price_median=summary.price_stats.median,
            price_avg=summary.price_stats.avg,
            seller_distribution=summary.seller_distribution,
            shipping_distribution=summary.shipping_distribution,
            timestamp=summary.timestamp
        )
        session.add(db_run)
        session.commit()
        session.refresh(db_run)

        snapshots = []
        for item in listings:
            snapshot = ListingSnapshot(
                run_id=db_run.id,
                listing_id=str(item.get("id", "")),
                title=item.get("title", ""),
                price=float(item.get("price", 0.0) or 0.0),
                permalink=item.get("permalink", ""),
                thumbnail=item.get("thumbnail", ""),
                original_data=item
            )
            snapshots.append(snapshot)
        
        if snapshots:
            session.bulk_save_objects(snapshots)
            session.commit()
    except Exception as e:
        logger.error(f"Error saving to DB: {e}")
        session.rollback()
    finally:
        session.close()