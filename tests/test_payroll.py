"""
Tests for Payroll Service
"""
import pytest
from decimal import Decimal
from datetime import date, datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from fastapi import HTTPException

from app.core.database import Base
from app.models.user import User
from app.models.role import Role
from app.models.hr import Employee, Department, Position, EmploymentStatus, EmploymentType
from app.models.payroll import PayPeriod, Payslip, PayPeriodStatus, PayPeriodType, PayslipStatus
from app.schemas.payroll import PayPeriodCreate, PayslipCalculation
from app.services.payroll_service import (
    create_pay_period,
    calculate_payslip,
    approve_payslip,
    process_pay_period,
    approve_pay_period,
    get_payroll_summary
)


# Test database setup
TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="function")
def db_session():
    """Create a test database session"""
    # Each test gets a fresh in-memory database
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    
    yield session
    
    session.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def test_role(db_session: Session):
    """Create a test role"""
    role = Role(
        name="Admin",
        description="Test admin role",
        is_active=True
    )
    db_session.add(role)
    db_session.commit()
    db_session.refresh(role)
    return role


@pytest.fixture
def test_user(db_session: Session, test_role: Role):
    """Create a test user"""
    user = User(
        email="test@example.com",
        hashed_password="hashed_password",
        full_name="Test User",
        is_active=True,
        role_id=test_role.id
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_department(db_session: Session):
    """Create a test department"""
    dept = Department(
        name="Engineering",
        description="Engineering Department",
        is_active=True
    )
    db_session.add(dept)
    db_session.commit()
    db_session.refresh(dept)
    return dept


@pytest.fixture
def test_position_exempt(db_session: Session, test_department: Department):
    """Create an exempt position (salaried)"""
    position = Position(
        title="Software Engineer",
        department_id=test_department.id,
        is_exempt=True,
        is_active=True
    )
    db_session.add(position)
    db_session.commit()
    db_session.refresh(position)
    return position


@pytest.fixture
def test_position_nonexempt(db_session: Session, test_department: Department):
    """Create a non-exempt position (hourly)"""
    position = Position(
        title="Junior Developer",
        department_id=test_department.id,
        is_exempt=False,
        is_active=True
    )
    db_session.add(position)
    db_session.commit()
    db_session.refresh(position)
    return position


@pytest.fixture
def salaried_employee(db_session: Session, test_department: Department, test_position_exempt: Position):
    """Create a salaried employee"""
    employee = Employee(
        employee_number="EMP001",
        first_name="John",
        last_name="Doe",
        email="john.doe@example.com",
        hire_date=date.today() - timedelta(days=365),
        status=EmploymentStatus.ACTIVE,
        employment_type=EmploymentType.FULL_TIME,
        position_id=test_position_exempt.id,
        department_id=test_department.id,
        salary=Decimal("60000.00")  # Annual salary
    )
    db_session.add(employee)
    db_session.commit()
    db_session.refresh(employee)
    return employee


@pytest.fixture
def hourly_employee(db_session: Session, test_department: Department, test_position_nonexempt: Position):
    """Create an hourly employee"""
    employee = Employee(
        employee_number="EMP002",
        first_name="Jane",
        last_name="Smith",
        email="jane.smith@example.com",
        hire_date=date.today() - timedelta(days=180),
        status=EmploymentStatus.ACTIVE,
        employment_type=EmploymentType.FULL_TIME,
        position_id=test_position_nonexempt.id,
        department_id=test_department.id,
        hourly_rate=Decimal("25.00")
    )
    db_session.add(employee)
    db_session.commit()
    db_session.refresh(employee)
    return employee


class TestPayPeriodCreation:
    """Test pay period creation and validation"""
    
    @pytest.mark.asyncio
    async def test_create_pay_period_success(self, db_session: Session, test_user: User):
        """Test successful pay period creation"""
        period_data = PayPeriodCreate(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 15),
            pay_date=date(2024, 1, 20),
            period_type=PayPeriodType.BI_WEEKLY
        )
        
        pay_period = await create_pay_period(db_session, period_data, test_user)
        
        assert pay_period.id is not None
        assert pay_period.status == PayPeriodStatus.OPEN
        assert pay_period.start_date == date(2024, 1, 1)
        assert pay_period.end_date == date(2024, 1, 15)
    
    @pytest.mark.asyncio
    async def test_create_pay_period_invalid_dates(self, db_session: Session, test_user: User):
        """Test pay period with invalid dates (start >= end)"""
        period_data = PayPeriodCreate(
            start_date=date(2024, 1, 15),
            end_date=date(2024, 1, 1),
            pay_date=date(2024, 1, 20),
            period_type=PayPeriodType.BI_WEEKLY
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await create_pay_period(db_session, period_data, test_user)
        
        assert exc_info.value.status_code == 400
        assert "before end date" in str(exc_info.value.detail)


class TestSalariedEmployeePayslip:
    """Test payslip calculation for salaried employees"""
    
    @pytest.mark.asyncio
    async def test_calculate_monthly_salary(
        self, db_session: Session, test_user: User, salaried_employee: Employee
    ):
        """Test monthly salary calculation"""
        # Create pay period
        period_data = PayPeriodCreate(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
            pay_date=date(2024, 2, 5),
            period_type=PayPeriodType.MONTHLY
        )
        pay_period = await create_pay_period(db_session, period_data, test_user)
        
        # Calculate payslip
        calc_data = PayslipCalculation(
            employee_id=salaried_employee.id,
            pay_period_id=pay_period.id
        )
        
        payslip = await calculate_payslip(db_session, calc_data, test_user)
        
        # For monthly pay period, annual salary / 12
        expected_gross = Decimal("60000.00") / 12
        assert payslip.gross_pay == expected_gross
        assert payslip.status == PayslipStatus.CALCULATED
        assert payslip.regular_hours == Decimal("0")  # Salaried don't track hours
        assert payslip.overtime_hours == Decimal("0")
        assert payslip.net_pay < payslip.gross_pay  # After deductions
    
    @pytest.mark.asyncio
    async def test_calculate_biweekly_salary(
        self, db_session: Session, test_user: User, salaried_employee: Employee
    ):
        """Test bi-weekly salary calculation"""
        period_data = PayPeriodCreate(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 14),
            pay_date=date(2024, 1, 20),
            period_type=PayPeriodType.BI_WEEKLY
        )
        pay_period = await create_pay_period(db_session, period_data, test_user)
        
        calc_data = PayslipCalculation(
            employee_id=salaried_employee.id,
            pay_period_id=pay_period.id
        )
        
        payslip = await calculate_payslip(db_session, calc_data, test_user)
        
        # For bi-weekly pay period, annual salary / 26
        expected_gross = Decimal("60000.00") / 26
        assert payslip.gross_pay == expected_gross


