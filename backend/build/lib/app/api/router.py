from fastapi import APIRouter

from app.api.v1 import audit, auth, employees, leave, records

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(employees.router)
api_router.include_router(leave.router)
api_router.include_router(records.router)
api_router.include_router(audit.router)
