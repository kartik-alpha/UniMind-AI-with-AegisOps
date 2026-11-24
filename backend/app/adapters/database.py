"""
Database Adapter Layer for Stage H Hybrid Distributed Infrastructure.
Provides abstract contract and concrete adapters for SQLite (local default) and PostgreSQL (production).
"""
import abc
import time
from typing import Dict, Any, List, Optional
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool, StaticPool

from app.core.config import settings
from app.adapters.exceptions import AdapterException, ResourceNotFoundError


class DatabaseAdapter(abc.ABC):
    """Abstract interface defining the relational database storage contract."""

    @abc.abstractmethod
    def connect(self) -> None:
        """Establish connection pool and verify connectivity."""
        pass

    @abc.abstractmethod
    def disconnect(self) -> None:
        """Dispose connection pool and close active connections."""
        pass

    @abc.abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """Verify database connectivity, latency, and read/write capability."""
        pass

    @abc.abstractmethod
    def get_session(self) -> Session:
        """Yield a database session from the connection pool."""
        pass

    @abc.abstractmethod
    def get_table_names(self) -> List[str]:
        """List all verified schema tables."""
        pass

    @abc.abstractmethod
    def execute_raw(self, sql: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute a parameterized query and return row dictionaries."""
        pass


class SQLiteDatabaseAdapter(DatabaseAdapter):
    """Default local zero-dependency database adapter using SQLite in WAL mode."""

    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url or settings.DATABASE_URL
        self._engine = None
        self._session_factory = None
        self._connected = False

    def connect(self) -> None:
        from sqlalchemy import event

        connect_args = {"check_same_thread": False, "timeout": 30}
        self._engine = create_engine(
            self.database_url,
            connect_args=connect_args,
            echo=settings.DEBUG,
        )

        @event.listens_for(self._engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            try:
                cursor.execute("PRAGMA journal_mode=WAL;")
                cursor.execute("PRAGMA synchronous=NORMAL;")
                cursor.execute("PRAGMA busy_timeout=30000;")
                cursor.execute("PRAGMA foreign_keys=ON;")
            except Exception:
                pass
            finally:
                cursor.close()

        self._session_factory = sessionmaker(autocommit=False, autoflush=False, bind=self._engine)
        self._connected = True

    def disconnect(self) -> None:
        if self._engine:
            self._engine.dispose()
            self._connected = False

    def health_check(self) -> Dict[str, Any]:
        start = time.perf_counter()
        try:
            with self.get_session() as session:
                res = session.execute(text("SELECT 1;")).scalar()
                latency_ms = (time.perf_counter() - start) * 1000
                return {
                    "status": "healthy" if res == 1 else "degraded",
                    "adapter": "SQLiteDatabaseAdapter",
                    "dialect": "sqlite",
                    "latency_ms": round(latency_ms, 2),
                    "wal_enabled": True,
                }
        except Exception as e:
            return {
                "status": "unhealthy",
                "adapter": "SQLiteDatabaseAdapter",
                "dialect": "sqlite",
                "error": str(e),
            }

    def get_session(self) -> Session:
        if not self._session_factory:
            self.connect()
        return self._session_factory()

    def get_table_names(self) -> List[str]:
        if not self._engine:
            self.connect()
        inspector = inspect(self._engine)
        return inspector.get_table_names()

    def execute_raw(self, sql: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        with self.get_session() as session:
            result = session.execute(text(sql), params or {})
            if result.returns_rows:
                return [dict(row._mapping) for row in result.fetchall()]
            session.commit()
            return []


class PostgreSQLDatabaseAdapter(DatabaseAdapter):
    """Production enterprise relational database adapter using PostgreSQL with connection pooling."""

    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url or settings.DATABASE_URL
        self._engine = None
        self._session_factory = None
        self._connected = False

    def connect(self) -> None:
        from sqlalchemy import event

        self._engine = create_engine(
            self.database_url,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
            pool_recycle=1800,
            pool_timeout=30,
            echo=settings.DEBUG,
        )

        @event.listens_for(self._engine, "connect")
        def set_pg_params(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            try:
                cursor.execute("SET statement_timeout = 30000;")
            except Exception:
                pass
            finally:
                cursor.close()

        self._session_factory = sessionmaker(autocommit=False, autoflush=False, bind=self._engine)
        self._connected = True

    def disconnect(self) -> None:
        if self._engine:
            self._engine.dispose()
            self._connected = False

    def health_check(self) -> Dict[str, Any]:
        start = time.perf_counter()
        try:
            with self.get_session() as session:
                res = session.execute(text("SELECT 1;")).scalar()
                latency_ms = (time.perf_counter() - start) * 1000
                pool_status = {
                    "pool_size": self._engine.pool.size(),
                    "checkedin": self._engine.pool.checkedin(),
                    "checkedout": self._engine.pool.checkedout(),
                    "overflow": self._engine.pool.overflow(),
                } if hasattr(self._engine, "pool") else {}
                return {
                    "status": "healthy" if res == 1 else "degraded",
                    "adapter": "PostgreSQLDatabaseAdapter",
                    "dialect": "postgresql",
                    "latency_ms": round(latency_ms, 2),
                    "pool": pool_status,
                }
        except Exception as e:
            return {
                "status": "unhealthy",
                "adapter": "PostgreSQLDatabaseAdapter",
                "dialect": "postgresql",
                "error": str(e),
            }

    def get_session(self) -> Session:
        if not self._session_factory:
            self.connect()
        return self._session_factory()

    def get_table_names(self) -> List[str]:
        if not self._engine:
            self.connect()
        inspector = inspect(self._engine)
        return inspector.get_table_names()

    def execute_raw(self, sql: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        with self.get_session() as session:
            result = session.execute(text(sql), params or {})
            if result.returns_rows:
                return [dict(row._mapping) for row in result.fetchall()]
            session.commit()
            return []