class TestHourlyEmployeePayslip:
    """Test payslip calculation for hourly employees"""
    
    @pytest.mark.asyncio
    async def test_calculate_regular_hours_only(
        self, db_session: Session, test_user: User, hourly_employee: Employee
    ):
        """Test hourly payslip with regular hours only"""
        period_data = PayPeriodCreate(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 7),
            pay_date=date(2024, 1, 12),
            period_type=PayPeriodType.WEEKLY
        )
        pay_period = await create_pay_period(db_session, period_data, test_user)
        
        calc_data = PayslipCalculation(
            employee_id=hourly_employee.id,
            pay_period_id=pay_period.id,
            regular_hours=Decimal("40.00"),
            overtime_hours=Decimal("0")
        )
        
        payslip = await calculate_payslip(db_session, calc_data, test_user)
        
        # Regular pay: 40 * 25 = 1000
        assert payslip.regular_hours == Decimal("40.00")
        assert payslip.overtime_hours == Decimal("0")
        assert payslip.regular_pay == Decimal("1000.00")
        assert payslip.overtime_pay == Decimal("0")
        assert payslip.gross_pay == Decimal("1000.00")
    
    @pytest.mark.asyncio
    async def test_calculate_with_overtime(
        self, db_session: Session, test_user: User, hourly_employee: Employee
    ):
        """Test hourly payslip with FLSA overtime (1.5x rate)"""
        period_data = PayPeriodCreate(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 7),
            pay_date=date(2024, 1, 12),
            period_type=PayPeriodType.WEEKLY
        )
        pay_period = await create_pay_period(db_session, period_data, test_user)
        
        calc_data = PayslipCalculation(
            employee_id=hourly_employee.id,
            pay_period_id=pay_period.id,
            regular_hours=Decimal("40.00"),
            overtime_hours=Decimal("10.00")  # 10 hours overtime
        )
        
        payslip = await calculate_payslip(db_session, calc_data, test_user)
        
        # Regular pay: 40 * 25 = 1000
        # Overtime pay: 10 * 25 * 1.5 = 375
        # Total gross: 1375
        assert payslip.regular_pay == Decimal("1000.00")
        assert payslip.overtime_pay == Decimal("375.00")
        assert payslip.gross_pay == Decimal("1375.00")
    
    @pytest.mark.asyncio
    async def test_calculate_with_bonus_and_commission(
        self, db_session: Session, test_user: User, hourly_employee: Employee
    ):
        """Test hourly payslip with bonus and commission"""
        period_data = PayPeriodCreate(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 7),
            pay_date=date(2024, 1, 12),
            period_type=PayPeriodType.WEEKLY
        )
        pay_period = await create_pay_period(db_session, period_data, test_user)
        
        calc_data = PayslipCalculation(
            employee_id=hourly_employee.id,
            pay_period_id=pay_period.id,
            regular_hours=Decimal("40.00"),
            overtime_hours=Decimal("0"),
            bonus=Decimal("500.00"),
            commission=Decimal("250.00")
        )
        
        payslip = await calculate_payslip(db_session, calc_data, test_user)
        
        # Regular pay: 1000
        # Bonus: 500
        # Commission: 250
        # Total: 1750
        assert payslip.bonus == Decimal("500.00")
        assert payslip.commission == Decimal("250.00")
        assert payslip.gross_pay == Decimal("1750.00")


