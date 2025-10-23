# trusted_data_agent/agent/formatter.py
import re
import uuid
import json
from trusted_data_agent.agent.response_models import CanonicalResponse, KeyMetric, Observation, PromptReportResponse, Synthesis
# The erroneous line "from trusted_data_agent.agent.formatter import OutputFormatter" has been removed from here.

class OutputFormatter:
    """
    Parses structured response data to generate professional,
    failure-safe HTML for the UI.
    """
    def __init__(self, collected_data: list | dict, canonical_response: CanonicalResponse = None, prompt_report_response: PromptReportResponse = None, llm_response_text: str = None, original_user_input: str = None, active_prompt_name: str = None):
        self.collected_data = collected_data
        self.original_user_input = original_user_input
        self.active_prompt_name = active_prompt_name
        self.processed_data_indices = set()

        self.canonical_report = canonical_response
        self.prompt_report = prompt_report_response
        self.llm_response_text = llm_response_text

    def _render_key_metric(self, metric: KeyMetric) -> str:
        """Renders the KeyMetric object into an HTML card."""
        if not metric:
            return ""
        
        metric_value = str(metric.value)
        metric_label = metric.label
        is_numeric = re.fullmatch(r'[\d,.]+', metric_value) is not None
        value_class = "text-4xl" if is_numeric else "text-2xl"
        label_class = "text-base"
        return f"""
<div class="key-metric-card bg-gray-900/50 p-4 rounded-lg mb-4 text-center">
    <div class="{value_class} font-bold text-white">{metric_value}</div>
    <div class="{label_class} text-gray-400 mt-1">{metric_label}</div>
</div>
"""

    def _render_direct_answer(self, answer: str) -> str:
        """
        Renders the direct answer text as a paragraph, but only if no key
        metric is present, to avoid redundancy in the UI.
        """
        if self.canonical_report and self.canonical_report.key_metric:
            return ""
        if not answer:
            return ""
        return f'<p class="text-gray-300 mb-4">{self._process_inline_markdown(answer)}</p>'

    def _render_observations(self, observations: list[Observation]) -> str:
        """Renders a list of Observation objects into an HTML list."""
        if not observations:
            return ""
        
        html_parts = [
            '<h3 class="text-lg font-bold text-white mb-3 border-b border-gray-700 pb-2">Key Observations</h3>',
            '<ul class="list-disc list-outside space-y-2 text-gray-300 mb-4 pl-5">'
        ]
        for obs in observations:
            html_parts.append(f'<li>{self._process_inline_markdown(obs.text)}</li>')
        
        html_parts.append('</ul>')
        return "".join(html_parts)

    def _render_synthesis(self, synthesis_items: list[Synthesis]) -> str:
        """Renders a list of Synthesis objects into an HTML list."""
        if not synthesis_items:
            return ""
        
        html_parts = [
            '<h3 class="text-lg font-bold text-white mb-3 border-b border-gray-700 pb-2">Agent\'s Analysis</h3>',
            '<ul class="list-disc list-outside space-y-2 text-gray-300 mb-4 pl-5">'
        ]
        for item in synthesis_items:
            html_parts.append(f'<li>{self._process_inline_markdown(item.text)}</li>')
        
        html_parts.append('</ul>')
        return "".join(html_parts)

    def _process_inline_markdown(self, text_content: str) -> str:
        """Handles basic inline markdown like code backticks and bolding."""
        if not isinstance(text_content, str):
            return ""
        # Handle escaped underscores first if necessary
        text_content = text_content.replace(r'\_', '_')
        # Process code backticks
        text_content = re.sub(r'`(.*?)`', r'<code class="bg-gray-900/70 text-teradata-orange rounded-md px-1.5 py-0.5 font-mono text-sm">\1</code>', text_content)
        # Process bold markdown (ensure it doesn't interfere with other markdown like italics if added later)
        text_content = re.sub(r'(?<!\*)\*\*(?!\*)(.*?)(?<!\*)\*\*(?!\*)', r'<strong>\1</strong>', text_content)
        return text_content


    def _render_standard_markdown(self, text: str) -> str:
        """
        Renders a block of text by processing standard markdown elements,
        including special key-value formats, fenced code blocks (handling SQL DDL
        specifically), and tables.
        """
        if not isinstance(text, str):
            return ""

        lines = text.strip().split('\n')
        html_output = []
        list_level_stack = []
        in_code_block = False
        code_lang = ""
        code_content = []
        in_table = False
        table_headers = []
        table_rows = []

        def get_indent_level(line_text):
            return len(line_text) - len(line_text.lstrip(' '))

        def is_table_separator(line_text):
            return re.match(r'^\s*\|?\s*:?-+:?\s*\|?(\s*:?-+:?\s*\|?)*\s*$', line_text)

        def parse_table_row(line_text):
            # Remove leading/trailing pipes and whitespace, then split by pipe
            cells = [cell.strip() for cell in line_text.strip().strip('|').split('|')]
            return cells

        # --- MODIFICATION START: Pattern to check for DDL content ---
        ddl_pattern = re.compile(r'^\s*CREATE\s+(MULTISET\s+)?TABLE', re.IGNORECASE)
        # --- MODIFICATION END ---

        i = 0
        while i < len(lines):
            line = lines[i]

            # --- Table Detection and Processing ---
            if not in_code_block and '|' in line and i + 1 < len(lines) and is_table_separator(lines[i+1]):
                if not in_table: # Start of a new table
                    in_table = True
                    table_headers = parse_table_row(line)
                    table_rows = []
                    i += 2 # Skip header and separator line
                    continue

            if in_table:
                if '|' in line:
                    table_rows.append(parse_table_row(line))
                    i += 1
                    continue
                else: # End of table block
                    in_table = False
                    # Render the collected table
                    html_output.append("<div class='table-container mb-4'><table class='assistant-table'><thead><tr>")
                    html_output.extend(f'<th>{self._process_inline_markdown(h)}</th>' for h in table_headers)
                    html_output.append("</tr></thead><tbody>")
                    for row in table_rows:
                        html_output.append("<tr>")
                        for k in range(len(table_headers)):
                            cell_content = row[k] if k < len(row) else ""
                            html_output.append(f'<td>{self._process_inline_markdown(cell_content)}</td>')
                        html_output.append("</tr>")
                    html_output.append("</tbody></table></div>")


            # --- Code Block Processing (with DDL Handling) ---
            if line.strip().startswith('```'):
                if in_code_block:
                    # --- MODIFICATION START: Check for SQL DDL before rendering generic block ---
                    full_code_content = "".join(code_content)
                    is_sql_ddl = (code_lang == 'sql' and ddl_pattern.match(full_code_content))

                    if is_sql_ddl:
                        # Delegate rendering to _render_ddl
                        # Create the minimal structure _render_ddl expects
                        mock_tool_result = {
                            "results": [{'Request Text': full_code_content}],
                            "metadata": {} # Add empty metadata for safety
                        }
                        # Call _render_ddl (index doesn't matter here)
                        html_output.append(self._render_ddl(mock_tool_result, 0))
                    else:
                        # Render as a generic code block
                        sanitized_code = full_code_content.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                        html_output.append(f"""
<div class="sql-code-block mb-4">
    <div class="sql-header">
        <span>{code_lang.upper() if code_lang else 'Code'}</span>
        <button class="copy-button" onclick="copyToClipboard(this)">
             <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16"><path d="M4 1.5H3a2 2 0 0 0-2 2V14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V3.5a2 2 0 0 0-2-2h-1v1h1a1 1 0 0 1 1 1V14a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V3.5a1 1 0 0 1 1-1h1v-1z"/><path d="M9.5 1a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-.5-.5h-3a.5.5 0 0 1-.5-.5v-1a.5.5 0 0 1 .5-.5h3zM-1 7a.5.5 0 0 1 .5-.5h15a.5.5 0 0 1 0 1H-.5A.5.5 0 0 1-1 7z"/></svg> Copy
        </button>
    </div>
    <pre><code class="language-{code_lang}">{sanitized_code}</code></pre>
</div>""")
                    # --- MODIFICATION END ---
                    in_code_block = False
                    code_content = []
                    code_lang = ""
                else:
                    in_code_block = True
                    code_lang = line.strip()[3:].strip().lower()
                i += 1
                continue

            if in_code_block:
                code_content.append(line + '\n')
                i += 1
                continue

            # --- Standard Markdown Processing (Lists, Headings, Paragraphs) ---
            stripped_line = line.lstrip(' ')
            current_indent = get_indent_level(line)

            key_value_match = re.match(r'^\s*\*\*\*(.*?):\*\*\*\s*(.*)$', stripped_line)
            list_item_match = re.match(r'^([*-])\s+(.*)$', stripped_line)

            while list_level_stack and (not list_item_match or current_indent < list_level_stack[-1]):
                html_output.append('</ul>')
                list_level_stack.pop()

            if key_value_match:
                key = key_value_match.group(1).strip()
                value = key_value_match.group(2).strip()
                processed_value = self._process_inline_markdown(value)
                html_output.append(f"""
<div class="grid grid-cols-1 md:grid-cols-[1fr,3fr] gap-x-4 gap-y-1 py-2 border-b border-gray-800">
    <dt class="text-sm font-medium text-gray-400">{key}:</dt>
    <dd class="text-sm text-gray-200 mt-0">{processed_value}</dd>
</div>""")
            elif list_item_match:
                if not list_level_stack or current_indent > list_level_stack[-1]:
                    html_output.append('<ul class="list-disc list-outside space-y-2 text-gray-300 mb-4 pl-5">')
                    list_level_stack.append(current_indent)

                content = list_item_match.group(2).strip()
                nested_kv_match = re.match(r'^\s*\*\*\*(.*?):\*\*\*\s*(.*)$', content)

                if nested_kv_match:
                    key = nested_kv_match.group(1).strip()
                    value = nested_kv_match.group(2).strip()
                    processed_value = self._process_inline_markdown(value)
                    html_output.append(f"""
<li class="list-none -ml-5">
    <div class="grid grid-cols-1 md:grid-cols-[1fr,3fr] gap-x-4 gap-y-1 py-1">
        <dt class="text-sm font-medium text-gray-400">{key}:</dt>
        <dd class="text-sm text-gray-200 mt-0">{processed_value}</dd>
    </div>
</li>""")
                elif content:
                    html_output.append(f'<li>{self._process_inline_markdown(content)}</li>')
            else:
                heading_match = re.match(r'^(#{1,6})\s+(.*)$', stripped_line)
                hr_match = re.match(r'^-{3,}$', stripped_line)

                if heading_match:
                    level = len(heading_match.group(1))
                    content = self._process_inline_markdown(heading_match.group(2).strip())
                    if level == 1:
                        html_output.append(f'<h2 class="text-xl font-bold text-white mb-3 border-b border-gray-700 pb-2">{content}</h2>')
                    elif level == 2:
                        html_output.append(f'<h3 class="text-lg font-bold text-white mb-3 border-b border-gray-700 pb-2">{content}</h3>')
                    else:
                        html_output.append(f'<h4 class="text-base font-semibold text-white mt-4 mb-2">{content}</h4>')
                elif hr_match:
                    html_output.append('<hr class="border-gray-600 my-4">')
                elif stripped_line:
                    html_output.append(f'<p class="text-gray-300 mb-4">{self._process_inline_markdown(stripped_line)}</p>')

            i += 1

        # --- Cleanup after loop ---
        if in_table: # Render any pending table
            html_output.append("<div class='table-container mb-4'><table class='assistant-table'><thead><tr>")
            html_output.extend(f'<th>{self._process_inline_markdown(h)}</th>' for h in table_headers)
            html_output.append("</tr></thead><tbody>")
            for row in table_rows:
                html_output.append("<tr>")
                for k in range(len(table_headers)):
                    cell_content = row[k] if k < len(row) else ""
                    html_output.append(f'<td>{self._process_inline_markdown(cell_content)}</td>')
                html_output.append("</tr>")
            html_output.append("</tbody></table></div>")

        while list_level_stack: # Close any open lists
            html_output.append('</ul>')
            list_level_stack.pop()

        return "".join(html_output)

    
    def _render_json_synthesis(self, data: list) -> str:
        """
        Renders a list of JSON objects into a structured HTML format,
        intelligently detecting title and summary keys.
        """
        html_parts = ['<div class="space-y-4">']
        for item in data:
            if not isinstance(item, dict):
                continue

            title_keys = ['table_name', 'name', 'title', 'header']
            summary_keys = ['summary', 'description', 'text', 'content']
            
            title = next((item[key] for key in title_keys if key in item), None)
            summary = next((item[key] for key in summary_keys if key in item), None)

            html_parts.append('<div class="bg-gray-900/50 p-4 rounded-lg">')
            if title:
                html_parts.append(f'<h4 class="text-md font-semibold text-teradata-orange mb-2"><code>{title}</code></h4>')
            if summary:
                html_parts.append(f'<p class="text-gray-300 text-sm">{self._process_inline_markdown(summary)}</p>')
            html_parts.append('</div>')
            
        html_parts.append('</div>')
        return "".join(html_parts)

    def _render_synthesis_content(self, text_content: str) -> str:
        """
        Intelligently renders synthesis content. If the content is valid JSON,
        it's formatted as a structured list. Otherwise, it's treated as markdown.
        """
        if not isinstance(text_content, str):
            return ""
        
        try:
            match = re.search(r'\[.*\]|\{.*\}', text_content, re.DOTALL)
            if match:
                data = json.loads(match.group(0))
                if isinstance(data, list):
                    return self._render_json_synthesis(data)
        except json.JSONDecodeError:
            pass
        
        return self._render_standard_markdown(text_content)

    def _render_ddl(self, tool_result: dict, index: int) -> str:
        """
        Renders DDL statements found within a tool result. Handles cases
        where the 'results' list might contain multiple DDL statements.
        Now wrapped in response-card div.
        """
        if not isinstance(tool_result, dict) or "results" not in tool_result: return ""
        results = tool_result.get("results")
        if not isinstance(results, list) or not results: return ""

        html_parts = []
        ddl_key = 'Request Text' 

        for result_item in results:
            if not isinstance(result_item, dict) or ddl_key not in result_item:
                continue

            ddl_text = result_item.get(ddl_key, '')
            if not ddl_text:
                continue

            ddl_text_sanitized = ddl_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            
            metadata = tool_result.get("metadata", {})
            table_name = metadata.get("table")
            if not table_name:
                 name_match = re.search(r'TABLE\s+([\w."]+)', ddl_text, re.IGNORECASE)
                 table_name = name_match.group(1) if name_match else "DDL"
            
            # --- MODIFICATION START: Wrap each DDL block in response-card ---
            html_parts.append(f"""
<div class="response-card mb-4"> 
    <div class="sql-code-block">
        <div class="sql-header">
            <span>SQL DDL: {table_name}</span>
            <button class="copy-button" onclick="copyToClipboard(this)">
                 <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16"><path d="M4 1.5H3a2 2 0 0 0-2 2V14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V3.5a2 2 0 0 0-2-2h-1v1h1a1 1 0 0 1 1 1V14a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V3.5a1 1 0 0 1 1-1h1v-1z"/><path d="M9.5 1a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-.5-.5h-3a.5.5 0 0 1-.5-.5v-1a.5.5 0 0 1 .5-.5h3zM-1 7a.5.5 0 0 1 .5-.5h15a.5.5 0 0 1 0 1H-.5A.5.5 0 0 1-1 7z"/></svg> Copy
            </button>
        </div>
        <pre><code class="language-sql">{ddl_text_sanitized}</code></pre>
    </div>
</div>""")
            # --- MODIFICATION END ---

        self.processed_data_indices.add(index)
        return "".join(html_parts)

    def _render_table(self, tool_result: dict, index: int, default_title: str) -> str:
        # ... (rest of _render_table is unchanged) ...
        if not isinstance(tool_result, dict) or "results" not in tool_result: return ""
        results = tool_result.get("results")
        if not isinstance(results, list) or not results: return ""
        dict_results = [item for item in results if isinstance(item, dict)]
        if not dict_results: return ""
        
        metadata = tool_result.get("metadata", {})
        title = metadata.get("tool_name", default_title)
        
        is_single_text_response = (
            len(dict_results) == 1 and 
            "response" in dict_results[0] and 
            len(dict_results[0].keys()) == 1
        )

        if is_single_text_response:
            response_text = dict_results[0].get("response", "")
            self.processed_data_indices.add(index)
            return f"<div class='response-card'>{self._render_synthesis_content(response_text)}</div>"
        
        headers = dict_results[0].keys() 
        table_data_json = json.dumps(dict_results) 

        html = f"""
        <div class="response-card">
            <div class="flex justify-between items-center mb-2">
                <h4 class="text-lg font-semibold text-white">Data: Result for <code>{title}</code></h4>
                <button class="copy-button" onclick="copyTableToClipboard(this)" data-table='{table_data_json}'>
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16"><path d="M4 1.5H3a2 2 0 0 0-2 2V14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V3.5a2 2 0 0 0-2-2h-1v1h1a1 1 0 0 1 1 1V14a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V3.5a1 1 0 0 1 1-1h1v-1z"/><path d="M9.5 1a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-.5-.5h-3a.5.5 0 0 1-.5-.5v-1a.5.5 0 0 1 .5-.5h3zM-1 7a.5.5 0 0 1 .5-.5h15a.5.5 0 0 1 0 1H-.5A.5.5 0 0 1-1 7z"/></svg> Copy Table
                </button>
            </div>
            <div class='table-container'>
                <table class='assistant-table'>
                    <thead><tr>{''.join(f'<th>{h}</th>' for h in headers)}</tr></thead>
                    <tbody>
        """
        for row in dict_results: 
            html += "<tr>"
            for header in headers:
                cell_data = str(row.get(header, ''))
                sanitized_cell = cell_data.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                html += f"<td>{sanitized_cell}</td>"
            html += "</tr>"
        html += "</tbody></table></div></div>"
        self.processed_data_indices.add(index)
        return html
        
    def _render_chart_with_details(self, chart_data: dict, table_data: dict, chart_index: int, table_index: int) -> str:
        # ... (unchanged) ...
        chart_id = f"chart-render-target-{uuid.uuid4()}"
        chart_spec_json = json.dumps(chart_data.get("spec", {}))
        
        table_html = "" 
        results = table_data.get("results")
        if isinstance(results, list) and results and all(isinstance(item, dict) for item in results):
            headers = results[0].keys()
            table_data_json = json.dumps(results)
            
            table_html += f"""
            <div class="flex justify-between items-center mt-4 mb-2">
                <h5 class="text-md font-semibold text-white">Chart Data</h5>
                <button class="copy-button" onclick="copyTableToClipboard(this)" data-table='{table_data_json}'>
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16"><path d="M4 1.5H3a2 2 0 0 0-2 2V14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V3.5a2 2 0 0 0-2-2h-1v1h1a1 1 0 0 1 1 1V14a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V3.5a1 1 0 0 1 1-1h1v-1z"/><path d="M9.5 1a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-.5-.5h-3a.5.5 0 0 1-.5-.5v-1a.5.5 0 0 1 .5-.5h3zM-1 7a.5.5 0 0 1 .5-.5h15a.5.5 0 0 1 0 1H-.5A.5.5 0 0 1-1 7z"/></svg> Copy Table
                </button>
            </div>
            """
            
            table_html += "<div class='table-container'><table class='assistant-table'><thead><tr>"
            table_html += ''.join(f'<th>{h}</th>' for h in headers)
            table_html += "</tr></thead><tbody>"
            for row in results:
                table_html += "<tr>"
                for header in headers:
                    cell_data = str(row.get(header, ''))
                    sanitized_cell = cell_data.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                    table_html += f"<td>{sanitized_cell}</td>"
                table_html += "</tr>"
            table_html += "</tbody></table></div>"

        self.processed_data_indices.add(chart_index)
        self.processed_data_indices.add(table_index)

        return f"""
        <div class="response-card">
            <div id="{chart_id}" class="chart-render-target" data-spec='{chart_spec_json}'></div>
            <details class="mt-4">
                <summary class="text-sm font-semibold text-gray-400 cursor-pointer hover:text-white">Show Details</summary>
                {table_html}
            </details>
        </div>
        """

    def _format_workflow_report(self) -> tuple[str, dict]:
        # ... (unchanged) ...
        tts_payload = { "direct_answer": "", "key_observations": "", "synthesis": "" }
        if self.canonical_report:
            tts_payload = {
                "direct_answer": self.canonical_report.direct_answer,
                "key_observations": " ".join([obs.text for obs in self.canonical_report.key_observations]),
                "synthesis": " ".join([synth.text for synth in self.canonical_report.synthesis])
            }
        
        summary_html_parts = []
        if self.canonical_report:
            if self.canonical_report.key_metric:
                summary_html_parts.append(self._render_key_metric(self.canonical_report.key_metric))
            
            summary_html_parts.append(self._render_direct_answer(self.canonical_report.direct_answer))

            if self.canonical_report.synthesis:
                summary_html_parts.append(self._render_synthesis(self.canonical_report.synthesis))
            
            if self.canonical_report.key_observations:
                summary_html_parts.append(self._render_observations(self.canonical_report.key_observations))

        html = ""
        if summary_html_parts:
             html += f"<div class='response-card summary-card'>{''.join(summary_html_parts)}</div>"

        data_to_process = self.collected_data if isinstance(self.collected_data, dict) else {"Execution Report": self.collected_data}
        if not data_to_process:
            return html, tts_payload
        
        for context_key, all_items_for_context in data_to_process.items():
            synthesis_items = []
            collateral_items = []

            for item in all_items_for_context:
                tool_name = item.get("metadata", {}).get("tool_name") if isinstance(item, dict) else None
                if tool_name == 'TDA_LLMTask':
                    synthesis_items.append(item)
                else:
                    collateral_items.append(item)

            display_key = context_key.replace("Workflow: ", "").replace(">", "&gt;").replace("Plan Results: ", "")

            if synthesis_items:
                synthesis_html = ""
                for item in synthesis_items:
                    if isinstance(item, dict) and "results" in item and isinstance(item["results"], list) and item["results"]:
                        response_text = item["results"][0].get("response", "")
                        if response_text:
                            synthesis_html += f"<div class='response-card'>{self._render_synthesis_content(response_text)}</div>"
                
                if synthesis_html:
                    html += f"<details class='response-card bg-white/5 open:pb-4 mb-4 rounded-lg border border-white/10'><summary class='p-4 font-bold text-lg text-white cursor-pointer hover:bg-white/10 rounded-t-lg'>Synthesis Report for: <code>{display_key}</code></summary><div class='px-4'>{synthesis_html}</div></details>"

            if collateral_items:
                collateral_html = ""
                for i in range(len(collateral_items)):
                    if i in self.processed_data_indices:
                        continue
                        
                    item = collateral_items[i]
                    tool_name = item.get("metadata", {}).get("tool_name") if isinstance(item, dict) else None
                    
                    if isinstance(item, list) and item and isinstance(item[0], dict):
                        combined_results = []
                        metadata = {}
                        for sub_item in item:
                            if isinstance(sub_item, dict) and sub_item.get('status') == 'success':
                                if not metadata: metadata = sub_item.get("metadata", {})
                                combined_results.extend(sub_item.get("results", []))
                        
                        if combined_results:
                            table_to_render = {"results": combined_results, "metadata": metadata}
                            collateral_html += self._render_table(table_to_render, i, "Column Iteration Result")
                        elif any(isinstance(sub_item, dict) and (sub_item.get('status') == 'skipped' or sub_item.get('status') == 'error') for sub_item in item):
                            collateral_html += f"<div class='response-card'><p class='text-sm text-gray-400 italic'>No data results for '{display_key}' due to skipped or errored sub-steps.</p></div>"
                        self.processed_data_indices.add(i)
                        continue
                    elif isinstance(item, dict):
                        if item.get("type") == "business_description":
                            collateral_html += f"<div class='response-card'><h4 class='text-lg font-semibold text-white mb-2'>Business Description</h4><p class='text-gray-300'>{item.get('description')}</p></div>"
                            self.processed_data_indices.add(i)
                        elif tool_name == 'base_tableDDL':
                            collateral_html += self._render_ddl(item, i)
                        elif "results" in item:
                            collateral_html += self._render_table(item, i, f"Result for {tool_name}")
                        elif item.get("status") == "skipped":
                            collateral_html += f"<div class='response-card'><p class='text-sm text-gray-400 italic'>Skipped Step: <strong>{tool_name or 'N/A'}</strong>. Reason: {item.get('reason')}</p></div>"
                            self.processed_data_indices.add(i)
                        elif item.get("status") == "error":
                            collateral_html += f"<div class='response-card'><p class='text-sm text-red-400 italic'>Error in Step: <strong>{tool_name or 'N/A'}</strong>. Details: {item.get('error_message', item.get('data', ''))}</p></div>"
                            self.processed_data_indices.add(i)
                
                if collateral_html:
                    html += f"<details class='response-card bg-white/5 open:pb-4 mb-4 rounded-lg border border-white/10'><summary class='p-4 font-bold text-lg text-white cursor-pointer hover:bg-white/10 rounded-t-lg'>Collateral Report for: <code>{display_key}</code></summary><div class='px-4'>{collateral_html}</div></details>"
        return html, tts_payload

    def _format_standard_query_report(self) -> tuple[str, dict]:
        # ... (unchanged) ...
        summary_html_parts = []
        tts_payload = {"direct_answer": "", "key_observations": "", "synthesis": ""}

        if self.canonical_report:
            if self.canonical_report.key_metric:
                summary_html_parts.append(self._render_key_metric(self.canonical_report.key_metric))
            summary_html_parts.append(self._render_direct_answer(self.canonical_report.direct_answer))
            if self.canonical_report.synthesis:
                summary_html_parts.append(self._render_synthesis(self.canonical_report.synthesis))
            if self.canonical_report.key_observations:
                summary_html_parts.append(self._render_observations(self.canonical_report.key_observations))

            tts_payload = {
                "direct_answer": self.canonical_report.direct_answer,
                "key_observations": " ".join([obs.text for obs in self.canonical_report.key_observations]),
                "synthesis": " ".join([synth.text for synth in self.canonical_report.synthesis])
            }
        elif self.llm_response_text:
            summary_html_parts.append(self._render_standard_markdown(self.llm_response_text))
            tts_payload["direct_answer"] = self.llm_response_text
        
        summary_html = f'<div class="response-card summary-card">{"".join(summary_html_parts)}</div>' if summary_html_parts else ""

        data_source = []
        if isinstance(self.collected_data, dict):
            for item_list in self.collected_data.values():
                data_source.extend(item_list)
        elif isinstance(self.collected_data, list):
            data_source = self.collected_data
        
        if not data_source:
            return summary_html, tts_payload
        
        primary_chart_html = ""
        collateral_html_content = ""
        
        for i, tool_result in enumerate(data_source):
            if isinstance(tool_result, dict) and tool_result.get("type") == "chart":
                table_data_result = data_source[i-1] if i > 0 else None
                if table_data_result and isinstance(table_data_result, dict) and "results" in table_data_result:
                    primary_chart_html = self._render_chart_with_details(tool_result, table_data_result, i, i-1)
                else: 
                    chart_id = f"chart-render-target-{uuid.uuid4()}"
                    chart_spec_json = json.dumps(tool_result.get("spec", {}))
                    primary_chart_html = f'<div class="response-card"><div id="{chart_id}" class="chart-render-target" data-spec=\'{chart_spec_json}\'></div></div>'
                    self.processed_data_indices.add(i)
                break 

        for i in range(len(data_source)):
            if i in self.processed_data_indices: 
                continue
            
            tool_result = data_source[i] 
            if not isinstance(tool_result, dict):
                continue
            
            metadata = tool_result.get("metadata", {})
            tool_name = metadata.get("tool_name")

            if tool_name == 'base_tableDDL':
                collateral_html_content += self._render_ddl(tool_result, i)
            elif "results" in tool_result:
                collateral_html_content += self._render_table(tool_result, i, tool_name or "Result")

        final_html_parts = []
        final_html_parts.append(summary_html) 
        final_html_parts.append(primary_chart_html) 
        
        if collateral_html_content:
            display_key = self.active_prompt_name or "Ad-hoc Query"
            collateral_wrapper = (
                f"<details class='response-card bg-white/5 open:pb-4 mb-4 rounded-lg border border-white/10'>"
                f"<summary class='p-4 font-bold text-lg text-white cursor-pointer hover:bg-white/10 rounded-t-lg'>Collateral Report for: <code>{display_key}</code></summary>"
                f"<div class='px-4'>{collateral_html_content}</div>"
                f"</details>"
            )
            final_html_parts.append(collateral_wrapper)
            
        return "".join(final_html_parts), tts_payload


    def _format_complex_prompt_report(self) -> tuple[str, dict]:
        # ... (unchanged) ...
        report = self.prompt_report
        if not report:
            return "<p>Error: Report data is missing.</p>", {}

        tts_payload = {
            "direct_answer": f"Report: {report.title}. Summary: {report.executive_summary}",
            "key_observations": "" 
        }

        html_parts = [f"<div class='response-card summary-card'>"]
        html_parts.append(f'<h2 class="text-xl font-bold text-white mb-3 border-b border-gray-700 pb-2">{self._process_inline_markdown(report.title)}</h2>')
        html_parts.append('<h3 class="text-lg font-semibold text-white mb-2">Executive Summary</h3>')
        html_parts.append(f'<p class="text-gray-300 mb-4">{self._process_inline_markdown(report.executive_summary)}</p>')

        if report.report_sections:
            for section in report.report_sections:
                html_parts.append(f'<h3 class="text-lg font-semibold text-white mt-4 mb-2 border-t border-gray-700 pt-3">{self._process_inline_markdown(section.title)}</h3>')
                html_parts.append(self._render_standard_markdown(section.content))
        
        html_parts.append("</div>")

        data_source = []
        if isinstance(self.collected_data, dict):
            for item_list in self.collected_data.values():
                data_source.extend(item_list)
        elif isinstance(self.collected_data, list):
            data_source = self.collected_data
        
        synthesis_items = []
        collateral_items = []
        for item in data_source:
            tool_name = item.get("metadata", {}).get("tool_name") if isinstance(item, dict) else None
            if tool_name == 'TDA_LLMTask':
                synthesis_items.append(item)
            elif tool_name not in ["TDA_ComplexPromptReport", "TDA_FinalReport"]:
                 collateral_items.append(item)

        display_key = self.active_prompt_name or "Ad-hoc Query"

        if synthesis_items:
            synthesis_html_content = ""
            for item in synthesis_items:
                if isinstance(item, dict) and "results" in item and isinstance(item["results"], list) and item["results"]:
                    response_text = item["results"][0].get("response", "")
                    if response_text:
                        synthesis_html_content += f"<div class='response-card'>{self._render_synthesis_content(response_text)}</div>"
            
            if synthesis_html_content:
                html_parts.append(f"<details class='response-card bg-white/5 open:pb-4 mb-4 rounded-lg border border-white/10'><summary class='p-4 font-bold text-lg text-white cursor-pointer hover:bg-white/10 rounded-t-lg'>Synthesis Report for: <code>{display_key}</code></summary><div class='px-4'>{synthesis_html_content}</div></details>")

        if collateral_items:
            collateral_html_content = ""
            for i in range(len(collateral_items)):
                if i in self.processed_data_indices:
                    continue
                tool_result = collateral_items[i]
                metadata = tool_result.get("metadata", {})
                tool_name = metadata.get("tool_name")
                if tool_name == 'base_tableDDL':
                    collateral_html_content += self._render_ddl(tool_result, i)
                elif "results" in tool_result:
                    collateral_html_content += self._render_table(tool_result, i, tool_name or "Result")

            if collateral_html_content:
                html_parts.append(
                    f"<details class='response-card bg-white/5 open:pb-4 mb-4 rounded-lg border border-white/10'>"
                    f"<summary class='p-4 font-bold text-lg text-white cursor-pointer hover:bg-white/10 rounded-t-lg'>Collateral Report for: <code>{display_key}</code></summary>"
                    f"<div class='px-4'>{collateral_html_content}</div>"
                    f"</details>"
                )
        
        final_html = "".join(html_parts)
        return final_html, tts_payload

    def render(self) -> tuple[str, dict]:
        """
        Main rendering method. Routes to the appropriate formatting strategy.
        
        Returns:
            A tuple containing:
            - final_html (str): The complete HTML string for the UI.
            - tts_payload (dict): The structured payload for the TTS engine.
        """
        self.processed_data_indices = set()
        
        if isinstance(self.prompt_report, PromptReportResponse):
            final_html, tts_payload = self._format_complex_prompt_report()
        elif self.canonical_report or self.active_prompt_name:
            if self.active_prompt_name:
                 final_html, tts_payload = self._format_workflow_report()
            else: 
                 final_html, tts_payload = self._format_standard_query_report()
        elif self.llm_response_text:
            final_html, tts_payload = self._format_standard_query_report()
        else:
            final_html = "<div class='response-card summary-card'><p>The agent has completed its work.</p></div>"
            tts_payload = {"direct_answer": "The agent has completed its work.", "key_observations": "", "synthesis": ""}

        return final_html, tts_payload

