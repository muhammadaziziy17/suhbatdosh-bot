from aiogram import Router
from .private_chat import private_router
from .group_chat import group_router
from .admin import admin_router

main_router = Router()
main_router.include_router(admin_router)
main_router.include_router(private_router)
main_router.include_router(group_router)

__all__ = ["main_router"]