class TestPayslipDeductions:
    """Test payslip tax and deduction calculations"""
    
    @pytest.mark.asyncio
    async def test_standard_deductions(
        self, db_session: Session, test_user: User, hourly_employee: Employee
    ):
        """Test standard tax deductions"""
        period_data = PayPeriodCreate(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 7),
            pay_date=date(2024, 1, 12),
            period_type=PayPeriodType.WEEKLY
        )
        pay_period = await create_pay_period(db_session, period_data, test_user)
        
        calc_data = PayslipCalculation(
            employee_id=hourly_employee.id,
            pay_period_id=pay_period.id,
            regular_hours=Decimal("40.00")
        )
        
        payslip = await calculate_payslip(db_session, calc_data, test_user)
        
        gross = Decimal("1000.00")
        
        # Verify tax calculations
        # Federal tax: 15%
        assert payslip.federal_tax == gross * Decimal("0.15")
        
        # State tax: 5%
        assert payslip.state_tax == gross * Decimal("0.05")
        
        # Social Security: 6.2%
        assert payslip.social_security == gross * Decimal("0.062")
        
        # Medicare: 1.45%
        assert payslip.medicare == gross * Decimal("0.0145")
        
        # Verify total deductions
        total_tax = (
            payslip.federal_tax + payslip.state_tax +
            payslip.social_security + payslip.medicare
        )
        assert payslip.total_deductions == total_tax
        
        # Verify net pay
        assert payslip.net_pay == gross - payslip.total_deductions
    
    @pytest.mark.asyncio
    async def test_custom_deductions(
        self, db_session: Session, test_user: User, hourly_employee: Employee
    ):
        """Test custom deductions (health insurance, 401k, etc.)"""
        period_data = PayPeriodCreate(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 7),
            pay_date=date(2024, 1, 12),
            period_type=PayPeriodType.WEEKLY
        )
        pay_period = await create_pay_period(db_session, period_data, test_user)
        
        calc_data = PayslipCalculation(
            employee_id=hourly_employee.id,
            pay_period_id=pay_period.id,
            regular_hours=Decimal("40.00"),
            health_insurance=Decimal("100.00"),
            retirement_401k=Decimal("50.00"),
            other_deductions=Decimal("25.00")
        )
        
        payslip = await calculate_payslip(db_session, calc_data, test_user)
        
        assert payslip.health_insurance == Decimal("100.00")
        assert payslip.retirement_401k == Decimal("50.00")
        assert payslip.other_deductions == Decimal("25.00")
        
        # Total deductions should include taxes + custom deductions
        custom_deductions = Decimal("175.00")
        assert payslip.total_deductions > custom_deductions


