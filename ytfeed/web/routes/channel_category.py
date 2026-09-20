"""Channel category taxonomy (Group -> Category -> Type) management.

Master-detail CRUD modelled on money-webapp's categories page: a left pane lists
the Groups, the right pane is an editable AG Grid of that group's categories.
The grid talks JSON to /api/channel-categories/*. Channels reference a category by
FK, so edits don't cascade — but deletes of an in-use category are guarded.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ytfeed.db.models import Channel, ChannelCategory
from ytfeed.web.dependencies import get_db, templates

router = APIRouter()

# grid column header -> model attribute
FIELD_MAP = {"Category": "name", "Group": "group", "Type": "type"}


def _grouped(db: Session) -> list[tuple[str, list[ChannelCategory]]]:
    """All categories bucketed by group (used by the channel-page picker)."""
    cats = list(
        db.scalars(
            select(ChannelCategory).order_by(ChannelCategory.group, ChannelCategory.name)
        )
    )
    groups: dict[str, list[ChannelCategory]] = {}
    for c in cats:
        groups.setdefault(c.group or "Ungrouped", []).append(c)
    return sorted(groups.items())


def _usage(db: Session) -> dict[int, int]:
    """category_id -> number of channels referencing it."""
    rows = db.execute(
        select(Channel.category_id, func.count(Channel.id))
        .where(Channel.category_id.is_not(None))
        .group_by(Channel.category_id)
    ).all()
    return {cid: n for cid, n in rows}


def _serialize(c: ChannelCategory) -> dict:
    return {"_id": c.id, "Category": c.name, "Group": c.group, "Type": c.type or ""}


# --- page -----------------------------------------------------------------------

@router.get("/channel-categories", response_class=HTMLResponse)
def channel_categories_page(request: Request):
    return templates.TemplateResponse(
        request,
        "channel_categories.html",
        {"request": request, "active_page": "channel-categories"},
    )


# --- JSON API -------------------------------------------------------------------

@router.get("/api/channel-categories/sections")
def api_sections(db: Session = Depends(get_db)):
    cats = list(db.scalars(select(ChannelCategory)))
    sections = sorted({c.group or "Ungrouped" for c in cats})
    options = {
        "Group": sections,
        "Type": sorted({c.type for c in cats if c.type}),
    }
    return {"sections": sections, "options": options}


@router.get("/api/channel-categories")
def api_items(section: str, db: Session = Depends(get_db)):
    stmt = select(ChannelCategory)
    if section == "*":  # all groups (used by the "All groups" search toggle)
        stmt = stmt.order_by(ChannelCategory.group, ChannelCategory.name)
    else:
        group = "" if section == "Ungrouped" else section
        stmt = stmt.where(ChannelCategory.group == group).order_by(ChannelCategory.name)
    return {"items": [_serialize(c) for c in db.scalars(stmt)]}


@router.post("/api/channel-categories/row")
async def api_add(request: Request, db: Session = Depends(get_db)):
    body = await request.json()
    name = (body.get("Category") or "").strip()
    if not name:
        return {"ok": False, "error": "Category name required"}
    if db.scalar(select(ChannelCategory).where(ChannelCategory.name == name)):
        return {"ok": False, "error": f"Category '{name}' already exists"}
    db.add(
        ChannelCategory(
            name=name,
            group=(body.get("Group") or "").strip(),
            type=(body.get("Type") or "").strip() or None,
        )
    )
    db.commit()
    return {"ok": True}


@router.post("/api/channel-categories/update")
async def api_update(request: Request, db: Session = Depends(get_db)):
    body = await request.json()
    cat = db.get(ChannelCategory, body.get("id"))
    if cat is None:
        return {"ok": False, "error": "Category not found"}
    field = FIELD_MAP.get(body.get("field"))
    if field is None:
        return {"ok": False, "error": "Unknown field"}
    value = (body.get("value") or "").strip()
    if field == "name":
        if not value:
            return {"ok": False, "error": "Category name required"}
        clash = db.scalar(
            select(ChannelCategory).where(
                ChannelCategory.name == value, ChannelCategory.id != cat.id
            )
        )
        if clash is not None:
            return {"ok": False, "error": f"Category '{value}' already exists"}
        cat.name = value
    elif field == "group":
        cat.group = value
    else:  # type
        cat.type = value or None
    db.commit()
    # channels keep their FK; report how many reference this row for context
    return {"ok": True, "updated": _usage(db).get(cat.id, 0)}


@router.post("/api/channel-categories/delete")
async def api_delete(request: Request, db: Session = Depends(get_db)):
    body = await request.json()
    cat = db.get(ChannelCategory, body.get("id"))
    if cat is None:
        return {"ok": False, "error": "Category not found"}
    in_use = _usage(db).get(cat.id, 0)
    reassign = body.get("reassign_to")
    new_id: int | None = None
    if reassign not in (None, "", "0"):
        target = db.scalar(
            select(ChannelCategory).where(ChannelCategory.name == str(reassign).strip())
        )
        if target is None:
            return {"ok": False, "error": f"No category named '{reassign}'"}
        new_id = target.id
    elif in_use and reassign is None:
        # tell the client to prompt for a reassign target (or '0' to unassign)
        return {"ok": False, "in_use": in_use}
    db.execute(
        Channel.__table__.update()
        .where(Channel.category_id == cat.id)
        .values(category_id=new_id)
    )
    db.delete(cat)
    db.commit()
    return {"ok": True}
