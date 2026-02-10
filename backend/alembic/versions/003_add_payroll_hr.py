"""Add payroll and HR tables

Revision ID: 003_add_payroll_hr
Revises: 002_add_compliance
Create Date: 2026-02-09 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '003_add_payroll_hr'
down_revision = '002_add_compliance'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create HR and Payroll tables: departments, positions, employees, 
    employee_documents, pay_periods, payroll_periods, payslips"""
    
    # =========================================
    # HR TABLES
    # =========================================
    
    # Create departments table
    op.create_table(
        'departments',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('parent_id', sa.Integer(), nullable=True),
        sa.Column('cost_center', sa.String(length=50), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['parent_id'], ['departments.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_departments_id', 'departments', ['id'])
    op.create_index('ix_departments_name', 'departments', ['name'], unique=True)
    op.create_index('ix_departments_parent_id', 'departments', ['parent_id'])
    op.create_index('ix_departments_cost_center', 'departments', ['cost_center'])
    
    # Create positions table
    op.create_table(
        'positions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('department_id', sa.Integer(), nullable=False),
        sa.Column('is_exempt', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('min_salary', mysql.DECIMAL(precision=12, scale=2), nullable=True),
        sa.Column('max_salary', mysql.DECIMAL(precision=12, scale=2), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['department_id'], ['departments.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_positions_id', 'positions', ['id'])
    op.create_index('ix_positions_title', 'positions', ['title'])
    op.create_index('ix_positions_department_id', 'positions', ['department_id'])
    
    # Create employees table
    op.create_table(
        'employees',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        # Personal information
        sa.Column('employee_number', sa.String(length=50), nullable=False),
        sa.Column('first_name', sa.String(length=100), nullable=False),
        sa.Column('last_name', sa.String(length=100), nullable=False),
        sa.Column('middle_name', sa.String(length=100), nullable=True),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('phone', sa.String(length=20), nullable=True),
        sa.Column('ssn_last_4', sa.String(length=4), nullable=True),
        # Employment details
        sa.Column('hire_date', sa.Date(), nullable=False),
        sa.Column('termination_date', sa.Date(), nullable=True),
        sa.Column('status', sa.Enum('ACTIVE', 'ON_LEAVE', 'TERMINATED', name='employmentstatus'), nullable=False, server_default='ACTIVE'),
        sa.Column('employment_type', sa.Enum('FULL_TIME', 'PART_TIME', 'CONTRACT', 'INTERN', name='employmenttype'), nullable=False, server_default='FULL_TIME'),
        # Position and department
        sa.Column('position_id', sa.Integer(), nullable=False),
        sa.Column('department_id', sa.Integer(), nullable=False),
        sa.Column('manager_id', sa.Integer(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        # Compensation
        sa.Column('salary', mysql.DECIMAL(precision=12, scale=2), nullable=True),
        sa.Column('hourly_rate', mysql.DECIMAL(precision=8, scale=2), nullable=True),
        # Address
        sa.Column('address_line1', sa.String(length=255), nullable=True),
        sa.Column('address_line2', sa.String(length=255), nullable=True),
        sa.Column('city', sa.String(length=100), nullable=True),
        sa.Column('state', sa.String(length=50), nullable=True),
        sa.Column('postal_code', sa.String(length=20), nullable=True),
        sa.Column('country', sa.String(length=100), nullable=True, server_default='USA'),
        # Emergency contact
        sa.Column('emergency_contact_name', sa.String(length=255), nullable=True),
        sa.Column('emergency_contact_phone', sa.String(length=20), nullable=True),
        sa.Column('emergency_contact_relationship', sa.String(length=100), nullable=True),
        # Notes
        sa.Column('notes', sa.Text(), nullable=True),
        # Timestamps
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['position_id'], ['positions.id'], ),
        sa.ForeignKeyConstraint(['department_id'], ['departments.id'], ),
        sa.ForeignKeyConstraint(['manager_id'], ['employees.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_employees_id', 'employees', ['id'])
    op.create_index('ix_employees_employee_number', 'employees', ['employee_number'], unique=True)
    op.create_index('ix_employees_email', 'employees', ['email'], unique=True)
    op.create_index('ix_employees_first_name', 'employees', ['first_name'])
    op.create_index('ix_employees_last_name', 'employees', ['last_name'])
    op.create_index('ix_employees_hire_date', 'employees', ['hire_date'])
    op.create_index('ix_employees_termination_date', 'employees', ['termination_date'])
    op.create_index('ix_employees_status', 'employees', ['status'])
    op.create_index('ix_employees_employment_type', 'employees', ['employment_type'])
    op.create_index('ix_employees_position_id', 'employees', ['position_id'])
    op.create_index('ix_employees_department_id', 'employees', ['department_id'])
    op.create_index('ix_employees_manager_id', 'employees', ['manager_id'])
    op.create_index('ix_employees_user_id', 'employees', ['user_id'], unique=True)
    
    # Create employee_documents table
    op.create_table(
        'employee_documents',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('employee_id', sa.Integer(), nullable=False),
        sa.Column('document_type', sa.Enum('I9', 'W4', 'OFFER_LETTER', 'NDA', 'PERFORMANCE_REVIEW', 'DISCIPLINARY_ACTION', 'BENEFITS_ENROLLMENT', 'OTHER', name='documenttype'), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('file_path', sa.String(length=500), nullable=True),
        sa.Column('expiration_date', sa.Date(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('uploaded_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['employee_id'], ['employees.id'], ),
        sa.ForeignKeyConstraint(['uploaded_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_employee_documents_id', 'employee_documents', ['id'])
    op.create_index('ix_employee_documents_employee_id', 'employee_documents', ['employee_id'])
    op.create_index('ix_employee_documents_document_type', 'employee_documents', ['document_type'])
    op.create_index('ix_employee_documents_expiration_date', 'employee_documents', ['expiration_date'])
    
    # =========================================
    # PAYROLL TABLES
    # =========================================
    
    # Create payroll_periods table (legacy/alternate model)
    op.create_table(
        'payroll_periods',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('period_start', sa.Date(), nullable=False),
        sa.Column('period_end', sa.Date(), nullable=False),
        sa.Column('pay_date', sa.Date(), nullable=False),
        sa.Column('status', sa.Enum('DRAFT', 'PENDING', 'PROCESSING', 'PROCESSED', 'FAILED', 'CANCELLED', name='payrollstatus'), nullable=False, server_default='DRAFT'),
        sa.Column('total_gross', mysql.DECIMAL(precision=12, scale=2), nullable=True),
        sa.Column('total_deductions', mysql.DECIMAL(precision=12, scale=2), nullable=True),
        sa.Column('total_net', mysql.DECIMAL(precision=12, scale=2), nullable=True),
        sa.Column('processed_at', sa.DateTime(), nullable=True),
        sa.Column('processed_by', sa.Integer(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['processed_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_payroll_periods_id', 'payroll_periods', ['id'])
    op.create_index('ix_payroll_periods_period_start', 'payroll_periods', ['period_start'])
    op.create_index('ix_payroll_periods_period_end', 'payroll_periods', ['period_end'])
    op.create_index('ix_payroll_periods_status', 'payroll_periods', ['status'])
    op.create_index('idx_payroll_period_dates', 'payroll_periods', ['period_start', 'period_end'])
    op.create_index('idx_payroll_period_status', 'payroll_periods', ['status'])
    
    # Create pay_periods table (primary model)
    op.create_table(
        'pay_periods',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=False),
        sa.Column('pay_date', sa.Date(), nullable=False),
        sa.Column('period_type', sa.Enum('WEEKLY', 'BI_WEEKLY', 'SEMI_MONTHLY', 'MONTHLY', name='payperiodtype'), nullable=False),
        sa.Column('status', sa.Enum('OPEN', 'PROCESSING', 'APPROVED', 'PAID', 'CLOSED', name='payperiodstatus'), nullable=False, server_default='OPEN'),
        sa.Column('processed_by', sa.Integer(), nullable=True),
        sa.Column('processed_at', sa.DateTime(), nullable=True),
        sa.Column('approved_by', sa.Integer(), nullable=True),
        sa.Column('approved_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['processed_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['approved_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_pay_periods_id', 'pay_periods', ['id'])
    op.create_index('ix_pay_periods_start_date', 'pay_periods', ['start_date'])
    op.create_index('ix_pay_periods_end_date', 'pay_periods', ['end_date'])
    op.create_index('ix_pay_periods_pay_date', 'pay_periods', ['pay_date'])
    op.create_index('ix_pay_periods_status', 'pay_periods', ['status'])
    op.create_index('idx_pay_period_dates', 'pay_periods', ['start_date', 'end_date'])
    op.create_index('idx_pay_period_status', 'pay_periods', ['status', 'pay_date'])
    
    # Create payslips table
    op.create_table(
        'payslips',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        # Relationships
        sa.Column('employee_id', sa.Integer(), nullable=False),
        sa.Column('pay_period_id', sa.Integer(), nullable=False),
        sa.Column('payroll_period_id', sa.Integer(), nullable=True),
        # Status
        sa.Column('status', sa.Enum('DRAFT', 'CALCULATED', 'APPROVED', 'PAID', 'VOIDED', name='payslipstatus'), nullable=False, server_default='DRAFT'),
        # Earnings
        sa.Column('regular_hours', mysql.DECIMAL(precision=8, scale=2), nullable=False, server_default='0.00'),
        sa.Column('overtime_hours', mysql.DECIMAL(precision=8, scale=2), nullable=False, server_default='0.00'),
        sa.Column('double_time_hours', mysql.DECIMAL(precision=8, scale=2), nullable=False, server_default='0.00'),
        sa.Column('regular_pay', mysql.DECIMAL(precision=12, scale=2), nullable=False, server_default='0.00'),
        sa.Column('overtime_pay', mysql.DECIMAL(precision=12, scale=2), nullable=False, server_default='0.00'),
        sa.Column('double_time_pay', mysql.DECIMAL(precision=12, scale=2), nullable=False, server_default='0.00'),
        sa.Column('bonus', mysql.DECIMAL(precision=12, scale=2), nullable=False, server_default='0.00'),
        sa.Column('commission', mysql.DECIMAL(precision=12, scale=2), nullable=False, server_default='0.00'),
        sa.Column('other_earnings', mysql.DECIMAL(precision=12, scale=2), nullable=False, server_default='0.00'),
        sa.Column('gross_pay', mysql.DECIMAL(precision=12, scale=2), nullable=False),
        # Deductions - Taxes
        sa.Column('federal_tax', mysql.DECIMAL(precision=12, scale=2), nullable=False, server_default='0.00'),
        sa.Column('state_tax', mysql.DECIMAL(precision=12, scale=2), nullable=False, server_default='0.00'),
        sa.Column('social_security', mysql.DECIMAL(precision=12, scale=2), nullable=False, server_default='0.00'),
        sa.Column('medicare', mysql.DECIMAL(precision=12, scale=2), nullable=False, server_default='0.00'),
        # Deductions - Benefits
        sa.Column('health_insurance', mysql.DECIMAL(precision=12, scale=2), nullable=False, server_default='0.00'),
        sa.Column('retirement_401k', mysql.DECIMAL(precision=12, scale=2), nullable=False, server_default='0.00'),
        sa.Column('other_deductions', mysql.DECIMAL(precision=12, scale=2), nullable=False, server_default='0.00'),
        # Totals
        sa.Column('total_deductions', mysql.DECIMAL(precision=12, scale=2), nullable=False, server_default='0.00'),
        sa.Column('net_pay', mysql.DECIMAL(precision=12, scale=2), nullable=False),
        # Compliance tracking
        sa.Column('flsa_compliant', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('ca_labor_code_compliant', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('compliance_notes', sa.Text(), nullable=True),
        # Timestamps
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['employee_id'], ['employees.id'], ),
        sa.ForeignKeyConstraint(['pay_period_id'], ['pay_periods.id'], ),
        sa.ForeignKeyConstraint(['payroll_period_id'], ['payroll_periods.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_payslips_id', 'payslips', ['id'])
    op.create_index('ix_payslips_employee_id', 'payslips', ['employee_id'])
    op.create_index('ix_payslips_pay_period_id', 'payslips', ['pay_period_id'])
    op.create_index('ix_payslips_payroll_period_id', 'payslips', ['payroll_period_id'])
    op.create_index('ix_payslips_status', 'payslips', ['status'])
    op.create_index('ix_payslips_flsa_compliant', 'payslips', ['flsa_compliant'])
    op.create_index('ix_payslips_ca_labor_code_compliant', 'payslips', ['ca_labor_code_compliant'])
    op.create_index('idx_payslip_employee_period', 'payslips', ['employee_id', 'pay_period_id'])


def downgrade() -> None:
    """Drop all HR and Payroll tables in reverse order"""
    
    # Drop payslips first (depends on employees, pay_periods, payroll_periods)
    op.drop_index('idx_payslip_employee_period', table_name='payslips')
    op.drop_index('ix_payslips_ca_labor_code_compliant', table_name='payslips')
    op.drop_index('ix_payslips_flsa_compliant', table_name='payslips')
    op.drop_index('ix_payslips_status', table_name='payslips')
    op.drop_index('ix_payslips_payroll_period_id', table_name='payslips')
    op.drop_index('ix_payslips_pay_period_id', table_name='payslips')
    op.drop_index('ix_payslips_employee_id', table_name='payslips')
    op.drop_index('ix_payslips_id', table_name='payslips')
    op.drop_table('payslips')
    
    # Drop pay_periods
    op.drop_index('idx_pay_period_status', table_name='pay_periods')
    op.drop_index('idx_pay_period_dates', table_name='pay_periods')
    op.drop_index('ix_pay_periods_status', table_name='pay_periods')
    op.drop_index('ix_pay_periods_pay_date', table_name='pay_periods')
    op.drop_index('ix_pay_periods_end_date', table_name='pay_periods')
    op.drop_index('ix_pay_periods_start_date', table_name='pay_periods')
    op.drop_index('ix_pay_periods_id', table_name='pay_periods')
    op.drop_table('pay_periods')
    
    # Drop payroll_periods
    op.drop_index('idx_payroll_period_status', table_name='payroll_periods')
    op.drop_index('idx_payroll_period_dates', table_name='payroll_periods')
    op.drop_index('ix_payroll_periods_status', table_name='payroll_periods')
    op.drop_index('ix_payroll_periods_period_end', table_name='payroll_periods')
    op.drop_index('ix_payroll_periods_period_start', table_name='payroll_periods')
    op.drop_index('ix_payroll_periods_id', table_name='payroll_periods')
    op.drop_table('payroll_periods')
    
    # Drop employee_documents (depends on employees)
    op.drop_index('ix_employee_documents_expiration_date', table_name='employee_documents')
    op.drop_index('ix_employee_documents_document_type', table_name='employee_documents')
    op.drop_index('ix_employee_documents_employee_id', table_name='employee_documents')
    op.drop_index('ix_employee_documents_id', table_name='employee_documents')
    op.drop_table('employee_documents')
    
    # Drop employees (depends on positions, departments, users)
    op.drop_index('ix_employees_user_id', table_name='employees')
    op.drop_index('ix_employees_manager_id', table_name='employees')
    op.drop_index('ix_employees_department_id', table_name='employees')
    op.drop_index('ix_employees_position_id', table_name='employees')
    op.drop_index('ix_employees_employment_type', table_name='employees')
    op.drop_index('ix_employees_status', table_name='employees')
    op.drop_index('ix_employees_termination_date', table_name='employees')
    op.drop_index('ix_employees_hire_date', table_name='employees')
    op.drop_index('ix_employees_last_name', table_name='employees')
    op.drop_index('ix_employees_first_name', table_name='employees')
    op.drop_index('ix_employees_email', table_name='employees')
    op.drop_index('ix_employees_employee_number', table_name='employees')
    op.drop_index('ix_employees_id', table_name='employees')
    op.drop_table('employees')
    
    # Drop positions (depends on departments)
    op.drop_index('ix_positions_department_id', table_name='positions')
    op.drop_index('ix_positions_title', table_name='positions')
    op.drop_index('ix_positions_id', table_name='positions')
    op.drop_table('positions')
    
    # Drop departments
    op.drop_index('ix_departments_cost_center', table_name='departments')
    op.drop_index('ix_departments_parent_id', table_name='departments')
    op.drop_index('ix_departments_name', table_name='departments')
    op.drop_index('ix_departments_id', table_name='departments')
    op.drop_table('departments')
