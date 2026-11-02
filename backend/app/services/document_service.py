import os
import shutil
from pathlib import Path
from typing import List, Optional
from fastapi import UploadFile, HTTPException, status
from sqlalchemy.orm import Session

from app.models.document import Document
from app.schemas.document import DocumentCreate


UPLOAD_DIR = Path("data/documents")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

VALID_CATEGORIES = {
    "attendance",
    "examinations",
    "hostel",
    "library",
    "academics",
    "departments",
    "student_guidelines",
    "notices",
    "policies",
}


def save_uploaded_file(upload_file: UploadFile, category: str) -> Path:
    category_dir = UPLOAD_DIR / category
    category_dir.mkdir(parents=True, exist_ok=True)
    file_path = category_dir / upload_file.filename

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(upload_file.file, buffer)

    return file_path


def create_document(
    db: Session,
    title: str,
    category: str,
    upload_file: UploadFile,
    uploader_id: Optional[int] = None,
) -> Document:
    clean_cat = category.lower().strip()
    if clean_cat not in VALID_CATEGORIES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid category '{category}'. Must be one of: {', '.join(sorted(VALID_CATEGORIES))}",
        )

    saved_path = save_uploaded_file(upload_file, clean_cat)
    file_size = os.path.getsize(saved_path)

    db_doc = Document(
        title=title,
        category=clean_cat,
        filename=upload_file.filename,
        file_path=str(saved_path),
        file_size=file_size,
        mime_type=upload_file.content_type or "text/plain",
        uploader_id=uploader_id,
        chunk_count=0,
        meta_info={"source": upload_file.filename, "category": clean_cat},
    )
    db.add(db_doc)
    db.commit()
    db.refresh(db_doc)
    return db_doc


def get_documents(
    db: Session, category: Optional[str] = None, skip: int = 0, limit: int = 100
) -> List[Document]:
    query = db.query(Document)
    if category:
        query = query.filter(Document.category == category.lower().strip())
    return query.offset(skip).limit(limit).all()


def get_document_by_id(db: Session, document_id: int) -> Optional[Document]:
    return db.query(Document).filter(Document.id == document_id).first()


def delete_document(db: Session, document_id: int) -> bool:
    db_doc = get_document_by_id(db, document_id)
    if not db_doc:
        return False

    if os.path.exists(db_doc.file_path):
        try:
            os.remove(db_doc.file_path)
        except OSError:
            pass

    # Clean up chunks in vector store and BM25 index
    try:
        from rag.retrieval.retriever import delete_document_from_rag
        delete_document_from_rag(document_id)
    except Exception:
        pass

    db.delete(db_doc)
    db.commit()
    return True
