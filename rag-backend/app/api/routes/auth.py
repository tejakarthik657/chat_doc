import asyncio
from fastapi import APIRouter, HTTPException, status, Depends
from datetime import datetime
from bson import ObjectId
from pymongo.errors import DuplicateKeyError

from app.models.schemas import UserRegister, UserLogin, TokenResponse, UserOut
from app.core.security import hash_password, verify_password, create_access_token
from app.core.security import get_current_user
from app.db.mongodb import users_col

import logging
from typing import Optional
from urllib.parse import urlencode
from fastapi.responses import RedirectResponse
import httpx
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(body: UserRegister):
    try:
        # Check password length (internal check for bcrypt safety)
        if len(body.password.encode("utf-8")) > 72:
            raise HTTPException(
                status_code=422,
                detail="Password too long (max 72 bytes)",
            )
            
        existing = await users_col().find_one({"email": body.email})
        if existing:
            raise HTTPException(status_code=409, detail="Email already registered.")

        user_id = str(ObjectId())
        hashed = await asyncio.to_thread(hash_password, body.password)
        user_doc = {
            "_id": user_id,
            "email": body.email,
            "password_hash": hashed,
            "plan": "FREE",
            "storage_used_mb": 0.0,
            "created_at": datetime.utcnow(),
            "last_active": datetime.utcnow()
        }
        
        await users_col().insert_one(user_doc)

        token = create_access_token({"sub": user_id})
        return TokenResponse(access_token=token)
    except HTTPException:
        raise
    except DuplicateKeyError:
        raise HTTPException(status_code=409, detail="Email already registered.")
    except Exception as e:
        print(f"[AUTH ERROR] {e}")
        raise HTTPException(status_code=500, detail="Internal server error. Please try again.")



@router.post("/login", response_model=TokenResponse)
async def login(body: UserLogin):
    user = await users_col().find_one({"email": body.email})
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials.")
        
    is_valid = await asyncio.to_thread(verify_password, body.password, user["password_hash"])
    if not is_valid:
        raise HTTPException(status_code=401, detail="Invalid credentials.")

    await users_col().update_one(
        {"_id": user["_id"]},
        {"$set": {"last_active": datetime.utcnow()}}
    )

    token = create_access_token({"sub": user["_id"]})
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserOut)
async def get_me(user_id: str = Depends(get_current_user)):
    user = await users_col().find_one({"_id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    return UserOut(
        id=user["_id"],
        email=user["email"],
        plan=user["plan"],
        storage_used_mb=user["storage_used_mb"],
        created_at=user["created_at"]
    )


# ── Google OAuth 2.0 Integration ─────────────────────────────────────────────

def resolve_redirect_uri(request: Request) -> str:
    """Auto-detects production hostname so OAuth redirect always matches live deployment."""
    host = request.headers.get("x-forwarded-host") or request.headers.get("host") or ""
    proto = request.headers.get("x-forwarded-proto") or request.url.scheme or "https"
    
    # If request is arriving on a cloud domain (e.g. *.onrender.com)
    if host and "localhost" not in host and "127.0.0.1" not in host:
        if not settings.google_redirect_uri or "localhost" in settings.google_redirect_uri:
            return f"{proto}://{host}/auth/google/callback"
            
    return settings.google_redirect_uri or f"{proto}://{host}/auth/google/callback"


@router.get("/google")
async def login_google(request: Request, state: Optional[str] = None):
    """
    Initiates Google OAuth 2.0 authentication flow.
    Preserves calling frontend origin via state parameter to guarantee return redirect.
    """
    if not settings.google_client_id:
        raise HTTPException(
            status_code=500,
            detail="Google OAuth is not configured on the server. Please set GOOGLE_CLIENT_ID.",
        )

    redirect_uri = resolve_redirect_uri(request)
    
    # If state not explicitly passed, auto-detect frontend origin from referer
    if not state:
        referer = request.headers.get("referer") or request.headers.get("origin")
        if referer and "google.com" not in referer:
            from urllib.parse import urlparse
            p = urlparse(referer)
            state = f"{p.scheme}://{p.netloc}"
        else:
            state = settings.frontend_url

    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "select_account",
        "state": state,
    }
    google_auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
    return RedirectResponse(url=google_auth_url)


