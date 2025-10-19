import httpx
import json
import time
import uuid
import logging
import asyncio
import base64
import re
import math
from typing import Dict, Any, AsyncGenerator, Optional, List
from xml.etree import ElementTree as ET
from cachetools import TTLCache
from threading import Lock

from fastapi import HTTPException, Request
from fastapi.responses import StreamingResponse, JSONResponse

from app.core.config import settings
from app.utils.sse_utils import create_sse_data, create_chat_completion_chunk, DONE_CHUNK

# 配置日志记录
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MyMapProvider:
    def __init__(self):
        self.client: Optional[httpx.AsyncClient] = None
        self.session_cache = TTLCache(maxsize=1024, ttl=settings.SESSION_CACHE_TTL)
        self.session_lock = Lock()
        self.base_url = "https://www.mymap.ai"
        self.chat_url = f"{self.base_url}/sapi/aichat"
        self.query_url = f"{self.base_url}/sapi/query"

    async def initialize(self):
        self.client = httpx.AsyncClient(headers=self._prepare_headers(), timeout=settings.API_REQUEST_TIMEOUT, http2=True)

    async def close(self):
        if self.client:
            await self.client.aclose()

    def _get_session_info(self, session_key: str) -> Dict[str, Any]:
        with self.session_lock:
            return self.session_cache.get(session_key, {})

    def _update_session_info(self, session_key: str, data: Dict[str, Any]):
        with self.session_lock:
            session_data = self.session_cache.get(session_key, {})
            session_data.update(data)
            self.session_cache[session_key] = session_data

    def _prepare_headers(self) -> Dict[str, str]:
        return {
            "Accept": "application/json, text/plain, */*", "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8", "Content-Type": "application/json",
            "Origin": self.base_url, "Referer": f"{self.base_url}/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Sec-CH-UA": '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
            "Sec-CH-UA-Mobile": "?0", "Sec-CH-UA-Platform": '"Windows"', "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors", "Sec-Fetch-Site": "same-origin", "X-Distinct-Id": str(uuid.uuid4())
        }

    async def _handle_file_upload(self, content_part: Dict[str, Any]) -> Dict[str, Any]:
        image_url_data = content_part.get("image_url", {})
        url = image_url_data.get("url")
        if not url: raise ValueError("image_url part is missing the 'url' field.")
        logger.info("检测到文件上传任务，开始处理...")
        if url.startswith("data:"):
            try:
                header, encoded = url.split(",", 1)
                file_data = base64.b64decode(encoded)
                mime_type = header.split(":")[1].split(";")[0]
                file_name = f"upload.{mime_type.split('/')[-1]}"
            except Exception as e:
                raise ValueError(f"无法解析 Base64 数据 URL: {e}")
        else:
            logger.info(f"正在从 URL 下载文件: {url}")
            async with httpx.AsyncClient() as download_client:
                response = await download_client.get(url)
                response.raise_for_status()
                file_data = response.content
                mime_type = response.headers.get("content-type", "application/octet-stream")
                file_name = url.split("/")[-1] or f"upload.{mime_type.split('/')[-1]}"
        logger.info("步骤 1/3: 获取 S3 预签名上传 URL...")
        signed_url_data = await self._get_signed_upload_url(mime_type)
        logger.info(f"步骤 2/3: 上传文件到 S3 (ID: {signed_url_data['id']})...")
        await self._upload_to_s3(signed_url_data["url"], file_data, mime_type)
        logger.info("步骤 3/3: 构建文件消息...")
        final_s3_url = signed_url_data["url"].split("?")[0]
        return {"type": "file", "content": final_s3_url, "card_id": signed_url_data["id"], "file_name": file_name}

    async def _get_signed_upload_url(self, content_type: str) -> Dict[str, str]:
        payload = {"operationName": "getSignedUrl", "variables": {"input": {"type": content_type}}, "query": "mutation getSignedUrl($input: SignedUrlPayload!) {\n  getSignedUrl(input: $input) {\n    url\n    id\n    type\n    __typename\n  }\n}\n"}
        response = await self.client.post(self.query_url, json=payload)
        response.raise_for_status()
        data = response.json()
        if "errors" in data or "data" not in data or "getSignedUrl" not in data["data"]:
            raise Exception(f"获取签名URL失败: {data.get('errors', '未知GraphQL错误')}")
        return data["data"]["getSignedUrl"]

    async def _upload_to_s3(self, upload_url: str, file_data: bytes, content_type: str):
        async with httpx.AsyncClient() as upload_client:
            response = await upload_client.put(upload_url, content=file_data, headers={"Content-Type": content_type})
            response.raise_for_status()

    async def _convert_openai_to_mymap(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        mymap_messages = []
        for msg in messages:
            if msg.get("role") == "user":
                content = msg.get("content")
                if isinstance(content, str): mymap_messages.append({"type": "text", "content": content})
                elif isinstance(content, list):
                    for part in content:
                        if part.get("type") == "text": mymap_messages.append({"type": "text", "content": part.get("text", "")})
                        elif part.get("type") == "image_url": mymap_messages.append(await self._handle_file_upload(part))
            elif msg.get("role") == "system": mymap_messages.insert(0, {"type": "text", "content": msg.get("content", "")})
        return mymap_messages

    def _parse_mindmap_xml(self, xml_content):
        xml_content = re.sub(r'\sxmlns="[^"]+"', '', xml_content, count=1)
        root = ET.fromstring(xml_content)
        title = root.get('title', '思维导图')
        content = "".join(root.itertext()).strip()
        return {'title': title, 'content': content}

    def _markdown_to_tree(self, content):
        lines = content.split('\n')
        nodes = []
        for line in lines:
            line = line.strip()
            if not line: continue
            match = re.match(r'^(#+)\s*(.*)', line)
            if match:
                level = len(match.group(1))
                text = match.group(2).strip()
                nodes.append({'level': level, 'text': text, 'description': '', 'children': []})
            elif nodes:
                nodes[-1]['description'] += f' {line}'
        if not nodes: return []
        root_node = nodes.pop(0)
        tree = {'text': root_node['text'], 'description': root_node['description'].strip(), 'children': [], 'level': root_node['level']}
        stack = [tree]
        for node in nodes:
            current = {'text': node['text'], 'description': node['description'].strip(), 'children': [], 'level': node['level']}
            while len(stack) > 1 and stack[-1]['level'] >= node['level']: stack.pop()
            stack[-1]['children'].append(current)
            stack.append(current)
        return [tree]

    def _generate_mindmap_html(self, tree_data, title="思维导图"):
        def get_icon(level): return {1: "🌊", 2: "📚", 3: "🚫"}.get(level, "📌")
        def gen_children(children, level):
            if not children: return ""
            html = '<div class="sub-items">'
            for child in children:
                html += f'<div class="sub-item"><div class="sub-item-title">{get_icon(level)} {child["text"]}</div>'
                if child.get('description'): html += f'<div class="sub-item-description">{child["description"]}</div>'
                html += '</div>'
            return html + '</div>'
        def gen_branches(children, level):
            if not children: return ""
            html = ""
            for child in children:
                html += f'<div class="branch"><div class="branch-title"><div class="branch-icon">{get_icon(level)}</div>{child["text"]}</div>'
                if child.get('description'): html += f'<div class="branch-description">{child["description"]}</div>'
                html += gen_children(child.get('children', []), level + 1) + '</div>'
            return html
        center = tree_data[0] if tree_data else {'text': '中心主题', 'description': '', 'children': []}
        center_html = f'<div class="center-node pulse"><div class="node-title">{center["text"]}</div>'
        if center.get('description'): center_html += f'<div class="node-desc">{center["description"]}</div>'
        center_html += '</div>'
        branches_html = f"<div class='branches'>{gen_branches(center.get('children', []), 1)}</div>"
        return f'<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><title>{title}</title><style>body{{font-family:sans-serif;background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);padding:20px;display:flex;justify-content:center;align-items:center;}} .container{{background:white;border-radius:20px;box-shadow:0 20px 60px rgba(0,0,0,0.3);padding:40px;max-width:1200px;}} .title{{text-align:center;color:#2c3e50;font-size:2.5em;margin-bottom:30px;}} .mindmap{{display:flex;justify-content:center;align-items:center;gap:60px;}} .center-node{{background:linear-gradient(135deg,#3498db,#2980b9);color:white;padding:30px;border-radius:15px;font-size:1.8em;text-align:center;box-shadow:0 10px 30px rgba(52,152,219,0.3);z-index:10;}} .branches{{display:flex;flex-direction:column;gap:30px;}} .branch{{background:#f8f9fa;border-radius:15px;padding:25px;box-shadow:0 5px 20px rgba(0,0,0,0.1);border-left:5px solid #3498db;}} .branch-title{{color:#2c3e50;font-size:1.4em;font-weight:bold;margin-bottom:15px;display:flex;align-items:center;gap:10px;}} .branch-icon{{width:30px;height:30px;background:#3498db;border-radius:50%;display:flex;align-items:center;justify-content:center;color:white;font-size:1.2em;flex-shrink:0;}} .sub-items{{display:flex;flex-direction:column;gap:15px;}} .sub-item{{background:white;padding:15px 20px;border-radius:10px;border-left:3px solid #e74c3c;box-shadow:0 2px 10px rgba(0,0,0,0.05);}} .pulse{{animation:pulse 2s infinite;}} @keyframes pulse{{0%{{box-shadow:0 10px 30px rgba(52,152,219,0.3);}}50%{{box-shadow:0 10px 40px rgba(52,152,219,0.5);}}100%{{box-shadow:0 10px 30px rgba(52,152,219,0.3);}}}} @media (max-width:992px){{.mindmap{{flex-direction:column;}} .branches{{width:100%;}}}}</style></head><body><div class="container"><h1 class="title">🌊 {title}</h1><div class="mindmap">{center_html}{branches_html}</div></div></body></html>'

    # **【全新功能】** 流程图专用渲染器
    def _generate_flowchart_html(self, root: ET.Element):
        title = root.get('title', '流程图')
        width = root.get('width', '1000')
        height = root.get('height', '800')
        
        nodes = {elem.get('id'): elem for elem in root.findall('text')}
        boxes_html = ""
        for elem_id, elem in nodes.items():
            style = elem.get('style', '')
            shape = elem.get('shape', 'rectangle')
            text_content = (elem.text or "").strip().replace('\n', '<br>')
            box_html = f"<div class='box {style} shape_{shape}' style='left:{elem.get('x')}px; top:{elem.get('y')}px; width:{elem.get('width')}px; height:{elem.get('height')}px;'><div>{text_content}</div></div>"
            boxes_html += box_html
        
        lines_html = ""
        for line in root.findall('line'):
            start_node = nodes.get(line.get('start-node'))
            end_node = nodes.get(line.get('end-node'))
            if start_node is not None and end_node is not None:
                x1 = float(start_node.get('x')) + float(start_node.get('width')) / 2
                y1 = float(start_node.get('y')) + float(start_node.get('height'))
                x2 = float(end_node.get('x')) + float(end_node.get('width')) / 2
                y2 = float(end_node.get('y'))
                
                length = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
                angle = math.degrees(math.atan2(y2 - y1, x2 - x1)) - 90
                
                lines_html += f"<div class='line' style='height:{length}px; left:{x1}px; top:{y1}px; transform:rotate({angle}deg);'></div>"

        return f'<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><title>{title}</title><style>body{{background:#f0f2f5;}} .flowchart{{position:relative;width:{width}px;height:{height}px;margin:auto;background-image:linear-gradient(45deg,#e9ecef 25%,transparent 25%),linear-gradient(-45deg,#e9ecef 25%,transparent 25%),linear-gradient(45deg,transparent 75%,#e9ecef 75%),linear-gradient(-45deg,transparent 75%,#e9ecef 75%);background-size:20px 20px;border:1px solid #dee2e6;}} .box{{position:absolute;padding:10px;border:2px solid #343a40;background-color:#fff;text-align:center;box-shadow:0 2px 4px rgba(0,0,0,0.05);display:flex;align-items:center;justify-content:center;}} .shape_circle{{border-radius:50%;}} .shape_rectangle{{border-radius:8px;}} .border_blue{{border-color:#4a90e2;}} .border_green{{border-color:#7ed321;}} .border_yellow{{border-color:#f5a623;}} .border_purple{{border-color:#9013fe;}} .border_orange{{border-color:#f88010;}} .line{{position:absolute;background-color:#808080;width:2px;transform-origin:top center;}}</style></head><body><div class="flowchart">{boxes_html}{lines_html}</div></body></html>'

    # **【智能分发】** 根据类型调用不同的渲染器
    def _convert_visual_to_html(self, xml_content):
        try:
            xml_content = re.sub(r'\sxmlns="[^"]+"', '', xml_content, count=1)
            root = ET.fromstring(xml_content)
            visual_type = root.get("type", "")

            if 'mindmap' in visual_type:
                data = self._parse_mindmap_xml(xml_content)
                tree_data = self._markdown_to_tree(data['content'])
                return self._generate_mindmap_html(tree_data, data['title'])
            elif 'flowchart' in visual_type:
                return self._generate_flowchart_html(root)
            else:
                # 提供一个后备的简单渲染
                return f"<h1>未知图表类型</h1><pre>{ET.tostring(root, encoding='unicode')}</pre>"
        except Exception as e:
            logger.error(f"生成HTML时出错: {e}", exc_info=True)
            return f"<h1>HTML Generation Error</h1><p>{e}</p>"

    async def chat_completion(self, request: Request, request_data: Dict[str, Any]) -> StreamingResponse:
        session_key = request_data.get("user", str(uuid.uuid4()))
        session_info = self._get_session_info(session_key)
        chat_id = session_info.get("chat_id")
        board_id = session_info.get("board_id", str(uuid.uuid4().hex[:13]))
        openai_messages = request_data.get("messages", [])
        mymap_messages = await self._convert_openai_to_mymap(openai_messages)
        payload = {"messages": mymap_messages, "board_id": board_id, "playground": True}
        if chat_id: payload["id"] = chat_id
        model = request_data.get("model", settings.DEFAULT_MODEL)
        return StreamingResponse(self._stream_generator(session_key, board_id, payload, model), media_type="text/event-stream")

    async def _stream_generator(self, session_key: str, board_id: str, payload: Dict, model: str) -> AsyncGenerator[bytes, None]:
        request_id = f"chatcmpl-{uuid.uuid4()}"
        full_response_content = ""
        try:
            async with self.client.stream("POST", self.chat_url, json=payload) as response:
                if response.status_code == 200 and "x-chat-id" in response.headers:
                    new_chat_id = response.headers["x-chat-id"]
                    self._update_session_info(session_key, {"chat_id": new_chat_id, "board_id": board_id})
                    logger.info(f"会话 '{session_key}' 已关联到 chat_id: {new_chat_id}")
                response.raise_for_status()
                async for chunk_bytes in response.aiter_bytes():
                    chunk_str = chunk_bytes.decode('utf-8')
                    full_response_content += chunk_str
                    yield create_sse_data(create_chat_completion_chunk(request_id, model, chunk_str))
        except httpx.HTTPStatusError as e:
            error_message = f"\n\n---\n**错误提示：** 请求上游服务失败。\n- **状态码:** {e.response.status_code}\n- **原因:** {e.response.reason_phrase}"
            logger.error(f"流式请求失败: {e}")
            yield create_sse_data(create_chat_completion_chunk(request_id, model, error_message))
            yield create_sse_data(create_chat_completion_chunk(request_id, model, "", "stop")); yield DONE_CHUNK; return
        except Exception as e:
            error_message = f"\n\n---\n**未知错误：** {str(e)}"
            logger.error(f"流式生成器发生未知错误: {e}", exc_info=True)
            yield create_sse_data(create_chat_completion_chunk(request_id, model, error_message))
            yield create_sse_data(create_chat_completion_chunk(request_id, model, "", "stop")); yield DONE_CHUNK; return
        
        try:
            pattern = re.compile(r'<visual.*?</visual>', re.DOTALL)
            captured_visual_blocks = pattern.findall(full_response_content)
            if captured_visual_blocks:
                logger.info(f"原始流传输完毕。检测到 {len(captured_visual_blocks)} 个 visual 块，开始转换并追加。")
                for i, visual_block in enumerate(captured_visual_blocks):
                    html_content = self._convert_visual_to_html(visual_block)
                    html_source_markdown = f"\n\n---\n\n**图表 {i+1} HTML 预览源代码:**\n```html\n{html_content}\n```\n"
                    yield create_sse_data(create_chat_completion_chunk(request_id, model, html_source_markdown))
                    logger.info(f"已追加图表 {i+1} 的HTML源代码。")
        except Exception as e:
            logger.error(f"追加HTML块时出错: {e}", exc_info=True)
            error_markdown = f"\n\n--- \n**HTML转换失败:** `{str(e)}`"
            yield create_sse_data(create_chat_completion_chunk(request_id, model, error_markdown))

        yield create_sse_data(create_chat_completion_chunk(request_id, model, "", "stop"))
        yield DONE_CHUNK
        logger.info(f"会话 '{session_key}' 流式传输结束（包含追加内容）。")

    async def get_models(self) -> JSONResponse:
        return JSONResponse(content={"object": "list", "data": [{"id": name, "object": "model", "created": int(time.time()), "owned_by": "lzA6"} for name in settings.KNOWN_MODELS]})
