from app.db.base_class import Base
from app.db.session import engine
# Import all models to ensure DeclarativeBase registers them
from app.models.user import User, UserRole
from app.models.document import Document
from app.models.conversation import Conversation, Message
from app.models.ticket import Ticket, Incident
from app.models.audit import AuditLog


def init_db():
    """Initializes the database schema by creating all registered tables."""
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    init_db()
    print("Database tables initialized successfully.")
