from app.repositories.db import get_connection


class ChangeSetRepository:
    def _row_to_dict(self, row):
        return dict(row) if row else None

    def create_change_set(
        self,
        *,
        source_document_id,
        new_version_id,
        change_type,
        old_version_id=None,
        summary=None,
        keyword_hit_count=0,
        has_structural_change=0,
    ):
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO change_sets (
                source_document_id,
                old_version_id,
                new_version_id,
                change_type,
                summary,
                keyword_hit_count,
                has_structural_change
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                source_document_id,
                old_version_id,
                new_version_id,
                change_type,
                summary,
                keyword_hit_count,
                has_structural_change,
            ),
        )
        change_set_id = cur.lastrowid
        conn.commit()
        conn.close()
        return change_set_id

    def get_change_set(self, change_set_id):
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT *
            FROM change_sets
            WHERE id = ?
            """,
            (change_set_id,),
        )
        row = cur.fetchone()
        conn.close()
        return self._row_to_dict(row)

    def list_change_sets_by_document(self, source_document_id, limit=20):
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT *
            FROM change_sets
            WHERE source_document_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (source_document_id, limit),
        )
        rows = cur.fetchall()
        conn.close()
        return [dict(row) for row in rows]
