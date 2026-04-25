import json

import requests

from app.config.settings import settings


class GPTCompareService:
    def analyze_change_detail(self, detail):
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다.")

        payload = self._build_request_payload(detail)
        response = requests.post(
            f"{settings.OPENAI_API_BASE.rstrip('/')}/responses",
            headers={
                "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=120,
        )
        response.raise_for_status()
        response_json = response.json()
        output_text = self._extract_output_text(response_json)
        if not output_text.strip():
            raise ValueError("GPT 비교 결과가 비어 있습니다.")

        return {
            "text": output_text.strip(),
            "model": response_json.get("model") or settings.OPENAI_MODEL,
            "response_id": response_json.get("id"),
        }

    def _build_request_payload(self, detail):
        source_document = detail.get("source_document") or {}
        old_version = detail.get("old_version_display") or detail.get("old_version") or {}
        new_version = detail.get("new_version") or {}
        items = detail.get("items") or []

        item_blocks = []
        for index, item in enumerate(items[:20], start=1):
            item_blocks.append(
                "\n".join(
                    [
                        f"[항목 {index}] {item.get('item_key') or '-'}",
                        f"- 변경 종류: {item.get('change_kind') or '-'}",
                        f"- 이전 조문:",
                        (item.get("old_text") or "-")[:4000],
                        f"- 최신 조문:",
                        (item.get("new_text") or "-")[:4000],
                        f"- diff:",
                        (item.get("diff_text") or "-")[:4000],
                    ]
                )
            )

        comparison_text = "\n\n".join(item_blocks) if item_blocks else "비교할 조문 항목이 없습니다."

        prompt = "\n".join(
            [
                "다음은 최신 법령과 직전 법령의 비교 데이터입니다.",
                "한국어로만 답하고, 법무/준법/실무 담당자가 바로 읽을 수 있게 간결하지만 실무적으로 설명하세요.",
                "반드시 아래 형식으로 작성하세요.",
                "1. 핵심 변경 요약",
                "2. 실무 영향",
                "3. 확인이 필요한 조문",
                "4. 권고 조치",
                "",
                f"- 법령명: {source_document.get('document_name') or '-'}",
                f"- 유형: {source_document.get('target_type') or '-'}",
                f"- 이전 시행일: {old_version.get('effective_date') or '-'}",
                f"- 최신 시행일: {new_version.get('effective_date') or '-'}",
                "",
                comparison_text,
            ]
        )

        return {
            "model": settings.OPENAI_MODEL,
            "instructions": (
                "당신은 법령 변경 비교를 돕는 준법감시 보조 분석가입니다. "
                "과장하지 말고, 입력에 없는 사실은 추정이라고 명시하세요."
            ),
            "input": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": prompt,
                        }
                    ],
                }
            ],
        }

    def _extract_output_text(self, response_json):
        output_text = response_json.get("output_text")
        if isinstance(output_text, str) and output_text.strip():
            return output_text

        chunks = []
        for item in response_json.get("output", []):
            if item.get("type") != "message":
                continue
            for content in item.get("content", []):
                if content.get("type") == "output_text":
                    chunks.append(content.get("text") or "")

        return "\n".join(chunk for chunk in chunks if chunk)
