import main
from library_routes import router as library_router

main.APP_VERSION = "0.7.0"
app = main.app
app.version = main.APP_VERSION
app.include_router(library_router)
