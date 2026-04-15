# app/parsers/law_parser.py
import re

class LawParser:

    def parse(self, data):

        law_data = data.get("법령", {})
        info = law_data.get("기본정보", {})

        return {
            "name": info.get("법령명_한글"),
            "articles": self._parse_articles(law_data),
            "addenda": self._parse_addenda(law_data),     # 부칙
            "appendix": self._parse_appendix(law_data)    # 별표
        }
    # def parse(self, data):

    #     law_data = data.get("법령", {})
    #     info = law_data.get("기본정보", {})

    #     return {
    #         "meta": {
    #             "name": info.get("법령명_한글"),
    #         },
    #         "articles": self._parse_articles(law_data),
    #         "addenda": self._parse_addenda(law_data),
    #         "appendix": self._parse_appendix(law_data)
    #     }
    
    def _parse_articles(self, law_data):

        raw_articles = law_data.get("조문", {}).get("조문단위", [])

        if not isinstance(raw_articles, list):
            raw_articles = [raw_articles]

        results = []

        for art in raw_articles:

            article_text = []

            # 1️⃣ 조문내용
            content_raw = art.get("조문내용")
            if content_raw:
                flat = self._flatten(content_raw)
                structured = self._split_structure(flat)

                for typ, text in structured:
                    if typ == "chapter":
                        article_text.append(f"# {text}")
                    elif typ == "section":
                        article_text.append(f"## {text}")
                    elif typ == "subsection":
                        article_text.append(f"### {text}")
                    else:
                        article_text.append(self._to_str(text))
            # if art.get("조문내용"):
            #     article_text.append(self._to_str(art.get("조문내용")))

            # 2️⃣ 항 파싱
            paragraphs = art.get("항", [])
            if not isinstance(paragraphs, list):
                paragraphs = [paragraphs]

            for para in paragraphs:
                if not para:
                    continue

                # 2️⃣ 항
                if para.get("항내용"):
                    article_text.append(f"  {self._to_str(para.get('항내용'))}")

                # 3️⃣ 호 파싱
                items = para.get("호", [])
                if not isinstance(items, list):
                    items = [items]

                for item in items:
                    if not item:
                        continue

                    # 3️⃣ 호
                    if item.get("호내용"):
                        article_text.append(f"   {self._to_str(item.get('호내용'))}")

                    # 4️⃣ 목 파싱
                    sub_items = item.get("목", [])
                    if not isinstance(sub_items, list):
                        sub_items = [sub_items]

                    for sub in sub_items:
                        if not sub:
                            continue

                        # 4️⃣ 목
                        if sub.get("목내용"):
                            article_text.append(f"     {self._to_str(sub.get('목내용'))}")

            # 🔥 본문이 하나라도 있어야 추가
            if not article_text:
                continue

            results.append({
                "number": art.get("조문번호"),
                "title": art.get("조문제목"),
                "content": "\n".join(article_text)
            })

        return results
    
    def _parse_addenda(self, law_data):

        addenda = law_data.get("부칙")
        if not addenda:
            return None

        # 케이스 1: 문자열
        if isinstance(addenda, str):
            return addenda

        # 케이스 2: 부칙내용 직접
        if addenda.get("부칙내용"):
            return self._to_str(addenda.get("부칙내용"))

        # 케이스 3: 부칙단위
        units = addenda.get("부칙단위", [])

        if not isinstance(units, list):
            units = [units]

        texts = []
        for unit in units:
            if unit.get("부칙내용"):
                texts.append(self._to_str(unit.get("부칙내용")))

        return "\n".join(texts) if texts else None

    def _parse_appendix(self, law_data):

        appendix = law_data.get("별표")
        if not appendix:
            return []

        if isinstance(appendix, dict):
            appendix = appendix.get("별표단위", [])

        if not isinstance(appendix, list):
            appendix = [appendix]

        results = []

        for app in appendix:
            if not app:
                continue

            raw_content = app.get("별표내용")

            if self.is_table_content(raw_content):

                flat = []
                for item in raw_content:
                    if isinstance(item, list):
                        flat.extend(item)
                    else:
                        flat.append(item)

                # table_text = "\n".join(flat)
                table_html = self._parse_ascii_table_to_html(flat)

                results.append({
                    "title":  f"[별표 {format_appendix_no(app.get("별표번호"))}] {app.get("별표제목")}",
                    # "content": to_markdown_table_block(table_text)
                    "content": table_html
                })
                continue 

            # 🔥 핵심 변경
            parsed_content = self.normalize_appendix_lines(raw_content)

            results.append({
                "title": f"[별표 {format_appendix_no(app.get("별표번호"))}] {app.get("별표제목")}",
                "content": parsed_content
            })

        return results  

    def _to_str(self, value):
        if not value:
            return ""

        if isinstance(value, list):
            return "\n".join(self._to_str(v) for v in value)

        return str(value) 
    
    def _flatten(self, value):
        if isinstance(value, list):
            result = []
            for v in value:
                result.extend(self._flatten(v))
            return result
        return [value]
    
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

    def _merge_appendix_lines(self, content):
        if not content:
            return []

        # 문자열이면 리스트로 변환
        if isinstance(content, str):
            return [content.strip()]

        merged = []
        buffer = ""

        for line in content:
            line = str(line).strip()

            if not line:
                continue

            # 새로운 항목 시작 패턴
            if re.match(r'^(\d+\.|[가-힣]\.|[①-⑳])', line):
                if buffer:
                    merged.append(buffer.strip())
                buffer = line
            else:
                buffer += " " + line

        if buffer:
            merged.append(buffer.strip())

        return merged
    
    def normalize_appendix_lines(self, content):

        import re  # 🔥 여기로 이동

        if not content:
            return []

        # 1. flatten
        flat_lines = []
        for item in content:
            if isinstance(item, list):
                flat_lines.extend(item)
            else:
                flat_lines.append(item)

        result = []
        buffer = ""

        for line in flat_lines:
            line = str(line).rstrip()

            if not line.strip():
                if buffer:
                    result.append(buffer.strip())
                    buffer = ""
                continue

            # 항목 시작
            if re.match(r'^\s*(\d+\.|[가-힣]\.|[①-⑳])', line):
                if buffer:
                    result.append(buffer.strip())
                buffer = line.strip()
            else:
                # 🔥 핵심 수정 (공백 추가)
                buffer += " " + line.strip()

        if buffer:
            result.append(buffer.strip())

        # 후처리 (줄바꿈)
        result = [self._post_process_line(line) for line in result]

        return result
    
    def _post_process_line(self, text):

        import re

        # 1) 숫자 항목 줄바꿈 (앞에 공백 포함 대응)
        text = re.sub(r'\s*(\d+\))', r'\n\1', text)

        # 2) 가. 나. 다. 줄바꿈
        text = re.sub(r'\s*([가-힣]\.)', r'\n\1', text)

        # 3) ① ② ③ 줄바꿈
        text = re.sub(r'\s*([①-⑳])', r'\n\1', text)

        return text.strip()
    
    def is_table_content(self, content):
        text = "".join(str(content))

        return any(x in text for x in [
            "┏","┓","┗","┛",
            "┌","┐","└","┘",
            "┬","┴","┼","├","┤",
            "┃","│","─"
        ])

    def _parse_ascii_table_to_html(self, content):
        import re

        def is_new_row(text):
            if not text:
                return False
            return bool(re.match(r'^(\d+\.|[가-힣]\.|[①-⑳])', text.strip()))

        prefix_lines = []
        table_lines = []
        in_table = False

        # --------------------------
        # 1️⃣ 표 / 일반 텍스트 분리
        # --------------------------
        for line in content:
            line = str(line)

            if any(x in line for x in ["┏", "┌"]):
                in_table = True
                continue

            if not in_table:
                prefix_lines.append(line)
                continue

            if any(x in line for x in ["┗", "┘"]):
                break

            table_lines.append(line)

        # --------------------------
        # 2️⃣ row 수집
        # --------------------------
        rows = []

        for line in table_lines:
            if not (line.startswith("┃") or line.startswith("│")):
                continue

            row = line.strip().strip("┃").strip("│")
            cols = [c.strip() for c in row.split("│")]
            rows.append(cols)

        # --------------------------
        # 3️⃣ 헤더 / 바디 분리
        # --------------------------
        header = []
        body = []
        mode = "header"

        row_idx = 0

        for line in table_lines:

            if line.startswith("┠") or line.startswith("├"):
                mode = "body"
                continue

            if not (line.startswith("┃") or line.startswith("│")):
                continue

            # 👉 row는 따로 가져옴
            row = rows[row_idx]
            row_idx += 1

            if mode == "header":
                header.append(row)
            else:
                body.append(row)
        # for line, row in zip(table_lines, rows):

        #     if line.startswith("┠"):
        #         mode = "body"
        #         continue

        #     if not line.startswith("┃"):
        #         continue

        #     if mode == "header":
        #         header.append(row)
        #     else:
        #         body.append(row)

        # --------------------------
        # 4️⃣ 헤더 병합
        # --------------------------
        final_header = []
        if header:
            for i in range(len(header[0])):
                merged = " ".join(h[i] for h in header if h[i])
                final_header.append(merged.strip())

        # --------------------------
        # 5️⃣ 멀티라인 row 병합 🔥🔥🔥
        # --------------------------
        merged_rows = []

        for row in body:

            # 완전 빈 row 제거
            if all(not c.strip() for c in row):
                continue

            first = row[0].strip() if row else ""
            second = row[1].strip() if len(row) > 1 else ""
            third = row[2].strip() if len(row) > 2 else ""

            # 🔥 이어붙일 조건 (핵심!)
            is_continuation = (
                merged_rows and (
                    not is_new_row(first) or   # 번호 시작 아님
                    third == ""                # 금액 없음 → 이어지는 줄
                )
            )

            if is_continuation:
                prev = merged_rows[-1]

                for i in range(len(row)):
                    if row[i].strip():
                        prev[i] += " " + row[i].strip()
            else:
                merged_rows.append(row)

        # --------------------------
        # 6️⃣ HTML 생성
        # --------------------------
        html = []

        # 👉 표 제목 복원
        if prefix_lines:
            html.append("<div class='appendix-title'>")
            for line in prefix_lines:
                html.append(f"<p>{line}</p>")
            html.append("</div>")

        html.append("<table class='law-table'>")

        # header
        if final_header:
            html.append("<thead><tr>")
            for col in final_header:
                html.append(f"<th>{col}</th>")
            html.append("</tr></thead>")

        # body
        html.append("<tbody>")
        for row in merged_rows:
            html.append("<tr>")
            for col in row:
                html.append(f"<td>{col}</td>")
            html.append("</tr>")
        html.append("</tbody></table>")

        return "\n".join(html)
    
    def _to_html(self, rows):
        if not rows:
            return ""

        # 🔥 여기 추가 (가장 중요)
        max_cols = max(len(r) for r in rows)
        for r in rows:
            while len(r) < max_cols:
                r.append("")

        html = ["<table class='law-table'>"]

        # header
        header = rows[0]
        html.append("<thead><tr>")
        for col in header:
            html.append(f"<th>{col}</th>")
        html.append("</tr></thead>")

        # body
        html.append("<tbody>")
        for row in rows[1:]:
            html.append("<tr>")
            for col in row:
                html.append(f"<td>{col}</td>")
            html.append("</tr>")
        html.append("</tbody></table>")

        return "\n".join(html)
    # def _parse_ascii_table_to_html(self, content):
    #     parsed_rows = []

    #     for line in content:
    #         if "┃" not in line:
    #             continue

    #         row = line.strip().strip("┃")
    #         cols = [c.strip() for c in row.split("│")]

    #         if not parsed_rows:
    #             parsed_rows.append(cols)
    #             continue

    #         # 🔥 핵심: 컬럼 개수 같으면 이어붙이기
    #         if len(cols) == len(parsed_rows[-1]):
    #             for i in range(len(cols)):
    #                 if cols[i]:
    #                     parsed_rows[-1][i] += "<br>" + cols[i]
    #         else:
    #             parsed_rows.append(cols)

    #     # HTML 생성
    #     html = ["<table class='law-table'>"]

    #     # header
    #     html.append("<thead><tr>")
    #     for col in parsed_rows[0]:
    #         html.append(f"<th>{col}</th>")
    #     html.append("</tr></thead>")

    #     # body
    #     html.append("<tbody>")
    #     for row in parsed_rows[1:]:
    #         html.append("<tr>")
    #         for col in row:
    #             html.append(f"<td>{col}</td>")
    #         html.append("</tr>")
    #     html.append("</tbody></table>")

    #     return "\n".join(html)

