from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.setting import Setting


class ThemePaletteService:
    """主题色卡服务，提供预设色卡与自定义色卡持久化。"""

    PALETTE_KEY = "chart_theme_palette"

    @staticmethod
    def get_capabilities() -> Dict[str, Any]:
        return {
            "service": "theme_palettes",
            "description": "提供预设与自定义图表色卡，支持保存到项目设置。",
            "palette_types": ["preset", "custom"],
            "supported_actions": ["list", "detail", "create", "delete", "apply"],
        }

    @staticmethod
    def get_default_palettes() -> List[Dict[str, Any]]:
        return [
            {"key": "solo-default", "name": "Solo 默认", "colors": ["#1677ff", "#52c41a", "#faad14", "#f5222d", "#722ed1"]},
            {"key": "business-blue", "name": "商务蓝", "colors": ["#1d39c4", "#40a9ff", "#69c0ff", "#91d5ff", "#bae7ff"]},
            {"key": "warm-insight", "name": "暖色洞察", "colors": ["#d4380d", "#fa8c16", "#fadb14", "#a0d911", "#389e0d"]},
            {"key": "morandi-soft", "name": "莫兰迪柔和", "colors": ["#7C8DA6", "#A3B18A", "#D4A373", "#B56576", "#6D597A"]},
        ]

    @classmethod
    def list_palettes(cls, db: Session, project_id: Optional[int] = None) -> Dict[str, Any]:
        query = db.query(Setting).filter(Setting.key == cls.PALETTE_KEY)
        if project_id is None:
            records = query.filter(Setting.is_global == True).all()
        else:
            records = query.filter(Setting.project_id == project_id).all()
        return {
            "presets": cls.get_default_palettes(),
            "custom": [
                {
                    "id": item.id,
                    "project_id": item.project_id,
                    "is_global": item.is_global,
                    **(item.value or {}),
                }
                for item in records
            ],
        }

    @classmethod
    def create_palette(
        cls,
        db: Session,
        *,
        name: str,
        colors: List[str],
        project_id: Optional[int] = None,
        is_global: bool = False,
    ) -> Setting:
        payload = {"name": name, "colors": colors, "key": f"custom-{name}"}
        setting = Setting(key=cls.PALETTE_KEY, value=payload, project_id=project_id, is_global=is_global)
        db.add(setting)
        db.commit()
        db.refresh(setting)
        return setting

    @staticmethod
    def delete_palette(db: Session, palette_id: int) -> bool:
        palette = db.query(Setting).filter(Setting.id == palette_id, Setting.key == ThemePaletteService.PALETTE_KEY).first()
        if not palette:
            return False
        db.delete(palette)
        db.commit()
        return True
