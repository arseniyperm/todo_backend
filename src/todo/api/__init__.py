from fastapi import APIRouter

from .auth import router as auth_router
from .todo import router as todos_router


router = APIRouter()
router.include_router(auth_router)
router.include_router(todos_router)
