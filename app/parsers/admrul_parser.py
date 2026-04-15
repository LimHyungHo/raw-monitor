from app.parsers.base_parser import BaseParser
import re


class AdmRulParser(BaseParser):

    def parse(self, data):

        service = data.get("AdmRulService", {})

        # 1️⃣ 기본 정보
        info = service.get("행정규칙기본정보", {})
        name = info.get("행정규칙명", "")

        result = {
            "name": name,
            "articles": [],
            "addenda": [],
            "appendix": []
        }

        # 2️⃣ 조문내용 파싱
        contents = service.get("조문내용", [])

        for text in contents:
            if not text:
                continue

            text = text.strip()
            text = self.format_content(text)

            # 🔥 제X조 파싱
            m = re.match(r"^제\s*(\d+)\s*조\((.*?)\)", text)

            if m:
                number = m.group(1)
                title = m.group(2)

                result["articles"].append({
                    "number": number,
                    "title": title,
                    "content": text
                })
            else:
                # 장/절 등
                result["articles"].append({
                    "number": "",
                    "title": "",
                    "content": text
                })

        # 3️⃣ 별표 처리
        appendix_units = (
            service.get("별표", {})
            .get("별표단위", [])
        )

        for app in appendix_units:

            content_rows = app.get("별표내용", [])

            # 🔥 2차원 배열 → 문자열 변환
            content_text = "\n".join(
                [
                    " ".join(row) if isinstance(row, list) else str(row)
                    for row in content_rows
                ]
            )

            result["appendix"].append({
                "title": app.get("별표제목", ""),
                "content": content_text
            })

        return result

    # =========================
    # 🔥 핵심: 텍스트 정리
    # =========================
    def format_content(self, text):

        if not text:
            return text

        # 1️⃣ 개정 태그 줄바꿈 제거 (🔥 먼저 처리)
        text = re.sub(
            r"<개정\s*([\d\.\s\n]+)>",
            lambda m: "<개정 " + " ".join(m.group(1).split()) + ">",
            text
        )

        # 2️⃣ 제X조(제목) 뒤 줄바꿈
        text = re.sub(
            r"(제\s*\d+\s*조\([^)]+\))",
            r"\1\n",
            text
        )

        # 3️⃣ 항목 번호만 줄바꿈 (🔥 핵심 수정)
        text = re.sub(
            r"(?<!\n)(?<!\d)(\d{1,2}\.)\s",
            r"\n\1 ",
            text
        )

        # 4️⃣ 공백 정리
        text = re.sub(r"\n{2,}", "\n\n", text)

        return text.strip()