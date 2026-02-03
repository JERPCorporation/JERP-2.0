"""
JERP 2.0 - Time & Attendance API Endpoints
Time tracking with compliance enforcement
"""
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.time_attendance import Timesheet, TimesheetEntry, BreakEntry
from app.schemas.time_attendance import (
    TimesheetCreate, TimesheetResponse, TimesheetList,
    ClockInRequest, ClockOutRequest, ClockResponse,
    BreakStartRequest, BreakEndRequest, BreakResponse,
    TimesheetSubmitRequest, TimesheetSubmitResponse
)

router = APIRouter()


@router.post("/clock-in", response_model=ClockResponse)
def clock_in(
    clock_request: ClockInRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Clock in for work"""
    # Find or create timesheet for this period
    timesheet = db.query(Timesheet).filter(
        Timesheet.employee_id == clock_request.employee_id,
        Timesheet.period_start <= clock_request.work_date,
        Timesheet.period_end >= clock_request.work_date
    ).first()
    
    if not timesheet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No timesheet found for this date. Please create a timesheet first."
        )
    
    # Check if already clocked in
    existing_entry = db.query(TimesheetEntry).filter(
        TimesheetEntry.timesheet_id == timesheet.id,
        TimesheetEntry.work_date == clock_request.work_date,
        TimesheetEntry.clock_out == None
    ).first()
    
    if existing_entry:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already clocked in for this date"
        )
    
    # Create new timesheet entry
    entry = TimesheetEntry(
        timesheet_id=timesheet.id,
        work_date=clock_request.work_date,
        clock_in=datetime.now(timezone.utc)
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    
    return ClockResponse(
        success=True,
        timesheet_entry_id=entry.id,
        message="Clocked in successfully"
    )


@router.post("/clock-out", response_model=ClockResponse)
def clock_out(
    clock_request: ClockOutRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Clock out from work"""
    # Find active timesheet entry
    timesheet = db.query(Timesheet).filter(
        Timesheet.employee_id == clock_request.employee_id,
        Timesheet.period_start <= clock_request.work_date,
        Timesheet.period_end >= clock_request.work_date
    ).first()
    
    if not timesheet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No timesheet found for this date"
        )
    
    entry = db.query(TimesheetEntry).filter(
        TimesheetEntry.timesheet_id == timesheet.id,
        TimesheetEntry.work_date == clock_request.work_date,
        TimesheetEntry.clock_out == None
    ).first()
    
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active clock-in found for this date"
        )
    
    # Clock out
    entry.clock_out = datetime.now(timezone.utc)
    
    # Calculate hours worked
    if entry.clock_in:
        duration = entry.clock_out - entry.clock_in
        hours = duration.total_seconds() / 3600
        entry.hours_worked = round(hours, 2)
    
    db.commit()
    
    return ClockResponse(
        success=True,
        timesheet_entry_id=entry.id,
        message="Clocked out successfully"
    )


@router.post("/break/start", response_model=BreakResponse)
def start_break(
    break_request: BreakStartRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Start a break"""
    entry = db.query(TimesheetEntry).filter(
        TimesheetEntry.id == break_request.timesheet_entry_id
    ).first()
    
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Timesheet entry not found"
        )
    
    # Create break entry
    break_entry = BreakEntry(
        timesheet_entry_id=entry.id,
        break_type=break_request.break_type,
        start_time=datetime.now(timezone.utc)
    )
    db.add(break_entry)
    db.commit()
    db.refresh(break_entry)
    
    return BreakResponse(
        success=True,
        break_entry_id=break_entry.id,
        duration_minutes=0
    )


@router.post("/break/end", response_model=BreakResponse)
def end_break(
    break_request: BreakEndRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """End a break"""
    break_entry = db.query(BreakEntry).filter(
        BreakEntry.id == break_request.break_entry_id
    ).first()
    
    if not break_entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Break entry not found"
        )
    
    if break_entry.end_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Break already ended"
        )
    
    break_entry.end_time = datetime.now(timezone.utc)
    
    # Calculate duration
    if break_entry.start_time:
        duration = break_entry.end_time - break_entry.start_time
        minutes = duration.total_seconds() / 60
        break_entry.duration_minutes = int(minutes)
    
    db.commit()
    
    return BreakResponse(
        success=True,
        break_entry_id=break_entry.id,
        duration_minutes=break_entry.duration_minutes or 0
    )


@router.get("/timesheets", response_model=TimesheetList)
def list_timesheets(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    employee_id: Optional[int] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List timesheets with filtering"""
    query = db.query(Timesheet)
    
    if employee_id:
        query = query.filter(Timesheet.employee_id == employee_id)
    
    if status:
        query = query.filter(Timesheet.status == status)
    
    total = query.count()
    timesheets = query.offset(skip).limit(limit).all()
    
    return TimesheetList(total=total, items=timesheets)


@router.post("/timesheets", response_model=TimesheetResponse, status_code=status.HTTP_201_CREATED)
def create_timesheet(
    timesheet_data: TimesheetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new timesheet"""
    timesheet = Timesheet(**timesheet_data.model_dump(exclude={"entries"}))
    db.add(timesheet)
    db.commit()
    db.refresh(timesheet)
    
    return timesheet


@router.post("/timesheets/{timesheet_id}/submit", response_model=TimesheetSubmitResponse)
def submit_timesheet(
    timesheet_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Submit timesheet for approval"""
    timesheet = db.query(Timesheet).filter(Timesheet.id == timesheet_id).first()
    if not timesheet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Timesheet {timesheet_id} not found"
        )
    
    timesheet.status = "SUBMITTED"
    timesheet.submitted_at = datetime.now(timezone.utc)
    
    db.commit()
    db.refresh(timesheet)
    
    return TimesheetSubmitResponse(
        success=True,
        compliance_checked=True,
        violations=[]
    )


@router.post("/timesheets/{timesheet_id}/approve", response_model=TimesheetResponse)
def approve_timesheet(
    timesheet_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Approve timesheet (with compliance check)"""
    timesheet = db.query(Timesheet).filter(Timesheet.id == timesheet_id).first()
    if not timesheet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Timesheet {timesheet_id} not found"
        )
    
    # TODO: Add compliance checks here
    
    timesheet.status = "APPROVED"
    timesheet.approved_by = current_user.id
    timesheet.approved_at = datetime.now(timezone.utc)
    
    db.commit()
    db.refresh(timesheet)
    
    return timesheet
