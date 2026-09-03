import main
from achievement_routes import router as achievement_router
from activity_routes import router as activity_router
from admin_routes import router as admin_router
from library_routes import router as library_router

main.APP_VERSION = "0.8.0"
app = main.app
app.version = main.APP_VERSION
app.include_router(library_router)
app.include_router(activity_router)
app.include_router(achievement_router)
app.include_router(admin_router)
