from sqlalchemy import create_engine, Column, Integer, Float, String, Date, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
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


class Repartidor(Base):
    __tablename__ = "repartidores"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False)
    color = Column(String, nullable=False, default="slate")
    zonas = Column(String, default="")
    created_at = Column(DateTime, default=datetime.now)


class DomicilioBatch(Base):
    __tablename__ = "domicilio_batches"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, default="")
    total = Column(Integer, default=0)
    clasificados = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now)

    domicilios = relationship("Domicilio", back_populates="batch", cascade="all, delete-orphan")


class Domicilio(Base):
    __tablename__ = "domicilios"

    id = Column(Integer, primary_key=True, index=True)
    batch_id = Column(Integer, ForeignKey("domicilio_batches.id"), nullable=False)
    direccion = Column(String, nullable=False)
    cliente = Column(String, default="")
    telefono = Column(String, default="")
    zona_detectada = Column(String, default="")
    repartidor_id = Column(Integer, ForeignKey("repartidores.id"), nullable=True)
    confianza = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.now)

    batch = relationship("DomicilioBatch", back_populates="domicilios")
    repartidor = relationship("Repartidor")


def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
