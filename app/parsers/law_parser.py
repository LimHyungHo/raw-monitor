# app/parsers/law_parser.py

class LawParser:

    def parse(self, data):

        law_data = data.get("법령", {})
        info = law_data.get("기본정보", {})

        return {
            "name": info.get("법령명_한글"),
            "articles": self._parse_articles(law_data)
        }

    def _parse_articles(self, law_data):

        raw_articles = law_data.get("조문", {}).get("조문단위", [])

        if not isinstance(raw_articles, list):
            raw_articles = [raw_articles]

        results = []

        for art in raw_articles:

            content = art.get("조문내용")

            if not content:
                continue

            results.append({
                "number": art.get("조문번호"),
                "title": art.get("조문제목"),
                "content": content
            })

        return results
# # app/parsers/law_parser.py

# from app.parsers.base_parser import BaseParser
# import re
# import ast


# class LawParser(BaseParser):

#     def parse(self, data):
#         law = data.get("법령", {})

#         return {
#             "meta": self._parse_meta(law),
#             "articles": self._parse_articles(law),
#             "addenda": self._parse_addenda(law)
#         }

#     # =========================
#     # META
#     # =========================
#     def _parse_meta(self, law):
#         info = law.get("기본정보", {})

#         return {
#             "law_id": info.get("법령ID"),
#             "name": info.get("법령명_한글"),
#             "department": info.get("소관부처", {}).get("content"),
#             "promulgation_date": self._format_date(info.get("공포일자")),
#             "effective_date": self._format_date(info.get("시행일자")),
#             "promulgation_no": info.get("공포번호")
#         }

#     # =========================
#     # 조문 파싱
#     # =========================
#     def _parse_articles(self, law):

#         articles_raw = law.get("조문", {}).get("조문단위", [])
#         articles = self._ensure_list(articles_raw)

#         results = []

#         for art in articles:
#             if not isinstance(art, dict):
#                 continue

#             content = self._extract_full_content(art)
#             content = self._normalize_content(content)

#             # 장/절 제거
#             if self._is_header(content):
#                 continue

#             # 실제 조문만
#             if not self._is_real_article(content):
#                 continue

#             results.append({
#                 "article_no": art.get("조문번호"),
#                 "title": art.get("조문제목"),
#                 "content": content
#             })

#         return results

#     # =========================
#     # 핵심: 조문 내용 + 가독성
#     # =========================
#     def _extract_full_content(self, art):

#         lines = []

#         # -------------------------
#         # 1️⃣ 조문내용
#         # -------------------------
#         content = art.get("조문내용")

#         if isinstance(content, str) and content.strip():

#             match = re.match(r"(제\d+조\([^)]+\))\s*(.*)", content)

#             if match:
#                 title = match.group(1)
#                 body = match.group(2)

#                 lines.append(title)
#                 lines.append(body.strip())
#                 lines.append("")
#             else:
#                 lines.append(content.strip())
#                 lines.append("")

#         elif isinstance(content, list):
#             content = self._flatten(content)
#             lines.extend([str(c).strip() for c in content if c])
#             lines.append("")

#         # -------------------------
#         # 2️⃣ 항 / 호 / 목
#         # -------------------------
#         para_obj = art.get("항")

#         if isinstance(para_obj, dict):

#             # 케이스1: 항단위 있음
#             if "항단위" in para_obj:
#                 paragraphs = self._ensure_list(para_obj.get("항단위"))

#             # 🔥 케이스2: 바로 호 시작
#             elif "호" in para_obj:
#                 paragraphs = [{
#                     "항번호": "",
#                     "항내용": "",
#                     "호": para_obj.get("호")
#                 }]
#             else:
#                 paragraphs = []

#         else:
#             paragraphs = []

#         for para in paragraphs:

#             para_no = para.get("항번호", "")
#             para_content = para.get("항내용", "")

#             if para_no or para_content:
#                 lines.append(f"{para_no} {para_content}".strip())

#             # 호
#             items = self._ensure_list(para.get("호"))

#             for item in items:

#                 item_no = item.get("호번호", "")
#                 item_content = item.get("호내용", "")

#                 item_content = self._clean_number_prefix(item_content, item_no)

#                 lines.append(f"{item_no} {item_content}".strip())

#                 # 목
#                 subs = self._ensure_list(item.get("목"))

#                 for sub in subs:

#                     sub_no = sub.get("목번호", "")
#                     sub_content = sub.get("목내용", "")

#                     sub_content = self._clean_number_prefix(sub_content, sub_no)

#                     lines.append(f"  {sub_no} {sub_content}".strip())

#             lines.append("")  # 줄바꿈

#         return "\n".join(lines).strip()

#     # =========================
#     # 부칙
#     # =========================
#     def _parse_addenda(self, law):

#         addenda_raw = law.get("부칙", {}).get("부칙단위", [])
#         addenda = self._ensure_list(addenda_raw)

#         results = []

#         for unit in addenda:

#             content = unit.get("부칙내용", [])
#             content = self._ensure_list(content)

#             # 🔥 flatten 적용
#             content = self._flatten(content)

#             text = "\n".join([str(c).strip() for c in content if c])

#             results.append({
#                 "type": "부칙",
#                 "content": text
#             })

#         return results

#     # =========================
#     # 유틸
#     # =========================
#     def _ensure_list(self, data):
#         if isinstance(data, list):
#             return data
#         elif data is None:
#             return []
#         else:
#             return [data]

#     def _flatten(self, data):
#         result = []

#         for item in data:
#             if isinstance(item, list):
#                 result.extend(self._flatten(item))
#             else:
#                 result.append(item)

#         return result

#     def _format_date(self, date_str):
#         if not date_str:
#             return None
#         if len(date_str) == 8:
#             return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
#         return date_str

#     # =========================
#     # 정제
#     # =========================
#     def _normalize_content(self, content):

#         if isinstance(content, str) and content.startswith("["):
#             try:
#                 parsed = ast.literal_eval(content)
#                 if isinstance(parsed, list):
#                     parsed = self._flatten(parsed)
#                     return "\n".join(parsed)
#             except:
#                 pass

#         return content

#     def _is_header(self, content):
#         if not content:
#             return False
#         return any(k in content for k in ["장", "절", "관"])

#     def _is_real_article(self, content):
#         if not content:
#             return False
#         return bool(re.match(r"제\d+조", content))

#     def _clean_number_prefix(self, text, number):

#         if not text:
#             return text

#         pattern = r"^\s*" + re.escape(number.strip()) + r"\s*"
#         return re.sub(pattern, "", text).strip()