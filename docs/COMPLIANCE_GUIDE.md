# JERP 2.0 - Compliance Guide

## Table of Contents
1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Labor Law Compliance](#labor-law-compliance)
4. [Financial Compliance](#financial-compliance)
5. [API Reference](#api-reference)
6. [Integration Guide](#integration-guide)
7. [Best Practices](#best-practices)

## Overview

JERP 2.0's compliance framework provides comprehensive monitoring and enforcement of labor laws and financial regulations. The system automatically detects violations, tracks them with immutable audit trails, and provides reporting and analytics.

### Key Features

- **California Labor Code Compliance**: Overtime, meal breaks, rest breaks, minimum wage
- **Federal FLSA Compliance**: Overtime, employee classification, child labor, record keeping
- **GAAP Validation**: US Generally Accepted Accounting Principles
- **IFRS Validation**: International Financial Reporting Standards
- **Immutable Audit Trail**: SHA-256 hash-chained audit logs
- **Real-time Violation Tracking**: Automatic detection and logging
- **Compliance Reporting**: Detailed reports and analytics

## Architecture

### Component Overview

```
┌─────────────────────────────────────────────────────────┐
│                   Compliance Framework                   │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  Labor Law   │  │  Financial   │  │   Violation  │  │
│  │   Engines    │  │   Engines    │  │   Tracking   │  │
│  ├──────────────┤  ├──────────────┤  ├──────────────┤  │
│  │ - CA Labor   │  │ - GAAP       │  │ - Models     │  │
│  │ - FLSA       │  │ - IFRS       │  │ - Service    │  │
│  └──────────────┘  └──────────────┘  │ - Reports    │  │
│                                       └──────────────┘  │
│                                                           │
│  ┌────────────────────────────────────────────────────┐ │
│  │              Audit Log Integration                 │ │
│  │  (SHA-256 Hash Chain for Immutability)            │ │
│  └────────────────────────────────────────────────────┘ │
│                                                           │
│  ┌────────────────────────────────────────────────────┐ │
│  │                  REST API Layer                    │ │
│  │  (FastAPI with Pydantic Validation)               │ │
│  └────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

### Database Models

#### ComplianceViolation
Tracks individual compliance violations with full audit trail.

**Fields:**
- `violation_type`: LABOR_LAW, FINANCIAL, OTHER
- `regulation`: Specific regulation violated
- `severity`: LOW, MEDIUM, HIGH, CRITICAL
- `description`: Detailed violation description
- `entity_type`: Type of entity (timesheet, transaction, etc.)
- `entity_id`: ID of the affected entity
- `status`: OPEN, IN_PROGRESS, RESOLVED, DISMISSED
- `financial_impact`: Dollar amount of violation
- `detected_at`: When violation was detected
- `resolved_at`: When violation was resolved
- `audit_log_id`: Link to audit trail

#### ComplianceRule
Defines compliance rules that can be checked automatically.

**Fields:**
- `rule_code`: Unique identifier
- `rule_name`: Human-readable name
- `regulation_type`: CALIFORNIA_LABOR, FLSA, GAAP, IFRS
- `severity`: Default severity for violations
- `is_active`: Whether rule is active
- `validation_logic`: JSON-encoded validation logic

#### ComplianceReport
Generated reports summarizing compliance status.

**Fields:**
- `report_type`: Type of report
- `start_date`: Report period start
- `end_date`: Report period end
- `total_violations`: Count by severity
- `generated_by`: User who generated report
- `report_data`: Detailed JSON data

## Labor Law Compliance

### California Labor Code

The California Labor Code engine implements state-specific labor regulations.

#### Overtime Rules

**Daily Overtime:**
```python
from app.compliance.labor.california import CaliforniaLaborCode
from decimal import Decimal

ca_engine = CaliforniaLaborCode()

# Example: 10 hour workday
result = ca_engine.calculate_daily_overtime(
    hours_worked=Decimal("10.0"),
    regular_rate=Decimal("20.00"),
    is_seventh_day=False
)

print(f"Regular hours: {result.regular_hours}")      # 8.0
print(f"1.5x OT hours: {result.overtime_1_5x_hours}") # 2.0
print(f"2x OT hours: {result.overtime_2x_hours}")    # 0.0
print(f"Total pay: ${result.total_pay}")             # $220.00
```

**7th Consecutive Day Rules:**
```python
# First 8 hours on 7th day: 1.5x
# Hours after 8 on 7th day: 2x
result = ca_engine.calculate_daily_overtime(
    hours_worked=Decimal("10.0"),
    regular_rate=Decimal("20.00"),
    is_seventh_day=True
)

print(f"1.5x OT hours: {result.overtime_1_5x_hours}") # 8.0 (first 8)
print(f"2x OT hours: {result.overtime_2x_hours}")    # 2.0 (after 8)
```

#### Meal Break Rules

**Requirements:**
- First meal break: Required for shifts > 5 hours
- Second meal break: Required for shifts > 10 hours
- Duration: 30 minutes unpaid
- Penalty: 1 hour of pay at regular rate per violation

```python
# Check meal break compliance
violations = ca_engine.check_meal_breaks(
    work_date=date.today(),
    hours_worked=Decimal("11.0"),
    meal_breaks_taken=1,  # Missing second break
    regular_rate=Decimal("20.00")
)

for v in violations:
    print(f"{v.description}")
    print(f"Penalty: ${v.penalty_amount}")
```

#### Rest Break Rules

**Requirements:**
- One 10-minute paid rest break per 4 hours worked
- Penalty: 1 hour of pay at regular rate per violation

```python
# Check rest break compliance
violations = ca_engine.check_rest_breaks(
    work_date=date.today(),
    hours_worked=Decimal("8.0"),
    rest_breaks_taken=1,  # Should have 2
    regular_rate=Decimal("20.00")
)
```

### Federal FLSA

The FLSA engine implements federal labor standards.

#### Weekly Overtime

```python
from app.compliance.labor.flsa import FLSA
from decimal import Decimal

flsa_engine = FLSA()

# Calculate weekly overtime (>40 hours)
result = flsa_engine.calculate_weekly_overtime(
    hours_worked=Decimal("50.0"),
    regular_rate=Decimal("15.00")
)

print(f"Regular hours: {result.regular_hours}")   # 40.0
print(f"OT hours: {result.overtime_hours}")       # 10.0
print(f"Total pay: ${result.total_pay}")          # $825.00
```

#### Employee Classification

```python
from app.compliance.labor.flsa import ExemptionType

# Check if employee qualifies for exempt status
is_exempt, reason = flsa_engine.check_exempt_classification(
    job_title="Director of Operations",
    weekly_salary=Decimal("1000.00"),
    annual_salary=Decimal("52000.00"),
    job_duties=["Manage team", "Supervise employees"],
    exemption_type=ExemptionType.EXECUTIVE
)

if not is_exempt:
    print(f"Not exempt: {reason}")
```

#### Child Labor Compliance

```python
# Check child labor compliance
violations = flsa_engine.check_child_labor_compliance(
    employee_age=15,
    hours_worked=Decimal("5.0"),
    work_date=date.today(),
    is_school_day=True,
    is_school_week=True,
    is_hazardous_work=False
)

for v in violations:
    print(f"{v.violation_description} (Severity: {v.severity})")
```

## Financial Compliance

### GAAP (US Standards)

The GAAP engine validates US Generally Accepted Accounting Principles.

#### Balance Sheet Validation

```python
from app.compliance.financial.gaap import GAAP
from decimal import Decimal

gaap_engine = GAAP()

# Validate balance sheet equation
result = gaap_engine.validate_balance_sheet(
    assets={"Cash": Decimal("10000"), "Equipment": Decimal("50000")},
    liabilities={"Accounts Payable": Decimal("15000")},
    equity={"Owner's Equity": Decimal("45000")}
)

if result.is_balanced:
    print("Balance sheet is balanced!")
else:
    print(f"Discrepancy: ${result.discrepancy}")
    for v in result.violations:
        print(f"  - {v.description}")
```

#### Revenue Recognition

```python
# Validate revenue recognition
violations = gaap_engine.validate_revenue_recognition(
    revenue_amount=Decimal("10000"),
    service_delivered=True,
    goods_delivered=False,
    payment_received=True,
    revenue_recognition_date=date(2024, 1, 15),
    transaction_date=date(2024, 1, 10)
)
```

#### Inventory Valuation

```python
from app.compliance.financial.gaap import InventoryMethod

# Validate inventory and COGS
violations = gaap_engine.validate_inventory_valuation(
    method=InventoryMethod.FIFO,
    beginning_inventory=Decimal("50000"),
    purchases=Decimal("100000"),
    ending_inventory=Decimal("60000"),
    cost_of_goods_sold=Decimal("90000")
)
```

### IFRS (International Standards)

The IFRS engine validates International Financial Reporting Standards.

#### Key Differences from GAAP

1. **No LIFO**: LIFO inventory method is prohibited
2. **Component Depreciation**: Required for significant components
3. **Fair Value**: More emphasis on fair value measurements

#### Inventory Validation

```python
from app.compliance.financial.ifrs import IFRS

ifrs_engine = IFRS()

# LIFO is prohibited under IFRS
violations = ifrs_engine.validate_inventory_method("LIFO")
# Returns violation: "LIFO inventory method is not permitted under IFRS"

# Lower of cost or NRV
violations = ifrs_engine.validate_inventory_valuation(
    method="FIFO",
    cost=Decimal("10000"),
    net_realizable_value=Decimal("9000"),
    recorded_value=Decimal("10000")  # Should be 9000
)
```

#### Component Depreciation (IAS 16)

```python
from app.compliance.financial.ifrs import ComponentDepreciation, IFRSDepreciationMethod

# Define asset components
components = [
    ComponentDepreciation(
        component_name="Building Structure",
        component_cost=Decimal("800000"),
        useful_life=40,
        depreciation_method=IFRSDepreciationMethod.STRAIGHT_LINE
    ),
    ComponentDepreciation(
        component_name="HVAC System",
        component_cost=Decimal("100000"),
        useful_life=15,
        depreciation_method=IFRSDepreciationMethod.STRAIGHT_LINE
    ),
    ComponentDepreciation(
        component_name="Roof",
        component_cost=Decimal("100000"),
        useful_life=20,
        depreciation_method=IFRSDepreciationMethod.STRAIGHT_LINE
    )
]

# Validate component depreciation
violations = ifrs_engine.validate_component_depreciation(
    asset_name="Commercial Building",
    total_cost=Decimal("1000000"),
    components=components
)
```

## API Reference

### Base URL
```
http://localhost:8000/api/v1
```

### Authentication
Currently uses mock authentication. In production, requires JWT Bearer token:
```
Authorization: Bearer <token>
```

### Endpoints

#### Create Violation
```http
POST /compliance/violations
Content-Type: application/json

{
  "violation_type": "LABOR_LAW",
  "regulation": "California Labor Code Section 512",
  "severity": "HIGH",
  "description": "Meal break not provided for 6-hour shift",
  "entity_type": "timesheet",
  "entity_id": 123,
  "financial_impact": "20.00",
  "metadata": {
    "employee_id": 456,
    "shift_date": "2024-01-15"
  }
}
```

#### List Violations
```http
GET /compliance/violations?status=OPEN&severity=HIGH&limit=50
```

**Query Parameters:**
- `violation_type`: Filter by type (LABOR_LAW, FINANCIAL, OTHER)
- `severity`: Filter by severity (LOW, MEDIUM, HIGH, CRITICAL)
- `status`: Filter by status (OPEN, IN_PROGRESS, RESOLVED, DISMISSED)
- `entity_type`: Filter by entity type
- `start_date`: Filter by date (ISO format)
- `end_date`: Filter by date (ISO format)
- `skip`: Pagination offset (default: 0)
- `limit`: Results per page (default: 100, max: 1000)

#### Get Violation Details
```http
GET /compliance/violations/{id}
```

#### Update Violation
```http
PUT /compliance/violations/{id}
Content-Type: application/json

{
  "status": "IN_PROGRESS",
  "assigned_to": 5,
  "resolution_notes": "Investigating with HR department"
}
```

#### Resolve Violation
```http
POST /compliance/violations/{id}/resolve
Content-Type: application/json

{
  "resolution_notes": "Employee was provided makeup break period. Policy clarified with manager."
}
```

#### Generate Report
```http
POST /compliance/reports
Content-Type: application/json

{
  "report_type": "monthly",
  "start_date": "2024-01-01",
  "end_date": "2024-01-31"
}
```

#### Get Dashboard Data
```http
GET /compliance/dashboard?days_back=30
```

**Response:**
```json
{
  "statistics": {
    "total_violations": 45,
    "open_violations": 12,
    "resolved_violations": 30,
    "critical_violations": 3,
    "high_violations": 15,
    "total_financial_impact": "2500.00"
  },
  "recent_violations": [...],
  "trends": [...],
  "top_violation_types": {
    "California Labor Code Section 512": 10,
    "FLSA Section 7(a)": 8
  },
  "compliance_score": 87.5
}
```

## Integration Guide

### Setting Up Compliance Checking

#### 1. Import Required Modules

```python
from sqlalchemy.orm import Session
from app.services.compliance_service import ComplianceService
from app.compliance.labor.california import CaliforniaLaborCode
from app.schemas.compliance import ComplianceViolationCreate
from app.models.compliance_violation import ViolationType, ViolationSeverity
```

#### 2. Check Timesheet for Compliance

```python
def check_timesheet_compliance(timesheet_id: int, db: Session, user_id: int):
    """Example: Check a timesheet for CA Labor Code compliance"""
    
    # Initialize engines and service
    ca_engine = CaliforniaLaborCode()
    compliance_service = ComplianceService(db)
    
    # Fetch timesheet data (example)
    timesheet = get_timesheet(timesheet_id)
    
    # Check meal breaks
    meal_violations = ca_engine.check_meal_breaks(
        work_date=timesheet.date,
        hours_worked=timesheet.hours,
        meal_breaks_taken=timesheet.meal_breaks,
        regular_rate=timesheet.hourly_rate
    )
    
    # Log any violations
    for violation in meal_violations:
        violation_data = ComplianceViolationCreate(
            violation_type=ViolationType.LABOR_LAW,
            regulation="California Labor Code Section 512",
            severity=ViolationSeverity.HIGH,
            description=violation.description,
            entity_type="timesheet",
            entity_id=timesheet_id,
            financial_impact=violation.penalty_amount,
            metadata={
                "date": str(violation.date),
                "hours_worked": str(timesheet.hours)
            }
        )
        
        compliance_service.log_violation(
            violation_data=violation_data,
            user_id=user_id,
            user_email="system@jerp.local"
        )
    
    return len(meal_violations) == 0
```

#### 3. Check Transaction for Compliance

```python
def check_transaction_compliance(transaction_id: int, db: Session, user_id: int):
    """Example: Check a transaction for GAAP compliance"""
    
    from app.compliance.financial.gaap import GAAP
    
    gaap_engine = GAAP()
    compliance_service = ComplianceService(db)
    
    # Fetch transaction data
    transaction = get_transaction(transaction_id)
    
    # Check revenue recognition
    violations = gaap_engine.validate_revenue_recognition(
        revenue_amount=transaction.amount,
        service_delivered=transaction.service_delivered,
        goods_delivered=transaction.goods_delivered,
        payment_received=transaction.payment_received,
        revenue_recognition_date=transaction.recognition_date,
        transaction_date=transaction.created_date
    )
    
    # Log violations
    for violation in violations:
        violation_data = ComplianceViolationCreate(
            violation_type=ViolationType.FINANCIAL,
            regulation=violation.principle,
            severity=getattr(ViolationSeverity, violation.severity),
            description=violation.description,
            entity_type="transaction",
            entity_id=transaction_id,
            financial_impact=violation.amount
        )
        
        compliance_service.log_violation(
            violation_data=violation_data,
            user_id=user_id,
            user_email="system@jerp.local"
        )
    
    return len(violations) == 0
```

### Automated Compliance Checking

Set up automated checks using background tasks or scheduled jobs:

```python
from celery import Celery
from datetime import datetime, timedelta

app = Celery('jerp_compliance')

@app.task
def daily_compliance_check():
    """Run daily compliance checks on all active timesheets"""
    db = SessionLocal()
    try:
        # Get yesterday's timesheets
        yesterday = datetime.now().date() - timedelta(days=1)
        timesheets = get_timesheets_by_date(yesterday, db)
        
        for timesheet in timesheets:
            check_timesheet_compliance(timesheet.id, db, system_user_id)
    finally:
        db.close()

@app.task
def weekly_compliance_report():
    """Generate weekly compliance report"""
    db = SessionLocal()
    try:
        compliance_service = ComplianceService(db)
        
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=7)
        
        report = compliance_service.generate_compliance_report(
            report_data=ComplianceReportCreate(
                report_type="weekly",
                start_date=start_date,
                end_date=end_date
            ),
            user_id=system_user_id
        )
        
        # Send report via email or notification
        send_compliance_report(report)
    finally:
        db.close()
```

## Best Practices

### 1. Proactive Compliance Checking

- Check compliance **before** finalizing timesheets/transactions
- Use validation endpoints in UI workflows
- Display warnings to users in real-time

### 2. Violation Management

- Assign violations to responsible parties immediately
- Set up notifications for critical violations
- Review and resolve violations promptly
- Document resolutions thoroughly

### 3. Regular Reporting

- Generate weekly compliance reports
- Review trends and patterns
- Identify systemic issues
- Implement corrective measures

### 4. Audit Trail Integrity

- Never modify existing violations directly
- Use the update/resolve endpoints to maintain audit trail
- Regularly verify hash chain integrity
- Back up audit logs securely

### 5. Configuration Management

- Keep compliance rules up to date
- Review and update minimum wage rates annually
- Document any custom rules or thresholds
- Test rule changes in staging environment

### 6. Training and Documentation

- Train staff on compliance requirements
- Document your organization's specific policies
- Provide examples and guidelines
- Regular refresher training

### 7. Performance Optimization

- Use appropriate filters when querying violations
- Implement pagination for large result sets
- Cache frequently accessed rules
- Index database tables appropriately

## Support and Maintenance

### Updating Minimum Wage Rates

California and federal minimum wage rates change over time. Update in the engine constants:

```python
# backend/app/compliance/labor/california.py
MINIMUM_WAGE = Decimal("17.00")  # Update as needed

# backend/app/compliance/labor/flsa.py
FEDERAL_MINIMUM_WAGE = Decimal("7.25")  # Update as needed
```

### Adding Custom Rules

Add custom compliance rules through the API:

```python
POST /compliance/rules
{
  "rule_code": "CUSTOM_OVERTIME_001",
  "rule_name": "Custom Overtime Rule",
  "description": "Organization-specific overtime policy",
  "regulation_type": "CALIFORNIA_LABOR",
  "severity": "HIGH",
  "is_active": true,
  "validation_logic": {
    "threshold_hours": 8.5,
    "rate_multiplier": 1.5
  }
}
```

### Troubleshooting

**Issue: Violations not being created**
- Check that compliance engines are imported correctly
- Verify database migrations have been applied
- Check audit log chain integrity
- Review application logs for errors

**Issue: Incorrect overtime calculations**
- Verify input data (hours, rates) are using Decimal type
- Check for timezone issues with date calculations
- Review 7th consecutive day identification logic
- Ensure workweek definition matches your organization

**Issue: Performance degradation**
- Add database indexes on frequently filtered columns
- Implement result caching for dashboard queries
- Use batch processing for bulk compliance checks
- Archive old resolved violations

## Additional Resources

- [California Labor Code](https://leginfo.legislature.ca.gov/faces/codes_displayText.xhtml?lawCode=LAB)
- [FLSA Overview](https://www.dol.gov/agencies/whd/flsa)
- [GAAP Standards](https://www.fasb.org/)
- [IFRS Standards](https://www.ifrs.org/)

---

**JERP 2.0 Compliance Framework** - Built for accuracy, transparency, and peace of mind.
