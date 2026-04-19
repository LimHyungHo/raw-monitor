from app.repositories.db import get_connection


class LawRepository:
    def _row_to_dict(self, row):
        return dict(row) if row else None

    def get_source_document(self, source_type, target_type, document_id):
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT *
            FROM source_documents
            WHERE source_type = ?
              AND target_type = ?
              AND document_id = ?
            """,
            (source_type, target_type, document_id),
        )
        row = cur.fetchone()
        conn.close()
        return self._row_to_dict(row)

    def get_source_document_by_id(self, source_document_id):
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT *
            FROM source_documents
            WHERE id = ?
            """,
            (source_document_id,),
        )
        row = cur.fetchone()
        conn.close()
        return self._row_to_dict(row)

    def create_source_document(
        self,
        *,
        source_type,
        target_type,
        document_id,
        document_name,
        document_subtype=None,
        parent_document_id=None,
        ministry_name=None,
        document_url=None,
        is_active=1,
    ):
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO source_documents (
                source_type,
                target_type,
                document_id,
                document_name,
                document_subtype,
                parent_document_id,
                ministry_name,
                document_url,
                is_active
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                source_type,
                target_type,
                document_id,
                document_name,
                document_subtype,
                parent_document_id,
                ministry_name,
                document_url,
                is_active,
            ),
        )
        source_document_id = cur.lastrowid
        conn.commit()
        conn.close()
        return source_document_id

    def update_source_document(self, source_document_id, **fields):
        if not fields:
            return

        allowed_fields = {
            "document_name",
            "document_subtype",
            "parent_document_id",
            "ministry_name",
            "document_url",
            "is_active",
        }
        update_fields = {k: v for k, v in fields.items() if k in allowed_fields}
        if not update_fields:
            return

        assignments = ", ".join(f"{key} = ?" for key in update_fields.keys())
        values = list(update_fields.values())
        values.append(source_document_id)

        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            f"""
            UPDATE source_documents
            SET {assignments},
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            values,
        )
        conn.commit()
        conn.close()

    def upsert_source_document(
        self,
        *,
        source_type,
        target_type,
        document_id,
        document_name,
        document_subtype=None,
        parent_document_id=None,
        ministry_name=None,
        document_url=None,
        is_active=1,
    ):
        existing = self.get_source_document(source_type, target_type, document_id)

        if existing:
            self.update_source_document(
                existing["id"],
                document_name=document_name,
                document_subtype=document_subtype,
                parent_document_id=parent_document_id,
                ministry_name=ministry_name,
                document_url=document_url,
                is_active=is_active,
            )
            return existing["id"]

        return self.create_source_document(
            source_type=source_type,
            target_type=target_type,
            document_id=document_id,
            document_name=document_name,
            document_subtype=document_subtype,
            parent_document_id=parent_document_id,
            ministry_name=ministry_name,
            document_url=document_url,
            is_active=is_active,
        )

    # Backward-compatible wrappers for legacy code paths
    def get_law_master(self, law_id):
        row = self.get_source_document("law_api", "unknown", law_id)
        return row["id"] if row else None

    def insert_law_master(self, law):
        return self.upsert_source_document(
            source_type="law_api",
            target_type=law.get("target", "unknown"),
            document_id=law["id"],
            document_name=law["name"],
            document_subtype=law.get("document_subtype"),
            ministry_name=law.get("ministry_name"),
            document_url=law.get("document_url"),
        )
