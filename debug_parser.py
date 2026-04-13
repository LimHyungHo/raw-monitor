import json
import sys
import os
import re
from pprint import pprint

from app.parsers.law_parser import LawParser

# 선택
import markdown
from weasyprint import HTML


# =========================
# 유틸
# =========================
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
    HTML(string=html).write_pdf(output_pdf)
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

    if re.match(r"^제\s*\d+\s*장", text):
        return "#"
    elif re.match(r"^제\s*\d+\s*절", text):
        return "##"
    elif re.match(r"^제\s*\d+\s*관", text):
        return "###"
    
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

    md = []

    name = law.get("name") or law.get("meta", {}).get("name", "")
    md.append(f"# {name}\n")

    # =========================
    # 1️⃣ 조문
    # =========================
    for art in law.get("articles", []):

        content = (art.get("content") or "").strip()

        # 🔥 장/절/관 감지
        level = detect_structure(content)
        if level:
            md.append(f"{level} {content}\n")
            continue

        # 일반 조문
        number = art.get("number", "")
        title = art.get("title", "")

        if not title:
            md.append(content)
        else:
            md.append(f"### 제{number}조 {title}")
            md.append(content)
        md.append("")
        # md.append("\n")

    # =========================
    # 2️⃣ 부칙
    # =========================
    addenda = law.get("addenda")

    if addenda:
        md.append("\n---\n")
        md.append("# 부칙\n")

        # 🔥 list 대응
        if isinstance(addenda, list):
            for item in addenda:
                md.append(str(item))
        else:
            md.append(str(addenda))

        md.append("")

    # =========================
    # 3️⃣ 별표
    # =========================
    appendix = law.get("appendix", [])

    if appendix:
        md.append("\n---\n")
        md.append("# 별표\n")

        # 🔥 dict → list 보정
        if not isinstance(appendix, list):
            appendix = [appendix]

        for idx, app in enumerate(appendix, 1):
            if not app:
                continue

            title = app.get("title", "")
            content = app.get("content", "")

            md.append(f"## [별표 {idx}] {title}")

            # 🔥 list / html 대응
            if isinstance(content, list):
                content = "\n".join(map(str, content))

            md.append(str(content))
            md.append("")

    return "\n".join(md)
# def to_markdown(law):
#     print("\n==============================")
#     print(law)

#     md = []

#     # 1️⃣ 제목
#     # md.append(f"# {law['meta']['name']}\n")
#     md.append(f"# {law['name']}\n")

#     # 2️⃣ 본문 (조문)
#     for art in law.get("articles", []):
#         md.append(f"## 제{art['number']}조 {art.get('title','')}")
#         md.append(art["content"])
#         md.append("")

#     # 3️⃣ 🔥 부칙
#     if law.get("addenda"):
#         md.append("\n---\n")
#         md.append("# 부칙\n")
#         md.append(law["addenda"])
#         md.append("")

#     # 4️⃣ 🔥 별표 (핵심)
#     if law.get("appendix"):
#         md.append("\n---\n")
#         md.append("# 별표\n")

#         for idx, app in enumerate(law["appendix"], 1):
#             md.append(f"## [별표 {idx}] {app.get('title','')}")
#             md.append(app.get("content", ""))
#             md.append("")

#     return "\n".join(md)
# def to_markdown(law):
# 
#     md = []
# 
#     md.append(f"# {law['name']}\n")
# 
#     for art in law["articles"]:
# 
#         md.append(f"## 제{art['number']}조 {art['title']}")
# 
#         content = art.get("content", "")
# 
#         # 🔥 핵심: list 방어
#         if isinstance(content, list):
#             content = "\n".join([str(c) for c in content if c])
# 
#         if content:
#             md.append(content)
# 
#         md.append("")
# 
#     return "\n".join(md)

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

    print("\n==============================")
    print("⚙️ Parser 실행")
    print("==============================")

    parser = LawParser()
    law = parser.parse(data)

    # 구조 확인
    # debug_print(law)
    import json
    print(json.dumps(law, ensure_ascii=False, indent=2))

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
# import json
# import sys
# from pprint import pprint
# import markdown
# from weasyprint import HTML

# from app.parsers.parser_factory import ParserFactory

# def md_to_pdf(md_text, output_pdf="output.pdf"):

#     html = markdown.markdown(md_text)

