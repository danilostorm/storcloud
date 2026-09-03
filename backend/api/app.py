from main import app
from library_routes import router as library_router

app.include_router(library_router)
