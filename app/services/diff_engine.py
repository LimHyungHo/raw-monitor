from difflib import unified_diff

class DiffEngine:

    def compare_articles(self, old, new):
        changes = []

        keys = set(old.keys()) | set(new.keys())

        for k in sorted(keys):
            o = old.get(k, "")
            n = new.get(k, "")

            if o == n:
                continue

            change_type = "수정"
            if not o:
                change_type = "신규"
            elif not n:
                change_type = "삭제"

            diff = unified_diff(
                o.splitlines(),
                n.splitlines(),
                lineterm=""
            )

            changes.append({
                "article": k,
                "type": change_type,
                "diff": "\n".join(diff)
            })

        return changes