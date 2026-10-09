"""Deterministic demo data: two tenants, ~25 employees each, 3 months of history (FR-03).

Runs as the table owner (MIGRATION_DATABASE_URL), so RLS does not apply here.
Usage:  python -m app.seed.seed
"""

import random
from dataclasses import dataclass
from datetime import date, time, timedelta
from decimal import Decimal

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.context import Role
from app.core.security import hash_password
from app.models import (
    Attendance,
    AttendanceStatus,
    Company,
    Employee,
    LeaveBalance,
    LeaveRequest,
    LeaveStatus,
    LeaveType,
    Payslip,
    Tenant,
    User,
)
from app.services.leave_rules import working_days


@dataclass(frozen=True)
class Person:
    name: str
    department: str
    title: str
    role: Role = Role.EMPLOYEE
    manager: str | None = None  # name of the manager within the same tenant
    email: str | None = None  # override for persona logins


ACME_PEOPLE = [
    Person("Kamran Siddiqui", "Executive", "Chief Executive Officer", Role.MANAGER),
    Person(
        "Sara Ahmed",
        "People & Culture",
        "HR Manager",
        Role.HR_ADMIN,
        "Kamran Siddiqui",
        "sara@acme.test",
    ),
    Person(
        "Bilal Khan",
        "Engineering",
        "Engineering Manager",
        Role.MANAGER,
        "Kamran Siddiqui",
        "bilal@acme.test",
    ),
    Person(
        "Ayesha Malik",
        "Engineering",
        "Software Engineer",
        Role.EMPLOYEE,
        "Bilal Khan",
        "ayesha@acme.test",
    ),
    Person("Hamza Raza", "Engineering", "Senior Software Engineer", manager="Bilal Khan"),
    Person("Fatima Noor", "Engineering", "QA Engineer", manager="Bilal Khan"),
    Person("Usman Tariq", "Engineering", "DevOps Engineer", manager="Bilal Khan"),
    Person("Zainab Hussain", "Engineering", "Frontend Engineer", manager="Bilal Khan"),
    Person("Ali Haider", "Engineering", "Backend Engineer", manager="Bilal Khan"),
    Person("Mahnoor Iqbal", "Sales", "Head of Sales", Role.MANAGER, "Kamran Siddiqui"),
    Person("Ali Raza", "Sales", "Account Executive", manager="Mahnoor Iqbal"),
    Person("Hira Shah", "Sales", "Account Executive", manager="Mahnoor Iqbal"),
    Person("Saad Mirza", "Sales", "Sales Development Rep", manager="Mahnoor Iqbal"),
    Person("Noor Fatima", "Sales", "Customer Success Manager", manager="Mahnoor Iqbal"),
    Person("Imran Qureshi", "Finance", "Finance Manager", Role.MANAGER, "Kamran Siddiqui"),
    Person("Sana Javed", "Finance", "Accountant", manager="Imran Qureshi"),
    Person("Faisal Abbasi", "Finance", "Payroll Specialist", manager="Imran Qureshi"),
    Person("Amna Rafiq", "People & Culture", "Talent Acquisition Lead", manager="Sara Ahmed"),
    Person("Danish Aslam", "People & Culture", "HR Generalist", manager="Sara Ahmed"),
    Person("Rabia Anwar", "Operations", "Operations Manager", Role.MANAGER, "Kamran Siddiqui"),
    Person("Waqas Butt", "Operations", "Office Administrator", manager="Rabia Anwar"),
    Person("Mehwish Akram", "Operations", "Procurement Officer", manager="Rabia Anwar"),
    Person("Adeel Chaudhry", "Operations", "IT Support Specialist", manager="Rabia Anwar"),
    Person("Kiran Yousaf", "Marketing", "Marketing Lead", manager="Kamran Siddiqui"),
    Person("Shahzaib Ali", "Marketing", "Content Strategist", manager="Kiran Yousaf"),
]

