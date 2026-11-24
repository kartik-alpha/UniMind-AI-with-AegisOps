import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
from fastapi import UploadFile, HTTPException, status
from sqlalchemy.orm import Session

from app.models.document import Document
from app.schemas.document import DocumentCreate
from app.adapters.factory import AdapterFactory
from app.services.governance_service import GovernanceService


BASE_DATA_DIR = Path("data")


def get_tenant_upload_dir(tenant_id: int, category: str) -> Path:
    """Returns the dedicated filesystem directory for a tenant's documents."""
    cat_dir = BASE_DATA_DIR / "tenants" / str(tenant_id) / "documents" / category
    cat_dir.mkdir(parents=True, exist_ok=True)
    return cat_dir


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
    "compliance",
    "operations",
    "security",
    "general",
}


MAX_UPLOAD_SIZE_BYTES = 25 * 1024 * 1024  # 25 MB
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md", ".csv", ".json"}


def validate_uploaded_file(upload_file: UploadFile) -> None:
    """
    Validates uploaded file against OWASP security requirements:
    - Path traversal prevention in filename (reject '../', '..\\', slashes)
    - Allowed extension whitelisting (.pdf, .docx, .txt, .md, .csv, .json)
    - Magic byte header verification (PDF '%PDF-', DOCX 'PK\x03\x04', text binary NUL check)
    - File size bound (maximum 25 MB)
    """
    filename = upload_file.filename or ""
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Security violation: Path traversal detected in filename.",
        )

    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '{ext}'. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    # Magic byte inspection
    header = upload_file.file.read(512)
    upload_file.file.seek(0)

    if hasattr(upload_file, "size") and upload_file.size and upload_file.size > MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum allowed size of 25 MB ({upload_file.size} bytes).",
        )

    if ext == ".pdf":
        if not header.startswith(b"%PDF-"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="MIME / Magic byte mismatch: File claims to be PDF but lacks '%PDF-' signature.",
            )
    elif ext == ".docx":
        if not header.startswith(b"PK\x03\x04"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="MIME / Magic byte mismatch: File claims to be DOCX but lacks 'PK\\x03\\x04' signature.",
            )
    elif ext in {".txt", ".md", ".csv", ".json"}:
        if b"\x00" in header:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="MIME / Magic byte mismatch: Text file contains binary NUL bytes.",
            )


def save_uploaded_file(upload_file: UploadFile, category: str, tenant_id: int = 1) -> Path:
    category_dir = get_tenant_upload_dir(tenant_id, category)
    # Sanitize filename to prevent directory traversal
    safe_filename = Path(upload_file.filename).name if upload_file.filename else "upload.bin"
    file_path = category_dir / safe_filename

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(upload_file.file, buffer)

    return file_path


def create_document(
    db: Session,
    title: str,
    category: str,
    upload_file: UploadFile,
    uploader_id: Optional[int] = None,
    tenant_id: int = 1,
) -> Document:
    validate_uploaded_file(upload_file)
    clean_cat = category.lower().strip()
    if clean_cat not in VALID_CATEGORIES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid category '{category}'. Must be one of: {', '.join(sorted(VALID_CATEGORIES))}",
        )

    # Check tenant storage quota before writing
    try:
        incoming_size = upload_file.size if hasattr(upload_file, "size") and upload_file.size else 0
        GovernanceService.check_storage_quota_before_upload(db, tenant_id, incoming_size)
    except HTTPException:
        raise
    except Exception:
        pass

    storage_adapter = AdapterFactory.get_storage()
    clean_name = Path(upload_file.filename).name if upload_file.filename else "upload.bin"
    try:
        res = storage_adapter.save_file(
            tenant_id=tenant_id,
            category=clean_cat,
            filename=clean_name,
            file_obj=upload_file.file,
            content_type=upload_file.content_type or "text/plain",
        )
        saved_path = res["storage_path"]
        file_size = res["size_bytes"]
    except HTTPException:
        raise
    except Exception:
        saved_path_obj = save_uploaded_file(upload_file, clean_cat, tenant_id=tenant_id)
        saved_path = str(saved_path_obj)
        file_size = os.path.getsize(saved_path)

    db_doc = Document(
        title=title,
        category=clean_cat,
        filename=upload_file.filename,
        file_path=str(saved_path),
        file_size=file_size,
        mime_type=upload_file.content_type or "text/plain",
        uploader_id=uploader_id,
        tenant_id=tenant_id,
        chunk_count=0,
        meta_info={"source": upload_file.filename, "category": clean_cat, "tenant_id": tenant_id},
    )
    db.add(db_doc)
    db.commit()
    db.refresh(db_doc)
    return db_doc