def format_appendix_no(no):
    if not no:
        return ""

    return str(int(no))  # "0001" → "1"

def to_markdown_table_block(text):
    return f"\n\n<pre>\n{text}\n</pre>\n\n"

import re

def is_new_row(first_col):
    if not first_col:
        return False
    first_col = first_col.strip()

    # 가., 나., 다. 또는 숫자.
    return bool(re.match(r'^(\d+\.|[가-힣]\.|[①-⑳])', first_col))

def parse_table(lines):
    table = []
    header = []
    rows = []
    mode = "header"

    for line in lines:
        if line.startswith(("┠", "├")):
            mode = "body"
            continue

        if line.startswith(("┃", "│")):
            cols = [c.strip() for c in line.strip("┃").strip("│").split("│")]

            if mode == "header":
                header.append(cols)
            else:
                rows.append(cols)

    # 👉 헤더 병합 (2줄짜리 대응)
    final_header = []
    for col_idx in range(len(header[0])):
        merged = " ".join(
            header_row[col_idx] for header_row in header if header_row[col_idx]
        )
        final_header.append(merged.strip())

    return final_header, rows

def table_to_md(header, rows):
    md = []

    md.append("| " + " | ".join(header) + " |")
    md.append("| " + " | ".join(["---"] * len(header)) + " |")

    for row in rows:
        md.append("| " + " | ".join(row) + " |")

    return "\n".join(md)
