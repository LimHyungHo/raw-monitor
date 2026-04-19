from app.repositories.db import get_connection


class UserRepository:
    def _row_to_dict(self, row):
        return dict(row) if row else None

    def get_user_by_id(self, user_id):
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT *
            FROM users
            WHERE id = ?
            """,
            (user_id,),
        )
        row = cur.fetchone()
        conn.close()
        return self._row_to_dict(row)

    def get_user_by_email(self, email):
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT *
            FROM users
            WHERE email = ?
            """,
            (email,),
        )
        row = cur.fetchone()
        conn.close()
        return self._row_to_dict(row)

    def list_users_by_name(self, name):
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT *
            FROM users
            WHERE name = ?
            ORDER BY id DESC
            """,
            (name,),
        )
        rows = cur.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def create_user(self, *, email, name=None, is_active=1):
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO users (email, name, is_active)
            VALUES (?, ?, ?)
            """,
            (email, name, is_active),
        )
        user_id = cur.lastrowid
        conn.commit()
        conn.close()
        return user_id

    def update_user(self, user_id, **fields):
        if not fields:
            return

        allowed_fields = {"email", "name", "is_active"}
        update_fields = {k: v for k, v in fields.items() if k in allowed_fields}
        if not update_fields:
            return

        assignments = ", ".join(f"{key} = ?" for key in update_fields.keys())
        values = list(update_fields.values())
        values.append(user_id)

        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            f"""
            UPDATE users
            SET {assignments},
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            values,
        )
        conn.commit()
        conn.close()

    def upsert_user(self, *, email, name=None, is_active=1):
        existing = self.get_user_by_email(email)
        if existing:
            self.update_user(existing["id"], name=name, is_active=is_active)
            return existing["id"]
        return self.create_user(email=email, name=name, is_active=is_active)
