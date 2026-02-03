"""
JERP 2.0 - Finance API Endpoints
Financial operations with GAAP/IFRS validation
"""
from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.finance import ChartOfAccounts, JournalEntry, JournalEntryLine
from app.schemas.finance import (
    ChartOfAccountsCreate, ChartOfAccountsResponse, ChartOfAccountsList,
    JournalEntryCreate, JournalEntryResponse, JournalEntryList,
    PostJournalEntryRequest, PostJournalEntryResponse,
    BalanceSheetResponse, IncomeStatementResponse, FinanceComplianceStatus
)
from app.services.finance_service import FinanceService

router = APIRouter()


# Chart of Accounts Endpoints
@router.get("/accounts", response_model=ChartOfAccountsList)
def list_accounts(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    account_type: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List chart of accounts with filtering"""
    query = db.query(ChartOfAccounts)
    
    if account_type:
        query = query.filter(ChartOfAccounts.account_type == account_type)
    
    if is_active is not None:
        query = query.filter(ChartOfAccounts.is_active == is_active)
    
    total = query.count()
    accounts = query.offset(skip).limit(limit).all()
    
    return ChartOfAccountsList(total=total, items=accounts)


@router.post("/accounts", response_model=ChartOfAccountsResponse, status_code=status.HTTP_201_CREATED)
def create_account(
    account_data: ChartOfAccountsCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new account"""
    # Check if account number already exists
    existing = db.query(ChartOfAccounts).filter(
        ChartOfAccounts.account_number == account_data.account_number
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Account number {account_data.account_number} already exists"
        )
    
    account = ChartOfAccounts(**account_data.model_dump())
    db.add(account)
    db.commit()
    db.refresh(account)
    
    return account


# Journal Entry Endpoints
@router.get("/journal-entries", response_model=JournalEntryList)
def list_journal_entries(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List journal entries with filtering"""
    query = db.query(JournalEntry)
    
    if status:
        query = query.filter(JournalEntry.status == status)
    
    total = query.count()
    entries = query.offset(skip).limit(limit).all()
    
    return JournalEntryList(total=total, items=entries)


@router.post("/journal-entries", response_model=JournalEntryResponse, status_code=status.HTTP_201_CREATED)
def create_journal_entry(
    entry_data: JournalEntryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new journal entry"""
    # Check if entry number already exists
    existing = db.query(JournalEntry).filter(
        JournalEntry.entry_number == entry_data.entry_number
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Entry number {entry_data.entry_number} already exists"
        )
    
    # Create entry
    entry_dict = entry_data.model_dump(exclude={"lines"})
    entry = JournalEntry(
        **entry_dict,
        created_by=current_user.id,
        status="DRAFT"
    )
    db.add(entry)
    db.flush()
    
    # Add lines
    for line_data in entry_data.lines:
        line = JournalEntryLine(
            **line_data.model_dump(),
            entry_id=entry.id
        )
        db.add(line)
    
    db.commit()
    db.refresh(entry)
    
    return entry


@router.post("/journal-entries/{entry_id}/post", response_model=PostJournalEntryResponse)
async def post_journal_entry(
    entry_id: int,
    post_request: PostJournalEntryRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Post journal entry with GAAP or IFRS validation"""
    service = FinanceService(db)
    
    try:
        result = await service.post_journal_entry(
            entry_id=entry_id,
            standard=post_request.standard,
            user_id=current_user.id,
            user_email=current_user.email,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent")
        )
        
        return PostJournalEntryResponse(**result)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# Financial Reports
@router.get("/reports/balance-sheet", response_model=BalanceSheetResponse)
def get_balance_sheet(
    as_of_date: date = Query(..., description="Balance sheet date"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Generate balance sheet"""
    service = FinanceService(db)
    return service.get_balance_sheet(as_of_date=as_of_date)


@router.get("/reports/income-statement", response_model=IncomeStatementResponse)
def get_income_statement(
    start_date: date = Query(..., description="Period start date"),
    end_date: date = Query(..., description="Period end date"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Generate income statement"""
    service = FinanceService(db)
    return service.get_income_statement(start_date=start_date, end_date=end_date)


@router.get("/compliance-status", response_model=FinanceComplianceStatus)
def get_compliance_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get GAAP/IFRS compliance status"""
    service = FinanceService(db)
    return service.get_compliance_status()
