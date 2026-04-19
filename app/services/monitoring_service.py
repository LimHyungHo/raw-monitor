import json
import requests

from app.collectors.law_api_collector import LawAPICollector
from app.config.settings import settings
from app.parsers.admrul_parser import AdmRulParser
from app.parsers.law_parser import LawParser
from app.repositories.change_item_repository import ChangeItemRepository
from app.repositories.change_set_repository import ChangeSetRepository
from app.repositories.law_repository import LawRepository
from app.repositories.monitoring_keyword_repository import MonitoringKeywordRepository
from app.repositories.monitoring_target_repository import MonitoringTargetRepository
from app.repositories.version_repository import VersionRepository
from app.services.diff_engine import DiffEngine
from app.services.law_id_service import LawIdService
from app.utils.hash_util import generate_hash


class MonitoringService:
    def __init__(self):
        self.collector = LawAPICollector()
        self.law_parser = LawParser()
        self.admrul_parser = AdmRulParser()
        self.diff_engine = DiffEngine()
        self.id_service = LawIdService()

        self.target_repository = MonitoringTargetRepository()
        self.keyword_repository = MonitoringKeywordRepository()
        self.law_repository = LawRepository()
        self.version_repository = VersionRepository()
        self.change_set_repository = ChangeSetRepository()
        self.change_item_repository = ChangeItemRepository()

    def run(self):
        self._validate_runtime_config()

        print("\n" + "=" * 30)
        print("   DB 기반 법령 모니터링 시작")
        print("=" * 30)

        targets = self._list_active_targets()
        if not targets:
            print("📭 활성화된 모니터링 대상이 없습니다.")
            return []

        results = []
        for target in targets:
            try:
                result = self.process_target(target)
            except Exception as exc:
                document_name = target.get("document_name", "알 수 없는 대상")
                print(f"❌ {document_name} 처리 실패: {exc}")
                result = {
                    "target_id": target.get("id"),
                    "status": "error",
                    "error": str(exc),
                    "document_name": document_name,
                }
            results.append(result)

        return results

    def run_pdf_job(self):
        print("⚠️ PDF 배치 작업은 아직 새 DB 기반 흐름으로 연결 전입니다.")
        print("현재는 monitor 모드에서 수집/버전저장/변경감지만 우선 지원합니다.")
        return []

    def process_target(self, target):
        target_id = target["id"]
        document_name = target["document_name"]
        target_type = self._normalize_target_type(target["target_type"])

        print(f"\n▶ {document_name} ({target_type}) 분석 중")

        document_id = target.get("document_id")
        if not document_id:
            document_id = self.id_service.get_law_id(document_name, target_type)
            self.target_repository.update_target(target_id, document_id=document_id)

        source_document_id = self.law_repository.upsert_source_document(
            source_type="law_api",
            target_type=target_type,
            document_id=document_id,
            document_name=document_name,
            document_subtype=self._infer_document_subtype(target_type, document_name),
            ministry_name=target.get("source_org"),
        )

        raw_json = self.collector.fetch_json(target_type, document_id)
        if not raw_json:
            raise ValueError("응답 본문이 비어 있습니다.")
        self._validate_raw_json(raw_json, target_type, document_name, document_id)
        raw_json_text = json.dumps(raw_json, ensure_ascii=False, sort_keys=True)
        content_hash = generate_hash(raw_json_text)
        version_metadata = self._extract_version_metadata(raw_json, target_type, document_id)
        parsed_data = self._parse_document(raw_json, target_type)
        parsed_json_text = json.dumps(parsed_data, ensure_ascii=False)
        article_map = self._build_article_map(parsed_data)
        raw_text = self._build_raw_text(parsed_data)

        current_version = self.version_repository.get_current_version(source_document_id)
        if current_version and current_version["content_hash"] == content_hash:
            backfill_result = self._maybe_backfill_previous_version(
                target=target,
                source_document_id=source_document_id,
                current_version=current_version,
                current_parsed_data=parsed_data,
                current_article_map=article_map,
            )
            if backfill_result:
                return backfill_result
            print("✅ 변경 사항 없음")
            return {
                "target_id": target_id,
                "source_document_id": source_document_id,
                "status": "unchanged",
                "change_set_id": None,
            }

        new_version_id = self.version_repository.save_version(
            source_document_id,
            version_key=version_metadata["version_key"],
            version_no=version_metadata["version_no"],
            effective_date=version_metadata["effective_date"],
            promulgation_date=version_metadata["promulgation_date"],
            announcement_no=version_metadata["announcement_no"],
            revision_type=version_metadata["revision_type"],
            content_hash=content_hash,
            raw_json=raw_json_text,
            raw_text=raw_text,
            parsed_json=parsed_json_text,
            is_current=1,
        )

        if not current_version:
            backfill_result = self._maybe_backfill_previous_version(
                target=target,
                source_document_id=source_document_id,
                current_version=self.version_repository.get_version_by_id(new_version_id),
                current_parsed_data=parsed_data,
                current_article_map=article_map,
            )
            if backfill_result:
                return backfill_result
            print("📁 최초 버전 저장 완료")
            return {
                "target_id": target_id,
                "source_document_id": source_document_id,
                "status": "initialized",
                "change_set_id": None,
                "version_id": new_version_id,
            }

        old_article_map = self._load_article_map_from_version(current_version)
        changes = self.diff_engine.compare_articles(old_article_map, article_map)
        if not changes:
            print("ℹ️ 해시는 달라졌지만 조문 단위 변경은 감지되지 않았습니다.")
            return {
                "target_id": target_id,
                "source_document_id": source_document_id,
                "status": "version_updated",
                "change_set_id": None,
                "version_id": new_version_id,
            }

        keywords = self.keyword_repository.list_keywords_by_target(target_id, active_only=True)
        keyword_values = [keyword["keyword"] for keyword in keywords]
        keyword_hit_count = 0

        change_set_id = self.change_set_repository.create_change_set(
            source_document_id=source_document_id,
            old_version_id=current_version["id"],
            new_version_id=new_version_id,
            change_type="updated",
            summary=self._build_change_summary(document_name, changes),
            keyword_hit_count=0,
            has_structural_change=1,
        )

        for index, change in enumerate(changes, start=1):
            matched_keywords = self._match_keywords(change["diff"], keyword_values)
            if matched_keywords:
                keyword_hit_count += len(matched_keywords)

            self.change_item_repository.create_change_item(
                change_set_id=change_set_id,
                item_type="article",
                item_key=change["article"],
                change_kind=change["type"],
                old_text=old_article_map.get(change["article"], ""),
                new_text=article_map.get(change["article"], ""),
                diff_text=change["diff"],
                keyword_matched=1 if matched_keywords else 0,
                matched_keywords=", ".join(matched_keywords) if matched_keywords else None,
                sort_order=index,
            )

        # keyword hit count update
        self._update_change_set_keyword_count(change_set_id, keyword_hit_count)

        print(f"🚨 변경 감지: {len(changes)}건, 키워드 일치 {keyword_hit_count}건")
        return {
            "target_id": target_id,
            "source_document_id": source_document_id,
            "status": "changed",
            "change_set_id": change_set_id,
            "version_id": new_version_id,
            "change_count": len(changes),
            "keyword_hit_count": keyword_hit_count,
        }

    def _maybe_backfill_previous_version(
        self,
        *,
        target,
        source_document_id,
        current_version,
        current_parsed_data,
        current_article_map,
    ):
        if not current_version:
            return None

        existing_versions = self.version_repository.list_versions(source_document_id)
        existing_change_sets = self.change_set_repository.list_change_sets_by_document(
            source_document_id,
            limit=1,
        )
        if len(existing_versions) > 1 or existing_change_sets:
            return None

        document_name = target["document_name"]
        target_type = self._normalize_target_type(target["target_type"])
        document_id = target.get("document_id")

        previous_metadata = self.id_service.find_previous_version_metadata(
            name=document_name,
            target=target_type,
            current_effective_date=current_version.get("effective_date"),
            document_id=document_id,
        )
        if not previous_metadata:
            return None

        previous_raw_json = self._fetch_previous_raw_json(previous_metadata, target_type)
        if not previous_raw_json:
            return None

        self._validate_raw_json(previous_raw_json, target_type, document_name, document_id)
        previous_raw_json_text = json.dumps(previous_raw_json, ensure_ascii=False, sort_keys=True)
        previous_content_hash = generate_hash(previous_raw_json_text)
        previous_version_metadata = self._extract_version_metadata(
            previous_raw_json,
            target_type,
            document_id,
        )
        previous_parsed_data = self._parse_document(previous_raw_json, target_type)
        previous_parsed_json_text = json.dumps(previous_parsed_data, ensure_ascii=False)
        previous_article_map = self._build_article_map(previous_parsed_data)
        previous_raw_text = self._build_raw_text(previous_parsed_data)

        previous_version_id = self.version_repository.save_version(
            source_document_id,
            version_key=previous_version_metadata["version_key"],
            version_no=previous_version_metadata["version_no"],
            effective_date=previous_version_metadata["effective_date"],
            promulgation_date=previous_version_metadata["promulgation_date"],
            announcement_no=previous_version_metadata["announcement_no"],
            revision_type=previous_version_metadata["revision_type"],
            content_hash=previous_content_hash,
            raw_json=previous_raw_json_text,
            raw_text=previous_raw_text,
            parsed_json=previous_parsed_json_text,
            is_current=0,
        )

        changes = self.diff_engine.compare_articles(previous_article_map, current_article_map)
        if not changes:
            print("ℹ️ 자동 백필 비교 결과 변경사항 없음")
            return {
                "target_id": target["id"],
                "source_document_id": source_document_id,
                "status": "unchanged",
                "change_set_id": None,
                "version_id": current_version["id"],
            }

        keyword_values = [
            keyword["keyword"]
            for keyword in self.keyword_repository.list_keywords_by_target(
                target["id"],
                active_only=True,
            )
        ]
        change_set_id = self.change_set_repository.create_change_set(
            source_document_id=source_document_id,
            old_version_id=previous_version_id,
            new_version_id=current_version["id"],
            change_type="backfilled",
            summary=self._build_change_summary(document_name, changes),
            keyword_hit_count=0,
            has_structural_change=1,
        )

        keyword_hit_count = 0
        for index, change in enumerate(changes, start=1):
            matched_keywords = self._match_keywords(change["diff"], keyword_values)
            if matched_keywords:
                keyword_hit_count += len(matched_keywords)

            self.change_item_repository.create_change_item(
                change_set_id=change_set_id,
                item_type="article",
                item_key=change["article"],
                change_kind=change["type"],
                old_text=previous_article_map.get(change["article"], ""),
                new_text=current_article_map.get(change["article"], ""),
                diff_text=change["diff"],
                keyword_matched=1 if matched_keywords else 0,
                matched_keywords=", ".join(matched_keywords) if matched_keywords else None,
                sort_order=index,
            )

        self._update_change_set_keyword_count(change_set_id, keyword_hit_count)
        print(f"🧩 자동 백필 비교 완료: {len(changes)}건")
        return {
            "target_id": target["id"],
            "source_document_id": source_document_id,
            "status": "backfilled_changed",
            "change_set_id": change_set_id,
            "version_id": current_version["id"],
            "change_count": len(changes),
            "keyword_hit_count": keyword_hit_count,
        }

    def _fetch_previous_raw_json(self, previous_metadata, target_type):
        detail_link = previous_metadata.get("detail_link")
        if detail_link:
            return self.collector.fetch_json_by_detail_link(detail_link)

        previous_document_id = previous_metadata.get("document_id")
        if not previous_document_id:
            return None
        return self.collector.fetch_json(target_type, previous_document_id)

    def _list_active_targets(self):
        conn = None
        try:
            from app.repositories.db import get_connection

            conn = get_connection()
            cur = conn.cursor()
            cur.execute(
                """
                SELECT *
                FROM monitoring_targets
                WHERE is_active = 1
                ORDER BY id ASC
                """
            )
            rows = cur.fetchall()
            return [dict(row) for row in rows]
        finally:
            if conn:
                conn.close()

    def _normalize_target_type(self, target_type):
        normalized = (target_type or "").strip().lower()
        if normalized in {"law", "eflaw"}:
            return "law"
        if normalized == "admrul":
            return "admrul"
        raise ValueError(f"지원하지 않는 target_type 입니다: {target_type}")

    def _infer_document_subtype(self, target_type, document_name):
        if target_type == "admrul":
            return "행정규칙"
        if "시행령" in document_name:
            return "시행령"
        if "시행규칙" in document_name:
            return "시행규칙"
        return "법령"

    def _extract_version_metadata(self, raw_json, target_type, document_id):
        if target_type == "law":
            info = raw_json.get("법령", {}).get("기본정보", {})
            version_no = self._safe_int(info.get("법령일련번호"))
            effective_date = info.get("시행일자")
            promulgation_date = info.get("공포일자")
            announcement_no = info.get("공포번호")
            revision_type = info.get("제개정구분명")
        else:
            service = raw_json.get("AdmRulService", {})
            info = service.get("행정규칙기본정보", {})
            version_no = self._safe_int(info.get("행정규칙일련번호"))
            effective_date = info.get("시행일자") or info.get("발령일자")
            promulgation_date = info.get("발령일자")
            announcement_no = info.get("발령번호")
            revision_type = info.get("제개정구분명")

        version_key_parts = [
            str(version_no or ""),
            effective_date or "",
            promulgation_date or "",
            announcement_no or "",
            document_id or "",
        ]
        version_key = "|".join(version_key_parts)

        return {
            "version_key": version_key,
            "version_no": version_no,
            "effective_date": effective_date,
            "promulgation_date": promulgation_date,
            "announcement_no": announcement_no,
            "revision_type": revision_type,
        }

    def _parse_document(self, raw_json, target_type):
        parser = self.law_parser if target_type == "law" else self.admrul_parser
        return parser.parse(raw_json)

    def _validate_raw_json(self, raw_json, target_type, document_name, document_id):
        if target_type == "law":
            law_root = raw_json.get("법령")
            if not isinstance(law_root, dict):
                raise ValueError(
                    f"{document_name} 상세 응답 구조가 올바르지 않습니다. "
                    f"(target={target_type}, id={document_id})"
                )
            return

        if target_type == "admrul":
            admrul_root = raw_json.get("AdmRulService")
            if not isinstance(admrul_root, dict):
                raise ValueError(
                    f"{document_name} 상세 응답 구조가 올바르지 않습니다. "
                    f"(target={target_type}, id={document_id})"
                )
            return

    def _build_article_map(self, parsed_data):
        article_map = {}

        for article in parsed_data.get("articles", []):
            if not isinstance(article, dict):
                continue

            key = self._get_article_key(article)
            content = (article.get("content") or "").strip()
            if not key:
                continue

            article_map[key] = content

        addenda = parsed_data.get("addenda")
        if addenda:
            if isinstance(addenda, list):
                article_map["부칙"] = "\n".join(str(item) for item in addenda if item)
            else:
                article_map["부칙"] = str(addenda)

        for appendix in self._flatten_appendix(parsed_data.get("appendix", [])):
            if not isinstance(appendix, dict):
                continue
            title = appendix.get("title")
            content = appendix.get("content")
            if not title:
                continue
            if isinstance(content, list):
                content = "\n".join(str(item) for item in content if item)
            article_map[title] = str(content or "")

        return article_map

    def _build_raw_text(self, parsed_data):
        chunks = []
        for key, value in self._build_article_map(parsed_data).items():
            chunks.append(key)
            chunks.append(value)
        return "\n\n".join(chunk for chunk in chunks if chunk)

    def _get_article_key(self, article):
        number = (article.get("number") or "").strip()
        title = (article.get("title") or "").strip()

        if number:
            return f"제{number}조" if number.isdigit() else number
        if title:
            return title
        content = (article.get("content") or "").strip()
        if not content:
            return ""
        first_line = content.splitlines()[0].strip()
        return first_line[:80]

    def _flatten_appendix(self, appendix):
        flat = []
        for item in appendix or []:
            if isinstance(item, list):
                flat.extend(self._flatten_appendix(item))
            else:
                flat.append(item)
        return flat

    def _load_article_map_from_version(self, version_row):
        parsed_json = version_row.get("parsed_json")
        if parsed_json:
            parsed_data = json.loads(parsed_json)
            return self._build_article_map(parsed_data)

        raw_text = version_row.get("raw_text") or ""
        if not raw_text.strip():
            return {}
        return {"전문": raw_text}

    def _build_change_summary(self, document_name, changes):
        first_keys = ", ".join(change["article"] for change in changes[:5])
        if len(changes) > 5:
            first_keys += " 외"
        return f"{document_name} 변경 {len(changes)}건: {first_keys}"

    def _match_keywords(self, text, keywords):
        return [keyword for keyword in keywords if keyword and keyword in text]

    def _update_change_set_keyword_count(self, change_set_id, keyword_hit_count):
        from app.repositories.db import get_connection

        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE change_sets
            SET keyword_hit_count = ?
            WHERE id = ?
            """,
            (keyword_hit_count, change_set_id),
        )
        conn.commit()
        conn.close()

    def _safe_int(self, value):
        if value in (None, ""):
            return None
        try:
            return int(str(value).strip())
        except (TypeError, ValueError):
            return None

    def _validate_runtime_config(self):
        if not settings.LAW_API_KEY:
            raise ValueError("LAW_API_KEY가 설정되지 않았습니다. .env 또는 환경변수를 확인해 주세요.")