class TestPayslipApproval:
    """Test payslip approval workflow"""
    
    @pytest.mark.asyncio
    async def test_approve_payslip(
        self, db_session: Session, test_user: User, hourly_employee: Employee
    ):
        """Test approving a calculated payslip"""
        # Create and calculate payslip
        period_data = PayPeriodCreate(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 7),
            pay_date=date(2024, 1, 12),
            period_type=PayPeriodType.WEEKLY
        )
        pay_period = await create_pay_period(db_session, period_data, test_user)
        
        calc_data = PayslipCalculation(
            employee_id=hourly_employee.id,
            pay_period_id=pay_period.id,
            regular_hours=Decimal("40.00")
        )
        
        payslip = await calculate_payslip(db_session, calc_data, test_user)
        assert payslip.status == PayslipStatus.CALCULATED
        
        # Approve it
        approved_payslip = await approve_payslip(db_session, payslip.id, test_user)
        
        assert approved_payslip.status == PayslipStatus.APPROVED
    
    @pytest.mark.asyncio
    async def test_cannot_approve_voided_payslip(
        self, db_session: Session, test_user: User, hourly_employee: Employee
    ):
        """Test that voided payslips cannot be approved"""
        period_data = PayPeriodCreate(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 7),
            pay_date=date(2024, 1, 12),
            period_type=PayPeriodType.WEEKLY
        )
        pay_period = await create_pay_period(db_session, period_data, test_user)
        
        calc_data = PayslipCalculation(
            employee_id=hourly_employee.id,
            pay_period_id=pay_period.id,
            regular_hours=Decimal("40.00")
        )
        
        payslip = await calculate_payslip(db_session, calc_data, test_user)
        
        # Manually void it
        payslip.status = PayslipStatus.VOIDED
        db_session.commit()
        
        # Try to approve
        with pytest.raises(HTTPException) as exc_info:
            await approve_payslip(db_session, payslip.id, test_user)
        
        assert exc_info.value.status_code == 400
        assert "voided" in str(exc_info.value.detail).lower()


class TestPayPeriodProcessing:
    """Test pay period processing workflow"""
    
    @pytest.mark.asyncio
    async def test_process_pay_period(
        self, db_session: Session, test_user: User,
        salaried_employee: Employee, hourly_employee: Employee
    ):
        """Test processing a pay period (auto-calculate all payslips)"""
        period_data = PayPeriodCreate(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 15),
            pay_date=date(2024, 1, 20),
            period_type=PayPeriodType.BI_WEEKLY
        )
        pay_period = await create_pay_period(db_session, period_data, test_user)
        
        # Process the pay period
        processed_period = await process_pay_period(db_session, pay_period.id, test_user)
        
        assert processed_period.status == PayPeriodStatus.PROCESSING
        assert processed_period.processed_by == test_user.id
        assert processed_period.processed_at is not None
        
        # Verify payslips were created
        payslips = db_session.query(Payslip).filter(
            Payslip.pay_period_id == pay_period.id
        ).all()
        
        # Should have created payslips for both employees
        assert len(payslips) == 2
    
    @pytest.mark.asyncio
    async def test_approve_pay_period(
        self, db_session: Session, test_user: User,
        salaried_employee: Employee, hourly_employee: Employee
    ):
        """Test approving a pay period (approves all payslips)"""
        period_data = PayPeriodCreate(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 15),
            pay_date=date(2024, 1, 20),
            period_type=PayPeriodType.BI_WEEKLY
        )
        pay_period = await create_pay_period(db_session, period_data, test_user)
        
        # Process then approve
        await process_pay_period(db_session, pay_period.id, test_user)
        approved_period = await approve_pay_period(db_session, pay_period.id, test_user)
        
        assert approved_period.status == PayPeriodStatus.APPROVED
        assert approved_period.approved_by == test_user.id
        assert approved_period.approved_at is not None
        
        # Verify all payslips are approved
        payslips = db_session.query(Payslip).filter(
            Payslip.pay_period_id == pay_period.id
        ).all()
        
        for payslip in payslips:
            assert payslip.status == PayslipStatus.APPROVED


