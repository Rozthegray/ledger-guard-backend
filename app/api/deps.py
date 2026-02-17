from datetime import datetime
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User

# 🟢 Define scheme (Do NOT import get_current_user from here)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(User).filter(User.email == email.lower()).first()
    if user is None:
        raise credentials_exception

    if user.plan != "starter" and user.plan_expires_at:
        if datetime.utcnow() > user.plan_expires_at:
            print(f"📉 Plan Expired for {user.email}. Resetting.")
            user.plan = "starter"
            user.plan_expires_at = None
            db.commit()
            db.refresh(user)

    return user

def check_subscription_tier(current_user: User = Depends(get_current_user)) -> dict:
    return {"tier": current_user.plan, "user": current_user}