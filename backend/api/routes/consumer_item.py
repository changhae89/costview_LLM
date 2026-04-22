from fastapi import APIRouter, Depends, HTTPException
from db import get_conn
from auth import require_admin
from schemas.consumer_item import ConsumerItemCreate, ConsumerItemUpdate

router = APIRouter()


def _row_to_dict(row, cursor) -> dict:
    cols = [d[0] for d in cursor.description]
    return dict(zip(cols, row))


@router.get("/")
def list_consumer_items(show_deleted: bool = False):
    with get_conn() as conn:
        with conn.cursor() as cur:
            if show_deleted:
                cur.execute("SELECT * FROM consumer_items ORDER BY created_at DESC")
            else:
                cur.execute("SELECT * FROM consumer_items WHERE is_deleted = false ORDER BY created_at DESC")
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, r)) for r in cur.fetchall()]


@router.post("/", dependencies=[Depends(require_admin)])
def create_consumer_item(body: ConsumerItemCreate):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO consumer_items
                  (category_code, name_ko, name_en, unit, typical_monthly_spend, weight, description)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING *
                """,
                (body.category_code, body.name_ko, body.name_en, body.unit,
                 body.typical_monthly_spend, body.weight, body.description),
            )
            conn.commit()
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=500, detail="insert_failed")
            return {"data": _row_to_dict(row, cur)}


@router.put("/{item_id}", dependencies=[Depends(require_admin)])
def update_consumer_item(item_id: str, body: ConsumerItemUpdate):
    fields = body.model_dump(exclude_none=True)
    if not fields:
        raise HTTPException(status_code=400, detail="no_fields")

    sets = [f"{k} = %s" for k in fields]
    vals = list(fields.values()) + [item_id]

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"UPDATE consumer_items SET {', '.join(sets)} WHERE id = %s RETURNING *",
                vals,
            )
            conn.commit()
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="not_found")
            return {"data": _row_to_dict(row, cur)}


@router.delete("/{item_id}", dependencies=[Depends(require_admin)])
def delete_consumer_item(item_id: str):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE consumer_items SET is_deleted = true WHERE id = %s AND is_deleted = false RETURNING id",
                (item_id,),
            )
            conn.commit()
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="not_found")
            return {"data": {"id": item_id}}


@router.post("/{item_id}/restore", dependencies=[Depends(require_admin)])
def restore_consumer_item(item_id: str):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE consumer_items SET is_deleted = false WHERE id = %s AND is_deleted = true RETURNING id",
                (item_id,),
            )
            conn.commit()
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="not_found")
            return {"data": {"id": item_id}}
