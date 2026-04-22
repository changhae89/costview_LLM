import json
from fastapi import APIRouter, Depends, HTTPException
from db import get_conn
from auth import require_admin
from schemas.category import CategoryCreate, CategoryUpdate

router = APIRouter()


def _row_to_dict(row, cursor) -> dict:
    cols = [d[0] for d in cursor.description]
    return dict(zip(cols, row))


@router.get("/")
def list_categories():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM cost_categories ORDER BY sort_order")
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, r)) for r in cur.fetchall()]


@router.post("/", dependencies=[Depends(require_admin)])
def create_category(body: CategoryCreate):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO cost_categories (code, name_ko, name_en, sort_order, keywords)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING *
                """,
                (body.code, body.name_ko, body.name_en, body.sort_order, json.dumps(body.keywords)),
            )
            conn.commit()
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=500, detail="insert_failed")
            return {"data": _row_to_dict(row, cur)}


@router.put("/{code}", dependencies=[Depends(require_admin)])
def update_category(code: str, body: CategoryUpdate):
    fields = body.model_dump(exclude_none=True)
    if not fields:
        raise HTTPException(status_code=400, detail="no_fields")

    sets, vals = [], []
    for k, v in fields.items():
        sets.append(f"{k} = %s")
        vals.append(json.dumps(v) if k == "keywords" else v)
    vals.append(code)

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"UPDATE cost_categories SET {', '.join(sets)} WHERE code = %s RETURNING *",
                vals,
            )
            conn.commit()
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="not_found")
            return {"data": _row_to_dict(row, cur)}


@router.delete("/{code}", dependencies=[Depends(require_admin)])
def delete_category(code: str):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM cost_categories WHERE code = %s RETURNING code", (code,))
            conn.commit()
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="not_found")
            return {"data": {"code": code}}
