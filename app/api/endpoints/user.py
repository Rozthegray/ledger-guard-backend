from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified # 🟢 Critical for JSON updates
from pydantic import BaseModel
from typing import Optional, Dict, Any

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User

# 🟢 1. INITIALIZE ROUTER (Must be before the endpoints)
router = APIRouter()

# 🟢 2. DEFINE INPUT MODEL
class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    company_name: Optional[str] = None
    phone: Optional[str] = None 
    dob: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None 

# 🟢 3. GET USER ENDPOINT
@router.get("/me")
def read_users_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "company_name": current_user.company_name,
        "plan": current_user.plan,
        "api_key": current_user.api_key,
        "settings": current_user.settings
    }

# 🟢 4. UPDATE USER ENDPOINT (Fixed Merge Logic)
@router.put("/me")
def update_user_profile(
    user_in: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 1. Update Basic Fields
    if user_in.full_name is not None: 
        current_user.full_name = user_in.full_name
    if user_in.company_name is not None: 
        current_user.company_name = user_in.company_name
        
    # 2. Settings JSON Handling
    # Create a copy to ensure we don't mutate the DB object in place weirdly
    current_settings = dict(current_user.settings) if current_user.settings else {}
    
    # Ensure default sections exist
    if "profile" not in current_settings: current_settings["profile"] = {}
    if "preferences" not in current_settings: current_settings["preferences"] = {}

    # 🟢 SMART MERGE: Iterate over everything sent from frontend
    # This automatically handles "preferences", "notifications", "billing", etc.
    if user_in.settings:
        for section_key, section_data in user_in.settings.items():
            # If it's a nested dict (like notifications, preferences), merge it
            if isinstance(section_data, dict):
                current_section = current_settings.get(section_key, {})
                
                # If the existing data isn't a dict (corruption safety), reset it
                if not isinstance(current_section, dict):
                    current_section = {}

                # Merge new values into existing section
                current_section.update(section_data)
                current_settings[section_key] = current_section
            else:
                # Flat value update
                current_settings[section_key] = section_data

    # Handle Top-Level Fields that act as shortcuts to JSON
    if user_in.phone: 
        current_settings["profile"]["phone"] = user_in.phone
    if user_in.dob: 
        current_settings["profile"]["dob"] = user_in.dob

    # Assign back
    current_user.settings = current_settings
    
    # 🟢 CRITICAL: Tell SQLAlchemy "This JSON field changed!"
    flag_modified(current_user, "settings")
    
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    
    return current_user