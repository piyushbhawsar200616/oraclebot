# ============================================================
#  ORACLE BOT — Python FastAPI Backend
#  File: main.py
#  Run: python main.py
#  Requires: pip install fastapi uvicorn pyquotex
# ============================================================

import asyncio
import logging
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pyquotex.stable_api import Quotex

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(name)

app = FastAPI(title="Oracle Bot API")

# Allow React frontend to call this backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Global client state ──────────────────────────────────────
client: Quotex = None
is_connected: bool = False

# ── Request models ───────────────────────────────────────────
class LoginRequest(BaseModel):
    email: str
    password: str
    account_mode: str = "PRACTICE"   # PRACTICE or REAL

class TradeRequest(BaseModel):
    asset: str          # e.g. "EURUSD" or "EURUSD_otc"
    direction: str      # "call" or "put"
    amount: float       # e.g. 10.0
    duration: int       # seconds: 60, 300, etc.
    account_mode: str = "PRACTICE"

# ── Routes ───────────────────────────────────────────────────

@app.get("/")
def root():
    return {"status": "Oracle Bot API running"}


@app.post("/login")
async def login(req: LoginRequest):
    global client, is_connected
    try:
        client = Quotex(
            email=req.email,
            password=req.password,
            lang="en",
        )
        client.set_account_mode(req.account_mode)
        check, reason = await client.connect()
        if not check:
            raise HTTPException(status_code=401, detail=f"Login failed: {reason}")
        is_connected = True
        balance = await client.get_balance()
        profile = await client.get_profile()
        return {
            "success": True,
            "balance": balance,
            "account_mode": req.account_mode,
            "profile": str(profile),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/balance")
async def get_balance():
    _require_connection()
    try:
        balance = await client.get_balance()
        return {"balance": balance}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/trade")
async def place_trade(req: TradeRequest):
    _require_connection()
    try:
        # Switch account mode if needed
        client.set_account_mode(req.account_mode)

        # Check asset is available (auto-switch to OTC if closed)
        asset, asset_info = await client.get_available_asset(req.asset, force_open=True)
        if not asset_info or not asset_info[2]:
            raise HTTPException(status_code=400, detail=f"Asset {req.asset} is not available right now")

        # Place the trade
        status, trade_id = await client.buy(
            amount=req.amount,
            asset=asset,
            direction=req.direction,
            duration=req.duration,
        )

        if not status:
            raise HTTPException(status_code=400, detail="Trade placement failed")

        logger.info(f"Trade placed: {asset} {req.direction} ${req.amount} ID={trade_id}")

        return {
            "success": True,
            "trade_id": trade_id,
            "asset": asset,
            "direction": req.direction,
            "amount": req.amount,
            "duration": req.duration,
            "time": datetime.now().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Trade error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
@app.get("/result/{trade_id}")
async def check_result(trade_id: int):
    _require_connection()
    try:
        result = await client.check_win(trade_id)
        balance = await client.get_balance()
        return {
            "trade_id": trade_id,
            "result": "WIN" if result > 0 else "LOSS",
            "profit": result,
            "balance": balance,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/assets")
async def get_assets():
    _require_connection()
    try:
        assets = client.get_all_asset_name()
        payments = client.get_payment()
        return {"assets": assets, "payments": payments}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/disconnect")
async def disconnect():
    global client, is_connected
    if client:
        await client.close()
    is_connected = False
    client = None
    return {"success": True}


# ── Helper ───────────────────────────────────────────────────
def _require_connection():
    if not client or not is_connected:
        raise HTTPException(status_code=401, detail="Not connected. Call /login first.")


# ── Run server ───────────────────────────────────────────────
if name == "main":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
