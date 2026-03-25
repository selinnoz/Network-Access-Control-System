from pydantic import BaseModel
from typing import Optional
from datetime import datetime

# ------------------------------------------------
# FreeRADIUS'tan gelen istek modelleri
# ------------------------------------------------
class AuthRequest(BaseModel):
    username: str
    password: str
    nas_ip: Optional[str] = None

class AuthorizeRequest(BaseModel):
    username: str
    calling_station_id: Optional[str] = None
    nas_ip: Optional[str] = None

class AccountingRequest(BaseModel):
    status_type: str          # Start, Stop, Interim-Update
    username: str
    session_id: str
    nas_ip: str
    session_time: Optional[str] = "0"
    input_octets: Optional[str] = "0"
    output_octets: Optional[str] = "0"
    calling_station_id: Optional[str] = None
    framed_ip: Optional[str] = None

# ------------------------------------------------
# API cevap modelleri
# ------------------------------------------------
class AuthResponse(BaseModel):
    code: str          # "Access-Accept" veya "Access-Reject"
    message: str

class AuthorizeResponse(BaseModel):
    code: str
    attributes: Optional[dict] = None

class UserInfo(BaseModel):
    username: str
    groupname: str
    active_session: bool

class SessionInfo(BaseModel):
    session_id: str
    username: str
    nas_ip: str
    start_time: Optional[str] = None