GLOBEX_PEOPLE = [
    Person("Tariq Mehmood", "Executive", "Managing Director", Role.MANAGER),
    Person(
        "Nadia Hassan",
        "Human Resources",
        "HR Director",
        Role.HR_ADMIN,
        "Tariq Mehmood",
        "nadia@globex.test",
    ),
    Person(
        "Asad Farooq",
        "Product",
        "Product Manager",
        Role.MANAGER,
        "Tariq Mehmood",
        "asad@globex.test",
    ),
    Person(
        "Omar Sheikh",
        "Product",
        "Product Designer",
        Role.EMPLOYEE,
        "Asad Farooq",
        "omar@globex.test",
    ),
    Person("Maria Khalid", "Product", "UX Researcher", manager="Asad Farooq"),
    Person("Junaid Akhtar", "Product", "Data Analyst", manager="Asad Farooq"),
    Person("Sadia Rehman", "Product", "Product Analyst", manager="Asad Farooq"),
    Person("Bushra Saleem", "Engineering", "Engineering Lead", Role.MANAGER, "Tariq Mehmood"),
    Person("Kashif Nawaz", "Engineering", "Mobile Engineer", manager="Bushra Saleem"),
    Person("Ayesha Siddiqa", "Engineering", "Backend Engineer", manager="Bushra Saleem"),
    Person("Rizwan Ashraf", "Engineering", "Site Reliability Engineer", manager="Bushra Saleem"),
    Person("Laiba Zafar", "Engineering", "Frontend Engineer", manager="Bushra Saleem"),
    Person("Ahmed Bilal", "Engineering", "QA Lead", manager="Bushra Saleem"),
    Person("Farah Naz", "Finance", "Finance Controller", Role.MANAGER, "Tariq Mehmood"),
    Person("Haris Jamil", "Finance", "Financial Analyst", manager="Farah Naz"),
    Person("Samina Riaz", "Finance", "Accounts Officer", manager="Farah Naz"),
    Person("Zeeshan Haider", "Human Resources", "HR Officer", manager="Nadia Hassan"),
    Person("Uzma Khan", "Human Resources", "Learning & Development", manager="Nadia Hassan"),
    Person("Naveed Iqbal", "Sales", "Sales Manager", Role.MANAGER, "Tariq Mehmood"),
    Person("Areeba Shah", "Sales", "Account Manager", manager="Naveed Iqbal"),
    Person("Moiz Qadir", "Sales", "Business Developer", manager="Naveed Iqbal"),
    Person("Hina Altaf", "Sales", "Sales Coordinator", manager="Naveed Iqbal"),
    Person("Shoaib Aziz", "Operations", "Operations Lead", manager="Tariq Mehmood"),
    Person("Rubina Kausar", "Operations", "Facilities Officer", manager="Shoaib Aziz"),
]

TENANTS = [
    {
        "name": "Acme Corp",
        "slug": "acme",
        "company": "Acme Corp (Pvt) Ltd",
        "domain": "acme.test",
        "code_prefix": "ACM",
        "people": ACME_PEOPLE,
        "quotas": {
            "CASUAL": ("Casual Leave", 10),
            "SICK": ("Sick Leave", 8),
            "ANNUAL": ("Annual Leave", 14),
        },
    },
    {
        "name": "Globex Ltd",
        "slug": "globex",
        "company": "Globex Ltd",
        "domain": "globex.test",
        "code_prefix": "GBX",
        "people": GLOBEX_PEOPLE,
        "quotas": {
            "CASUAL": ("Casual Leave", 12),
            "SICK": ("Sick Leave", 10),
            "ANNUAL": ("Annual Leave", 18),
        },
    },
]

SALARY_BANDS = {
    "Chief Executive Officer": 1_200_000,
    "Managing Director": 1_100_000,
    "HR Manager": 450_000,
    "HR Director": 520_000,
}


def _salary(person: Person, rng: random.Random) -> Decimal:
    if person.title in SALARY_BANDS:
        base = SALARY_BANDS[person.title]
    elif person.role is Role.MANAGER:
        base = rng.randrange(380_000, 600_000, 5_000)
    elif "Senior" in person.title or "Lead" in person.title:
        base = rng.randrange(280_000, 400_000, 5_000)
    else:
        base = rng.randrange(140_000, 280_000, 5_000)
    return Decimal(base)


def _email_for(person: Person, domain: str) -> str:
    if person.email:
        return person.email
    first, last = person.name.lower().split(" ", 1)
    return f"{first}.{last.replace(' ', '')}@{domain}"


def _months_back(today: date, count: int) -> list[date]:
    months, cursor = [], today.replace(day=1)
    for _ in range(count):
        cursor = (cursor - timedelta(days=1)).replace(day=1)
        months.append(cursor)
    return sorted(months)


def _next_weekday(d: date, weekday: int) -> date:
    return d + timedelta(days=(weekday - d.weekday()) % 7 or 7)


def _seed_attendance(
    session: Session, emp: Employee, start: date, end: date, rng: random.Random
) -> None:
    day = start
    while day < end:
        if day.weekday() < 5:
            roll = rng.random()
            if roll < 0.04:
                status, cin, cout = AttendanceStatus.ABSENT, None, None
            elif roll < 0.14:
                status = AttendanceStatus.WFH
                cin, cout = time(9, rng.randint(0, 20)), time(17, rng.randint(30, 59))
            elif roll < 0.26:
                status = AttendanceStatus.LATE
                cin, cout = time(10, rng.randint(0, 45)), time(18, rng.randint(15, 59))
            else:
                status = AttendanceStatus.PRESENT
                cin, cout = time(8, rng.randint(40, 59)), time(17, rng.randint(30, 59))
            session.add(
                Attendance(
                    tenant_id=emp.tenant_id,
                    employee_id=emp.id,
                    date=day,
                    check_in=cin,
                    check_out=cout,
                    status=status,
                )
            )
        day += timedelta(days=1)


