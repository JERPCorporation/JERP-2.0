"""
JERP 2.0 - HR API Endpoints
Employee, Department, and Position management
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.hr import Employee, Department, Position
from app.schemas.hr import (
    EmployeeCreate, EmployeeUpdate, EmployeeResponse, EmployeeList,
    DepartmentCreate, DepartmentUpdate, DepartmentResponse, DepartmentList,
    PositionCreate, PositionUpdate, PositionResponse, PositionList
)

router = APIRouter()


# Employee Endpoints
@router.get("/employees", response_model=EmployeeList)
def list_employees(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    department_id: Optional[int] = None,
    employment_status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List employees with pagination and filtering"""
    query = db.query(Employee)
    
    if department_id:
        query = query.filter(Employee.department_id == department_id)
    
    if employment_status:
        query = query.filter(Employee.employment_status == employment_status)
    
    total = query.count()
    employees = query.offset(skip).limit(limit).all()
    
    return EmployeeList(total=total, items=employees)


@router.post("/employees", response_model=EmployeeResponse, status_code=status.HTTP_201_CREATED)
def create_employee(
    employee_data: EmployeeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new employee"""
    # Check if employee number already exists
    existing = db.query(Employee).filter(Employee.employee_number == employee_data.employee_number).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Employee number {employee_data.employee_number} already exists"
        )
    
    # Check if email already exists
    existing_email = db.query(Employee).filter(Employee.email == employee_data.email).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Email {employee_data.email} already exists"
        )
    
    employee = Employee(**employee_data.model_dump())
    db.add(employee)
    db.commit()
    db.refresh(employee)
    
    return employee


@router.get("/employees/{employee_id}", response_model=EmployeeResponse)
def get_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get employee details"""
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Employee {employee_id} not found"
        )
    
    return employee


@router.put("/employees/{employee_id}", response_model=EmployeeResponse)
def update_employee(
    employee_id: int,
    employee_data: EmployeeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update employee"""
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Employee {employee_id} not found"
        )
    
    # Update fields
    update_data = employee_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(employee, field, value)
    
    db.commit()
    db.refresh(employee)
    
    return employee


@router.delete("/employees/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Soft delete employee (set to TERMINATED)"""
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Employee {employee_id} not found"
        )
    
    employee.employment_status = "TERMINATED"
    db.commit()
    
    return None


@router.get("/employees/{employee_id}/subordinates", response_model=EmployeeList)
def get_subordinates(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get direct reports for an employee"""
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Employee {employee_id} not found"
        )
    
    subordinates = db.query(Employee).filter(Employee.manager_id == employee_id).all()
    
    return EmployeeList(total=len(subordinates), items=subordinates)


# Department Endpoints
@router.get("/departments", response_model=DepartmentList)
def list_departments(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List departments with pagination"""
    query = db.query(Department)
    
    if is_active is not None:
        query = query.filter(Department.is_active == is_active)
    
    total = query.count()
    departments = query.offset(skip).limit(limit).all()
    
    return DepartmentList(total=total, items=departments)


@router.post("/departments", response_model=DepartmentResponse, status_code=status.HTTP_201_CREATED)
def create_department(
    department_data: DepartmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new department"""
    # Check if code already exists
    existing = db.query(Department).filter(Department.code == department_data.code).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Department code {department_data.code} already exists"
        )
    
    department = Department(**department_data.model_dump())
    db.add(department)
    db.commit()
    db.refresh(department)
    
    return department


# Position Endpoints
@router.get("/positions", response_model=PositionList)
def list_positions(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    department_id: Optional[int] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List positions with pagination"""
    query = db.query(Position)
    
    if department_id:
        query = query.filter(Position.department_id == department_id)
    
    if is_active is not None:
        query = query.filter(Position.is_active == is_active)
    
    total = query.count()
    positions = query.offset(skip).limit(limit).all()
    
    return PositionList(total=total, items=positions)


@router.post("/positions", response_model=PositionResponse, status_code=status.HTTP_201_CREATED)
def create_position(
    position_data: PositionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new position"""
    # Check if code already exists
    existing = db.query(Position).filter(Position.code == position_data.code).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Position code {position_data.code} already exists"
        )
    
    position = Position(**position_data.model_dump())
    db.add(position)
    db.commit()
    db.refresh(position)
    
    return position
