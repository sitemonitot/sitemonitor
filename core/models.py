from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_pro = Column(Boolean, default=False)
    stripe_customer_id = Column(String, nullable=True)
    stripe_subscription_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    monitors = relationship("Monitor", back_populates="user", cascade="all, delete")


class Monitor(Base):
    __tablename__ = "monitors"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    url = Column(String, nullable=False)
    label = Column(String, nullable=True)
    css_selector = Column(String, nullable=True)  # monitorizar solo parte de la página
    last_content = Column(Text, nullable=True)
    last_checked_at = Column(DateTime, nullable=True)
    last_changed_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="monitors")
    alerts = relationship("Alert", back_populates="monitor", cascade="all, delete")


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True)
    monitor_id = Column(Integer, ForeignKey("monitors.id"), nullable=False)
    old_content_snippet = Column(Text, nullable=True)
    new_content_snippet = Column(Text, nullable=True)
    detected_at = Column(DateTime, default=datetime.utcnow)
    email_sent = Column(Boolean, default=False)

    monitor = relationship("Monitor", back_populates="alerts")


class MarketingPost(Base):
    __tablename__ = "marketing_posts"

    id = Column(Integer, primary_key=True)
    platform = Column(String, nullable=False)  # reddit, devto, bluesky
    title = Column(String, nullable=True)
    content = Column(Text, nullable=False)
    subreddit = Column(String, nullable=True)
    status = Column(String, default="pending")  # pending, published, failed
    scheduled_at = Column(DateTime, nullable=True)
    published_at = Column(DateTime, nullable=True)
    post_url = Column(String, nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True)
    session_id = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id"), nullable=False)
    role = Column(String, nullable=False)  # user, assistant
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("ChatSession", back_populates="messages")