def get_documents(
    db: Session,
    category: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    tenant_id: Optional[int] = None,
) -> List[Document]:
    query = db.query(Document)
    if tenant_id is not None:
        query = query.filter(Document.tenant_id == tenant_id)
    if category:
        query = query.filter(Document.category == category.lower().strip())
    return query.offset(skip).limit(limit).all()


def get_document_by_id(
    db: Session,
    document_id: int,
    tenant_id: Optional[int] = None,
) -> Optional[Document]:
    query = db.query(Document).filter(Document.id == document_id)
    if tenant_id is not None:
        query = query.filter(Document.tenant_id == tenant_id)
    return query.first()


def delete_document(
    db: Session,
    document_id: int,
    tenant_id: Optional[int] = None,
) -> bool:
    db_doc = get_document_by_id(db, document_id, tenant_id=tenant_id)
    if not db_doc:
        return False

    tid = db_doc.tenant_id or tenant_id or 1
    storage_adapter = AdapterFactory.get_storage()
    try:
        storage_adapter.delete_file(tid, db_doc.file_path)
    except Exception:
        if os.path.exists(db_doc.file_path):
            try:
                os.remove(db_doc.file_path)
            except OSError:
                pass

    # Clean up chunks in vector store and BM25 index
    try:
        from rag.retrieval.retriever import delete_document_from_rag
        delete_document_from_rag(document_id, tenant_id=tid)
    except Exception:
        pass

    db.delete(db_doc)
    db.commit()
    return True


def update_document_approval_status(
    db: Session,
    document_id: int,
    approval_status: str,
    approver_username: str,
    tenant_id: Optional[int] = None,
    notes: Optional[str] = None,
) -> Optional[Document]:
    """
    Transitions a document through the institutional approval workflow:
    DRAFT -> PENDING_REVIEW -> APPROVED / REJECTED
    """
    valid_statuses = {"DRAFT", "PENDING_REVIEW", "APPROVED", "REJECTED"}
    norm_status = approval_status.upper().strip()
    if norm_status not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid approval status '{approval_status}'. Must be one of: {', '.join(sorted(valid_statuses))}",
        )

    doc = get_document_by_id(db, document_id, tenant_id=tenant_id)
    if not doc:
        return None

    meta = dict(doc.meta_info) if doc.meta_info else {}
    workflow_history = meta.get("workflow_history", [])
    now_iso = datetime.utcnow().isoformat()
    
    workflow_history.append({
        "from_status": meta.get("approval_status", "APPROVED"),
        "to_status": norm_status,
        "changed_by": approver_username,
        "changed_at": now_iso,
        "notes": notes,
    })

    meta["approval_status"] = norm_status
    meta["last_reviewed_by"] = approver_username
    meta["last_reviewed_at"] = now_iso
    meta["workflow_history"] = workflow_history

    doc.meta_info = meta
    db.commit()
    db.refresh(doc)
    return doc


def reindex_document(
    db: Session,
    document_id: int,
    tenant_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Re-extracts and re-indexes a single document into RAG vector and BM25 stores.
    """
    doc = get_document_by_id(db, document_id, tenant_id=tenant_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Document {document_id} not found.")

    tid = doc.tenant_id or tenant_id or 1
    from rag.retrieval.retriever import ingest_document_to_rag, delete_document_from_rag
    # Remove existing chunks before re-indexing
    delete_document_from_rag(document_id=doc.id, tenant_id=tid)
    res = ingest_document_to_rag(db=db, document_id=doc.id, tenant_id=tid)

    meta = dict(doc.meta_info) if doc.meta_info else {}
    meta["reindexed_at"] = datetime.utcnow().isoformat()
    doc.meta_info = meta
    db.commit()

    return {
        "document_id": doc.id,
        "title": doc.title,
        "chunks_indexed": res.get("chunks_indexed", 0),
        "status": "REINDEXED",
    }


def reindex_all_tenant_documents(
    db: Session,
    tenant_id: int,
) -> Dict[str, Any]:
    """
    Triggers complete knowledge base re-indexing for an entire tenant.
    """
    from rag.retrieval.retriever import reindex_tenant_knowledge_base
    return reindex_tenant_knowledge_base(db=db, tenant_id=tenant_id)
