"""
Tests for FLSA Compliance Engine
"""
import pytest
from decimal import Decimal
from datetime import date

from app.compliance.labor.flsa import (
    FLSA,
    EmployeeClassification,
    ExemptionType,
    FLSAOvertimeCalculation,
    ChildLaborViolation,
)


@pytest.fixture
def flsa_engine():
    """Fixture to create FLSA engine"""
    return FLSA()


class TestWeeklyOvertime:
    """Test FLSA weekly overtime calculations"""
    
    def test_no_overtime(self, flsa_engine):
        """Test week with 40 hours or less"""
        result = flsa_engine.calculate_weekly_overtime(
            hours_worked=Decimal("40.0"),
            regular_rate=Decimal("15.00")
        )
        
        assert result.regular_hours == Decimal("40.0")
        assert result.overtime_hours == Decimal("0")
        assert result.total_pay == Decimal("600.00")
    
    def test_with_overtime(self, flsa_engine):
        """Test week with overtime (>40 hours)"""
        result = flsa_engine.calculate_weekly_overtime(
            hours_worked=Decimal("50.0"),
            regular_rate=Decimal("15.00")
        )
        
        assert result.regular_hours == Decimal("40.0")
        assert result.overtime_hours == Decimal("10.0")
        assert result.regular_pay == Decimal("600.00")
        assert result.overtime_pay == Decimal("225.00")  # 10 * 15 * 1.5
        assert result.total_pay == Decimal("825.00")


class TestMinimumWage:
    """Test FLSA minimum wage validation"""
    
    def test_above_federal_minimum(self, flsa_engine):
        """Test hourly rate above federal minimum"""
        is_valid, message = flsa_engine.validate_minimum_wage(Decimal("10.00"))
        
        assert is_valid is True
        assert message is None
    
    def test_below_federal_minimum(self, flsa_engine):
        """Test hourly rate below federal minimum"""
        is_valid, message = flsa_engine.validate_minimum_wage(Decimal("5.00"))
        
        assert is_valid is False
        assert "minimum wage" in message.lower()
    
    def test_state_minimum_higher(self, flsa_engine):
        """Test state minimum wage higher than federal"""
        is_valid, message = flsa_engine.validate_minimum_wage(
            hourly_rate=Decimal("10.00"),
            state_minimum_wage=Decimal("15.00")
        )
        
        assert is_valid is False
        assert "state" in message.lower()


class TestExemptClassification:
    """Test FLSA exempt employee classification"""
    
    def test_exempt_executive(self, flsa_engine):
        """Test valid executive exemption"""
        is_exempt, reason = flsa_engine.check_exempt_classification(
            job_title="Director of Operations",
            weekly_salary=Decimal("1000.00"),
            annual_salary=Decimal("52000.00"),
            job_duties=["Manage team", "Supervise employees", "Director-level decisions"],
            exemption_type=ExemptionType.EXECUTIVE
        )
        
        assert is_exempt is True
        assert reason is None
    
    def test_below_salary_threshold(self, flsa_engine):
        """Test exemption fails due to low salary"""
        is_exempt, reason = flsa_engine.check_exempt_classification(
            job_title="Manager",
            weekly_salary=Decimal("500.00"),
            annual_salary=Decimal("26000.00"),
            job_duties=["Manage team"],
            exemption_type=ExemptionType.EXECUTIVE
        )
        
        assert is_exempt is False
        assert "salary" in reason.lower()
    
    def test_highly_compensated(self, flsa_engine):
        """Test highly compensated exemption"""
        is_exempt, reason = flsa_engine.check_exempt_classification(
            job_title="Senior Engineer",
            weekly_salary=Decimal("2500.00"),
            annual_salary=Decimal("130000.00"),
            job_duties=["Engineering work"],
            exemption_type=ExemptionType.HIGHLY_COMPENSATED
        )
        
        assert is_exempt is True


