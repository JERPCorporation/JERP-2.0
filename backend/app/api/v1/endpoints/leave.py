"""
JERP 2.0 - Leave Management API Endpoints
Leave policies, balances, and requests
"""
from datetime import datetime, timezone, date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.leave import LeavePolicy, LeaveBalance, LeaveRequest
from app.models.hr import Employee
from app.schemas.leave import (
    LeavePolicyCreate, LeavePolicyResponse, LeavePolicyList,
    LeaveBalanceResponse, LeaveBalanceList,
    LeaveRequestCreate, LeaveRequestResponse, LeaveRequestList,
    LeaveRequestReviewRequest, LeaveRequestReviewResponse,
    LeaveCalendarEntry, LeaveCalendarResponse
)

router = APIRouter()


# Leave Policy Endpoints
@router.get("/policies", response_model=LeavePolicyList)
def list_policies(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List leave policies"""
    query = db.query(LeavePolicy)
    
    if is_active is not None:
        query = query.filter(LeavePolicy.is_active == is_active)
    
    total = query.count()
    policies = query.offset(skip).limit(limit).all()
    
    return LeavePolicyList(total=total, items=policies)


@router.post("/policies", response_model=LeavePolicyResponse, status_code=status.HTTP_201_CREATED)
def create_policy(
    policy_data: LeavePolicyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new leave policy"""
    policy = LeavePolicy(**policy_data.model_dump())
    db.add(policy)
    db.commit()
    db.refresh(policy)
    
    return policy


# Leave Balance Endpoints
@router.get("/balances", response_model=LeaveBalanceList)
def get_my_balances(
    employee_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get leave balances for current user or specified employee"""
    # If no employee_id provided, try to find employee linked to current user
    if not employee_id:
        employee = db.query(Employee).filter(Employee.user_id == current_user.id).first()
        if not employee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No employee record found for current user"
            )
        employee_id = employee.id
    
    balances = db.query(LeaveBalance).filter(
        LeaveBalance.employee_id == employee_id
    ).all()
    
    return LeaveBalanceList(total=len(balances), items=balances)


# Leave Request Endpoints
@router.get("/requests", response_model=LeaveRequestList)
def list_requests(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    employee_id: Optional[int] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List leave requests"""
    query = db.query(LeaveRequest)
    
    if employee_id:
        query = query.filter(LeaveRequest.employee_id == employee_id)
    
    if status:
        query = query.filter(LeaveRequest.status == status)
    
    total = query.count()
    requests = query.offset(skip).limit(limit).all()
    
    return LeaveRequestList(total=total, items=requests)


@router.post("/requests", response_model=LeaveRequestResponse, status_code=status.HTTP_201_CREATED)
def create_request(
    request_data: LeaveRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new leave request"""
    # Check if employee has sufficient balance
    balance = db.query(LeaveBalance).filter(
        and_(
            LeaveBalance.employee_id == request_data.employee_id,
            LeaveBalance.policy_id == request_data.policy_id
        )
    ).first()
    
    if not balance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Leave balance not found for this employee and policy"
        )
    
    if balance.available_hours < request_data.hours_requested:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient leave balance. Available: {balance.available_hours}, Requested: {request_data.hours_requested}"
        )
    
    # Create leave request
    leave_request = LeaveRequest(**request_data.model_dump())
    db.add(leave_request)
    
    # Update balance
    balance.pending_hours += request_data.hours_requested
    balance.available_hours -= request_data.hours_requested
    
    db.commit()
    db.refresh(leave_request)
    
    return leave_request


@router.post("/requests/{request_id}/approve", response_model=LeaveRequestReviewResponse)
def approve_request(
    request_id: int,
    review_data: LeaveRequestReviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Approve a leave request"""
    leave_request = db.query(LeaveRequest).filter(LeaveRequest.id == request_id).first()
    if not leave_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Leave request {request_id} not found"
        )
    
    if leave_request.status != "PENDING":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Leave request is not pending (current status: {leave_request.status})"
        )
    
    # Update request
    leave_request.status = "APPROVED"
    leave_request.reviewed_by = current_user.id
    leave_request.reviewed_at = datetime.now(timezone.utc)
    leave_request.review_notes = review_data.review_notes
    
    # Update balance
    balance = db.query(LeaveBalance).filter(
        and_(
            LeaveBalance.employee_id == leave_request.employee_id,
            LeaveBalance.policy_id == leave_request.policy_id
        )
    ).first()
    
    if balance:
        balance.pending_hours -= leave_request.hours_requested
        balance.used_hours += leave_request.hours_requested
    
    db.commit()
    db.refresh(leave_request)
    
    return LeaveRequestReviewResponse(
        success=True,
        message="Leave request approved successfully",
        leave_request=leave_request
    )


@router.post("/requests/{request_id}/reject", response_model=LeaveRequestReviewResponse)
def reject_request(
    request_id: int,
    review_data: LeaveRequestReviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Reject a leave request"""
    leave_request = db.query(LeaveRequest).filter(LeaveRequest.id == request_id).first()
    if not leave_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Leave request {request_id} not found"
        )
    
    if leave_request.status != "PENDING":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Leave request is not pending (current status: {leave_request.status})"
        )
    
    # Update request
    leave_request.status = "REJECTED"
    leave_request.reviewed_by = current_user.id
    leave_request.reviewed_at = datetime.now(timezone.utc)
    leave_request.review_notes = review_data.review_notes
    
    # Restore balance
    balance = db.query(LeaveBalance).filter(
        and_(
            LeaveBalance.employee_id == leave_request.employee_id,
            LeaveBalance.policy_id == leave_request.policy_id
        )
    ).first()
    
    if balance:
        balance.pending_hours -= leave_request.hours_requested
        balance.available_hours += leave_request.hours_requested
    
    db.commit()
    db.refresh(leave_request)
    
    return LeaveRequestReviewResponse(
        success=True,
        message="Leave request rejected",
        leave_request=leave_request
    )


@router.get("/calendar", response_model=LeaveCalendarResponse)
def get_calendar(
    start_date: date = Query(..., description="Calendar start date"),
    end_date: date = Query(..., description="Calendar end date"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get leave calendar for a date range"""
    requests = db.query(LeaveRequest).filter(
        and_(
            LeaveRequest.status == "APPROVED",
            LeaveRequest.start_date <= end_date,
            LeaveRequest.end_date >= start_date
        )
    ).all()
    
    entries = []
    for req in requests:
        employee = req.employee
        policy = req.policy
        
        if employee and policy:
            entries.append(LeaveCalendarEntry(
                employee_id=employee.id,
                employee_name=f"{employee.first_name} {employee.last_name}",
                leave_type=policy.leave_type,
                start_date=req.start_date,
                end_date=req.end_date,
                status=req.status
            ))
    
    return LeaveCalendarResponse(
        start_date=start_date,
        end_date=end_date,
        entries=entries
    )
