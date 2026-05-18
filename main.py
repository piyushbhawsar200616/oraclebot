import asyncio
import json
import logging
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import websockets
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Oracle Bot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

session_data = {
    "token": None,
    "balance": 0,
    "mode": "PRACTICE"
}

class LoginRequest(BaseModel):
    email: str
    password: str
    account_mode: str = "PRACTICE"

class TradeRequest(BaseModel):
    asset: str
    direction: str
    amount: float
    duration: int
    account_mode: str = "PRACTICE"

@app.get("/")
def root():
    return {"status": "Oracle Bot API running"}

@app.post("/login")
async def login(req: LoginRequest):
    try:
        session_data["mode"] = req.account_mode
        session_data["token"] = f"demo_{req.email}"
        session_data["balance"] = 10000.0
        return {
            "success": True,
            "balance": session_data["balance"],
            "account_mode": req.account_mode,
            "profile": req.email,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/balance")
async def get_balance():
    if not session_data["token"]:
        raise HTTPException(status_code=401, detail="Not connected")
    return {"balance": session_data["balance"]}

@app.post("/trade")
async def place_trade(req: TradeRequest):
    if not session_data["token"]:
        raise HTTPException(status_code=401, detail="Not connected")
    try:
        import random
        trade_id = random.randint(100000, 999999)
        logger.info(f"Trade: {req.asset} {req.direction} ${req.amount}")
        return {
            "success": True,
            "trade_id": trade_id,
            "asset": req.asset,
            "direction": req.direction,
            "amount": req.amount,
            "duration": req.duration,
            "time": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/result/{trade_id}")
async def check_result(trade_id: int):
    if not session_data["token"]:
        raise HTTPException(status_code=401, detail="Not connected")
    import random
    win = random.random() > 0.5
    profit = 8.0 if win else -10.0
    session_data["balance"] += profit
    return {
        "trade_id": trade_id,
        "result": "WIN" if win else "LOSS",
        "profit": profit,
        "balance": session_data["balance"],
    }

@app.get("/assets")
async def get_assets():
    return {
        "assets": ["EURUSD_otc","GBPUSD_otc","EURUSD","GBPUSD","XAUUSD"],
        "payments": {"EURUSD_otc": 85, "GBPUSD_otc": 82}
    }

@app.post("/disconnect")
async def disconnect():
    session_data["token"] = None
    return {"success": True}

if name == "main":
    import uvicorn
    import os
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
