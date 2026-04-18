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

        # 조문 내용이 리스트로 분절되어 들어오므로 하나로 합친 후 정제하거나, 
        # 각 요소별로 정제 후 처리합니다.
        for text in contents:
            if not text:
                continue

            # 전처리: 특수 공백 제거 및 기본 정리
            text = text.replace('\xa0', ' ').strip()
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
                result["articles"].append({
                    "number": "",
                    "title": "",
                    "content": text
                })

        # 3️⃣ 별표(테이블 포함) 처리
        result["appendix"].append(self._parse_appendix(service))

        return result

    # ============================================
    # 🔥 핵심: 개정태그, 원문자, 호번호 통합 정제
    # ============================================
    def format_content(self, text):
        if not text:
            return text

        # 1. [해결] <개정 ...> 내부 줄바꿈 및 파편화된 공백 제거
        # 날짜 사이의 엔터나 중복 공백을 하나로 합칩니다.
        text = re.sub(
            r"<개정\s*([\d\.\s\n,]+)>",
            lambda m: "<개정 " + " ".join(m.group(1).split()) + ">",
            text
        )

        # 2. [해결] 단어 중간이 끊긴 줄바꿈 합치기 (본문 보존)
        # 한글/영문자/기호 바로 뒤에 오는 줄바꿈을 공백으로 바꿈 (단, 마침표 뒤는 제외하거나 신중히)
        text = re.sub(r"([가-힣\w,])\n(?![제\d])", r"\1 ", text)

        # 3. [해결] 원문자(①, ②) 및 목 번호(가., 나.) 줄바꿈
        # 문장 중간에 원문자가 나오면 새 줄로 내립니다.
        text = re.sub(r"(?<!\n)([①-⑳])", r"\n\1", text)
        # (1), (2) 형태의 소괄호 번호 줄바꿈
        text = re.sub(r"(?<!\n)(\(\d{1,2}\))", r"\n\1", text)
        
        # 4. [해결] 호 번호(1. 2.) 줄바꿈 (개정 날짜와 충돌 방지)
        # 앞이 숫자가 아니고, 뒤에 숫자가 오는 'N.' 패턴만 줄바꿈
        text = re.sub(r"(?<!\n)(?<!\d)(?<!\.\s)(\d{1,2}\.)\s", r"\n\1 ", text)

        # 5. [추가] 제X조(제목) 뒤 줄바꿈 강제
        text = re.sub(r"(제\s*\d+\s*조\([^)]+\))\s*", r"\1\n", text)

        # 6. 최종 공백 정리
        text = re.sub(r" +", " ", text) # 중복 스페이스 제거
        text = re.sub(r"\n{3,}", "\n\n", text) # 3번 이상의 줄바꿈은 2번으로 축소

        return text.strip()
    
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
                if not text: return False
                return bool(re.match(r'^(\d+\.|[가-힣]\.|[①-⑳])', text.strip()))

            prefix_lines = []
            table_lines = []
            in_table = False

            # 1️⃣ 표 / 일반 텍스트 분리
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

            # 2️⃣ 데이터 행(rows) 추출 및 열 개수 정규화
            raw_rows = []
            for line in table_lines:
                if not (line.startswith("┃") or line.startswith("│")):
                    continue
                # 양 끝 기호 제거 후 분할
                row_content = line.strip().strip("┃").strip("│")
                cols = [c.strip() for c in row_content.split("│")]
                raw_rows.append(cols)
            
            if not raw_rows: return ""

            # 🔥 [에러 해결 핵심] 모든 행의 열 개수를 최대 열 개수에 맞춤
            max_cols = max(len(r) for r in raw_rows)
            for r in raw_rows:
                while len(r) < max_cols:
                    r.append("")

            # 3️⃣ 헤더 / 바디 분리 (구분선 기준)
            header_rows = []
            body_rows = []
            mode = "header"
            
            row_idx = 0
            for line in table_lines:
                if any(x in line for x in ["┠", "├", "┯", "┰"]): # 구분선 만나면 바디 시작
                    mode = "body"
                    continue
                if not (line.startswith("┃") or line.startswith("│")):
                    continue
                
                if mode == "header":
                    header_rows.append(raw_rows[row_idx])
                else:
                    body_rows.append(raw_rows[row_idx])
                row_idx += 1

            # 4️⃣ 헤더 병합 (IndexError 방지 적용됨)
            final_header = []
            if header_rows:
                for i in range(max_cols):
                    # 각 행의 i번째 열을 합침 (값이 있을 때만)
                    merged_col = " ".join(h[i] for h in header_rows if i < len(h) and h[i])
                    final_header.append(merged_col.strip())

            # 5️⃣ 바디 멀티라인 병합 로직
            merged_body = []
            for row in body_rows:
                if all(not c.strip() for c in row): continue

                # 첫 번째 열의 텍스트로 시작 여부 판단
                first_col = row[0].strip()
                
                # 이어붙이기 조건: 이전 행이 있고, 현재 행이 새로운 번호로 시작하지 않을 때
                if merged_body and not is_new_row(first_col):
                    prev_row = merged_body[-1]
                    for i in range(len(row)):
                        if row[i].strip():
                            prev_row[i] += " " + row[i].strip()
                else:
                    merged_body.append(row)

            # 6️⃣ HTML 생성 (표 내부 텍스트도 format_content 적용)
            html = []
            if prefix_lines:
                html.append("<div class='appendix-prefix'>")
                for p in prefix_lines:
                    html.append(f"<p>{self.format_content(p)}</p>")
                html.append("</div>")

            html.append("<table class='law-table' border='1'>")
            if final_header:
                html.append("<thead><tr>")
                for col in final_header:
                    html.append(f"<th>{self.format_content(col)}</th>")
                html.append("</tr></thead>")

            html.append("<tbody>")
            for row in merged_body:
                html.append("<tr>")
                for col in row:
                    # 표 안의 텍스트도 개정 태그/원문자 정제 적용
                    html.append(f"<td>{self.format_content(col)}</td>")
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
    
def format_appendix_no(no):
    if not no:
        return ""

    return str(int(no))  # "0001" → "1"