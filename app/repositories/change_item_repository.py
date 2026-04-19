from app.repositories.db import get_connection


class ChangeItemRepository:
    def create_change_item(
        self,
        *,
        change_set_id,
        item_type,
        item_key,
        change_kind,
        old_text=None,
        new_text=None,
        diff_text=None,
        keyword_matched=0,
        matched_keywords=None,
        sort_order=0,
    ):
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO change_items (
                change_set_id,
                item_type,
                item_key,
                change_kind,
                old_text,
                new_text,
                diff_text,
                keyword_matched,
                matched_keywords,
                sort_order
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                change_set_id,
                item_type,
                item_key,
                change_kind,
                old_text,
                new_text,
                diff_text,
                keyword_matched,
                matched_keywords,
                sort_order,
            ),
        )
        change_item_id = cur.lastrowid
        conn.commit()
        conn.close()
        return change_item_id

    def list_change_items(self, change_set_id):
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT *
            FROM change_items
            WHERE change_set_id = ?
            ORDER BY sort_order ASC, id ASC
            """,
            (change_set_id,),
        )
        rows = cur.fetchall()
        conn.close()
        return [dict(row) for row in rows]
