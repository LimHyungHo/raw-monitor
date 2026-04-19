from app.repositories.db import get_connection


class VersionRepository:
    def _row_to_dict(self, row):
        return dict(row) if row else None

    def get_version_by_id(self, version_id):
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT *
            FROM document_versions
            WHERE id = ?
            """,
            (version_id,),
        )
        row = cur.fetchone()
        conn.close()
        return self._row_to_dict(row)

    def get_latest_version(self, source_document_id):
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT *
            FROM document_versions
            WHERE source_document_id = ?
            ORDER BY
                COALESCE(effective_date, '') DESC,
                COALESCE(version_no, 0) DESC,
                id DESC
            LIMIT 1
            """,
            (source_document_id,),
        )
        row = cur.fetchone()
        conn.close()
        return self._row_to_dict(row)

    def list_versions(self, source_document_id):
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT *
            FROM document_versions
            WHERE source_document_id = ?
            ORDER BY
                COALESCE(effective_date, '') DESC,
                COALESCE(version_no, 0) DESC,
                id DESC
            """,
            (source_document_id,),
        )
        rows = cur.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_current_version(self, source_document_id):
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT *
            FROM document_versions
            WHERE source_document_id = ?
              AND is_current = 1
            ORDER BY id DESC
            LIMIT 1
            """,
            (source_document_id,),
        )
        row = cur.fetchone()
        conn.close()
        return self._row_to_dict(row)

    def get_version_by_key(self, source_document_id, version_key):
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT *
            FROM document_versions
            WHERE source_document_id = ?
              AND version_key = ?
            """,
            (source_document_id, version_key),
        )
        row = cur.fetchone()
        conn.close()
        return self._row_to_dict(row)

    def update_version_metadata(self, version_id, **fields):
        if not fields:
            return

        allowed_fields = {
            "version_key",
            "version_no",
            "effective_date",
            "promulgation_date",
            "announcement_no",
            "revision_type",
            "content_hash",
            "raw_json",
            "raw_text",
            "parsed_json",
            "is_current",
        }
        update_fields = {k: v for k, v in fields.items() if k in allowed_fields}
        if not update_fields:
            return

        assignments = ", ".join(f"{key} = ?" for key in update_fields.keys())
        values = list(update_fields.values())
        values.append(version_id)

        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            f"""
            UPDATE document_versions
            SET {assignments}
            WHERE id = ?
            """,
            values,
        )
        conn.commit()
        conn.close()

    def clear_current_version_flag(self, source_document_id):
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE document_versions
            SET is_current = 0
            WHERE source_document_id = ?
            """,
            (source_document_id,),
        )
        conn.commit()
        conn.close()

    def insert_version(
        self,
        source_document_id,
        *,
        version_key,
        version_no=None,
        effective_date=None,
        promulgation_date=None,
        announcement_no=None,
        revision_type=None,
        content_hash=None,
        raw_json=None,
        raw_text=None,
        parsed_json=None,
        is_current=0,
    ):
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO document_versions (
                source_document_id,
                version_key,
                version_no,
                effective_date,
                promulgation_date,
                announcement_no,
                revision_type,
                content_hash,
                raw_json,
                raw_text,
                parsed_json,
                is_current
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                source_document_id,
                version_key,
                version_no,
                effective_date,
                promulgation_date,
                announcement_no,
                revision_type,
                content_hash,
                raw_json,
                raw_text,
                parsed_json,
                is_current,
            ),
        )
        version_id = cur.lastrowid
        conn.commit()
        conn.close()
        return version_id

    def save_version(self, source_document_id, **version_data):
        existing = self.get_version_by_key(source_document_id, version_data["version_key"])
        if existing:
            return existing["id"]

        if version_data.get("is_current"):
            self.clear_current_version_flag(source_document_id)

        return self.insert_version(source_document_id, **version_data)
