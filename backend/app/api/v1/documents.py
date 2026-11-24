from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user, require_roles
from app.api.tenant_deps import get_current_tenant
from app.models.organization import Organization
from app.models.user import User, UserRole
from app.schemas.document import DocumentResponse, DocumentWorkflowRequest
from app.services import document_service

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
def upload_document(
    title: str = Form(...),
    category: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.FACULTY)),
    current_tenant: Organization = Depends(get_current_tenant),
):
    """
    Upload a university document to the knowledge base storage for the current tenant.
    Restricted to FACULTY and ADMIN roles.
    """
    doc = document_service.create_document(
        db=db,
        title=title,
        category=category,
        upload_file=file,
        uploader_id=current_user.id,
        tenant_id=current_tenant.id,
    )
    return doc


@router.get("", response_model=List[DocumentResponse])
def list_documents(
    category: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_tenant: Organization = Depends(get_current_tenant),
):
    """
    List all uploaded documents for the current tenant, with optional category filter.
    """
    return document_service.get_documents(
        db=db, category=category, skip=skip, limit=limit, tenant_id=current_tenant.id
    )


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_tenant: Organization = Depends(get_current_tenant),
):
    """
    Retrieve document details by ID within current tenant.
    """
    doc = document_service.get_document_by_id(
        db=db, document_id=document_id, tenant_id=current_tenant.id
    )
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID {document_id} not found.",
        )
    return doc


@router.delete("/{document_id}", status_code=status.HTTP_200_OK)
def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
    current_tenant: Organization = Depends(get_current_tenant),
):
    """
    Delete a document and its stored file within current tenant. Restricted to ADMIN.
    """
    success = document_service.delete_document(
        db=db, document_id=document_id, tenant_id=current_tenant.id
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID {document_id} not found.",
        )
    return {"message": f"Document {document_id} deleted successfully."}


@router.post("/{document_id}/workflow", response_model=DocumentResponse)
def update_document_workflow(
    document_id: int,
    payload: DocumentWorkflowRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.FACULTY)),
    current_tenant: Organization = Depends(get_current_tenant),
):
    """
    Transition a document's institutional approval workflow state (DRAFT, PENDING_REVIEW, APPROVED, REJECTED).
    Restricted to FACULTY and ADMIN.
    """
    doc = document_service.update_document_approval_status(
        db=db,
        document_id=document_id,
        approval_status=payload.approval_status,
        approver_username=current_user.username,
        tenant_id=current_tenant.id,
        notes=payload.notes,
    )
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID {document_id} not found.",
        )
    return doc


@router.post("/{document_id}/reindex", status_code=status.HTTP_200_OK)
def reindex_single_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.FACULTY)),
    current_tenant: Organization = Depends(get_current_tenant),
):
    """
    Re-extract and re-index a single document's chunks in ChromaDB and BM25 index.
    """
    return document_service.reindex_document(
        db=db, document_id=document_id, tenant_id=current_tenant.id
    )


@router.post("/reindex-all", status_code=status.HTTP_200_OK)
def reindex_all_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
    current_tenant: Organization = Depends(get_current_tenant),
):
    """
    Full re-indexing of all tenant documents across vector store and BM25 index. Restricted to ADMIN.
    """
    return document_service.reindex_all_tenant_documents(
        db=db, tenant_id=current_tenant.id
    )
