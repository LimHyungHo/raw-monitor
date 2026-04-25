from app.repositories.change_item_repository import ChangeItemRepository
from app.repositories.change_set_repository import ChangeSetRepository
from app.repositories.law_repository import LawRepository
from app.repositories.monitoring_target_repository import MonitoringTargetRepository
from app.repositories.version_repository import VersionRepository
from app.services.law_id_service import LawIdService
from app.services.user_service import UserService


class ChangeHistoryService:
    def __init__(self):
        self.user_service = UserService()
        self.target_repository = MonitoringTargetRepository()
        self.law_repository = LawRepository()
        self.version_repository = VersionRepository()
        self.change_set_repository = ChangeSetRepository()
        self.change_item_repository = ChangeItemRepository()
        self.law_id_service = LawIdService()

    def list_changes(self, *, email=None, name=None, target_ids=None, limit_per_target=10):
        users = self.user_service.list_users(email=email, name=name)
        if not users:
            return []

        allowed_target_ids = {
            int(target_id)
            for target_id in (target_ids or [])
            if str(target_id).strip().isdigit()
        }
        histories = []

        for user in users:
            targets = self.target_repository.list_targets_by_user(user["id"], active_only=False)

            for target in targets:
                if allowed_target_ids and target["id"] not in allowed_target_ids:
                    continue
                document_id = target.get("document_id")
                if not document_id:
                    continue

                source_document = self.law_repository.get_source_document(
                    "law_api",
                    self._normalize_target_type(target["target_type"]),
                    document_id,
                )
                if not source_document:
                    continue

                change_sets = self.change_set_repository.list_change_sets_by_document(
                    source_document["id"],
                    limit=limit_per_target,
                )

                for change_set in change_sets:
                    histories.append(
                        self._build_change_summary_row(
                            target=target,
                            source_document=source_document,
                            change_set=change_set,
                            user=user,
                        )
                    )

        histories.sort(key=lambda item: (item["detected_at"], item["id"]), reverse=True)
        return histories

    def get_change_detail(self, change_set_id):
        change_set = self.change_set_repository.get_change_set(change_set_id)
        if not change_set:
            return None

        source_document = self.law_repository.get_source_document_by_id(
            change_set["source_document_id"]
        )
        old_version = None
        if change_set.get("old_version_id"):
            old_version = self.version_repository.get_version_by_id(change_set["old_version_id"])
        new_version = self.version_repository.get_version_by_id(change_set["new_version_id"])
        old_version_display = self._resolve_previous_version_metadata(
            target_type=source_document["target_type"] if source_document else None,
            document_name=source_document["document_name"] if source_document else None,
            document_id=source_document["document_id"] if source_document else None,
            old_version=old_version,
            new_version=new_version,
        )
        items = self.change_item_repository.list_change_items(change_set_id)

        return {
            "change_set": change_set,
            "source_document": source_document,
            "old_version": old_version,
            "old_version_display": old_version_display,
            "new_version": new_version,
            "items": items,
        }

    def _build_change_summary_row(self, *, target, source_document, change_set, user):
        old_version = None
        if change_set.get("old_version_id"):
            old_version = self.version_repository.get_version_by_id(change_set["old_version_id"])
        new_version = self.version_repository.get_version_by_id(change_set["new_version_id"])
        old_version_display = self._resolve_previous_version_metadata(
            target_type=target["target_type"],
            document_name=target["document_name"],
            document_id=target.get("document_id"),
            old_version=old_version,
            new_version=new_version,
        )

        return {
            "id": change_set["id"],
            "target_id": target["id"],
            "user_name": user.get("name"),
            "user_email": user.get("email"),
            "document_name": target["document_name"],
            "target_type": target["target_type"],
            "summary": change_set.get("summary") or "",
            "change_type": change_set["change_type"],
            "keyword_hit_count": change_set["keyword_hit_count"],
            "has_structural_change": change_set["has_structural_change"],
            "detected_at": change_set["detected_at"],
            "document_id": target.get("document_id"),
            "source_document_id": source_document["id"],
            "old_effective_date": old_version_display.get("effective_date") if old_version_display else None,
            "new_effective_date": new_version.get("effective_date") if new_version else None,
        }

    def _normalize_target_type(self, target_type):
        normalized = (target_type or "").strip().lower()
        if normalized in {"law", "eflaw"}:
            return "law"
        if normalized == "admrul":
            return "admrul"
        return normalized

    def _resolve_previous_version_metadata(
        self,
        *,
        target_type,
        document_name,
        document_id,
        old_version,
        new_version,
    ):
        if old_version and old_version.get("effective_date"):
            return old_version

        normalized_target_type = self._normalize_target_type(target_type)
        if not document_name or not normalized_target_type:
            return old_version

        current_effective_date = new_version.get("effective_date") if new_version else None

        try:
            previous_metadata = self.law_id_service.find_previous_version_metadata(
                name=document_name,
                target=normalized_target_type,
                current_effective_date=current_effective_date,
                document_id=document_id,
            )
        except Exception as exc:
            print(f"⚠️ 이전 버전 메타데이터 조회 실패: {document_name} / {exc}")
            return old_version

        if not previous_metadata:
            print(f"ℹ️ 이전 버전 메타데이터 미보강: {document_name}")
            return old_version

        merged = dict(old_version or {})
        merged.update(
            {
                "effective_date": previous_metadata.get("effective_date"),
                "promulgation_date": previous_metadata.get("promulgation_date"),
                "announcement_no": previous_metadata.get("announcement_no"),
                "revision_type": previous_metadata.get("revision_type"),
                "version_no": previous_metadata.get("version_no"),
            }
        )

        if old_version and old_version.get("id"):
            self._persist_previous_version_metadata(old_version, merged)

        return merged

    def _persist_previous_version_metadata(self, old_version, merged):
        fields_to_update = {}

        for field in ("effective_date", "promulgation_date", "announcement_no", "revision_type", "version_no"):
            if old_version.get(field):
                continue
            new_value = merged.get(field)
            if new_value in (None, ""):
                continue
            fields_to_update[field] = new_value

        if not fields_to_update:
            print(
                f"ℹ️ 이전 버전 메타데이터 저장 스킵: version_id={old_version.get('id')}, "
                f"이미 값이 있거나 새 값이 없음"
            )
            return

        print(
            f"💾 이전 버전 메타데이터 저장: version_id={old_version['id']}, "
            f"fields={fields_to_update}"
        )
        self.version_repository.update_version_metadata(old_version["id"], **fields_to_update)
