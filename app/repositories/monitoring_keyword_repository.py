from app.repositories.db import get_connection


class MonitoringKeywordRepository:
    def list_keywords_by_target(self, monitoring_target_id, active_only=False):
        conn = get_connection()
        cur = conn.cursor()

        query = """
            SELECT *
            FROM monitoring_keywords
            WHERE monitoring_target_id = ?
        """
        params = [monitoring_target_id]

        if active_only:
            query += " AND is_active = 1"

        query += " ORDER BY id ASC"
        cur.execute(query, params)
        rows = cur.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_keyword(self, monitoring_target_id, keyword):
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT *
            FROM monitoring_keywords
            WHERE monitoring_target_id = ?
              AND keyword = ?
            """,
            (monitoring_target_id, keyword),
        )
        row = cur.fetchone()
        conn.close()
        return dict(row) if row else None

    def create_keyword(
        self,
        *,
        monitoring_target_id,
        keyword,
        match_mode="contains",
        is_active=1,
    ):
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO monitoring_keywords (
                monitoring_target_id,
                keyword,
                match_mode,
                is_active
            )
            VALUES (?, ?, ?, ?)
            """,
            (monitoring_target_id, keyword, match_mode, is_active),
        )
        keyword_id = cur.lastrowid
        conn.commit()
        conn.close()
        return keyword_id

    def update_keyword(self, keyword_id, **fields):
        if not fields:
            return

        allowed_fields = {"keyword", "match_mode", "is_active"}
        update_fields = {k: v for k, v in fields.items() if k in allowed_fields}
        if not update_fields:
            return

        assignments = ", ".join(f"{key} = ?" for key in update_fields.keys())
        values = list(update_fields.values())
        values.append(keyword_id)

        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            f"""
            UPDATE monitoring_keywords
            SET {assignments}
            WHERE id = ?
            """,
            values,
        )
        conn.commit()
        conn.close()

    def upsert_keyword(
        self,
        *,
        monitoring_target_id,
        keyword,
        match_mode="contains",
        is_active=1,
    ):
        existing = self.get_keyword(monitoring_target_id, keyword)
        if existing:
            self.update_keyword(
                existing["id"],
                match_mode=match_mode,
                is_active=is_active,
            )
            return existing["id"]

        return self.create_keyword(
            monitoring_target_id=monitoring_target_id,
            keyword=keyword,
            match_mode=match_mode,
            is_active=is_active,
        )
