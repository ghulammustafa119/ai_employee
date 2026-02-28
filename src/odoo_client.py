"""
Mock Odoo JSON-RPC client.

This module simulates calls to Odoo Community's External JSON-RPC API.
Replace the mock methods with real JSON-RPC calls when connecting to a
live Odoo 19+ instance.

Real implementation would use:
    import xmlrpc.client
    common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
    uid = common.authenticate(db, username, password, {})
    models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')
    models.execute_kw(db, uid, password, 'account.move', 'search_read', ...)
"""

import logging
import random
from datetime import datetime

from src.config import ODOO_URL, ODOO_DB, ODOO_USERNAME, ODOO_PASSWORD

logger = logging.getLogger(__name__)


class OdooClient:
    """Mock Odoo JSON-RPC client for accounting operations."""

    def __init__(
        self,
        url: str = "",
        db: str = "",
        username: str = "",
        password: str = "",
    ):
        self.url = url or ODOO_URL
        self.db = db or ODOO_DB
        self.username = username or ODOO_USERNAME
        self.password = password or ODOO_PASSWORD
        self.uid: int | None = None

        # Mock data store
        self._invoices = [
            {"id": 1001, "partner": "Client A", "amount": 2500.00, "date": "2026-02-01", "status": "paid"},
            {"id": 1002, "partner": "Client B", "amount": 3500.00, "date": "2026-02-10", "status": "open"},
            {"id": 1003, "partner": "Client A", "amount": 1200.00, "date": "2026-02-20", "status": "draft"},
        ]
        self._payments = [
            {"id": 2001, "invoice_id": 1001, "amount": 2500.00, "date": "2026-02-15", "method": "bank_transfer"},
        ]
        self._contacts = [
            {"id": 1, "name": "Client A", "email": "clienta@example.com", "type": "customer"},
            {"id": 2, "name": "Client B", "email": "clientb@example.com", "type": "customer"},
            {"id": 3, "name": "Supplier X", "email": "supplierx@example.com", "type": "vendor"},
        ]
        self._next_id = 1004

    def authenticate(self) -> int:
        """Mock: Authenticate with Odoo and return uid."""
        self.uid = 1
        logger.info(f"[MOCK] Authenticated with Odoo at {self.url}")
        return self.uid

    def create_invoice(self, partner: str, lines: list[dict], date: str = "") -> dict:
        """Mock: Create a new invoice."""
        total = sum(l.get("quantity", 1) * l.get("unit_price", 0) for l in lines)
        invoice = {
            "id": self._next_id,
            "partner": partner,
            "amount": total,
            "date": date or datetime.now().strftime("%Y-%m-%d"),
            "status": "draft",
            "lines": lines,
        }
        self._next_id += 1
        self._invoices.append(invoice)
        logger.info(f"[MOCK] Invoice created: #{invoice['id']} for {partner}, ${total:.2f}")
        return invoice

    def get_invoices(self, status: str = "all") -> list[dict]:
        """Mock: Get invoices, optionally filtered by status."""
        if status == "all":
            return self._invoices
        return [i for i in self._invoices if i["status"] == status]

    def create_payment(self, invoice_id: int, amount: float, method: str = "bank_transfer") -> dict:
        """Mock: Record a payment for an invoice."""
        invoice = next((i for i in self._invoices if i["id"] == invoice_id), None)
        if invoice:
            invoice["status"] = "paid"

        payment = {
            "id": self._next_id,
            "invoice_id": invoice_id,
            "amount": amount,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "method": method,
        }
        self._next_id += 1
        self._payments.append(payment)
        logger.info(f"[MOCK] Payment recorded: ${amount:.2f} for invoice #{invoice_id}")
        return payment

    def get_contacts(self) -> list[dict]:
        """Mock: Get all contacts."""
        return self._contacts

    def create_contact(self, name: str, email: str, phone: str = "", contact_type: str = "customer") -> dict:
        """Mock: Create a new contact."""
        contact = {
            "id": self._next_id,
            "name": name,
            "email": email,
            "phone": phone,
            "type": contact_type,
        }
        self._next_id += 1
        self._contacts.append(contact)
        logger.info(f"[MOCK] Contact created: {name}")
        return contact

    def get_account_balance(self) -> dict:
        """Mock: Get account balances."""
        total_receivable = sum(i["amount"] for i in self._invoices if i["status"] in ("open", "draft"))
        total_received = sum(p["amount"] for p in self._payments)
        return {
            "bank_balance": total_received + 15000,
            "accounts_receivable": total_receivable,
            "total_received": total_received,
        }

    def get_financial_summary(self, period: str = "this_month") -> dict:
        """Mock: Get financial summary."""
        total_invoiced = sum(i["amount"] for i in self._invoices)
        total_paid = sum(i["amount"] for i in self._invoices if i["status"] == "paid")
        total_open = sum(i["amount"] for i in self._invoices if i["status"] == "open")

        return {
            "period": period,
            "total_invoiced": total_invoiced,
            "total_paid": total_paid,
            "total_open": total_open,
            "collection_rate": (total_paid / total_invoiced * 100) if total_invoiced > 0 else 0,
            "num_invoices": len(self._invoices),
            "num_payments": len(self._payments),
        }
