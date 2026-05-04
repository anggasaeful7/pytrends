from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pytrends.request import TrendReq
from typing import Optional
import time

app = FastAPI(title="PyTrends API", description="API untuk mengambil data Google Trends")

# CORS middleware - penting untuk keperluan development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Model data untuk request
class TrendRequest(BaseModel):
    keyword: str
    timeframe: str = "now 7-d"  # opsional: default 7 hari terakhir

# Helper untuk fetch dari PyTrends dengan rate limiting untuk mencegah block
def get_pytrends_data(keyword: str, timeframe: str = "now 7-d"):
    try:
        # Rate limiting untuk menghindari deteksi bot oleh Google
        time.sleep(60)  # jeda 60 detik antar request
        
        pytrends = TrendReq(hl='en-US', tz=360)
        pytrends.build_payload(kw_list=[keyword], timeframe=timeframe)
        
        interest_over_time_df = pytrends.interest_over_time()
        if interest_over_time_df.empty:
            return {"error": "No data found", "keyword": keyword, "timeframe": timeframe}
        
        # Format hasil untuk mudah digunakan
        data = []
        for date, row in interest_over_time_df.iterrows():
            data.append({
                "date": date.strftime("%Y-%m-%d"),
                "value": int(row[keyword]) if not pd.isna(row[keyword]) else 0
            })
        
        # Ambil topik terkait
        related_queries = pytrends.related_queries()
        related_top = []
        if keyword in related_queries and 'top' in related_queries[keyword]:
            top_df = related_queries[keyword]['top']
            if top_df is not None and not top_df.empty:
                related_top = top_df['query'].head(5).tolist()
        
        return {
            "keyword": keyword,
            "timeframe": timeframe,
            "data": data,
            "average": sum(d['value'] for d in data) / len(data) if data else 0,
            "related_queries": related_top
        }
    except Exception as e:
        return {"error": str(e), "keyword": keyword}

@app.post("/trends")
async def get_trends(request: TrendRequest):
    result = get_pytrends_data(request.keyword, request.timeframe)
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
    return result

@app.get("/")
async def root():
    return {"message": "PyTrends API is running", "endpoint": "/trends (POST)"}