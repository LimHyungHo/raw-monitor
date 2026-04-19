from app.repositories.monitoring_keyword_repository import MonitoringKeywordRepository
from app.repositories.monitoring_target_repository import MonitoringTargetRepository
from app.services.user_service import UserService


class MonitoringTargetService:
    def __init__(self):
        self.user_service = UserService()
        self.target_repository = MonitoringTargetRepository()
        self.keyword_repository = MonitoringKeywordRepository()

    def register_monitoring(
        self,
        *,
        email,
        document_name,
        target_type,
        keywords=None,
        user_name=None,
        target_name=None,
        document_id=None,
        source_org="law.go.kr",
        notify_email=None,
        is_active=1,
        keyword_match_mode="contains",
    ):
        user = self.user_service.register_user(email=email, name=user_name, is_active=1)
        recipient_email = self.user_service.normalize_email(notify_email or email)
        normalized_document_name = self._require_text(document_name, "법령명")
        normalized_target_type = self._require_text(target_type, "대상 유형")
        normalized_target_name = (
            target_name.strip()
            if target_name and target_name.strip()
            else f"{normalized_document_name} 모니터링"
        )

        target_id = self.target_repository.upsert_target(
            user_id=user["id"],
            target_name=normalized_target_name,
            target_type=normalized_target_type,
            document_name=normalized_document_name,
            document_id=document_id,
            source_org=source_org,
            notify_email=recipient_email,
            is_active=is_active,
        )

        saved_keywords = []
        for keyword in self._normalize_keywords(keywords):
            keyword_id = self.keyword_repository.upsert_keyword(
                monitoring_target_id=target_id,
                keyword=keyword,
                match_mode=keyword_match_mode,
                is_active=is_active,
            )
            saved_keywords.append(
                {
                    "id": keyword_id,
                    "keyword": keyword,
                    "match_mode": keyword_match_mode,
                }
            )

        target = self.target_repository.get_target_by_id(target_id)
        return {
            "user": user,
            "target": target,
            "keywords": saved_keywords,
        }

    def list_monitoring_targets(self, *, email=None, name=None, active_only=False):
        users = self.user_service.list_users(email=email, name=name)
        if not users:
            return []

        all_targets = []
        for user in users:
            targets = self.target_repository.list_targets_by_user(
                user["id"],
                active_only=active_only,
            )

            for target in targets:
                target["user_name"] = user.get("name")
                target["user_email"] = user.get("email")
                target["keywords"] = self.keyword_repository.list_keywords_by_target(
                    target["id"],
                    active_only=active_only,
                )
                all_targets.append(target)

        return all_targets

    def deactivate_target(self, target_id):
        self.target_repository.update_target(target_id, is_active=0)
        target = self.target_repository.get_target_by_id(target_id)
        if not target:
            return None

        for keyword in self.keyword_repository.list_keywords_by_target(target_id):
            self.keyword_repository.update_keyword(keyword["id"], is_active=0)

        target["keywords"] = self.keyword_repository.list_keywords_by_target(target_id)
        return target

    def _normalize_keywords(self, keywords):
        if not keywords:
            return []

        if isinstance(keywords, str):
            keywords = [keywords]

        normalized_keywords = []
        seen = set()

        for keyword in keywords:
            normalized_keyword = self._require_text(keyword, "키워드")
            if normalized_keyword in seen:
                continue
            seen.add(normalized_keyword)
            normalized_keywords.append(normalized_keyword)

        return normalized_keywords

    def _require_text(self, value, field_name):
        normalized_value = (value or "").strip()
        if not normalized_value:
            raise ValueError(f"{field_name}이(가) 필요합니다.")
        return normalized_value
