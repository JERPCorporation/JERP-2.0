"""
JERP 2.0 - Finance Service
Business logic for finance operations with GAAP/IFRS validation
"""
from datetime import datetime, timezone, date
from decimal import Decimal
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from app.models.finance import ChartOfAccounts, JournalEntry, JournalEntryLine
from app.compliance.financial.gaap import GAAP
from app.compliance.financial.ifrs import IFRS
from app.services.compliance_service import ComplianceService
from app.schemas.compliance import ComplianceViolationCreate
from app.models.compliance_violation import ViolationType, ViolationSeverity


class FinanceService:
    """Service for finance operations with automatic compliance validation"""
    
    def __init__(self, db: Session):
        self.db = db
        self.gaap = GAAP()
        self.ifrs = IFRS()
        self.compliance_service = ComplianceService(db)
    
    async def post_journal_entry(
        self,
        entry_id: int,
        standard: str,
        user_id: int,
        user_email: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict:
        """
        Post journal entry with GAAP or IFRS validation
        
        Args:
            entry_id: ID of journal entry to post
            standard: Accounting standard to use (GAAP or IFRS)
            user_id: User posting entry
            user_email: User email
            ip_address: Request IP
            user_agent: Request user agent
            
        Returns:
            Dictionary with posting results
        """
        entry = self.db.query(JournalEntry).filter(JournalEntry.id == entry_id).first()
        if not entry:
            raise ValueError(f"Journal entry {entry_id} not found")
        
        if entry.status == "POSTED":
            raise ValueError(f"Journal entry {entry_id} is already posted")
        
        # Validate debits = credits
        total_debits = sum([line.debit for line in entry.lines])
        total_credits = sum([line.credit for line in entry.lines])
        
        if abs(total_debits - total_credits) > Decimal("0.01"):
            raise ValueError(
                f"Journal entry not balanced: Debits ${total_debits} != Credits ${total_credits}"
            )
        
        violations = []
        compliant = True
        
        # Validate against accounting standard
        if standard.upper() == "GAAP":
            # Simplified GAAP validation - in real system would be more comprehensive
            # Just check that entry is balanced (already done above)
            entry.gaap_compliant = True
            
            # Check for any specific GAAP violations based on account types
            for line in entry.lines:
                account = line.account
                if account and account.gaap_category:
                    # Add any GAAP-specific validation here
                    pass
        
        elif standard.upper() == "IFRS":
            # Check IFRS-specific rules
            entry.ifrs_compliant = True
            
            # Check for any IFRS violations based on account types
            for line in entry.lines:
                account = line.account
                if account and account.ifrs_category:
                    # Check if using LIFO (not allowed in IFRS)
                    if "INVENTORY" in account.ifrs_category.upper() and "LIFO" in account.account_name.upper():
                        violations.append("LIFO inventory method is not permitted under IFRS")
                        entry.ifrs_compliant = False
                        compliant = False
                        
                        await self.compliance_service.log_violation(
                            violation_data=ComplianceViolationCreate(
                                violation_type=ViolationType.FINANCIAL,
                                regulation="IFRS_IAS2",
                                severity=ViolationSeverity.CRITICAL,
                                description="LIFO inventory method used (prohibited under IFRS)",
                                entity_type="journal_entry",
                                entity_id=str(entry_id),
                                financial_impact=None
                            ),
                            user_id=user_id,
                            user_email=user_email,
                            ip_address=ip_address,
                            user_agent=user_agent
                        )
        else:
            raise ValueError(f"Invalid accounting standard: {standard}")
        
        if violations:
            entry.validation_notes = "; ".join(violations)
        
        # Post the entry
        entry.status = "POSTED"
        entry.posted_by = user_id
        entry.posted_at = datetime.now(timezone.utc)
        
        self.db.commit()
        self.db.refresh(entry)
        
        return {
            "success": True,
            "compliant": compliant,
            "violations": violations
        }
    
    def get_balance_sheet(
        self,
        as_of_date: date
    ) -> Dict:
        """
        Generate balance sheet as of a specific date
        
        Args:
            as_of_date: Date for balance sheet
            
        Returns:
            Dictionary with balance sheet data
        """
        # Get all posted journal entries up to the date
        entries = self.db.query(JournalEntry).filter(
            and_(
                JournalEntry.status == "POSTED",
                JournalEntry.posting_date <= as_of_date
            )
        ).all()
        
        # Calculate account balances
        account_balances = {}
        for entry in entries:
            for line in entry.lines:
                account = line.account
                if not account:
                    continue
                
                if account.id not in account_balances:
                    account_balances[account.id] = {
                        "account": account,
                        "debit": Decimal("0"),
                        "credit": Decimal("0"),
                        "balance": Decimal("0")
                    }
                
                account_balances[account.id]["debit"] += line.debit
                account_balances[account.id]["credit"] += line.credit
        
        # Calculate final balances based on normal balance
        assets = Decimal("0")
        liabilities = Decimal("0")
        equity = Decimal("0")
        accounts_list = []
        
        for acc_id, data in account_balances.items():
            account = data["account"]
            
            if account.normal_balance == "DEBIT":
                balance = data["debit"] - data["credit"]
            else:
                balance = data["credit"] - data["debit"]
            
            data["balance"] = balance
            accounts_list.append({
                "account_number": account.account_number,
                "account_name": account.account_name,
                "account_type": account.account_type,
                "balance": float(balance)
            })
            
            # Categorize
            if account.account_type == "ASSET":
                assets += balance
            elif account.account_type == "LIABILITY":
                liabilities += balance
            elif account.account_type == "EQUITY":
                equity += balance
        
        is_balanced = abs(assets - (liabilities + equity)) < Decimal("0.01")
        
        return {
            "as_of_date": as_of_date,
            "total_assets": float(assets),
            "total_liabilities": float(liabilities),
            "total_equity": float(equity),
            "is_balanced": is_balanced,
            "accounts": accounts_list
        }
    
    def get_income_statement(
        self,
        start_date: date,
        end_date: date
    ) -> Dict:
        """
        Generate income statement for a period
        
        Args:
            start_date: Period start date
            end_date: Period end date
            
        Returns:
            Dictionary with income statement data
        """
        # Get all posted journal entries in the period
        entries = self.db.query(JournalEntry).filter(
            and_(
                JournalEntry.status == "POSTED",
                JournalEntry.posting_date >= start_date,
                JournalEntry.posting_date <= end_date
            )
        ).all()
        
        # Calculate account balances
        account_balances = {}
        for entry in entries:
            for line in entry.lines:
                account = line.account
                if not account:
                    continue
                
                # Only include revenue and expense accounts
                if account.account_type not in ["REVENUE", "EXPENSE"]:
                    continue
                
                if account.id not in account_balances:
                    account_balances[account.id] = {
                        "account": account,
                        "debit": Decimal("0"),
                        "credit": Decimal("0"),
                        "balance": Decimal("0")
                    }
                
                account_balances[account.id]["debit"] += line.debit
                account_balances[account.id]["credit"] += line.credit
        
        # Calculate final balances
        revenue = Decimal("0")
        expenses = Decimal("0")
        accounts_list = []
        
        for acc_id, data in account_balances.items():
            account = data["account"]
            
            if account.normal_balance == "CREDIT":
                balance = data["credit"] - data["debit"]
            else:
                balance = data["debit"] - data["credit"]
            
            data["balance"] = balance
            accounts_list.append({
                "account_number": account.account_number,
                "account_name": account.account_name,
                "account_type": account.account_type,
                "balance": float(balance)
            })
            
            if account.account_type == "REVENUE":
                revenue += balance
            elif account.account_type == "EXPENSE":
                expenses += balance
        
        net_income = revenue - expenses
        
        return {
            "start_date": start_date,
            "end_date": end_date,
            "total_revenue": float(revenue),
            "total_expenses": float(expenses),
            "net_income": float(net_income),
            "accounts": accounts_list
        }
    
    def get_compliance_status(self) -> Dict:
        """
        Get GAAP/IFRS compliance status summary
        
        Returns:
            Dictionary with compliance statistics
        """
        total_entries = self.db.query(JournalEntry).filter(
            JournalEntry.status == "POSTED"
        ).count()
        
        gaap_compliant = self.db.query(JournalEntry).filter(
            and_(
                JournalEntry.status == "POSTED",
                JournalEntry.gaap_compliant == True
            )
        ).count()
        
        ifrs_compliant = self.db.query(JournalEntry).filter(
            and_(
                JournalEntry.status == "POSTED",
                JournalEntry.ifrs_compliant == True
            )
        ).count()
        
        gaap_violations = total_entries - gaap_compliant
        ifrs_violations = total_entries - ifrs_compliant
        
        compliance_rate = 0.0
        if total_entries > 0:
            compliance_rate = (gaap_compliant + ifrs_compliant) / (2 * total_entries) * 100
        
        return {
            "total_entries": total_entries,
            "gaap_compliant_entries": gaap_compliant,
            "ifrs_compliant_entries": ifrs_compliant,
            "gaap_violations": gaap_violations,
            "ifrs_violations": ifrs_violations,
            "compliance_rate": round(compliance_rate, 2)
        }