@router.get("/google/callback")
async def google_callback(
    request: Request,
    code: Optional[str] = None,
    error: Optional[str] = None,
    state: Optional[str] = None,
):
    """
    Handles Google OAuth 2.0 redirect callback.
    Exchanges authorization code for Google profile, upserts user into MongoDB,
    generates application JWT token, and redirects to frontend dashboard.
    """
    # Dynamically determine the frontend return address from state or config
    target_frontend = state or settings.frontend_url
    if not target_frontend or (target_frontend.startswith("http://localhost") and request.headers.get("host") and "localhost" not in request.headers.get("host", "")):
        referer = request.headers.get("referer") or ""
        if referer and "google.com" not in referer:
            from urllib.parse import urlparse
            p = urlparse(referer)
            target_frontend = f"{p.scheme}://{p.netloc}"
        else:
            target_frontend = settings.frontend_url
    target_frontend = target_frontend.rstrip("/")

    if error or not code:
        logger.error(f"[Google OAuth Callback Error] Error received: {error}")
        return RedirectResponse(
            url=f"{target_frontend}/login?error={error or 'access_denied'}"
        )

    redirect_uri = resolve_redirect_uri(request)

    try:
        # 1. Exchange authorization code for access token
        token_endpoint = "https://oauth2.googleapis.com/token"
        token_payload = {
            "code": code,
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            token_resp = await client.post(token_endpoint, data=token_payload)
            if token_resp.status_code != 200:
                logger.error(f"[Google OAuth Token Exchange Failed] {token_resp.text}")
                return RedirectResponse(
                    url=f"{settings.frontend_url}/login?error=token_exchange_failed"
                )

            token_data = token_resp.json()
            access_token = token_data.get("access_token")

            # 2. Retrieve verified user profile from Google UserInfo endpoint
            userinfo_endpoint = "https://www.googleapis.com/oauth2/v2/userinfo"
            userinfo_resp = await client.get(
                userinfo_endpoint, headers={"Authorization": f"Bearer {access_token}"}
            )
            if userinfo_resp.status_code != 200:
                logger.error(f"[Google OAuth UserInfo Failed] {userinfo_resp.text}")
                return RedirectResponse(
                    url=f"{settings.frontend_url}/login?error=userinfo_fetch_failed"
                )

            google_profile = userinfo_resp.json()
            email = google_profile.get("email")
            google_id = google_profile.get("id")
            name = google_profile.get("name", "Google User")
            picture = google_profile.get("picture", "")

            if not email:
                return RedirectResponse(
                    url=f"{settings.frontend_url}/login?error=no_email_provided"
                )

        # 3. Upsert user in MongoDB Atlas users_col
        existing_user = await users_col().find_one({"email": email})
        now = datetime.utcnow()

        if existing_user:
            user_id = existing_user["_id"]
            await users_col().update_one(
                {"_id": user_id},
                {
                    "$set": {
                        "name": name,
                        "avatar_url": picture,
                        "google_id": google_id,
                        "auth_provider": "google",
                        "last_active": now,
                    }
                },
            )
        else:
            user_id = str(ObjectId())
            new_user = {
                "_id": user_id,
                "email": email,
                "name": name,
                "avatar_url": picture,
                "google_id": google_id,
                "auth_provider": "google",
                "plan": "FREE",
                "storage_used_mb": 0.0,
                "created_at": now,
                "last_active": now,
            }
            await users_col().insert_one(new_user)

        # 4. Issue standard application JWT access token
        app_jwt = create_access_token({"sub": user_id})

        # 5. Redirect browser back to frontend client callback
        return RedirectResponse(
            url=f"{target_frontend}/auth/callback?token={app_jwt}"
        )

    except Exception as exc:
        logger.error(f"[Google OAuth Internal Error] {exc}", exc_info=True)
        return RedirectResponse(
            url=f"{target_frontend}/login?error=oauth_internal_error"
        )
