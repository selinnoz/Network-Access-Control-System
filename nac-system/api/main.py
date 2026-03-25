from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import bcrypt
import uuid
from datetime import datetime

from database import get_db, check_db_connection
from redis_client import (
    check_rate_limit, increment_failed_attempts, reset_failed_attempts,
    cache_session, get_all_active_sessions, delete_session, check_redis_connection
)
from models import (
    AuthRequest, AuthResponse,
    AuthorizeRequest, AuthorizeResponse,
    AccountingRequest, UserInfo, SessionInfo
)

app = FastAPI(title="NAC Policy Engine", version="1.0.0")

# ================================================
# HEALTH CHECK
# ================================================
@app.get("/health")
async def health():
    db_ok    = await check_db_connection()
    redis_ok = await check_redis_connection()
    return {
        "status":    "ok" if (db_ok and redis_ok) else "degraded",
        "database":  "ok" if db_ok else "error",
        "redis":     "ok" if redis_ok else "error"
    }

# ================================================
# AUTH - Kimlik Doğrulama
# ================================================
@app.post("/auth", response_model=AuthResponse)
async def authenticate(req: AuthRequest, db: AsyncSession = Depends(get_db)):

    # Rate limit kontrolü
    if await check_rate_limit(req.username):
        return AuthResponse(code="Access-Reject", message="Too many failed attempts")

    # Kullanıcıyı veritabanında ara
    result = await db.execute(
        text("SELECT value FROM radcheck WHERE username = :u AND attribute = 'Crypt-Password'"),
        {"u": req.username}
    )
    row = result.fetchone()

    if not row:
        await increment_failed_attempts(req.username)
        return AuthResponse(code="Access-Reject", message="User not found")

    # Şifreyi doğrula
    hashed = row[0].encode("utf-8")
    if not bcrypt.checkpw(req.password.encode("utf-8"), hashed):
        await increment_failed_attempts(req.username)
        return AuthResponse(code="Access-Reject", message="Invalid password")

    # Başarılı giriş - rate limit sıfırla
    await reset_failed_attempts(req.username)
    return AuthResponse(code="Access-Accept", message="Authentication successful")

# ================================================
# AUTHORIZE - Yetkilendirme (VLAN ataması)
# ================================================
@app.post("/authorize", response_model=AuthorizeResponse)
async def authorize(req: AuthorizeRequest, db: AsyncSession = Depends(get_db)):

    # MAC Authentication Bypass kontrolü
    is_mab = False
    if req.calling_station_id:
        mac = req.calling_station_id.lower()
        mac_result = await db.execute(
            text("SELECT groupname FROM radmac WHERE macaddress = :mac AND active = true"),
            {"mac": mac}
        )
        mac_row = mac_result.fetchone()
        if mac_row:
            groupname = mac_row[0]
            is_mab = True
        else:
            # Bilinmeyen MAC → guest VLAN
            groupname = "guest"
            is_mab = True

    if not is_mab:
        # Normal kullanıcı - grup sorgula
        group_result = await db.execute(
            text("SELECT groupname FROM radusergroup WHERE username = :u ORDER BY priority LIMIT 1"),
            {"u": req.username}
        )
        group_row = group_result.fetchone()
        if not group_row:
            return AuthorizeResponse(code="Access-Reject")
        groupname = group_row[0]

    # Gruba göre VLAN atribütlerini al
    vlan_result = await db.execute(
        text("SELECT attribute, op, value FROM radgroupreply WHERE groupname = :g"),
        {"g": groupname}
    )
    vlan_rows = vlan_result.fetchall()

    attributes = {row[0]: row[2] for row in vlan_rows}
    attributes["Class"] = groupname  # grup bilgisini de ekle

    return AuthorizeResponse(code="Access-Accept", attributes=attributes)

# ================================================
# ACCOUNTING - Oturum Kayıtları
# ================================================
@app.post("/accounting")
async def accounting(req: AccountingRequest, db: AsyncSession = Depends(get_db)):
    status = req.status_type.lower()

    if status == "start":
        # Yeni oturum başlat
        await db.execute(
            text("""
                INSERT INTO radacct
                    (acctuniqueid, username, nasipaddress, acctstarttime,
                     acctstatustype, callingstationid, acctinputoctets, acctoutputoctets)
                VALUES
                    (:sid, :u, :nas, NOW(), 'Start', :csid, 0, 0)
                ON CONFLICT (acctuniqueid) DO NOTHING
            """),
            {"sid": req.session_id, "u": req.username,
             "nas": req.nas_ip, "csid": req.calling_station_id}
        )
        await db.commit()

        # Redis'e cache'le
        await cache_session(req.session_id, {
            "username":   req.username,
            "nas_ip":     req.nas_ip,
            "start_time": datetime.now().isoformat(),
            "session_id": req.session_id
        })

    elif status == "interim-update":
        # Oturumu güncelle
        await db.execute(
            text("""
                UPDATE radacct SET
                    acctsessiontime  = :stime,
                    acctinputoctets  = :in_oct,
                    acctoutputoctets = :out_oct,
                    acctstatustype   = 'Interim-Update',
                    updated_at       = NOW()
                WHERE acctuniqueid = :sid
            """),
            {"sid": req.session_id,
             "stime":   int(req.session_time or 0),
             "in_oct":  int(req.input_octets or 0),
             "out_oct": int(req.output_octets or 0)}
        )
        await db.commit()

    elif status == "stop":
        # Oturumu kapat
        await db.execute(
            text("""
                UPDATE radacct SET
                    acctstoptime     = NOW(),
                    acctsessiontime  = :stime,
                    acctinputoctets  = :in_oct,
                    acctoutputoctets = :out_oct,
                    acctstatustype   = 'Stop',
                    updated_at       = NOW()
                WHERE acctuniqueid = :sid
            """),
            {"sid": req.session_id,
             "stime":   int(req.session_time or 0),
             "in_oct":  int(req.input_octets or 0),
             "out_oct": int(req.output_octets or 0)}
        )
        await db.commit()

        # Redis cache'den sil
        await delete_session(req.session_id)

    return {"status": "ok"}

# ================================================
# USERS - Kullanıcı Listesi
# ================================================
@app.get("/users")
async def list_users(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        text("""
            SELECT r.username, ug.groupname
            FROM radcheck r
            LEFT JOIN radusergroup ug ON r.username = ug.username
            ORDER BY r.username
        """)
    )
    rows = result.fetchall()
    active_sessions = await get_all_active_sessions()
    active_users = {s.get("username") for s in active_sessions}

    return [
        UserInfo(
            username=row[0],
            groupname=row[1] or "unknown",
            active_session=row[0] in active_users
        )
        for row in rows
    ]

# ================================================
# SESSIONS - Aktif Oturumlar (Redis'ten)
# ================================================
@app.get("/sessions/active")
async def active_sessions():
    sessions = await get_all_active_sessions()
    return {
        "count":    len(sessions),
        "sessions": sessions
    }