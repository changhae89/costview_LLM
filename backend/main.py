import os
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from supabase import create_client, Client

# .env 로드
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
env_path = os.path.join(root_dir, ".env")
load_dotenv(dotenv_path=env_path)

app = FastAPI(title="Cost-Vue API", description="AI 기반 인과관계 저널리즘 서비스")

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Supabase 초기화
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY) if SUPABASE_URL and SUPABASE_ANON_KEY else None

# ======== MODELS ========
class IndicatorSnapshot(BaseModel):
    label: str
    value: float
    unit: str
    change: float
    status: str 

class LogicStep(BaseModel):
    label: str
    change: str

class CausalChain(BaseModel):
    id: str
    category: str
    tags: List[str]
    title: str
    description: str
    raw_shock: str
    raw_shock_rationale: Optional[str] = ""
    logic_steps: List[LogicStep] = []
    wallet_hit: str
    transmission: str
    transmission_rationale: Optional[str] = ""
    magnitude: str
    monthly_impact: int
    created_at: Optional[str] = ""

class DashboardResponse(BaseModel):
    indicators: List[IndicatorSnapshot]
    chains: List[CausalChain]

# ======== API ENDPOINTS ========

@app.get("/api/dashboard", response_model=DashboardResponse)
async def get_dashboard():
    indicators = []
    if supabase:
        try:
            res = supabase.table("indicator_fred_daily_logs").select("*").order("reference_date", desc=True).limit(10).execute()
            if res.data:
                latest_data = {}
                prev_data = {}
                target_cols = ["fred_wti", "fred_usd_index", "fred_treasury_10y"]
                for col in target_cols:
                    values = [row[col] for row in res.data if row.get(col) is not None]
                    if values:
                        latest_data[col] = values[0]
                        prev_data[col] = values[1] if len(values) > 1 else values[0]

                if "fred_wti" in latest_data:
                    val, prev = latest_data["fred_wti"], prev_data["fred_wti"]
                    indicators.append(IndicatorSnapshot(label="WTI 유가", value=val, unit="USD/bbl", change=round(val-prev,2), status="danger" if val>90 else "warning" if val>80 else "safe"))
                if "fred_usd_index" in latest_data:
                    val, prev = latest_data["fred_usd_index"], prev_data["fred_usd_index"]
                    indicators.append(IndicatorSnapshot(label="달러 인덱스", value=val, unit="index", change=round(val-prev,2), status="warning" if val>105 else "safe"))
                if "fred_treasury_10y" in latest_data:
                    val, prev = latest_data["fred_treasury_10y"], prev_data["fred_treasury_10y"]
                    indicators.append(IndicatorSnapshot(label="미 국채 10년", value=val, unit="%", change=round(val-prev,2), status="danger" if val>4.5 else "safe"))
        except Exception as e:
            print(f"지표 에러: {e}")

    chains = []
    if supabase:
        try:
            res = supabase.table("causal_chains").select("*").order("created_at", desc=True).limit(10).execute()
            if res.data:
                for item in res.data:
                    # Logic Steps 필드 유연하게 처리
                    raw_steps = item.get("logic_steps", [])
                    processed_steps = []
                    if isinstance(raw_steps, list):
                        for s in raw_steps:
                            # 다양한 필드명 대응 (label/step, change/description)
                            label = s.get("label") or s.get("description") or f"Step {s.get('step', '')}"
                            change = s.get("change") or (f"+{s.get('value')}%" if s.get('value') else "분석 중")
                            processed_steps.append(LogicStep(label=str(label), change=str(change)))
                    
                    chains.append(CausalChain(
                        id=str(item.get("id", "")),
                        category=item.get("category", "others"),
                        tags=item.get("tags", ["Economy"]),
                        title=item.get("event", "Unnamed Insight"),
                        description=item.get("mechanism", ""),
                        raw_shock=f"+{item.get('raw_shock_percent', 0)}%",
                        raw_shock_rationale=item.get("raw_shock_rationale", "분석 중..."),
                        logic_steps=processed_steps,
                        wallet_hit=f"+{item.get('wallet_hit_percent', 0)}%",
                        transmission=f"{item.get('transmission_time_months', 1)}개월",
                        transmission_rationale=item.get("transmission_rationale", "분석 중..."),
                        magnitude=item.get("magnitude", "medium"),
                        monthly_impact=item.get("monthly_impact", 0),
                        created_at=item.get("created_at", "")
                    ))
        except Exception as e:
            print(f"인과관계 에러: {e}")

    return {"indicators": indicators, "chains": chains}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
