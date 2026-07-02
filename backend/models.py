from sqlalchemy import create_engine, Column, Integer, Float, String, Date, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime

DATABASE_URL = "sqlite:///./tickets.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True)
    monto = Column(Float, nullable=False)
    tipo_pago = Column(String, nullable=False, default="efectivo")
    descripcion = Column(String, default="")
    imagen_path = Column(String, default="")
    fecha = Column(Date, nullable=False)
    created_at = Column(DateTime, default=datetime.now)


def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
