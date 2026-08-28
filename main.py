import os
import sqlite3
import pandas as pd
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

app = FastAPI()

if not os.path.exists("templates"):
    os.makedirs("templates")

templates = Jinja2Templates(directory="templates")

# Initialize Database for Paper Trading Dashboard
def init_db():
    conn = sqlite3.connect("paper_trader.db")
    cursor = conn.cursor()
    
    # Running Positions table
    cursor.execute('''CREATE TABLE IF NOT EXISTS positions (
                        ticket INTEGER PRIMARY KEY AUTOINCREMENT,
                        provider TEXT, symbol TEXT, type TEXT, 
                        volume REAL, price_open REAL, sl REAL, tp REAL, profit REAL)''')
    
    # Managed Accounts table
    cursor.execute('''CREATE TABLE IF NOT EXISTS accounts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        login TEXT, server TEXT, password TEXT, lot_size REAL, 
                        balance REAL, pl REAL, status INTEGER)''')
    
    # Signal Logs table
    cursor.execute('''CREATE TABLE IF NOT EXISTS signals (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        channel TEXT, symbol TEXT, action TEXT, 
                        entry TEXT, tp TEXT, confidence INTEGER, time TEXT, status TEXT)''')
    
    # Providers ranking table
    cursor.execute('''CREATE TABLE IF NOT EXISTS providers (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT, signals INTEGER, wins INTEGER, losses INTEGER, status INTEGER)''')
    
    # Loss logs table
    cursor.execute('''CREATE TABLE IF NOT EXISTS loss_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        channel TEXT, symbol TEXT, reason TEXT, timestamp TEXT)''')
    
    # Assets table
    cursor.execute('''CREATE TABLE IF NOT EXISTS assets (
                        symbol TEXT PRIMARY KEY, status INTEGER)''')
    
    conn.commit()
    
    # Populate default data from top_50_paper_test.csv if available
    cursor.execute("SELECT COUNT(*) FROM providers")
    if cursor.fetchone()[0] == 0:
        if os.path.exists("top_50_paper_test.csv"):
            df_top = pd.read_csv("top_50_paper_test.csv")
            for _, row in df_top.iterrows():
                cursor.execute("INSERT INTO providers (name, signals, wins, losses, status) VALUES (?, 15, 10, 5, 1)", 
                               (row['Channel Name'],))
        else:
            cursor.execute("INSERT INTO providers (name, signals, wins, losses, status) VALUES ('Pullback Signal 🥇', 20, 14, 6, 1)")
            cursor.execute("INSERT INTO providers (name, signals, wins, losses, status) VALUES ('Smart Money Trader', 18, 12, 6, 1)")

    # Populate default assets if empty
    cursor.execute("SELECT COUNT(*) FROM assets")
    if cursor.fetchone()[0] == 0:
        default_assets = [("XAUUSD", 1), ("EURUSD", 1), ("GBPUSD", 1), ("BTCUSD", 1), ("NAS100", 1)]
        cursor.executemany("INSERT OR IGNORE INTO assets (symbol, status) VALUES (?, ?)", default_assets)
        
    # Populate a sample account if empty
    cursor.execute("SELECT COUNT(*) FROM accounts")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO accounts (login, server, password, lot_size, balance, pl, status) VALUES ('99887766', 'Demo-Server', 'secret', 0.01, 10500.00, 142.50, 1)",)
        
    # Populate sample position if empty
    cursor.execute("SELECT COUNT(*) FROM positions")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO positions (provider, symbol, type, volume, price_open, sl, tp, profit) VALUES ('Pullback Signal 🥇', 'XAUUSD', 'BUY', 0.10, 2350.20, 2345.00, 2365.00, 124.50)")

    # Populate sample signal logs if empty
    cursor.execute("SELECT COUNT(*) FROM signals")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO signals (channel, symbol, action, entry, tp, confidence, time, status) VALUES ('Pullback Signal 🥇', 'XAUUSD', 'BUY', '2350.20', 'TP1: 2355, TP2: 2365', 95, '2026-08-28 01:25', 'Executed')")

    conn.commit()
    conn.close()

