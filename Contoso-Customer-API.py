"""
Contoso Customer API
Synthetic source code for Microsoft Purview DLP lab testing.
No production credentials, customer data, or external services are used.
"""

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, List, Optional
import hashlib
import json
import logging
import re
import uuid

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("contoso.customer.api")


@dataclass
class Customer:
    customer_id: str
    first_name: str
    last_name: str
    email: str
    status: str = "ACTIVE"

    def to_dict(self) -> Dict[str, str]:
        return asdict(self)


class CustomerValidator:
    CUSTOMER_ID_PATTERN = re.compile(r"^CUS[0-9]{5}$")
    EMAIL_PATTERN = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")

    @classmethod
    def validate_customer_id(cls, customer_id: str) -> bool:
        return bool(cls.CUSTOMER_ID_PATTERN.match(customer_id))

    @classmethod
    def validate_email(cls, email: str) -> bool:
        return bool(cls.EMAIL_PATTERN.match(email))

    @classmethod
    def validate_customer(cls, customer: Customer) -> None:
        if not cls.validate_customer_id(customer.customer_id):
            raise ValueError("Invalid Contoso customer ID format")
        if not cls.validate_email(customer.email):
            raise ValueError("Invalid customer email address")
        if not customer.first_name.strip() or not customer.last_name.strip():
            raise ValueError("Customer name cannot be empty")


class AuditService:
    def __init__(self) -> None:
        self.events: List[Dict[str, str]] = []

    def record(self, action: str, customer_id: str) -> None:
        event = {
            "event_id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "action": action,
            "customer_id_hash": hashlib.sha256(customer_id.encode("utf-8")).hexdigest(),
        }
        self.events.append(event)
        logger.info("Audit event recorded: %s", action)

    def export(self) -> str:
        return json.dumps(self.events, indent=2)


class CustomerRepository:
    def __init__(self) -> None:
        self._customers: Dict[str, Customer] = {}

    def create(self, customer: Customer) -> Customer:
        if customer.customer_id in self._customers:
            raise KeyError("Customer already exists")
        self._customers[customer.customer_id] = customer
        return customer

    def get(self, customer_id: str) -> Optional[Customer]:
        return self._customers.get(customer_id)

    def update_email(self, customer_id: str, email: str) -> Customer:
        customer = self.get(customer_id)
        if customer is None:
            raise KeyError("Customer not found")
        if not CustomerValidator.validate_email(email):
            raise ValueError("Invalid email address")
        customer.email = email
        return customer

    def deactivate(self, customer_id: str) -> Customer:
        customer = self.get(customer_id)
        if customer is None:
            raise KeyError("Customer not found")
        customer.status = "INACTIVE"
        return customer

    def list_active(self) -> List[Customer]:
        return [c for c in self._customers.values() if c.status == "ACTIVE"]


class CustomerAPI:
    def __init__(self, repository: CustomerRepository, audit: AuditService) -> None:
        self.repository = repository
        self.audit = audit

    def create_customer(self, payload: Dict[str, str]) -> Dict[str, str]:
        required = {"customer_id", "first_name", "last_name", "email"}
        missing = required.difference(payload)
        if missing:
            raise ValueError(f"Missing required fields: {', '.join(sorted(missing))}")

        customer = Customer(
            customer_id=payload["customer_id"],
            first_name=payload["first_name"],
            last_name=payload["last_name"],
            email=payload["email"],
        )
        CustomerValidator.validate_customer(customer)
        created = self.repository.create(customer)
        self.audit.record("CUSTOMER_CREATED", created.customer_id)
        return created.to_dict()

    def get_customer(self, customer_id: str) -> Dict[str, str]:
        if not CustomerValidator.validate_customer_id(customer_id):
            raise ValueError("Invalid customer ID")
        customer = self.repository.get(customer_id)
        if customer is None:
            raise KeyError("Customer not found")
        self.audit.record("CUSTOMER_READ", customer.customer_id)
        return customer.to_dict()

    def change_customer_email(self, customer_id: str, new_email: str) -> Dict[str, str]:
        updated = self.repository.update_email(customer_id, new_email)
        self.audit.record("CUSTOMER_EMAIL_UPDATED", customer_id)
        return updated.to_dict()

    def deactivate_customer(self, customer_id: str) -> Dict[str, str]:
        updated = self.repository.deactivate(customer_id)
        self.audit.record("CUSTOMER_DEACTIVATED", customer_id)
        return updated.to_dict()

    def active_customers(self) -> List[Dict[str, str]]:
        return [c.to_dict() for c in self.repository.list_active()]


def run_demo() -> None:
    api = CustomerAPI(CustomerRepository(), AuditService())

    payload = {
        "customer_id": "CUS10002",
        "first_name": "Alex",
        "last_name": "Morgan",
        "email": "alex.morgan@example.test",
    }

    print(json.dumps(api.create_customer(payload), indent=2))
    print(json.dumps(api.get_customer("CUS10002"), indent=2))
    print(json.dumps(
        api.change_customer_email("CUS10002", "alex.updated@example.test"),
        indent=2,
    ))
    print(json.dumps(api.active_customers(), indent=2))


if __name__ == "__main__":
    run_demo()
