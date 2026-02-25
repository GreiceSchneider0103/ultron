from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, ForeignKey, Boolean
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

Base = declarative_base()

class ResearchRun(Base):
    __tablename__ = "research_runs"

    id = Column(Integer, primary_key=True, index=True)
    keyword = Column(String, index=True)
    marketplace = Column(String, index=True)
    total_listings = Column(Integer)
    price_min = Column(Float)
    price_max = Column(Float)
    price_median = Column(Float)
    price_avg = Column(Float)
    seller_distribution = Column(JSON)
    shipping_distribution = Column(JSON)
    timestamp = Column(DateTime, default=datetime.utcnow)

    snapshots = relationship("ListingSnapshot", back_populates="run", cascade="all, delete-orphan")

class ListingSnapshot(Base):
    __tablename__ = "listing_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(Integer, ForeignKey("research_runs.id"))
    listing_id = Column(String, index=True)
    title = Column(String)
    price = Column(Float)
    permalink = Column(String)
    thumbnail = Column(String)
    original_data = Column(JSON)

    run = relationship("ResearchRun", back_populates="snapshots")