def seed() -> None:
    settings = get_settings()
    if not settings.demo_password:
        raise SystemExit("Set DEMO_PASSWORD in .env before seeding.")
    engine = create_engine(settings.migration_database_url)
    rng = random.Random(42)  # deterministic: the same seed always yields the same data
    today = date.today()
    password_hash = hash_password(settings.demo_password)

    with Session(engine) as session, session.begin():
        session.execute(
            text(
                "TRUNCATE tenants, users, audit_log, documents, doc_chunks RESTART IDENTITY CASCADE"
            )
        )

        for spec in TENANTS:
            tenant = Tenant(name=spec["name"], slug=spec["slug"], plan="standard")
            session.add(tenant)
            session.flush()
            company = Company(tenant_id=tenant.id, name=spec["company"])
            session.add(company)
            session.flush()

            leave_types = {
                code: LeaveType(tenant_id=tenant.id, code=code, name=name, annual_quota=quota)
                for code, (name, quota) in spec["quotas"].items()
            }
            session.add_all(leave_types.values())

            employees: dict[str, Employee] = {}
            people: list[Person] = spec["people"]
            for idx, person in enumerate(people, start=1):
                employees[person.name] = Employee(
                    tenant_id=tenant.id,
                    company_id=company.id,
                    employee_code=f"{spec['code_prefix']}-{1000 + idx}",
                    full_name=person.name,
                    email=_email_for(person, spec["domain"]),
                    department=person.department,
                    job_title=person.title,
                    join_date=today - timedelta(days=rng.randint(20, 6 * 365)),
                    salary=_salary(person, rng),
                    national_id=f"{rng.randint(35000, 42999)}-{rng.randint(1000000, 9999999)}"
                    f"-{rng.randint(1, 9)}",
                )
            session.add_all(employees.values())
            session.flush()

            for person in people:
                emp = employees[person.name]
                if person.manager:
                    emp.manager_id = employees[person.manager].id
                session.add(
                    User(
                        tenant_id=tenant.id,
                        company_id=company.id,
                        employee_id=emp.id,
                        email=emp.email,
                        password_hash=password_hash,
                        role=person.role.value,
                    )
                )
                for lt in leave_types.values():
                    session.add(
                        LeaveBalance(
                            tenant_id=tenant.id,
                            employee_id=emp.id,
                            leave_type_id=lt.id,
                            year=today.year,
                            allocated=Decimal(lt.annual_quota),
                            used=Decimal(rng.randint(0, lt.annual_quota // 3)),
                        )
                    )

                history_start = _months_back(today, 3)[0]
                _seed_attendance(session, emp, history_start, today, rng)
                for month in _months_back(today, 3):
                    gross = emp.salary
                    deductions = (gross * Decimal("0.12")).quantize(Decimal("1"))
                    session.add(
                        Payslip(
                            tenant_id=tenant.id,
                            employee_id=emp.id,
                            month=month,
                            gross=gross,
                            deductions=deductions,
                            net=gross - deductions,
                        )
                    )
            session.flush()

            # A few realistic open requests so the approval flows have something to show.
            pending = [p for p in people if p.manager and rng.random() < 0.3]
            demo_requesters = [p for p in people if p.email and p.role is not Role.HR_ADMIN]
            for person in {p.name: p for p in pending + demo_requesters}.values():
                start = _next_weekday(today + timedelta(days=rng.randint(5, 30)), 0)
                end = start + timedelta(days=rng.choice([0, 1, 2]))
                lt = leave_types[rng.choice(["CASUAL", "ANNUAL"])]
                session.add(
                    LeaveRequest(
                        tenant_id=tenant.id,
                        employee_id=employees[person.name].id,
                        leave_type_id=lt.id,
                        start_date=start,
                        end_date=end,
                        days=working_days(start, end),
                        reason="Personal commitments",
                        status=LeaveStatus.PENDING,
                    )
                )

        # Platform operator: sees audit metadata across tenants but no HR data.
        session.add(
            User(
                tenant_id=None,
                company_id=None,
                employee_id=None,
                email="admin@platform.test",
                password_hash=password_hash,
                role=Role.PLATFORM_ADMIN.value,
            )
        )

    print("Seed complete. Every account uses DEMO_PASSWORD from .env.")
    for email in [
        "ayesha@acme.test (EMPLOYEE)",
        "bilal@acme.test (MANAGER)",
        "sara@acme.test (HR_ADMIN)",
        "omar@globex.test (EMPLOYEE, Globex)",
        "admin@platform.test (PLATFORM_ADMIN)",
    ]:
        print("  -", email)


if __name__ == "__main__":
    seed()
