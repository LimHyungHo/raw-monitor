from app.repositories.db import get_connection


class MonitoringTargetRepository:
    def _row_to_dict(self, row):
        return dict(row) if row else None

    def list_targets_by_user(self, user_id, active_only=False):
        conn = get_connection()
        cur = conn.cursor()

        query = """
            SELECT *
            FROM monitoring_targets
            WHERE user_id = ?
        """
        params = [user_id]

        if active_only:
            query += " AND is_active = 1"

        query += " ORDER BY id DESC"
        cur.execute(query, params)
        rows = cur.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_target_by_id(self, target_id):
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT *
            FROM monitoring_targets
            WHERE id = ?
            """,
            (target_id,),
        )
        row = cur.fetchone()
        conn.close()
        return self._row_to_dict(row)

    def find_target(self, *, user_id, target_type, document_name, notify_email):
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT *
            FROM monitoring_targets
            WHERE user_id = ?
              AND target_type = ?
              AND document_name = ?
              AND notify_email = ?
            """,
            (user_id, target_type, document_name, notify_email),
        )
        row = cur.fetchone()
        conn.close()
        return self._row_to_dict(row)

    def create_target(
        self,
        *,
        user_id,
        target_name,
        target_type,
        document_name,
        document_id=None,
        source_org="law.go.kr",
        notify_email,
        is_active=1,
    ):
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO monitoring_targets (
                user_id,
                target_name,
                target_type,
                document_name,
                document_id,
                source_org,
                notify_email,
                is_active
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                target_name,
                target_type,
                document_name,
                document_id,
                source_org,
                notify_email,
                is_active,
            ),
        )
        target_id = cur.lastrowid
        conn.commit()
        conn.close()
        return target_id

    def update_target(self, target_id, **fields):
        if not fields:
            return

        allowed_fields = {
            "target_name",
            "target_type",
            "document_name",
            "document_id",
            "source_org",
            "notify_email",
            "is_active",
        }
        update_fields = {k: v for k, v in fields.items() if k in allowed_fields}
        if not update_fields:
            return

        assignments = ", ".join(f"{key} = ?" for key in update_fields.keys())
        values = list(update_fields.values())
        values.append(target_id)

        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            f"""
            UPDATE monitoring_targets
            SET {assignments},
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            values,
        )
        conn.commit()
        conn.close()

    def upsert_target(
        self,
        *,
        user_id,
        target_name,
        target_type,
        document_name,
        document_id=None,
        source_org="law.go.kr",
        notify_email,
        is_active=1,
    ):
        existing = self.find_target(
            user_id=user_id,
            target_type=target_type,
            document_name=document_name,
            notify_email=notify_email,
        )
        if existing:
            self.update_target(
                existing["id"],
                target_name=target_name,
                document_id=document_id,
                source_org=source_org,
                is_active=is_active,
            )
            return existing["id"]

        return self.create_target(
            user_id=user_id,
            target_name=target_name,
            target_type=target_type,
            document_name=document_name,
            document_id=document_id,
            source_org=source_org,
            notify_email=notify_email,
            is_active=is_active,
        )