class TestPayrollSummary:
    """Test payroll summary and aggregations"""
    
    @pytest.mark.asyncio
    async def test_payroll_summary_for_period(
        self, db_session: Session, test_user: User,
        salaried_employee: Employee, hourly_employee: Employee
    ):
        """Test getting payroll summary for a pay period"""
        period_data = PayPeriodCreate(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 15),
            pay_date=date(2024, 1, 20),
            period_type=PayPeriodType.BI_WEEKLY
        )
        pay_period = await create_pay_period(db_session, period_data, test_user)
        
        # Process the period
        await process_pay_period(db_session, pay_period.id, test_user)
        
        # Get summary
        summary = await get_payroll_summary(db_session, pay_period_id=pay_period.id)
        
        assert summary.total_employees == 2
        assert summary.total_payslips == 2
        assert summary.total_gross_pay > 0
        assert summary.total_net_pay > 0
        assert summary.total_deductions > 0
        assert summary.by_status is not None
        assert summary.by_department is not None


class TestValidations:
    """Test payroll validations and error handling"""
    
    @pytest.mark.asyncio
    async def test_employee_without_compensation(
        self, db_session: Session, test_user: User, test_department: Department,
        test_position_exempt: Position
    ):
        """Test that employee without salary or hourly_rate fails"""
        # Create employee without compensation
        employee = Employee(
            employee_number="EMP999",
            first_name="No",
            last_name="Compensation",
            email="no.comp@example.com",
            hire_date=date.today(),
            status=EmploymentStatus.ACTIVE,
            employment_type=EmploymentType.FULL_TIME,
            position_id=test_position_exempt.id,
            department_id=test_department.id
            # No salary or hourly_rate set
        )
        db_session.add(employee)
        db_session.commit()
        
        period_data = PayPeriodCreate(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 7),
            pay_date=date(2024, 1, 12),
            period_type=PayPeriodType.WEEKLY
        )
        pay_period = await create_pay_period(db_session, period_data, test_user)
        
        calc_data = PayslipCalculation(
            employee_id=employee.id,
            pay_period_id=pay_period.id
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await calculate_payslip(db_session, calc_data, test_user)
        
        assert exc_info.value.status_code == 400
        assert "salary or hourly_rate" in str(exc_info.value.detail).lower()
    
    @pytest.mark.asyncio
    async def test_duplicate_payslip_prevention(
        self, db_session: Session, test_user: User, hourly_employee: Employee
    ):
        """Test that duplicate payslips for same employee/period are prevented"""
        period_data = PayPeriodCreate(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 7),
            pay_date=date(2024, 1, 12),
            period_type=PayPeriodType.WEEKLY
        )
        pay_period = await create_pay_period(db_session, period_data, test_user)
        
        calc_data = PayslipCalculation(
            employee_id=hourly_employee.id,
            pay_period_id=pay_period.id,
            regular_hours=Decimal("40.00")
        )
        
        # Create first payslip
        await calculate_payslip(db_session, calc_data, test_user)
        
        # Try to create duplicate
        with pytest.raises(HTTPException) as exc_info:
            await calculate_payslip(db_session, calc_data, test_user)
        
        assert exc_info.value.status_code == 400
        assert "already exists" in str(exc_info.value.detail).lower()
