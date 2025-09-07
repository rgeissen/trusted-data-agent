# trusted_data_agent/agent/formatter.py
import re
import uuid
import json
from trusted_data_agent.agent.response_models import CanonicalResponse, KeyMetric, Observation

class OutputFormatter:
    """
    Parses structured response data to generate professional,
    failure-safe HTML for the UI.
    """
    def __init__(self, collected_data: list | dict, canonical_response: CanonicalResponse = None, llm_response_text: str = None, original_user_input: str = None, active_prompt_name: str = None):
        self.collected_data = collected_data
        self.original_user_input = original_user_input
        self.active_prompt_name = active_prompt_name
        self.processed_data_indices = set()

        if canonical_response:
            self.response = canonical_response
        elif llm_response_text:
            self.response = CanonicalResponse(direct_answer=llm_response_text)
        else:
            self.response = CanonicalResponse(direct_answer="The agent has completed its work.")

    def _has_renderable_tables(self) -> bool:
        """Checks if there is any data that will be rendered as a table."""
        data_source = []
        if isinstance(self.collected_data, dict):
            for item_list in self.collected_data.values():
                data_source.extend(item_list)
        else:
            data_source = self.collected_data

        for item in data_source:
            if isinstance(item, dict) and "results" in item:
                results = item.get("results")
                if isinstance(results, list) and results and all(isinstance(row, dict) for row in results):
                    return True
        return False

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
        # --- MODIFICATION START: Suppress direct answer if a key metric is displayed ---
        if self.response and self.response.key_metric:
            return ""
        # --- MODIFICATION END ---
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

    def _process_inline_markdown(self, text_content: str) -> str:
        """Handles basic inline markdown like code backticks and bolding."""
        text_content = text_content.replace(r'\_', '_')
        text_content = re.sub(r'`(.*?)`', r'<code class="bg-gray-900/70 text-teradata-orange rounded-md px-1.5 py-0.5 font-mono text-sm">\1</code>', text_content)
        text_content = re.sub(r'(?<!\*)\*\*(?!\*)(.*?)(?<!\*)\*\*(?!\*)', r'<strong>\1</strong>', text_content)
        return text_content


    def _render_standard_markdown(self, text: str) -> str:
        """
        Renders a block of text by processing standard markdown elements,
        including special key-value formats.
        """
        lines = text.strip().split('\n')
        html_output = []
        list_level_stack = []

        def get_indent_level(line_text):
            return len(line_text) - len(line_text.lstrip(' '))

        for line in lines:
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
</div>
""")
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
</li>
""")
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

        while list_level_stack:
            html_output.append('</ul>')
            list_level_stack.pop()

        return "".join(html_output)
    
    def _render_ddl(self, tool_result: dict, index: int) -> str:
        if not isinstance(tool_result, dict) or "results" not in tool_result: return ""
        results = tool_result.get("results")
        if not isinstance(results, list) or not results: return ""
        ddl_text = results[0].get('Request Text', 'DDL not available.')
        ddl_text_sanitized = ddl_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        metadata = tool_result.get("metadata", {})
        table_name = metadata.get("table", "DDL")
        self.processed_data_indices.add(index)
        return f"""
        <div class="response-card">
            <div class="sql-code-block">
                <div class="sql-header">
                    <span>SQL DDL: {table_name}</span>
                    <button class="copy-button" onclick="copyToClipboard(this)">
                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16"><path d="M4 1.5H3a2 2 0 0 0-2 2V14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V3.5a2 2 0 0 0-2-2h-1v1h1a1 1 0 0 1 1 1V14a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V3.5a1 1 0 0 1 1-1h1v-1z"/><path d="M9.5 1a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-.5-.5h-3a.5.5 0 0 1-.5-.5v-1a.5.5 0 0 1 .5-.5h3zM-1 7a.5.5 0 0 1 .5-.5h15a.5.5 0 0 1 0 1H-.5A.5.5 0 0 1-1 7z"/></svg>
                        Copy
                    </button>
                </div>
                <pre><code class="language-sql">{ddl_text_sanitized}</code></pre>
            </div>
        </div>
        """

    def _render_table(self, tool_result: dict, index: int, default_title: str) -> str:
        if not isinstance(tool_result, dict) or "results" not in tool_result: return ""
        results = tool_result.get("results")
        if not isinstance(results, list) or not results or not all(isinstance(item, dict) for item in results): return ""
        
        metadata = tool_result.get("metadata", {})
        title = metadata.get("tool_name", default_title)
        
        if "response" in results[0] and title == default_title:
            first_line_match = re.match(r'#\s*(.*?)(?:\n|$)', results[0]["response"])
            if first_line_match:
                title = first_line_match.group(1).strip()
            else:
                title = "LLM Generated Content"

        headers = results[0].keys()
        
        table_data_json = json.dumps(results)

        html = f"""
        <div class="response-card">
            <div class="flex justify-between items-center mb-2">
                <h4 class="text-lg font-semibold text-white">Data: Result for <code>{title}</code></h4>
                <button class="copy-button" onclick="copyTableToClipboard(this)" data-table='{table_data_json}'>
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16"><path d="M4 1.5H3a2 2 0 0 0-2 2V14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V3.5a2 2 0 0 0-2-2h-1v1h1a1 1 0 0 1 1 1V14a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V3.5a1 1 0 0 1 1-1h1v-1z"/><path d="M9.5 1a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-.5-.5h-3a.5.5 0 0 1-.5-.5v-1a.5.5 0 0 1 .5-.5h3zM-1 7a.5.5 0 0 1 .5-.5h15a.5.5 0 0 1 0 1H-.5A.5.5 0 0 1-1 7z"/></svg>
                        Copy Table
                    </button>
                </div>
            <div class='table-container'>
                <table class='assistant-table'>
                    <thead><tr>{''.join(f'<th>{h}</th>' for h in headers)}</tr></thead>
                    <tbody>
        """
        for row in results:
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
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16"><path d="M4 1.5H3a2 2 0 0 0-2 2V14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V3.5a2 2 0 0 0-2-2h-1v1h1a1 1 0 0 1 1 1V14a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V3.5a1 1 0 0 1 1-1h1v-1z"/><path d="M9.5 1a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-.5-.5h-3a.5.5 0 0 1-.5-.5v-1a.5.5 0 0 1 .5-.5h3zM-1 7a.5.5 0 0 1 .5-.5h15a.5.5 0 0 1 0 1H-.5A.5.5 0 0 1-1 7z"/></svg>
                    Copy Table
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
                    table_html += f"<td>{sanitized_cell}</td>" # Corrected variable name
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
        """
        A specialized formatter for multi-step workflows that uses the CanonicalResponse model.
        """
        tts_payload = {
            "direct_answer": self.response.direct_answer,
            "key_observations": " ".join([obs.text for obs in self.response.key_observations])
        }
        
        summary_html_parts = []
        if self.response.key_metric:
            summary_html_parts.append(self._render_key_metric(self.response.key_metric))
        
        summary_html_parts.append(self._render_direct_answer(self.response.direct_answer))
        
        if self.response.key_observations:
            summary_html_parts.append(self._render_observations(self.response.key_observations))

        html = ""
        if summary_html_parts:
             html += f"<div class='response-card summary-card'>{''.join(summary_html_parts)}</div>"

        data_to_process = self.collected_data if isinstance(self.collected_data, dict) else {"Execution Report": self.collected_data}
        if not data_to_process:
            return html, tts_payload
        
        all_data_items = []
        for item_list in data_to_process.values():
            all_data_items.extend(item_list)
        
        is_simple_report = False
        successful_results = [item for item in all_data_items if isinstance(item, dict) and item.get("status") == "success"]
        if len(successful_results) == 1 and successful_results[0].get("metadata", {}).get("tool_name") == "CoreLLMTask":
             is_simple_report = True
             if not self.response.direct_answer.strip() and not self.response.key_observations:
                 core_llm_response_text = successful_results[0].get("results", [{}])[0].get("response", "")
                 html = f"<div class='response-card summary-card'>{self._render_standard_markdown(core_llm_response_text)}</div>"


        for context_key, data_items in data_to_process.items():
            if is_simple_report:
                 continue

            display_key = context_key.replace("Workflow: ", "").replace(">", "&gt;").replace("Plan Results: ", "")
            html += f"<details class='response-card bg-white/5 open:pb-4 mb-4 rounded-lg border border-white/10'><summary class='p-4 font-bold text-lg text-white cursor-pointer hover:bg-white/10 rounded-t-lg'>Report for: code>{display_key}</code></summary><div class='px-4'>"
            
            for i, item in enumerate(data_items):
                tool_name = item.get("metadata", {}).get("tool_name") if isinstance(item, dict) else None
                if tool_name == 'CoreLLMTask':
                    continue
                
                if isinstance(item, list) and item and isinstance(item[0], dict):
                    combined_results = []
                    metadata = {}
                    for sub_item in item:
                        if isinstance(sub_item, dict) and sub_item.get('status') == 'success':
                            if not metadata: metadata = sub_item.get("metadata", {})
                            combined_results.extend(sub_item.get("results", []))
                    
                    if combined_results:
                        table_to_render = {"results": combined_results, "metadata": metadata}
                        html += self._render_table(table_to_render, i, "Column Iteration Result")
                    elif any(isinstance(sub_item, dict) and (sub_item.get('status') == 'skipped' or sub_item.get('status') == 'error') for sub_item in item):
                        html += f"<div class='response-card'><p class='text-sm text-gray-400 italic'>No data results for '{display_key}' due to skipped or errored sub-steps.</p></div>"
                    continue
                elif isinstance(item, dict):
                    if item.get("type") == "business_description":
                        html += f"<div class='response-card'><h4 class='text-lg font-semibold text-white mb-2'>Business Description</h4><p class='text-gray-300'>{item.get('description')}</p></div>"
                    elif tool_name == 'base_tableDDL':
                        html += self._render_ddl(item, i)
                    elif "results" in item:
                        html += self._render_table(item, i, f"Result for {tool_name}")
                    elif item.get("status") == "skipped":
                        html += f"<div class='response-card'><p class='text-sm text-gray-400 italic'>Skipped Step: <strong>{tool_name or 'N/A'}</strong>. Reason: {item.get('reason')}</p></div>"
                    elif item.get("status") == "error":
                        html += f"<div class='response-card'><p class='text-sm text-red-400 italic'>Error in Step: <strong>{tool_name or 'N/A'}</strong>. Details: {item.get('error_message', item.get('data', ''))}</p></div>"
            html += "</div></details>"

        return html, tts_payload

    def _format_standard_query_report(self) -> tuple[str, dict]:
        """
        Formats a standard query report using the CanonicalResponse model.
        """
        final_html = ""
        
        summary_html_parts = []
        if self.response.key_metric:
            summary_html_parts.append(self._render_key_metric(self.response.key_metric))
        
        summary_html_parts.append(self._render_direct_answer(self.response.direct_answer))
        
        if self.response.key_observations:
            summary_html_parts.append(self._render_observations(self.response.key_observations))

        if summary_html_parts:
            final_html += f'<div class="response-card summary-card">{"".join(summary_html_parts)}</div>'

        tts_payload = {
            "direct_answer": self.response.direct_answer,
            "key_observations": " ".join([obs.text for obs in self.response.key_observations])
        }

        data_source = []
        if isinstance(self.collected_data, dict):
            for item_list in self.collected_data.values():
                data_source.extend(item_list)
        elif isinstance(self.collected_data, list):
            data_source = self.collected_data
            
        if not data_source:
            return final_html, tts_payload

        charts = []
        for i, tool_result in enumerate(data_source):
            if isinstance(tool_result, dict) and tool_result.get("type") == "chart":
                charts.append((i, tool_result))
        
        for i, chart_result in charts:
            table_data_result = data_source[i-1] if i > 0 else None
            if table_data_result and isinstance(table_data_result, dict) and "results" in table_data_result:
                final_html += self._render_chart_with_details(chart_result, table_data_result, i, i-1)
            else:
                chart_id = f"chart-render-target-{uuid.uuid4()}"
                chart_spec_json = json.dumps(chart_result.get("spec", {}))
                final_html += f"""
                <div class="response-card">
                    <div id="{chart_id}" class="chart-render-target" data-spec='{chart_spec_json}'></div>
                </div>
                """
                self.processed_data_indices.add(i)

        details_html = ""
        for i, tool_result in enumerate(data_source):
            if i in self.processed_data_indices or not isinstance(tool_result, dict):
                continue
            
            metadata = tool_result.get("metadata", {})
            tool_name = metadata.get("tool_name")

            if tool_name == 'base_tableDDL':
                details_html += self._render_ddl(tool_result, i)
            elif "results" in tool_result:
                 details_html += self._render_table(tool_result, i, tool_name or "Result")

        if details_html:
            final_html += (
                f"<details class='response-card bg-white/5 open:pb-4 mb-4 rounded-lg border border-white/10'>"
                f"<summary class='p-4 font-bold text-lg text-white cursor-pointer hover:bg-white/10 rounded-t-lg'>Execution Report</summary>"
                f"<div class='px-4'>{details_html}</div>"
                f"</details>"
            )
            
        return final_html, tts_payload

    def render(self) -> tuple[str, dict]:
        """
        Main rendering method. Routes to the appropriate formatting strategy.
        
        Returns:
            A tuple containing:
            - final_html (str): The complete HTML string for the UI.
            - tts_payload (dict): The structured payload for the TTS engine.
        """
        if self.active_prompt_name:
            return self._format_workflow_report()
        else:
            return self._format_standard_query_report()
