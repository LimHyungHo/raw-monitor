from app.repositories.db import get_connection

class VersionRepository:

    def get_latest_version(self, law_master_id):
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT ID, VERSION_NO, CONTENT, CONTENT_HASH
            FROM LAW_VERSION
            WHERE LAW_MASTER_ID = :1
            ORDER BY VERSION_NO DESC
            FETCH FIRST 1 ROW ONLY
        """, [law_master_id])

        row = cur.fetchone()
        conn.close()

        return row

    def insert_version(self, law_master_id, version_no, content, hash):
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO LAW_VERSION
            (LAW_MASTER_ID, VERSION_NO, CONTENT, CONTENT_HASH)
            VALUES (:1, :2, :3, :4)
        """, [law_master_id, version_no, content, hash])

        conn.commit()
        conn.close()