from fastapi import APIRouter, Depends
from typing import List
from app.services.db import get_db
from app.models.domain import Role
from supabase import Client

router = APIRouter()

@router.get("", response_model=List[Role])
async def get_roles(db: Client = Depends(get_db)):
    res = db.table("roles").select("*").execute()
    return res.data
