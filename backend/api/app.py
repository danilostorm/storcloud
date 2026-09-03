import main
from achievement_routes import router as achievement_router
from activity_routes import router as activity_router
from admin_routes import router as admin_router
from admin_claim_routes import router as admin_claim_router
from agent_activity_routes import router as agent_activity_router
from catalog_routes import router as catalog_router
from library_routes import router as library_router
from retro_metadata_routes import router as retro_metadata_router
from streaming_routes import router as streaming_router

main.APP_VERSION = "0.9.0"
app = main.app
app.version = main.APP_VERSION
app.include_router(library_router)
app.include_router(retro_metadata_router)
app.include_router(activity_router)
app.include_router(achievement_router)
app.include_router(admin_router)
app.include_router(admin_claim_router)
app.include_router(agent_activity_router)
app.include_router(catalog_router)
app.include_router(streaming_router)