init_db()

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    conn = sqlite3.connect("paper_trader.db")
    cursor = conn.cursor()
    
    cursor.execute("SELECT SUM(balance), SUM(pl) FROM accounts WHERE status = 1")
    res = cursor.fetchone()
    total_balance = res[0] if res[0] else 10000.0
    total_pl = res[1] if res[1] else 0.0
    
    cursor.execute("SELECT COUNT(*) FROM accounts WHERE status = 1")
    active_accounts_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT * FROM positions")
    live_positions = cursor.fetchall()
    
    cursor.execute("SELECT * FROM accounts")
    accounts = cursor.fetchall()
    
    cursor.execute("SELECT channel, symbol, action, entry, tp, confidence, time, status FROM signals ORDER BY id DESC LIMIT 20")
    signal_logs = cursor.fetchall()
    
    cursor.execute("SELECT name, signals, wins, losses, status FROM providers")
    providers = cursor.fetchall()
    
    cursor.execute("SELECT channel, symbol, reason, timestamp FROM loss_logs")
    loss_logs = cursor.fetchall()
    
    cursor.execute("SELECT symbol, status FROM assets")
    assets = cursor.fetchall()
    
    conn.close()
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "total_balance": total_balance,
        "total_pl": total_pl,
        "today_generated": 48,
        "today_executed": 12,
        "active_accounts_count": active_accounts_count,
        "live_positions": [{
            "ticket": p[0], "provider": p[1], "symbol": p[2], "type": p[3],
            "volume": p[4], "price_open": p[5], "sl": p[6], "tp": p[7], "profit": p[8]
        } for p in live_positions],
        "accounts": accounts,
        "signal_logs": signal_logs,
        "providers": providers,
        "loss_logs": loss_logs,
        "assets": assets,
        "confidence_threshold": 85,
        "default_lot_size": 0.01,
        "max_trades": 5,
        "tokens_used": 1420,
        "token_limit": 50000,
        "approx_cost": 0.0214
    })

@app.post("/emergency_close")
async def emergency_close():
    conn = sqlite3.connect("paper_trader.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM positions")
    conn.commit()
    conn.close()
    return RedirectResponse(url="/", status_code=303)

@app.post("/close_position/{ticket}")
async def close_position(ticket: int):
    conn = sqlite3.connect("paper_trader.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM positions WHERE ticket = ?", (ticket,))
    conn.commit()
    conn.close()
    return RedirectResponse(url="/", status_code=303)

@app.post("/add_account")
async def add_account(login: str = Form(...), server: str = Form(...), password: str = Form(...), lot_size: float = Form(...)):
    conn = sqlite3.connect("paper_trader.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO accounts (login, server, password, lot_size, balance, pl, status) VALUES (?, ?, ?, ?, 10000.0, 0.0, 1)",
                   (login, server, password, lot_size))
    conn.commit()
    conn.close()
    return RedirectResponse(url="/", status_code=303)

@app.get("/toggle_account/{acc_id}")
async def toggle_account(acc_id: int):
    conn = sqlite3.connect("paper_trader.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE accounts SET status = 1 - status WHERE id = ?", (acc_id,))
    conn.commit()
    conn.close()
    return RedirectResponse(url="/", status_code=303)

@app.post("/toggle_provider/{channel_name}")
async def toggle_provider(channel_name: str):
    conn = sqlite3.connect("paper_trader.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE providers SET status = 1 - status WHERE name = ?", (channel_name,))
    conn.commit()
    conn.close()
    return RedirectResponse(url="/", status_code=303)

@app.post("/toggle_asset/{symbol}")
async def toggle_asset(symbol: str):
    conn = sqlite3.connect("paper_trader.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE assets SET status = 1 - status WHERE symbol = ?", (symbol,))
    conn.commit()
    conn.close()
    return RedirectResponse(url="/", status_code=303)

@app.post("/update_settings")
async def update_settings(confidence_threshold: int = Form(...), default_lot_size: float = Form(...), max_trades: int = Form(...)):
    return RedirectResponse(url="/", status_code=303)