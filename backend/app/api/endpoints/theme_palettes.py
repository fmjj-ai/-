from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional, List

from app.db.session import get_db
from app.schemas.response import StandardResponse
from app.services.theme_palette_service import ThemePaletteService

router = APIRouter()


@router.get("/capabilities", response_model=StandardResponse[dict])
def get_theme_palette_capabilities():
    return StandardResponse(success=True, data={
        "capabilities": ThemePaletteService.get_capabilities(),
        "default_palettes": ThemePaletteService.get_default_palettes(),
    })


@router.get("/", response_model=StandardResponse[Dict[str, Any]])
def list_theme_palettes(
    project_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    return StandardResponse(success=True, data=ThemePaletteService.list_palettes(db, project_id=project_id))


@router.post("/", response_model=StandardResponse[Dict[str, Any]])
def create_theme_palette(
    name: str = Body(..., embed=True),
    colors: List[str] = Body(..., embed=True),
    project_id: Optional[int] = Body(None, embed=True),
    is_global: bool = Body(False, embed=True),
    db: Session = Depends(get_db)
):
    if len(colors) < 3:
        raise HTTPException(status_code=400, detail="色卡至少需要 3 个颜色")
    palette = ThemePaletteService.create_palette(db, name=name, colors=colors, project_id=project_id, is_global=is_global)
    return StandardResponse(success=True, data={
        "id": palette.id,
        "name": palette.value.get("name"),
        "colors": palette.value.get("colors"),
        "project_id": palette.project_id,
        "is_global": palette.is_global,
    })


@router.delete("/{palette_id}", response_model=StandardResponse[bool])
def delete_theme_palette(palette_id: int, db: Session = Depends(get_db)):
    deleted = ThemePaletteService.delete_palette(db, palette_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="色卡不存在")
    return StandardResponse(success=True, data=True)
