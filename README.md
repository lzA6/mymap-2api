# 🌊 mymap-2api: 你的 MyMap.ai 超级连接器 🚀

[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/lzA6/mymap-2api/blob/main/LICENSE)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg?logo=docker)](https://hub.docker.com/)
[![Tech Stack](https://img.shields.io/badge/stack-FastAPI%20%7C%20Nginx%20%7C%20Docker-green.svg)](https://fastapi.tiangolo.com/)
[![Status](https://img.shields.io/badge/status-v1.0.0%20稳定版-brightgreen.svg)]()

> "我们不是在创造新的孤岛，而是在已有的群岛之间架设桥梁。" —— mymap-2api 开发者

欢迎来到 `mymap-2api` 的世界！这是一个充满魔力的项目，能将强大的 [MyMap.ai](https://www.mymap.ai/) 思维导图和智能对话能力，无缝转换为与 OpenAI API 完全兼容的格式。

**这意味着什么？** 🤔 你可以将 MyMap 的超能力轻松接入到任何支持 OpenAI 接口的第三方应用、工作流或你自己的程序中！无论是文件分析、上下文对话，还是动态生成思维导图和流程图，现在都触手可及。

**仓库链接:** [https://github.com/lzA6/mymap-2api](https://github.com/lzA6/mymap-2api)

---

## ✨ 项目亮点与核心功能

- **🤖 OpenAI 格式兼容** - 像使用 `gpt-3.5-turbo` 一样调用 MyMap，无缝迁移，零学习成本
- **🧠 上下文记忆** - 支持多轮对话，保持对话连贯性，体验如丝般顺滑
- **📄 强大的文件处理** - 直接处理各类文件（图片、文档等），支持本地上传和网络链接
- **🎨 动态视觉生成** - 返回思维导图 (`mindmap`) 和流程图 (`flowchart`) 的结构化数据，后端智能渲染成精美 HTML 页面
- **⚡ 高性能流式响应** - 基于 Server-Sent Events (SSE) 实时传输，带来打字机般的流畅体验
- **🐳 Docker 一键部署** - 提供完整的 `docker-compose` 配置，一条命令启动整个服务
- **🌐 自带 Web UI** - 内置简洁的 Web 聊天界面，方便快速测试和体验所有功能
- **🔐 安全可靠** - 通过 API Key 保护服务，确保访问安全

---

## 📜 目录

1. [哲学与愿景](#-哲学与愿景我们为何创造它)
2. [快速上手](#-快速上手懒人一键部署教程)
3. [详细使用指南](#-详细使用指南一步步成为大师)
4. [技术内幕](#-技术内幕揭秘魔法背后的原理)
5. [优缺点与场景分析](#-优缺点与场景分析)
6. [未来蓝图与贡献指南](#-未来蓝图与贡献指南)
7. [开源协议](#-开源协议)

---

## 🌌 哲学与愿景：我们为何创造它？

在这个信息爆炸的时代，我们拥有无数强大的工具，但它们往往像一座座孤岛，彼此隔绝。`MyMap.ai` 是一座美丽的岛屿，它能帮助我们整理思绪，构建知识的宫殿。但我们想，如果能让这座岛与大陆连接起来，会发生什么？

`mymap-2api` 就是我们建造的桥梁。

我们的哲学很简单：**连接优于创造，赋能胜于替代**。我们不重新发明轮子，而是将优秀的轮子装上标准化的轴承，让它能在更广阔的道路上飞驰。

通过这个项目，我们希望：
- **降低技术门槛** - 让不熟悉 `MyMap.ai` 内部机制的开发者，也能通过熟悉的 OpenAI API 享用其强大功能
- **激发创造力** - 当一个强大的工具变得易于集成，无数新的应用场景和可能性将被解锁
- **拥抱开源精神** - 我们将整个项目开源，不仅是分享代码，更是分享一种解决问题的思路

---

## 🚀 快速上手：懒人一键部署教程

我们为你准备了最简单的方式来启动项目，只需要你的电脑安装了 `Git` 和 `Docker`。

### 第一步：克隆项目
```bash
git clone https://github.com/lzA6/mymap-2api.git
cd mymap-2api
```

### 第二步：配置环境
复制环境配置文件并修改：
```bash
cp .env.example .env
```

编辑 `.env` 文件，设置你的专属密码：
```dotenv
# .env
API_MASTER_KEY=sk-your-super-secret-key-here
NGINX_PORT=8088
```

### 第三步：启动服务
```bash
docker-compose up -d --build
```

### 第四步：验证服务
- **访问 Web UI**: `http://localhost:8088`
- **API 接口地址**: `http://localhost:8088/v1`

恭喜你！服务已成功启动！☕

---

## 📖 详细使用指南：一步步成为大师

### 1. 使用 Web UI

这是最直观的体验方式：

- **API Key** - 在设置面板填入 `.env` 中设置的 `API_MASTER_KEY`
- **User ID** - 任意标识，用于区分不同对话会话
- **文件上传** - 点击 📎 图标上传本地文件
- **对话体验** - 输入问题如"帮我规划北京三日游并用思维导图展示"

### 2. 在代码中使用 API

使用 OpenAI 兼容的客户端库：

```python
import openai

# 配置客户端
client = openai.OpenAI(
    api_key="sk-your-super-secret-key-here",
    base_url="http://localhost:8088/v1",
)

# 基础对话
response = client.chat.completions.create(
    model="mymap-ai",
    messages=[
        {"role": "user", "content": "你好，请介绍一下你自己"},
    ],
    stream=True,
)

for chunk in response:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="", flush=True)
```

### 3. API 端点说明

| 端点 | 方法 | 描述 |
|------|------|------|
| `/v1/chat/completions` | POST | 核心聊天完成接口 |
| `/v1/models` | GET | 获取可用模型列表 |
| `/` | GET | Web UI 界面 |

---

## 🔬 技术内幕：揭秘魔法背后的原理

### 📂 项目架构概览

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   客户端请求     │────│   Nginx 反向代理  │────│   FastAPI 应用   │
│ (Web/API Client)│    │   (负载均衡)     │    │   (业务逻辑)    │
└─────────────────┘    └──────────────────┘    └─────────┬───────┘
                                                         │
                                           ┌─────────────┼─────────────┐
                                           │             │             │
                                    ┌──────┴─────┐ ┌─────┴──────┐ ┌─────┴──────┐
                                    │  会话管理   │ │ 文件处理   │ │ 视觉渲染   │
                                    │ (TTLCache) │ │ (上传/解析)│ │ (HTML生成) │
                                    └──────┬─────┘ └─────┬──────┘ └─────┬──────┘
                                           │             │             │
                                           └─────────────┼─────────────┘
                                                         │
                                           ┌─────────────┴─────────────┐
                                           │    MyMap.ai 非官方 API     │
                                           │     (上游服务调用)         │
                                           └───────────────────────────┘
```

### 📂 项目文件结构

```
mymap-2api/
├── 🐳 docker-compose.yml          # 容器编排配置
├── 🐋 Dockerfile                  # 应用容器镜像定义
├── 🛠️ main.py                     # FastAPI 应用入口
├── 🔧 nginx.conf                  # Nginx 反向代理配置
├── 📋 requirements.txt            # Python 依赖清单
├── 📁 app/                        # 核心应用代码
│   ├── 🎯 core/
│   │   └── config.py              # 配置管理
│   ├── 🔌 providers/
│   │   ├── base_provider.py       # Provider 基类
│   │   └── mymap_provider.py      # MyMap.ai 接口实现
│   └── 🛠️ utils/
│       └── sse_utils.py           # SSE 工具函数
├── 📁 static/                     # 静态资源
│   ├── index.html                 # Web UI 主页面
│   ├── script.js                  # 前端交互逻辑
│   └── style.css                  # 样式文件
└── 📄 .env.example                # 环境配置模板
```

### 🛠️ 核心技术栈

| 技术组件 | 版本 | 职责描述 | 实现评级 |
|---------|------|----------|----------|
| **FastAPI** | 0.104+ | 异步 Web 框架，提供 API 服务和自动文档 | ★★★★★ |
| **Uvicorn** | 0.24+ | ASGI 服务器，高性能异步请求处理 | ★★★★★ |
| **Nginx** | 1.24+ | 反向代理，负载均衡，静态文件服务 | ★★★★★ |
| **Docker** | 20.10+ | 容器化部署，环境隔离 | ★★★★★ |
| **HTTX** | 0.25+ | 异步 HTTP 客户端，上游 API 调用 | ★★★★★ |
| **Cachetools** | 5.3+ | 内存缓存，会话状态管理 | ★★★★☆ |
| **Pydantic** | 2.4+ | 数据验证和设置管理 | ★★★★★ |

### 🧠 核心处理流程

#### 1. 请求处理流程
```python
# app/providers/mymap_provider.py
async def create_chat_completion(self, request):
    # 1. 转换 OpenAI 格式到 MyMap 格式
    mymap_messages = self._convert_openai_to_mymap(request.messages)
    
    # 2. 处理文件上传（如存在）
    for message in mymap_messages:
        if has_files(message):
            await self._handle_file_upload(message)
    
    # 3. 流式调用 MyMap.ai API
    async for chunk in self._stream_generator(mymap_messages):
        # 4. 处理可视化内容
        if contains_visual_markup(chunk):
            chunk = self._convert_visual_to_html(chunk)
        
        yield chunk
```

#### 2. 文件上传机制
```python
async def _handle_file_upload(self, message):
    # 1. 获取预签名上传 URL
    signed_url = await self._get_signed_upload_url()
    
    # 2. 上传文件到云存储
    upload_response = await self._upload_to_s3(signed_url, file_content)
    
    # 3. 构建文件消息
    return self._build_file_message(upload_response)
```

#### 3. 可视化渲染引擎
```python
def _convert_visual_to_html(self, visual_xml):
    visual_type = parse_visual_type(visual_xml)
    
    if visual_type == "mindmap":
        return self._generate_mindmap_html(visual_xml)
    elif visual_type == "flowchart":
        return self._generate_flowchart_html(visual_xml)
    
    return visual_xml
```

#### 4. 前端渲染逻辑
```javascript
// static/script.js
class ChatInterface {
    async sendMessage(message, files = []) {
        // 构建 OpenAI 兼容的请求
        const request = {
            model: 'mymap-ai',
            messages: [...this.messages, {role: 'user', content: message}],
            stream: true
        };
        
        // 处理流式响应
        const response = await fetch('/v1/chat/completions', {
            method: 'POST',
            headers: {'Authorization': `Bearer ${this.apiKey}`},
            body: JSON.stringify(request)
        });
        
        await this.handleStreamResponse(response);
    }
    
    async handleStreamResponse(response) {
        const reader = response.body.getReader();
        
        while (true) {
            const {done, value} = await reader.read();
            if (done) break;
            
            const chunk = new TextDecoder().decode(value);
            this.processSSEChunk(chunk);
        }
    }
}
```

---

## 📊 优缺点与场景分析

### ✅ 核心优势

1. **生态兼容性** - 无缝接入 OpenAI 生态，支持现有工具链
2. **功能增强** - 在代理基础上增加可视化渲染等增强功能
3. **部署简便** - Docker 一体化部署，降低运维复杂度
4. **开发友好** - 提供完整 Web UI 和 API 文档，加速开发调试

### ⚠️ 注意事项

1. **依赖上游服务** - 功能稳定性依赖于 MyMap.ai 服务的可用性
2. **非官方接口** - 基于逆向工程，可能存在服务变更风险
3. **内存缓存限制** - 当前会话管理基于内存，重启后状态丢失
4. **性能瓶颈** - 文件处理和可视化渲染可能成为性能瓶颈

### 🎯 适用场景

| 场景 | 说明 | 收益 |
|------|------|------|
| **个人知识管理** | 集成到笔记软件中自动生成思维导图 | 提升知识整理效率 |
| **自动化报告** | 数据分析后自动生成可视化总结 | 增强报告可读性 |
| **智能教育** | 学习内容自动生成知识图谱 | 改善学习体验 |
| **快速原型** | 需要多模态AI能力的应用原型 | 加速产品开发 |
| **团队协作** | 集成到聊天工具中进行头脑风暴 | 提升协作效率 |

---

## 🗺️ 未来蓝图与贡献指南

### 🎯 v1.0 已实现功能

- [x] OpenAI API 完全兼容
- [x] 流式响应支持
- [x] 多轮对话上下文
- [x] 文件上传处理
- [x] 思维导图可视化
- [x] 流程图可视化
- [x] Docker 一体化部署
- [x] Web UI 交互界面

### 🔮 规划中的功能

#### 功能增强
- [ ] 更多图表类型支持（甘特图、时序图等）
- [ ] 批量处理能力
- [ ] API 速率限制
- [ ] 请求重试机制

#### 架构优化
- [ ] Redis 会话存储
- [ ] 多实例负载均衡
- [ ] 健康检查端点
- [ ] 性能监控指标

#### 开发者体验
- [ ] 完整的测试覆盖
- [ ] API 文档增强
- [ ] 配置验证改进
- [ ] 错误处理优化

### 🤝 贡献指南

我们欢迎各种形式的贡献！

#### 报告问题
在 [GitHub Issues](https://github.com/lzA6/mymap-2api/issues) 提交 bug 报告或功能建议。

#### 代码贡献
1. Fork 本仓库
2. 创建功能分支：`git checkout -b feature/amazing-feature`
3. 提交更改：`git commit -m 'Add amazing feature'`
4. 推送分支：`git push origin feature/amazing-feature`
5. 创建 Pull Request

#### 开发环境设置
```bash
# 克隆仓库
git clone https://github.com/lzA6/mymap-2api.git
cd mymap-2api

# 安装依赖
pip install -r requirements.txt

# 启动开发服务器
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

---

## ⚖️ 开源协议

本项目采用 **Apache License 2.0** 开源协议。

**简单理解：**
- ✅ **允许** - 商业使用、修改、分发、专利授权
- ✅ **要求** - 保留版权声明、包含许可文本
- ✅ **提供** - 明确专利授权
- ❌ **不保证** - 软件适用性担保
- ❌ **不承担** - 间接损害责任

完整的协议文本请参阅 [LICENSE](https://github.com/lzA6/mymap-2api/blob/main/LICENSE) 文件。

---

## 🎯 快速开始 Checklist

- [ ] 安装 Docker 和 Docker Compose
- [ ] 克隆项目仓库
- [ ] 复制并配置 `.env` 文件
- [ ] 运行 `docker-compose up -d`
- [ ] 访问 `http://localhost:8088`
- [ ] 配置 API Key 开始使用

> "代码是新时代的诗歌，而开源，则是我们与世界分享诗意的方式。"
>
> 感谢你的阅读，现在，去创造属于你的奇迹吧！✨

---