class TestChildLabor:
    """Test FLSA child labor compliance"""
    
    def test_below_minimum_age(self, flsa_engine):
        """Test employee below minimum working age"""
        violations = flsa_engine.check_child_labor_compliance(
            employee_age=12,
            hours_worked=Decimal("8.0"),
            work_date=date.today(),
            is_school_day=False,
            is_school_week=False,
            is_hazardous_work=False
        )
        
        assert len(violations) == 1
        assert violations[0].severity == "CRITICAL"
        assert "minimum work age" in violations[0].violation_description.lower()
    
    def test_hazardous_work_under_18(self, flsa_engine):
        """Test minor performing hazardous work"""
        violations = flsa_engine.check_child_labor_compliance(
            employee_age=16,
            hours_worked=Decimal("8.0"),
            work_date=date.today(),
            is_school_day=False,
            is_school_week=False,
            is_hazardous_work=True
        )
        
        assert len(violations) == 1
        assert "hazardous" in violations[0].violation_description.lower()
    
    def test_school_day_hours_exceeded(self, flsa_engine):
        """Test 14-15 year old exceeding school day hours"""
        violations = flsa_engine.check_child_labor_compliance(
            employee_age=15,
            hours_worked=Decimal("5.0"),
            work_date=date.today(),
            is_school_day=True,
            is_school_week=True,
            is_hazardous_work=False
        )
        
        assert len(violations) >= 1
        assert any("school day" in v.violation_description.lower() for v in violations)
    
    def test_non_school_day_hours_exceeded(self, flsa_engine):
        """Test 14-15 year old exceeding non-school day hours"""
        violations = flsa_engine.check_child_labor_compliance(
            employee_age=15,
            hours_worked=Decimal("10.0"),
            work_date=date.today(),
            is_school_day=False,
            is_school_week=False,
            is_hazardous_work=False
        )
        
        assert len(violations) >= 1
    
    def test_age_16_17_no_hour_restrictions(self, flsa_engine):
        """Test 16-17 year old has no hour restrictions (non-hazardous)"""
        violations = flsa_engine.check_child_labor_compliance(
            employee_age=17,
            hours_worked=Decimal("10.0"),
            work_date=date.today(),
            is_school_day=False,
            is_school_week=False,
            is_hazardous_work=False
        )
        
        # Should have no violations (16-17 can work any hours if not hazardous)
        assert len(violations) == 0


class TestRecordKeeping:
    """Test FLSA record keeping requirements"""
    
    def test_all_records_present(self, flsa_engine):
        """Test compliant record keeping"""
        missing = flsa_engine.check_record_keeping_requirements(
            employee_id=1,
            has_name=True,
            has_address=True,
            has_ssn=True,
            has_birth_date=True,
            has_occupation=True,
            has_hourly_rate=True,
            has_hours_worked_records=True,
            has_wages_paid_records=True
        )
        
        assert len(missing) == 0
    
    def test_missing_records(self, flsa_engine):
        """Test non-compliant record keeping"""
        missing = flsa_engine.check_record_keeping_requirements(
            employee_id=1,
            has_name=True,
            has_address=False,
            has_ssn=False,
            has_birth_date=True,
            has_occupation=True,
            has_hourly_rate=True,
            has_hours_worked_records=False,
            has_wages_paid_records=True
        )
        
        assert len(missing) == 3
        assert "address" in " ".join(missing).lower()
        assert "social security" in " ".join(missing).lower()
        assert "hours worked" in " ".join(missing).lower()


class TestCompensatoryTime:
    """Test FLSA compensatory time (public sector)"""
    
    def test_comp_time_public_sector(self, flsa_engine):
        """Test comp time calculation for public sector"""
        comp_hours, error = flsa_engine.calculate_compensatory_time(
            overtime_hours=Decimal("10.0"),
            is_public_sector=True
        )
        
        assert comp_hours == Decimal("15.0")  # 10 * 1.5
        assert error is None
    
    def test_comp_time_private_sector(self, flsa_engine):
        """Test comp time not allowed for private sector"""
        comp_hours, error = flsa_engine.calculate_compensatory_time(
            overtime_hours=Decimal("10.0"),
            is_public_sector=False
        )
        
        assert comp_hours == Decimal("0")
        assert "public sector" in error.lower()


class TestSalaryBasis:
    """Test FLSA salary basis test"""
    
    def test_valid_salary_basis(self, flsa_engine):
        """Test valid salary basis"""
        is_valid, message = flsa_engine.validate_salary_basis(
            pay_type="salary",
            guaranteed_weekly_amount=Decimal("1000.00")
        )
        
        assert is_valid is True
        assert message is None
    
    def test_hourly_pay_type(self, flsa_engine):
        """Test hourly pay type fails salary basis"""
        is_valid, message = flsa_engine.validate_salary_basis(
            pay_type="hourly",
            guaranteed_weekly_amount=Decimal("1000.00")
        )
        
        assert is_valid is False
        assert "salary basis" in message.lower()
    
    def test_below_threshold(self, flsa_engine):
        """Test salary below threshold"""
        is_valid, message = flsa_engine.validate_salary_basis(
            pay_type="salary",
            guaranteed_weekly_amount=Decimal("500.00")
        )
        
        assert is_valid is False
        assert "threshold" in message.lower()
