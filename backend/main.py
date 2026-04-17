from fastapi import FastAPI
from api.routes import category

app = FastAPI(title="Costview API", version="1.0.0")

# Register routes
app.include_router(category.router, prefix="/api/v1/categories")

@app.get("/")
async def root():
    return {"message": "Costview Backend API Server is running."}

# 향후 프론트엔드가 요청할 API 엔드포인트 뼈대 (Node.js에서 마이그레이션)
@app.get("/api/news")
async def get_news():
    return {"message": "News endpoint ready to be wired"}

@app.get("/api/indicators/latest")
async def get_latest_indicators():
    return {"message": "Indicators endpoint ready to be wired"}

