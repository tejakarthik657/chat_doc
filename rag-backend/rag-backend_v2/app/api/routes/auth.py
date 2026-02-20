from fastapi import APIRouter, HTTPException, status
from datetime import datetime
from bson import ObjectId

from app.models.schemas import UserRegister, UserLogin, TokenResponse, UserOut
from app.core.security import hash_password, verify_password, create_access_token
from app.db.mongodb import users_col

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(body: UserRegister):
    existing = await users_col().find_one({"email": body.email})
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered.")

    user_id = str(ObjectId())
    await users_col().insert_one({
        "_id": user_id,
        "email": body.email,
        "password_hash": hash_password(body.password),
        "plan": "FREE",
        "storage_used_mb": 0.0,
        "created_at": datetime.utcnow(),
        "last_active": datetime.utcnow()
    })

    token = create_access_token({"sub": user_id})
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
async def login(body: UserLogin):
    user = await users_col().find_one({"email": body.email})
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials.")

    await users_col().update_one(
        {"_id": user["_id"]},
        {"$set": {"last_active": datetime.utcnow()}}
    )

    token = create_access_token({"sub": user["_id"]})
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserOut)
async def get_me(user_id: str = None):
    # user_id injected by dependency in main app
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
