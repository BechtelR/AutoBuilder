"""Skill management routes."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.gateway.deps import get_skill_library
from app.gateway.models.skills import SkillCatalogEntry
from app.skills.library import SkillLibrary

router = APIRouter(tags=["skills"])


@router.post("/skills/cache/invalidate")
async def invalidate_skill_cache(
    skill_library: Annotated[SkillLibrary, Depends(get_skill_library)],
) -> dict[str, str]:
    """Trigger skill cache invalidation and rescan."""
    await skill_library.invalidate_cache()
    skill_library.scan()
    await skill_library.save_to_cache()
    return {"status": "invalidated"}


@router.get("/skills")
async def list_skills(
    skill_library: Annotated[SkillLibrary, Depends(get_skill_library)],
) -> list[SkillCatalogEntry]:
    """Return lightweight catalog of all indexed skills."""
    index = skill_library.get_index()
    return [
        SkillCatalogEntry(
            name=entry.name,
            description=entry.description,
            triggers=list(entry.triggers),
            tags=list(entry.tags),
            applies_to=list(entry.applies_to),
            priority=entry.priority,
            has_references=entry.has_references,
            has_assets=entry.has_assets,
            has_scripts=entry.has_scripts,
        )
        for entry in sorted(index.values(), key=lambda e: e.name)
    ]
