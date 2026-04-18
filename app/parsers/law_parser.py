# app/parsers/law_parser.py
import html
import re

class LawParser:
    ITEM_START_RE = re.compile(r"^\s*(\d+\.|[가-힣]\.|[①-⑳⑴-⒇])")
    TOP_LEVEL_ITEM_RE = re.compile(r"^\s*\d+\.")
    LEGAL_TERM_REPLACEMENTS = (
        ("정보 보호", "정보보호"),
        ("정보 기술", "정보기술"),
        ("전자 금융", "전자금융"),
        ("금융 위원회", "금융위원회"),
        ("최고 책임자", "최고책임자"),
        ("취약 점", "취약점"),
        ("분석 ㆍ평가", "분석ㆍ평가"),
        ("소액후 불", "소액후불"),
        ("후 불", "후불"),
        ("연체 정보", "연체정보"),
        ("총제공 한도", "총제공한도"),
        ("업무 정지", "업무정지"),
        ("과징 금", "과징금"),
        ("과태 료", "과태료"),
        ("정보 처리", "정보처리"),
        ("처리 방법", "처리방법"),
        ("세부 기준", "세부기준"),
        ("이용 한도", "이용한도"),
    )

    def _to_html_text(self, value):
        if value is None:
            return ""
        return html.escape(str(value), quote=False).replace("\n", "<br>")

    def _get_column_widths(self, max_cols):
        if max_cols == 2:
            return ["28%", "72%"]
        if max_cols == 3:
            return ["18%", "22%", "60%"]
        if max_cols == 4:
            return ["40%", "20%", "20%", "20%"]
        if max_cols == 5:
            return ["22%", "22%", "18%", "18%", "20%"]
        if max_cols == 6:
            return ["18%", "17%", "16%", "16%", "17%", "16%"]
        if max_cols == 7:
            return ["16%", "16%", "13%", "15%", "13%", "15%", "12%"]
        return None

    def _append_continuation(self, original, addition, use_newline=False):
        if not original:
            return addition
        separator = "\n" if use_newline else " "
        return f"{original}{separator}{addition}".strip()

    def _normalize_table_cell_text(self, text):
        if not text:
            return ""

        text = self._normalize_legal_text(text)

        # ASCII 표 줄바꿈으로 생긴 법령 표기 분절 복원
        text = re.sub(r"제\s+(\d+[조항호목])", r"제\1", text)
        text = re.sub(r"(\d+)\s+([조항호목])", r"\1\2", text)
        text = re.sub(r"([제법영])\s+(\d)", r"\1\2", text)

        # 자주 깨지는 조사/접속부 복원
        replacements = {
            "다 만": "다만",
            "제 외": "제외",
            "경 우": "경우",
            "한 다": "한다",
            "한 때": "한 때",
            "위 반": "위반",
            "업 무": "업무",
            "금 융": "금융",
            "전 자": "전자",
            "자 금": "자금",
            "거 래": "거래",
            "정 보": "정보",
            "위 원회": "위원회",
        }
        for src, dst in replacements.items():
            text = text.replace(src, dst)

        # 한 글자만 남고 다음 줄이 이어진 형태를 제한적으로 복원
        text = re.sub(r"\b(전)\s+(자금융)\b", r"\1\2", text)
        text = re.sub(r"\b(자)\s+(금융)\b", r"\1\2", text)
        text = re.sub(r"\b(금융)\s+(위원회)\b", r"\1\2", text)
        text = re.sub(r"\b(제외한)\s+(다\.)", r"\1\2", text)
        text = re.sub(r"\b(제공)\s+(또는)\b", r"\1 또는", text)
        text = re.sub(r"\b(누설)\s+(하거나)\b", r"\1하거나", text)

        text = re.sub(r" {2,}", " ", text)
        return text.strip()

    def _normalize_legal_text(self, text):
        if not text:
            return ""

        text = str(text).strip()

        # 일반 별표 본문의 기계적 줄바꿈은 접고, 하위 항목 시작은 유지
        text = re.sub(r"\n(?!\s*(\d+\)|[가-힣]\.|[①-⑳⑴-⒇]|비고))", " ", text)

        for src, dst in self.LEGAL_TERM_REPLACEMENTS:
            text = text.replace(src, dst)

        text = re.sub(r"([가-힣]{1,6})\s+다\.", r"\1다.", text)
        text = re.sub(r"\b다\s+음\b", "다음", text)
        text = re.sub(r"\b말\s+한다\.", "말한다.", text)
        text = re.sub(r"\b가진\s+다\.", "가진다.", text)
        text = re.sub(r"\b정하\s+여\b", "정하여", text)
        text = re.sub(r"\b학력\s+을\b", "학력을", text)
        text = re.sub(r"\b경력\s+이\b", "경력이", text)
        text = re.sub(r"\b학교\s+에서\b", "학교에서", text)
        text = re.sub(r"\b이\s+호\b", "이 호", text)
        text = re.sub(r"\b각\s+목\b", "각 목", text)
        text = re.sub(r"\b그\s+밖\b", "그 밖", text)
        text = re.sub(r" {2,}", " ", text)

        return text.strip()

    def _merge_appendix_fragments(self, lines):
        merged = []

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue

            if merged and re.match(r"^(다\.|을 말한다\.|를 말한다\.|한다\.|된다\.)$", stripped):
                merged[-1] = self._normalize_legal_text(f"{merged[-1]} {stripped}")
                continue

            merged.append(stripped)

        return merged

    def _is_cell_fragment_row(self, row):
        if not row:
            return False
        first_col = row[0].strip()
        if not re.match(r"^[가-힣]\.$", first_col):
            return False
        return all(not col.strip() for col in row[1:])

    def _is_multi_panel_form(self, content):
        for line in content or []:
            text = str(line)
            if text.count("┏") >= 2 and text.count("┓") >= 2:
                return True
        return False

    def _render_multi_panel_form(self, content):
        flat = []
        for item in content:
            if isinstance(item, list):
                flat.extend(item)
            else:
                flat.append(item)

        box_start = next(
            (idx for idx, line in enumerate(flat) if "┏" in str(line) or "┌" in str(line)),
            None,
        )
        if box_start is None:
            return ""

        prefix_lines = [str(line).strip() for line in flat[:box_start] if str(line).strip()]
        box_lines = [str(line).rstrip() for line in flat[box_start:]]

        first_box_line = box_lines[0]
        panel_count = len(re.split(r"(?<=[┓┨┛┃])(?=[┏┠┗┃])", first_box_line))
        if panel_count < 2:
            return ""

        panels = [[] for _ in range(panel_count)]

        for line in box_lines:
            parts = re.split(r"(?<=[┓┨┛┃])(?=[┏┠┗┃])", line)
            if len(parts) < panel_count:
                parts.extend([""] * (panel_count - len(parts)))
            for idx in range(panel_count):
                panels[idx].append(parts[idx].rstrip())

        html_blocks = ["<div class='ascii-form-panels'>"]
        if prefix_lines:
            html_blocks.append("<div class='appendix-prefix' style='flex-basis: 100%;'>")
            for line in prefix_lines:
                html_blocks.append(f"<p>{self._to_html_text(line)}</p>")
            html_blocks.append("</div>")
        for panel in panels:
            panel_text = "\n".join(panel).rstrip()
            html_blocks.append("<div class='ascii-form-panel'>")
            html_blocks.append(f"<pre>{self._to_html_text(panel_text)}</pre>")
            html_blocks.append("</div>")
        html_blocks.append("</div>")
        return "\n".join(html_blocks)

    def parse(self, data):

        law_data = data.get("법령", {})
        info = law_data.get("기본정보", {})

        return {
            "name": info.get("법령명_한글"),
            "articles": self._parse_articles(law_data),
            "addenda": self._parse_addenda(law_data),     # 부칙
            "appendix": self._parse_appendix(law_data)    # 별표
        }
    
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

            if self._is_multi_panel_form(raw_content):
                results.append({
                    "title": f"[별표 {format_appendix_no(app.get('별표번호'))}] {app.get('별표제목')}",
                    "content": self._render_multi_panel_form(raw_content)
                })
                continue

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

        if isinstance(content, str):
            content = [content]

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
            if self.ITEM_START_RE.match(line):
                if buffer:
                    result.append(buffer.strip())
                buffer = line.strip()
            else:
                join_with_newline = bool(self.TOP_LEVEL_ITEM_RE.match(buffer))
                buffer = self._append_continuation(
                    buffer.strip(),
                    line.strip(),
                    use_newline=join_with_newline,
                )

        if buffer:
            result.append(buffer.strip())

        # 후처리 (줄바꿈)
        result = [self._normalize_legal_text(self._post_process_line(line)) for line in result]
        result = self._merge_appendix_fragments(result)

        return result
    
    def _post_process_line(self, text):

        import re

        # 1) 숫자 항목 줄바꿈 (앞에 공백 포함 대응)
        text = re.sub(r'(?<=\s)(\d+\))', r'\n\1', text)

        # 2) 가. 나. 다. 줄바꿈
        text = re.sub(r'(?<=\s)([가-힣]\.)', r'\n\1', text)

        # 3) ① ② ③ 줄바꿈
        text = re.sub(r'(?<=[\)\]:])\s+([①-⑳⑴-⒇])', r'\n\1', text)

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
                if not text: return False
                return bool(re.match(r'^(\d+\.|[가-힣]\.|[①-⑳⑴-⒇])', text.strip()))

            prefix_lines = []
            table_lines = []
            in_table = False

            # 1️⃣ 표 영역 분리
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

            # 2️⃣ 데이터 행 추출 및 열 개수 정규화 (IndexError 방지 핵심)
            raw_rows = []
            for line in table_lines:
                if not (line.startswith("┃") or line.startswith("│")):
                    continue
                row_content = line.strip().strip("┃").strip("│")
                cols = [c.strip() for c in row_content.split("│")]
                raw_rows.append(cols)
            
            if not raw_rows: return ""

            # 🔥 모든 행의 열 길이를 최대 길이에 맞춰 맞춤 (IndexError 방지)
            max_cols = max(len(r) for r in raw_rows)
            for r in raw_rows:
                while len(r) < max_cols:
                    r.append("")

            # 3️⃣ 헤더 / 바디 분리
            header_rows = []
            body_rows = []
            mode = "header"
            row_idx = 0
            
            for line in table_lines:
                if any(x in line for x in ["┠", "├", "┯", "┰"]):
                    mode = "body"
                    continue
                if not (line.startswith("┃") or line.startswith("│")):
                    continue
                
                if mode == "header":
                    header_rows.append(raw_rows[row_idx])
                else:
                    body_rows.append(raw_rows[row_idx])
                row_idx += 1

            # 4️⃣ 헤더 병합
            final_header = []
            if header_rows:
                for i in range(max_cols):
                    # i번째 열이 존재할 때만 병합 (이미 위에서 정규화해서 안전함)
                    merged = " ".join(h[i] for h in header_rows if i < len(h) and h[i])
                    final_header.append(merged.strip())

            # 5️⃣ 멀티라인 행 병합 (이어붙이기)
            merged_body = []
            for row in body_rows:
                if all(not c.strip() for c in row): continue

                first_col = row[0].strip()
                # 이어붙이기 조건: 이전 행이 있고, 현재 행이 새로운 번호로 시작하지 않을 때
                if merged_body and (self._is_cell_fragment_row(row) or not is_new_row(first_col)):
                    prev_row = merged_body[-1]
                    for i in range(len(row)):
                        if row[i].strip():
                            prev_row[i] = self._append_continuation(
                                prev_row[i].strip(),
                                row[i].strip(),
                                use_newline=(i != 0),
                            )
                else:
                    merged_body.append(row)

            for row in merged_body:
                for i, col in enumerate(row):
                    row[i] = self._normalize_table_cell_text(col)

            # 6️⃣ HTML 생성
            html = []
            if prefix_lines:
                html.append("<div class='appendix-prefix'>")
                for p in prefix_lines:
                    html.append(f"<p>{self._to_html_text(p)}</p>")
                html.append("</div>")

            table_class = "law-table"
            if max_cols >= 5:
                table_class += " compact-table"
            html.append(f"<table class='{table_class}' border='1'>")
            widths = self._get_column_widths(max_cols)
            if widths:
                html.append("<colgroup>")
                for width in widths:
                    html.append(f"<col style='width: {width};'>")
                html.append("</colgroup>")
            if final_header:
                html.append("<thead><tr>")
                for col in final_header:
                    html.append(f"<th>{self._to_html_text(col)}</th>")
                html.append("</tr></thead>")

            html.append("<tbody>")
            for row in merged_body:
                html.append("<tr>")
                for col in row:
                    html.append(f"<td>{self._to_html_text(col)}</td>")
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
            html.append(f"<th>{self._to_html_text(col)}</th>")
        html.append("</tr></thead>")

        # body
        html.append("<tbody>")
        for row in rows[1:]:
            html.append("<tr>")
            for col in row:
                html.append(f"<td>{self._to_html_text(col)}</td>")
            html.append("</tr>")
        html.append("</tbody></table>")

        return "\n".join(html)

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
    return bool(re.match(r'^(\d+\.|[가-힣]\.|[①-⑳⑴-⒇])', first_col))

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
