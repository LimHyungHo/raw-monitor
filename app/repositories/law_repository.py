from app.repositories.db import get_connection

class LawRepository:

    def get_law_master(self, law_id):
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT ID FROM LAW_MASTER WHERE LAW_ID = :1
        """, [law_id])

        row = cur.fetchone()
        conn.close()

        return row[0] if row else None

    def insert_law_master(self, law):
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO LAW_MASTER (LAW_ID, LAW_NAME, LAW_TYPE)
            VALUES (:1, :2, :3)
        """, [law["id"], law["name"], law["target"]])

        conn.commit()
        conn.close()