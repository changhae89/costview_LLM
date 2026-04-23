from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import category, causal, consumer_item, dashboard, indicators, news

app = FastAPI(title="Costview API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:4173"],
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


@app.get("/")
def root():
    return {"message": "Costview Backend API Server is running."}
