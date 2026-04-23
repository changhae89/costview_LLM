from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import get_cors_allow_origins
from api.routes import briefing, category, causal, consumer_item, dashboard, indicators, mobile, news

app = FastAPI(title="Costview API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_allow_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(category.router,      prefix="/api/v1/categories")
app.include_router(consumer_item.router, prefix="/api/v1/consumer-items")
app.include_router(dashboard.router,     prefix="/api/v1/dashboard")
app.include_router(indicators.router,    prefix="/api/v1/indicators")
app.include_router(news.router,          prefix="/api/v1/news")
app.include_router(causal.router,        prefix="/api/v1/causal")
app.include_router(briefing.router,      prefix="/api/v1/briefing")
app.include_router(mobile.router,        prefix="/api/v1/mobile")


@app.get("/")
def root():
    return {"message": "Costview Backend API Server is running."}
