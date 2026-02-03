"""
Tests for California Labor Code Compliance Engine
"""
import pytest
from decimal import Decimal
from datetime import date, timedelta

from app.compliance.labor.california import (
    CaliforniaLaborCode,
    WorkDay,
    OvertimeCalculation,
    BreakViolation,
)


@pytest.fixture
def ca_engine():
    """Fixture to create California Labor Code engine"""
    return CaliforniaLaborCode()


class TestDailyOvertime:
    """Test daily overtime calculations"""
    
    def test_regular_hours_only(self, ca_engine):
        """Test calculation with only regular hours (<=8)"""
        result = ca_engine.calculate_daily_overtime(
            hours_worked=Decimal("8.0"),
            regular_rate=Decimal("20.00"),
            is_seventh_day=False
        )
        
        assert result.regular_hours == Decimal("8.0")
        assert result.overtime_1_5x_hours == Decimal("0")
        assert result.overtime_2x_hours == Decimal("0")
        assert result.total_pay == Decimal("160.00")
    
    def test_daily_overtime_1_5x(self, ca_engine):
        """Test daily overtime at 1.5x rate (8-12 hours)"""
        result = ca_engine.calculate_daily_overtime(
            hours_worked=Decimal("10.0"),
            regular_rate=Decimal("20.00"),
            is_seventh_day=False
        )
        
        assert result.regular_hours == Decimal("8.0")
        assert result.overtime_1_5x_hours == Decimal("2.0")
        assert result.overtime_2x_hours == Decimal("0")
        assert result.regular_pay == Decimal("160.00")
        assert result.overtime_1_5x_pay == Decimal("60.00")  # 2 * 20 * 1.5
        assert result.total_pay == Decimal("220.00")
    
    def test_daily_overtime_2x(self, ca_engine):
        """Test daily overtime at 2x rate (>12 hours)"""
        result = ca_engine.calculate_daily_overtime(
            hours_worked=Decimal("14.0"),
            regular_rate=Decimal("20.00"),
            is_seventh_day=False
        )
        
        assert result.regular_hours == Decimal("8.0")
        assert result.overtime_1_5x_hours == Decimal("4.0")  # Hours 9-12
        assert result.overtime_2x_hours == Decimal("2.0")    # Hours 13-14
        assert result.regular_pay == Decimal("160.00")
        assert result.overtime_1_5x_pay == Decimal("120.00")  # 4 * 20 * 1.5
        assert result.overtime_2x_pay == Decimal("80.00")     # 2 * 20 * 2.0
        assert result.total_pay == Decimal("360.00")
    
    def test_seventh_day_overtime_first_8_hours(self, ca_engine):
        """Test 7th day overtime for first 8 hours (1.5x)"""
        result = ca_engine.calculate_daily_overtime(
            hours_worked=Decimal("8.0"),
            regular_rate=Decimal("20.00"),
            is_seventh_day=True
        )
        
        assert result.regular_hours == Decimal("0")
        assert result.overtime_1_5x_hours == Decimal("8.0")
        assert result.overtime_2x_hours == Decimal("0")
        assert result.overtime_1_5x_pay == Decimal("240.00")  # 8 * 20 * 1.5
    
    def test_seventh_day_overtime_over_8_hours(self, ca_engine):
        """Test 7th day overtime for hours over 8 (2x)"""
        result = ca_engine.calculate_daily_overtime(
            hours_worked=Decimal("10.0"),
            regular_rate=Decimal("20.00"),
            is_seventh_day=True
        )
        
        assert result.regular_hours == Decimal("0")
        assert result.overtime_1_5x_hours == Decimal("8.0")   # First 8 hours
        assert result.overtime_2x_hours == Decimal("2.0")     # Hours 9-10
        assert result.overtime_1_5x_pay == Decimal("240.00")
        assert result.overtime_2x_pay == Decimal("80.00")