#     HTML(string=html).write_pdf(output_pdf)

#     print(f"[DEBUG] PDF 생성 완료: {output_pdf}")

# def md_to_html(md_text):
#     html = markdown.markdown(md_text)
#     return html

# def html_to_pdf(html_text, output_path):
#     HTML(string=html_text).write_pdf(output_path)

# def load_json(file_path):
#     try:
#         with open(file_path, "r", encoding="utf-8") as f:
#             return json.load(f)
#     except Exception as e:
#         print(f"[ERROR] JSON 로드 실패: {e}")
#         sys.exit(1)


# def print_structure(data, depth=0, max_depth=3):
#     """JSON 구조를 간단히 출력"""
#     if depth > max_depth:
#         return

#     if isinstance(data, dict):
#         for k, v in data.items():
#             print("  " * depth + f"- {k} ({type(v).__name__})")
#             print_structure(v, depth + 1, max_depth)

#     elif isinstance(data, list):
#         print("  " * depth + f"[list len={len(data)}]")
#         if len(data) > 0:
#             print_structure(data[0], depth + 1, max_depth)


# def detect_type(data):
#     """law vs admrul 자동 판별"""
#     if "법령" in data:
#         return "law"
#     elif "행정규칙" in data:
#         return "admrul"
#     else:
#         return "unknown"

# def generate_markdown(parsed):

#     md = []

#     # 제목
#     md.append(f"# {parsed['meta']['name']}\n")

#     # 조문
#     for art in parsed["articles"]:
#         content = art["content"]

#         if not content:
#             continue

#         md.append(content)
#         md.append("")

#     # 부칙
#     md.append("## 부칙\n")

#     for add in parsed["addenda"]:
#         md.append(add["content"])
#         md.append("")

#     return "\n".join(md)

# def to_markdown(law):

#     md = []
#     md.append(f"# {law.name}\n")

#     for art in law.articles:
#         md.append(f"## 제{art.number}조 {art.title}")

#         for p in art.paragraphs:

#             if p.content:
#                 md.append(p.content)

#             for item in p.items:
#                 md.append(f"{item.number} {item.content}")

#                 for sub in item.sub_items:
#                     md.append(f"  {sub.number} {sub.content}")

#         md.append("")

#     return "\n".join(md)

# def save_markdown(md_text, path="output.md"):
#     with open(path, "w", encoding="utf-8") as f:
#         f.write(md_text)

#     print(f"[DEBUG] Markdown 저장 완료: {path}")

# def main(file_path):
#     print("\n==============================")
#     print("📂 JSON 파일 로드")
#     print("==============================")

#     data = load_json(file_path)

#     print("\n==============================")
#     print("🔍 최상위 키")
#     print("==============================")
#     print(list(data.keys()))

#     print("\n==============================")
#     print("🧱 JSON 구조 (상위)")
#     print("==============================")
#     print_structure(data)

#     data_type = detect_type(data)
#     print("\n==============================")
#     print(f"📌 데이터 타입: {data_type}")
#     print("==============================")

#     if data_type == "unknown":
#         print("❌ law / admrul 구조 아님")
#         return

#     print("\n==============================")
#     print("⚙️ Parser 실행")
#     print("==============================")

#     try:
#         parser = ParserFactory.get_parser(data_type)
#         result = parser.parse(data)

#         # print("\n==============================")
#         # print("✅ 파싱 결과 샘플")
#         # print("==============================")

#         # if isinstance(result, list):
#         #     print(f"총 {len(result)} 건")
#         #     pprint(result[:3])  # 앞 3개만 출력
#         # else:
#         #     pprint(result)

#         # 3. Markdown 생성
#         md_text = generate_markdown(result)

#         # 🔥 3. 중간 저장
#         save_markdown(md_text, "output.md")

#         # 4. PDF 생성
#         md_to_pdf(md_text, "output.pdf")

#         # # 4. HTML 변환
#         # html = markdown.markdown(md_text)

#         # # 5. PDF 생성
#         # HTML(string=html).write_pdf("output.pdf")

#     except Exception as e:
#         print(f"\n❌ 파싱 중 오류 발생: {e}")


# if __name__ == "__main__":
#     if len(sys.argv) < 2:
#         print("사용법:")
#         print("python3 debug_parser.py <json파일경로>")
#         sys.exit(1)

#     file_path = sys.argv[1]
#     main(file_path)