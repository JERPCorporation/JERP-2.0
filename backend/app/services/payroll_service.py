"""
JERP 2.0 - Payroll Service
Business logic for payroll processing with compliance enforcement
"""
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.payroll import PayrollPeriod, Payslip
from app.models.hr import Employee
from app.models.time_attendance import Timesheet, TimesheetEntry, BreakEntry
from app.compliance.labor.california import CaliforniaLaborCode
from app.compliance.labor.flsa import FLSA
from app.services.compliance_service import ComplianceService
from app.schemas.compliance import ComplianceViolationCreate
from app.models.compliance_violation import ViolationType, ViolationSeverity


class PayrollService:
    """Service for payroll processing with automatic compliance checking"""
    
    def __init__(self, db: Session):
        self.db = db
        self.ca_labor = CaliforniaLaborCode()
        self.flsa = FLSA()
        self.compliance_service = ComplianceService(db)
    
    async def process_payroll_period(
        self,
        period_id: int,
        user_id: int,
        user_email: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict:
        """
        Process payroll period with automatic compliance checking
        
        Args:
            period_id: ID of payroll period to process
            user_id: User processing payroll
            user_email: Email of user
            ip_address: Request IP
            user_agent: Request user agent
            
        Returns:
            Dictionary with processing results
        """
        period = self.db.query(PayrollPeriod).filter(PayrollPeriod.id == period_id).first()
        if not period:
            raise ValueError(f"Payroll period {period_id} not found")
        
        # Get all approved timesheets for this period
        timesheets = self.db.query(Timesheet).filter(
            and_(
                Timesheet.period_start >= period.start_date,
                Timesheet.period_end <= period.end_date,
                Timesheet.status == "APPROVED"
            )
        ).all()
        
        violations_count = 0
        total_gross = Decimal("0")
        total_net = Decimal("0")
        total_deductions = Decimal("0")
        payslips_created = 0
        
        for timesheet in timesheets:
            employee = timesheet.employee
            
            if not employee:
                continue
            
            # Calculate pay with compliance
            pay_result = await self._calculate_employee_pay(
                timesheet=timesheet,
                employee=employee,
                user_id=user_id,
                user_email=user_email,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            violations_count += pay_result['violations_count']
            
            # Create payslip
            payslip = Payslip(
                period_id=period_id,
                employee_id=employee.id,
                regular_hours=pay_result['regular_hours'],
                overtime_hours=pay_result['overtime_hours'],
                double_time_hours=pay_result['double_time_hours'],
                regular_pay=pay_result['regular_pay'],
                overtime_pay=pay_result['overtime_pay'],
                double_time_pay=pay_result['double_time_pay'],
                meal_break_penalty=pay_result['meal_break_penalty'],
                rest_break_penalty=pay_result['rest_break_penalty'],
                gross_pay=pay_result['gross_pay'],
                total_deductions=pay_result['total_deductions'],
                net_pay=pay_result['net_pay'],
                california_labor_compliant=pay_result['california_compliant'],
                flsa_compliant=pay_result['flsa_compliant'],
                compliance_notes=pay_result.get('compliance_notes')
            )
            
            self.db.add(payslip)
            payslips_created += 1
            
            total_gross += pay_result['gross_pay']
            total_net += pay_result['net_pay']
            total_deductions += pay_result['total_deductions']
        
        # Update period
        period.status = "PROCESSING"
        period.processed_by = user_id
        period.processed_at = datetime.now(timezone.utc)
        period.total_gross = total_gross
        period.total_deductions = total_deductions
        period.total_net = total_net
        period.compliance_checked = True
        period.compliance_violations_count = violations_count
        
        self.db.commit()
        
        return {
            "payslips_created": payslips_created,
            "violations_count": violations_count,
            "total_gross": float(total_gross),
            "total_net": float(total_net)
        }
    
    async def _calculate_employee_pay(
        self,
        timesheet: Timesheet,
        employee: Employee,
        user_id: int,
        user_email: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict:
        """
        Calculate pay for a single employee with compliance checks
        
        Args:
            timesheet: Employee timesheet
            employee: Employee record
            user_id: User processing payroll
            user_email: User email
            ip_address: Request IP
            user_agent: Request user agent
            
        Returns:
            Dictionary with pay calculation and compliance results
        """
        regular_hours = Decimal("0")
        overtime_hours = Decimal("0")
        double_time_hours = Decimal("0")
        meal_break_penalty = Decimal("0")
        rest_break_penalty = Decimal("0")
        violations_count = 0
        california_compliant = True
        flsa_compliant = True
        compliance_notes = []
        
        # Get pay rate
        pay_rate = employee.pay_rate or Decimal("0")
        
        # California Labor Code compliance
        if employee.is_california_employee:
            # Check each timesheet entry for compliance
            for entry in timesheet.entries:
                if not entry.hours_worked:
                    continue
                
                # Calculate overtime using CA Labor Code
                ot_calc = self.ca_labor.calculate_daily_overtime(
                    hours_worked=entry.hours_worked,
                    regular_rate=pay_rate,
                    is_seventh_day=timesheet.is_seventh_consecutive_day
                )
                
                regular_hours += ot_calc.regular_hours
                overtime_hours += ot_calc.overtime_1_5x_hours
                double_time_hours += ot_calc.overtime_2x_hours
                
                # Check meal breaks
                meal_breaks_taken = len([b for b in entry.breaks if b.break_type == "MEAL"])
                meal_violations = self.ca_labor.check_meal_breaks(
                    work_date=entry.work_date,
                    hours_worked=entry.hours_worked,
                    meal_breaks_taken=meal_breaks_taken,
                    regular_rate=pay_rate
                )
                
                if meal_violations:
                    california_compliant = False
                    for violation in meal_violations:
                        meal_break_penalty += violation.penalty_amount
                        compliance_notes.append(violation.description)
                        
                        # Log violation
                        await self.compliance_service.log_violation(
                            violation_data=ComplianceViolationCreate(
                                violation_type=ViolationType.LABOR_LAW,
                                regulation="CA_LABOR_CODE_512",
                                severity=ViolationSeverity.HIGH,
                                description=violation.description,
                                entity_type="timesheet_entry",
                                entity_id=str(entry.id),
                                financial_impact=violation.penalty_amount
                            ),
                            user_id=user_id,
                            user_email=user_email,
                            ip_address=ip_address,
                            user_agent=user_agent
                        )
                        violations_count += 1
                
                # Check rest breaks
                rest_breaks_taken = len([b for b in entry.breaks if b.break_type == "REST"])
                rest_violations = self.ca_labor.check_rest_breaks(
                    work_date=entry.work_date,
                    hours_worked=entry.hours_worked,
                    rest_breaks_taken=rest_breaks_taken,
                    regular_rate=pay_rate
                )
                
                if rest_violations:
                    california_compliant = False
                    for violation in rest_violations:
                        rest_break_penalty += violation.penalty_amount
                        compliance_notes.append(violation.description)
                        
                        # Log violation
                        await self.compliance_service.log_violation(
                            violation_data=ComplianceViolationCreate(
                                violation_type=ViolationType.LABOR_LAW,
                                regulation="CA_LABOR_CODE_516",
                                severity=ViolationSeverity.HIGH,
                                description=violation.description,
                                entity_type="timesheet_entry",
                                entity_id=str(entry.id),
                                financial_impact=violation.penalty_amount
                            ),
                            user_id=user_id,
                            user_email=user_email,
                            ip_address=ip_address,
                            user_agent=user_agent
                        )
                        violations_count += 1
        else:
            # Use regular calculation for non-CA employees
            regular_hours = timesheet.regular_hours
            overtime_hours = timesheet.overtime_hours
            double_time_hours = timesheet.double_time_hours
        
        # FLSA validation
        total_hours = regular_hours + overtime_hours + double_time_hours
        if employee.flsa_status == "NON_EXEMPT":
            flsa_calc = self.flsa.calculate_weekly_overtime(
                hours_worked=total_hours,
                regular_rate=pay_rate
            )
            
            # FLSA requires 1.5x for hours over 40, compare with CA calculation
            # Use the calculation more favorable to employee
            if flsa_calc.overtime_hours > (overtime_hours + double_time_hours):
                flsa_compliant = False
                compliance_notes.append(
                    f"FLSA overtime ({flsa_calc.overtime_hours} hrs) differs from state calculation"
                )
        
        # Calculate gross pay
        regular_pay = regular_hours * pay_rate
        overtime_pay = overtime_hours * pay_rate * Decimal("1.5")
        double_time_pay = double_time_hours * pay_rate * Decimal("2.0")
        
        gross_pay = regular_pay + overtime_pay + double_time_pay + meal_break_penalty + rest_break_penalty
        
        # Calculate deductions (simplified - would be more complex in real system)
        federal_tax = gross_pay * Decimal("0.12")  # Simplified
        state_tax = gross_pay * Decimal("0.05")  # Simplified
        social_security = gross_pay * Decimal("0.062")
        medicare = gross_pay * Decimal("0.0145")
        
        total_deductions = federal_tax + state_tax + social_security + medicare
        net_pay = gross_pay - total_deductions
        
        return {
            "regular_hours": regular_hours,
            "overtime_hours": overtime_hours,
            "double_time_hours": double_time_hours,
            "regular_pay": regular_pay,
            "overtime_pay": overtime_pay,
            "double_time_pay": double_time_pay,
            "meal_break_penalty": meal_break_penalty,
            "rest_break_penalty": rest_break_penalty,
            "gross_pay": gross_pay,
            "total_deductions": total_deductions,
            "net_pay": net_pay,
            "california_compliant": california_compliant,
            "flsa_compliant": flsa_compliant,
            "violations_count": violations_count,
            "compliance_notes": "; ".join(compliance_notes) if compliance_notes else None
        }
    
    async def approve_payroll_period(
        self,
        period_id: int,
        user_id: int
    ) -> PayrollPeriod:
        """
        Approve a payroll period after review
        
        Args:
            period_id: ID of period to approve
            user_id: User approving
            
        Returns:
            Updated PayrollPeriod
        """
        period = self.db.query(PayrollPeriod).filter(PayrollPeriod.id == period_id).first()
        if not period:
            raise ValueError(f"Payroll period {period_id} not found")
        
        period.status = "APPROVED"
        self.db.commit()
        self.db.refresh(period)
        
        return period