class TestMealBreaks:
    """Test meal break compliance"""
    
    def test_no_meal_break_required(self, ca_engine):
        """Test no violation for shift <= 5 hours"""
        violations = ca_engine.check_meal_breaks(
            work_date=date.today(),
            hours_worked=Decimal("5.0"),
            meal_breaks_taken=0,
            regular_rate=Decimal("20.00")
        )
        
        assert len(violations) == 0
    
    def test_first_meal_break_required(self, ca_engine):
        """Test violation when first meal break not taken"""
        violations = ca_engine.check_meal_breaks(
            work_date=date.today(),
            hours_worked=Decimal("6.0"),
            meal_breaks_taken=0,
            regular_rate=Decimal("20.00")
        )
        
        assert len(violations) == 1
        assert violations[0].violation_type == "meal"
        assert violations[0].penalty_amount == Decimal("20.00")
        assert violations[0].penalty_hours == Decimal("1.0")
    
    def test_second_meal_break_required(self, ca_engine):
        """Test violation when second meal break not taken"""
        violations = ca_engine.check_meal_breaks(
            work_date=date.today(),
            hours_worked=Decimal("11.0"),
            meal_breaks_taken=1,
            regular_rate=Decimal("20.00")
        )
        
        assert len(violations) == 1
        assert violations[0].violation_type == "meal"
    
    def test_both_meal_breaks_missing(self, ca_engine):
        """Test both meal breaks missing"""
        violations = ca_engine.check_meal_breaks(
            work_date=date.today(),
            hours_worked=Decimal("11.0"),
            meal_breaks_taken=0,
            regular_rate=Decimal("20.00")
        )
        
        assert len(violations) == 2
        total_penalty = sum(v.penalty_amount for v in violations)
        assert total_penalty == Decimal("40.00")  # 2 hours penalty


class TestRestBreaks:
    """Test rest break compliance"""
    
    def test_rest_break_for_4_hours(self, ca_engine):
        """Test rest break required for 4 hours"""
        violations = ca_engine.check_rest_breaks(
            work_date=date.today(),
            hours_worked=Decimal("4.0"),
            rest_breaks_taken=0,
            regular_rate=Decimal("20.00")
        )
        
        assert len(violations) == 1
        assert violations[0].penalty_amount == Decimal("20.00")
    
    def test_rest_breaks_for_8_hours(self, ca_engine):
        """Test rest breaks required for 8 hours"""
        violations = ca_engine.check_rest_breaks(
            work_date=date.today(),
            hours_worked=Decimal("8.0"),
            rest_breaks_taken=1,
            regular_rate=Decimal("20.00")
        )
        
        # Should require 2 rest breaks for 8 hours
        assert len(violations) == 1


class TestMinimumWage:
    """Test minimum wage validation"""
    
    def test_valid_minimum_wage(self, ca_engine):
        """Test hourly rate above minimum wage"""
        is_valid, message = ca_engine.validate_minimum_wage(Decimal("20.00"))
        
        assert is_valid is True
        assert message is None
    
    def test_below_minimum_wage(self, ca_engine):
        """Test hourly rate below minimum wage"""
        is_valid, message = ca_engine.validate_minimum_wage(Decimal("10.00"))
        
        assert is_valid is False
        assert "minimum wage" in message.lower()


class TestSeventhConsecutiveDay:
    """Test identification of 7th consecutive workday"""
    
    def test_seven_consecutive_days(self, ca_engine):
        """Test identification of 7th consecutive day"""
        start_date = date.today()
        work_dates = [start_date + timedelta(days=i) for i in range(7)]
        
        seventh_days = ca_engine.identify_seventh_consecutive_day(work_dates)
        
        assert len(seventh_days) == 1
        assert seventh_days[0] == work_dates[6]
    
    def test_less_than_seven_days(self, ca_engine):
        """Test no 7th day when working less than 7 days"""
        start_date = date.today()
        work_dates = [start_date + timedelta(days=i) for i in range(5)]
        
        seventh_days = ca_engine.identify_seventh_consecutive_day(work_dates)
        
        assert len(seventh_days) == 0
    
    def test_non_consecutive_days(self, ca_engine):
        """Test no 7th day when days are not consecutive"""
        start_date = date.today()
        work_dates = [
            start_date,
            start_date + timedelta(days=1),
            start_date + timedelta(days=3),  # Gap here
            start_date + timedelta(days=4),
            start_date + timedelta(days=5),
            start_date + timedelta(days=6),
            start_date + timedelta(days=7),
        ]
        
        seventh_days = ca_engine.identify_seventh_consecutive_day(work_dates)
        
        # Should not identify 7th day due to gap
        assert len(seventh_days) == 0
