from sqlalchemy import Column, Integer, String, Float, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class ResearchRun(Base):
    __tablename__ = "research_runs"
    id = Column(Integer, primary_key=True, index=True)
    keyword = Column(String, index=True)
    marketplace = Column(String)
    total_listings = Column(Integer)
    price_min = Column(Float)
    price_max = Column(Float)
    price_median = Column(Float)
    price_avg = Column(Float)
    seller_distribution = Column(JSON)
    shipping_distribution = Column(JSON)
    timestamp = Column(DateTime, default=datetime.utcnow)

class ListingSnapshot(Base):
    __tablename__ = "listing_snapshots"
    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(Integer)
    listing_id = Column(String, index=True)
    title = Column(String)
    price = Column(Float)
    permalink = Column(String)
    thumbnail = Column(String)
    original_data = Column(JSON)