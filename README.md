# JERP 2.0 - On-Premise Compliance ERP Suite

**Julio's Enterprise Resource Planning System - Version 2.0**

A comprehensive, on-premise ERP solution focused on **Labor Law Compliance** and **Financial Compliance (GAAP/IFRS**).

## 🎯 Overview

JERP 2.0 is a complete enterprise resource planning system designed for single-tenant, on-premise deployment. Built from the ground up with compliance as the core focus.

### Target Hardware
- **ACEMAGIC AM08Pro Mini PC**
- AMD Ryzen 9 6900HX (8 cores/16 threads)
- 32GB DDR5 RAM
- 1TB NVMe SSD

## 🔒 Compliance Focus

JERP 2.0 includes a comprehensive compliance framework that automatically monitors and enforces labor laws and financial regulations.

| Area | Standards | Features |
|------|-----------|----------|
| **Labor Law** | California Labor Code, Federal FLSA | Overtime calculations, meal/rest breaks, minimum wage, child labor |
| **Financial** | GAAP (US), IFRS (International) | Revenue recognition, balance sheet validation, inventory methods |
| **Audit** | Immutable SHA-256 hash-chained logs | Tamper-proof audit trail for all compliance violations |

### ✨ Compliance Features

- **Automatic Violation Detection**: Real-time monitoring of timesheets and transactions
- **California Labor Code**: 
  - Daily overtime (1.5x > 8hrs, 2x > 12hrs)
  - 7th day overtime (1.5x first 8hrs, 2x after)
  - Meal and rest break enforcement
  - Minimum wage validation
- **Federal FLSA**:
  - Weekly overtime (1.5x > 40hrs)
  - Employee classification (exempt/non-exempt)
  - Child labor protections
  - Record keeping requirements
- **GAAP Validation**:
  - Balance sheet reconciliation
  - Revenue recognition
  - Inventory valuation (FIFO, LIFO, Average Cost)
  - Depreciation methods
- **IFRS Validation**:
  - IAS 1: Financial statement presentation
  - IAS 2: Inventory (no LIFO)
  - IAS 16: Property, Plant & Equipment
  - Component depreciation
- **Violation Tracking**: Full lifecycle management with assignment and resolution
- **Compliance Reports**: Automated reporting and analytics
- **Dashboard**: Real-time compliance score and violation trends

## 📦 Modules

- Core (Auth, RBAC, Security)
- HR/HRIS
- Payroll (with compliance enforcement)
- CRM
- Finance (GAAP/IFRS validated)
- Inventory
- Procurement
- Manufacturing
- Project Management
- Helpdesk
- BI/Reports
- Notifications
- Documents
- Workflow Engine
- AI/ML
- Multi-language (i18n)
- Mobile Support

## 🚀 Quick Start

```bash
# Clone the repository
git clone https://github.com/ninoyerbas/JERP-2.0.git
cd JERP-2.0

# Configure environment
cp .env.example .env
# Edit .env with your settings

# Install Python dependencies
cd backend
pip install -r requirements.txt

# Run the application
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Access the API documentation at: `http://localhost:8000/api/v1/docs`

## 🔧 API Examples

### Create a Compliance Violation

```bash
curl -X POST http://localhost:8000/api/v1/compliance/violations \
  -H "Content-Type: application/json" \
  -d '{
    "violation_type": "LABOR_LAW",
    "regulation": "California Labor Code Section 512",
    "severity": "HIGH",
    "description": "Meal break not provided for 6-hour shift",
    "entity_type": "timesheet",
    "entity_id": 123
  }'
```

### Get Compliance Dashboard

```bash
curl http://localhost:8000/api/v1/compliance/dashboard?days_back=30
```

### Generate Compliance Report

```bash
curl -X POST http://localhost:8000/api/v1/compliance/reports \
  -H "Content-Type: application/json" \
  -d '{
    "report_type": "monthly",
    "start_date": "2024-01-01",
    "end_date": "2024-01-31"
  }'
```

## 📚 Documentation

- [Installation Guide](docs/INSTALLATION.md)
- [Compliance Guide](docs/COMPLIANCE_GUIDE.md)
- [Admin Guide](docs/ADMIN_GUIDE.md)
- [API Reference](docs/API_REFERENCE.md)
- [Statement of Work](SOW.md)

## 📄 License

MIT License - See LICENSE file for details.

---

**JERP 2.0** - Enterprise Compliance Made Simple