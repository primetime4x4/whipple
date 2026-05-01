"""SQLAlchemy 2 models for whipple."""
from datetime import datetime
from sqlalchemy import (Column, Integer, String, Text, Float, ForeignKey,
                        DateTime, CheckConstraint, Index)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

ARTICLE_STATES = ("SCRAPED", "CLASSIFIED", "IRRELEVANT", "SELECTED",
                  "SUMMARIZED", "SKIPPED", "COMPOSED", "FAILED")
SOURCE_TYPES = ("rss", "scraper", "manual")
BULLETIN_STATUSES = ("DRAFT", "COMPOSED", "SENT", "FAILED")
GEMINI_STAGES = ("classify", "summarize", "compose", "extract_quotes")
RUN_MODES = ("tick", "finalize", "manual_trigger", "manual_finalize")

# 6 article-bearing sections (5 narrative + briefs)
SECTIONS = ("energy_prices", "geopolitical", "climate",
            "global_economy", "renewables", "briefs")


class Source(Base):
    __tablename__ = "sources"
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    url = Column(String(1024), nullable=False, unique=True)
    source_type = Column(String(20), nullable=False)
    section_hint = Column(String(64))
    weight = Column(Float, nullable=False, default=1.0)
    selector_config = Column(Text)  # JSON for scrapers; null for RSS
    active = Column(Integer, nullable=False, default=0)
    last_checked_at = Column(DateTime)
    last_success_at = Column(DateTime)
    consecutive_failures = Column(Integer, nullable=False, default=0)
    notes = Column(Text)
    added_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    origin = Column(String(32))  # whipple-archive / modern / manual

    articles = relationship("Article", back_populates="source")

    __table_args__ = (
        CheckConstraint("source_type IN " + str(SOURCE_TYPES)),
        Index("idx_sources_active_checked", "active", "last_checked_at"),
    )


class Article(Base):
    __tablename__ = "articles"
    id = Column(Integer, primary_key=True)
    source_id = Column(Integer, ForeignKey("sources.id"), nullable=False)
    url = Column(String(1024), nullable=False, unique=True)
    title = Column(Text)
    published_at = Column(DateTime)
    scraped_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    week_of = Column(String(10), nullable=False)  # YYYY-MM-DD ISO Sunday CT
    raw_content = Column(Text)
    state = Column(String(16), nullable=False, default="SCRAPED")
    section = Column(String(32))
    score = Column(Float)
    summary_text = Column(Text)
    bulletin_id = Column(Integer, ForeignKey("bulletins.id"))
    classified_at = Column(DateTime)
    summarized_at = Column(DateTime)
    error_message = Column(Text)

    source = relationship("Source", back_populates="articles")
    bulletin = relationship("Bulletin", back_populates="articles")

    __table_args__ = (
        CheckConstraint("state IN " + str(ARTICLE_STATES)),
        Index("idx_articles_state_week", "state", "week_of"),
        Index("idx_articles_section", "section"),
        Index("idx_articles_week", "week_of"),
    )


class Bulletin(Base):
    __tablename__ = "bulletins"
    id = Column(Integer, primary_key=True)
    week_of = Column(String(10), nullable=False, unique=True)
    status = Column(String(16), nullable=False, default="DRAFT")
    generated_at = Column(DateTime)
    sent_at = Column(DateTime)
    html_content = Column(Text)
    quote_a = Column(Text)
    quote_b = Column(Text)
    graphic_url = Column(String(1024))
    graphic_caption = Column(Text)
    article_count = Column(Integer)
    total_word_count = Column(Integer)
    error_message = Column(Text)

    articles = relationship("Article", back_populates="bulletin")

    __table_args__ = (CheckConstraint("status IN " + str(BULLETIN_STATUSES)),)


class GeminiCall(Base):
    __tablename__ = "gemini_calls"
    id = Column(Integer, primary_key=True)
    called_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    stage = Column(String(20), nullable=False)
    model = Column(String(64), nullable=False)
    input_tokens = Column(Integer)
    output_tokens = Column(Integer)
    latency_ms = Column(Integer)
    article_id = Column(Integer, ForeignKey("articles.id"))
    bulletin_id = Column(Integer, ForeignKey("bulletins.id"))
    success = Column(Integer, nullable=False, default=1)
    error_message = Column(Text)

    __table_args__ = (
        CheckConstraint("stage IN " + str(GEMINI_STAGES)),
        Index("idx_gemini_called_at", "called_at"),
    )


class Run(Base):
    __tablename__ = "runs"
    id = Column(Integer, primary_key=True)
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    finished_at = Column(DateTime)
    mode = Column(String(20), nullable=False)
    articles_scraped = Column(Integer, nullable=False, default=0)
    articles_classified = Column(Integer, nullable=False, default=0)
    articles_selected = Column(Integer, nullable=False, default=0)
    articles_summarized = Column(Integer, nullable=False, default=0)
    articles_composed = Column(Integer, nullable=False, default=0)
    gemini_calls = Column(Integer, nullable=False, default=0)
    success = Column(Integer, nullable=False, default=1)
    error_message = Column(Text)
    notes = Column(Text)

    __table_args__ = (CheckConstraint("mode IN " + str(RUN_MODES)),)
