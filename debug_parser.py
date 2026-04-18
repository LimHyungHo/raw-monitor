import json
import sys
import os
import re
import markdown
from pprint import pprint

from app.parsers.law_parser import LawParser
from app.parsers.admrul_parser import AdmRulParser

# 선택
from weasyprint import HTML
from weasyprint import CSS

css = CSS(string="""
.law-table {
    border-collapse: collapse;
    width: 100%;
    table-layout: fixed;   /* 🔥 핵심: 컬럼 균등 분배 */
    font-size: 12px;
}

.law-table th, .law-table td {
    border: 1px solid #333;
    padding: 8px 10px;
    vertical-align: middle;   /* 🔥 위쪽 붙는 문제 해결 */
    word-break: break-word;   /* 🔥 긴 문장 자동 줄바꿈 */
    line-height: 1.5;
}

.law-table th {
    background-color: #f2f2f2;
    font-weight: bold;
    text-align: center;
}

.law-table td {
    text-align: left;
}

/* 🔥 컬럼별 너비 조정 (중요) */
.law-table td:nth-child(1),
.law-table th:nth-child(1) {
    width: 55%;
}

.law-table td:nth-child(2),
.law-table th:nth-child(2) {
    width: 20%;
}

.law-table td:nth-child(3),
.law-table th:nth-child(3) {
    width: 12%;
    text-align: center;
}

.law-table td:nth-child(4),
.law-table th:nth-child(4) {
    width: 13%;
    text-align: center;
}
""")

# =========================
# 유틸
# =========================
def get_parser(data):
    if isinstance(data, dict):
        if data.get("AdmRulService"):
            print("👉 AdmRulParser 선택")
            return AdmRulParser()

        if data.get("LawService") or data.get("법령"):
            print("👉 LawParser 선택")
            return LawParser()

    raise ValueError("지원하지 않는 JSON 구조입니다")
    
def load_json(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_markdown(md_text, path="debug.md"):
    with open(path, "w", encoding="utf-8") as f:
        f.write(md_text)
    print(f"[DEBUG] Markdown 저장 완료: {path}")


def md_to_pdf(md_text, output_pdf="debug.pdf"):
    # html = markdown.markdown(md_text)
    html = markdown.markdown(md_text, extensions=['nl2br'])
    # HTML(string=html).write_pdf(output_pdf)
    HTML(string=html).write_pdf(output_pdf, stylesheets=[css])
    print(f"[DEBUG] PDF 생성 완료: {output_pdf}")

def _flatten(self, value):
    if isinstance(value, list):
        result = []
        for v in value:
            result.extend(self._flatten(v))
        return result
    return [value]

def detect_structure(text):
    if not text:
        return None

    text = text.strip()

    if re.match(r"^제\s*\d+\s*편", text):
        return "#"
    elif re.match(r"^제\s*\d+\s*장", text):
        return "##"
    elif re.match(r"^제\s*\d+\s*절", text):
        return "###"
    elif re.match(r"^제\s*\d+\s*관", text):
        return "####"

    return None

def _split_structure(self, texts):
    results = []

    for text in texts:
        if not text:
            continue

        text = text.strip()

        # 장
        if re.match(r"^제\s*\d+\s*장", text):
            results.append(("chapter", text))

        # 절
        elif re.match(r"^제\s*\d+\s*절", text):
            results.append(("section", text))

        # 관
        elif re.match(r"^제\s*\d+\s*관", text):
            results.append(("subsection", text))

        else:
            results.append(("text", text))

    return results

# =========================
# Markdown 변환 (도메인 기반)
# =========================
def to_markdown(law):
    if not law:
        return ""

    md = []

    # 1️⃣ 법령/규정명 (meta 또는 name)
    name = law.get("name") or law.get("meta", {}).get("name", "규정 명칭")
    md.append(f"# {name}\n")

    # 2️⃣ 조문 처리 (Articles)
    for art in law.get("articles", []):
        if not art: continue
        content = art.get("content") or ""
        
        # 장/절/관 감지하여 마크다운 헤더로 변환
        level = detect_structure(content)
        if level:
            md.append(f"{level} {content}\n")
            continue

        num = art.get("number", "")
        title = art.get("title", "")
        
        if title:
            md.append(f"### 제{num}조 {title}")
        md.append(f"{content}\n")

    # 3️⃣ 부칙 처리 (Addenda)
    addenda = law.get("addenda")
    if addenda:
        md.append("\n---\n# 부칙\n")
        if isinstance(addenda, list):
            md.append("\n".join(map(str, addenda)))
        else:
            md.append(str(addenda))

    # 4️⃣ 별표 처리 (Appendix) - 🔥 AttributeError 해결 포인트
    appendix_data = law.get("appendix", [])
    if appendix_data:
        md.append("\n---\n# 별표\n")

        # [핵심] 리스트 속에 리스트가 있는 경우([[...]])를 대비한 평탄화
        flat_appendix = []
        if isinstance(appendix_data, list):
            for item in appendix_data:
                if isinstance(item, list):
                    flat_appendix.extend(item) # 이중 리스트 해제
                else:
                    flat_appendix.append(item)
        else:
            flat_appendix = [appendix_data]

        for app in flat_appendix:
            # app이 dict가 아니면 .get()에서 에러가 나므로 체크
            if not isinstance(app, dict):
                continue

            title = app.get("title", "별표")
            content = app.get("content", "")

            md.append(f"## {title}")

            # 내용이 리스트(normalize_appendix_lines 결과물)라면 줄바꿈으로 합침
            if isinstance(content, list):
                content = "\n".join(map(str, content))
            
            md.append(str(content))
            md.append("")

    return "\n".join(md)

# =========================
# 디버깅 출력
# =========================
def debug_print(law):

    print("\n==============================")
    print("📌 Law 정보")
    print("==============================")

    print("법령명:", law["name"])
    print("조문 수:", len(law["articles"]))

    print("\n==============================")
    print("📌 첫 번째 조문")
    print("==============================")

    if law["articles"]:
        first = law["articles"][0]

        print("번호:", first["number"])
        print("제목:", first["title"])
        print("내용:", first["content"][:200])


# =========================
# MAIN
# =========================
def main(file_path):

    print("\n==============================")
    print("📂 JSON 로드")
    print("==============================")

    data = load_json(file_path)
    # print("JSON 구조:",data.keys())

    print("\n==============================")
    print("⚙️ Parser 실행")
    print("==============================")
    # parser = LawParser()
    parser = get_parser(data)
    law = parser.parse(data)

    print("\n==============================")
    print("📌 PARSE RESULT")
    print("==============================")
    from pprint import pprint
    pprint(law)

    # 구조 확인
    print("\n==============================")
    print("📝 Markdown 생성")
    print("==============================")
    md_text = to_markdown(law)

    # 🔥 핵심 디버깅 포인트
    save_markdown(md_text, "output.md")
    print("\n==============================")
    print("📄 PDF 생성")
    print("==============================")

    try:
        md_to_pdf(md_text, "output.pdf")
    except Exception as e:
        print("❌ PDF 생성 실패:", e)


if __name__ == "__main__":

    if len(sys.argv) < 2:
        print("사용법:")
        print("python debug_parser.py <json파일경로>")
        sys.exit(1)

    file_path = sys.argv[1]
    main(file_path)