"""
JERP 2.0 - Payroll API Endpoints
Payroll processing with compliance enforcement
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.payroll import PayrollPeriod, Payslip
from app.schemas.payroll import (
    PayrollPeriodCreate, PayrollPeriodUpdate, PayrollPeriodResponse, PayrollPeriodList,
    PayslipResponse, PayslipList,
    ProcessPayrollRequest, ProcessPayrollResponse,
    PayrollComplianceReport
)
from app.services.payroll_service import PayrollService

router = APIRouter()


@router.get("/periods", response_model=PayrollPeriodList)
def list_payroll_periods(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List payroll periods with pagination"""
    query = db.query(PayrollPeriod)
    
    if status:
        query = query.filter(PayrollPeriod.status == status)
    
    total = query.count()
    periods = query.offset(skip).limit(limit).all()
    
    return PayrollPeriodList(total=total, items=periods)


@router.post("/periods", response_model=PayrollPeriodResponse, status_code=status.HTTP_201_CREATED)
def create_payroll_period(
    period_data: PayrollPeriodCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new payroll period"""
    period = PayrollPeriod(**period_data.model_dump())
    db.add(period)
    db.commit()
    db.refresh(period)
    
    return period


@router.post("/periods/{period_id}/process", response_model=ProcessPayrollResponse)
async def process_payroll_period(
    period_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Process payroll period with automatic compliance checking"""
    service = PayrollService(db)
    
    try:
        result = await service.process_payroll_period(
            period_id=period_id,
            user_id=current_user.id,
            user_email=current_user.email,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent")
        )
        
        return ProcessPayrollResponse(**result)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/periods/{period_id}/approve", response_model=PayrollPeriodResponse)
async def approve_payroll_period(
    period_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Approve payroll period after review"""
    service = PayrollService(db)
    
    try:
        period = await service.approve_payroll_period(
            period_id=period_id,
            user_id=current_user.id
        )
        return period
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.get("/payslips", response_model=PayslipList)
def list_payslips(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    period_id: Optional[int] = None,
    employee_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List payslips with filtering"""
    query = db.query(Payslip)
    
    if period_id:
        query = query.filter(Payslip.period_id == period_id)
    
    if employee_id:
        query = query.filter(Payslip.employee_id == employee_id)
    
    total = query.count()
    payslips = query.offset(skip).limit(limit).all()
    
    return PayslipList(total=total, items=payslips)


@router.get("/payslips/{payslip_id}", response_model=PayslipResponse)
def get_payslip(
    payslip_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get payslip details"""
    payslip = db.query(Payslip).filter(Payslip.id == payslip_id).first()
    if not payslip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Payslip {payslip_id} not found"
        )
    
    return payslip


@router.get("/compliance-report", response_model=PayrollComplianceReport)
def get_compliance_report(
    period_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get compliance report for a payroll period"""
    period = db.query(PayrollPeriod).filter(PayrollPeriod.id == period_id).first()
    if not period:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Payroll period {period_id} not found"
        )
    
    payslips = db.query(Payslip).filter(Payslip.period_id == period_id).all()
    
    total_employees = len(payslips)
    california_compliant = sum(1 for p in payslips if p.california_labor_compliant)
    flsa_compliant = sum(1 for p in payslips if p.flsa_compliant)
    total_penalties = sum((p.meal_break_penalty or 0) + (p.rest_break_penalty or 0) for p in payslips)
    
    return PayrollComplianceReport(
        period_id=period_id,
        total_employees=total_employees,
        california_compliant=california_compliant,
        california_violations=total_employees - california_compliant,
        flsa_compliant=flsa_compliant,
        flsa_violations=total_employees - flsa_compliant,
        total_penalties=total_penalties
    )
