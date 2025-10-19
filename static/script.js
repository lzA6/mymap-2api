document.addEventListener('DOMContentLoaded', () => {
    const chatBox = document.getElementById('chat-box');
    const messageInput = document.getElementById('message-input');
    const sendBtn = document.getElementById('send-btn');
    const uploadBtn = document.getElementById('upload-btn');
    const fileInput = document.getElementById('file-input');
    const apiKeyInput = document.getElementById('api-key');
    const userIdInput = document.getElementById('user-id');

    let messages = [];

    mermaid.initialize({ startOnLoad: false, theme: 'neutral' });

    const renderAllVisuals = (container) => {
        container.querySelectorAll('code.language-mymap').forEach(el => {
            if (el.getAttribute('data-rendered') === 'true') return;

            try {
                const xmlString = el.textContent;
                const parser = new DOMParser();
                const xmlDoc = parser.parseFromString(xmlString, "text/xml");
                
                // 检查解析是否出错
                if (xmlDoc.getElementsByTagName("parsererror").length > 0) {
                    throw new Error("Invalid XML format in visual block.");
                }

                const visualElement = xmlDoc.documentElement;
                const visualType = visualElement.getAttribute('type');

                let renderResultContainer;

                if (visualType.startsWith('mindmap')) {
                    renderResultContainer = renderMindmap(visualElement);
                } else if (visualType.startsWith('flowchart') || visualType.startsWith('diagram') || visualType.startsWith('cheat-sheet')) {
                    renderResultContainer = renderPositionalGraphic(visualElement);
                } else {
                    throw new Error(`Unknown visual type: ${visualType}`);
                }
                
                el.parentElement.replaceWith(renderResultContainer);
                el.setAttribute('data-rendered', 'true');

            } catch (e) {
                console.error("Error rendering mymap visual:", e);
                const errorDiv = document.createElement('div');
                errorDiv.className = 'error-box';
                errorDiv.innerText = `Failed to render visual: ${e.message}`;
                el.parentElement.replaceWith(errorDiv);
            }
        });
    };

    function renderMindmap(visualElement) {
        const markdownContent = visualElement.textContent;
        const mermaidGraph = convertMarkdownToMermaid(markdownContent);
        const graphContainer = document.createElement('div');
        graphContainer.className = 'visual-container mermaid-graph';
        const graphId = 'mermaid-' + Date.now() + Math.random().toString(36).substr(2, 9);
        
        // Mermaid.js 渲染是异步的
        mermaid.render(graphId, mermaidGraph, (svgCode) => {
            graphContainer.innerHTML = svgCode;
        });
        
        return graphContainer;
    }

    function renderPositionalGraphic(visualElement) {
        const container = document.createElement('div');
        container.className = 'visual-container positional-graphic';
        const containerWidth = parseInt(visualElement.getAttribute('width'), 10) || 1000;
        const containerHeight = parseInt(visualElement.getAttribute('height'), 10) || 800;
        container.style.width = `${containerWidth}px`;
        container.style.height = `${containerHeight}px`;
        container.style.position = 'relative';

        for (const child of visualElement.children) {
            if (child.tagName.toLowerCase() === 'text') {
                const textDiv = document.createElement('div');
                textDiv.className = 'positional-text';
                textDiv.style.position = 'absolute';
                textDiv.style.left = `${child.getAttribute('x')}px`;
                textDiv.style.top = `${child.getAttribute('y')}px`;
                textDiv.style.width = `${child.getAttribute('width')}px`;
                textDiv.style.height = `${child.getAttribute('height')}px`;
                
                const styleString = child.getAttribute('style') || '';
                styleString.split(' ').forEach(cls => {
                    if(cls) textDiv.classList.add(cls.replace(/_/g, '-'));
                });

                textDiv.innerHTML = marked.parse(child.textContent);
                container.appendChild(textDiv);
            }
            // 未来可以在此添加对 <line> 等其他图形元素的支持
        }
        return container;
    }

    function convertMarkdownToMermaid(markdownString) {
        let mermaidString = 'graph TD\n';
        const lines = markdownString.trim().split('\n');
        const idMap = new Map();
        const parentMap = new Map();

        function getNodeId(text, level) {
            const key = `${level}-${text}`;
            if (!idMap.has(key)) {
                const safeId = 'node' + idMap.size;
                idMap.set(key, safeId);
            }
            return idMap.get(key);
        }

        lines.forEach(line => {
            line = line.trim();
            if (!line) return;

            const match = line.match(/^(#+)\s+(.*)/);
            if (match) {
                const level = match[1].length;
                const text = match[2].trim().replace(/"/g, '#quot;');
                const nodeId = getNodeId(text, level);

                mermaidString += `    ${nodeId}["${text}"]\n`;

                if (level > 1) {
                    let parentId = null;
                    for (let i = level - 1; i >= 1; i--) {
                        if (parentMap.has(i)) {
                            parentId = parentMap.get(i);
                            break;
                        }
                    }
                    if (parentId) {
                        mermaidString += `    ${parentId} --> ${nodeId}\n`;
                    }
                }
                parentMap.set(level, nodeId);
                for (let i = level + 1; i <= 6; i++) {
                    parentMap.delete(i);
                }
            }
        });
        return mermaidString;
    }

    const addMessageToChat = (role, content) => {
        const messageElem = document.createElement('div');
        messageElem.classList.add('message', role === 'user' ? 'user-message' : 'assistant-message');
        messageElem.innerHTML = marked.parse(content);
        chatBox.appendChild(messageElem);
        chatBox.scrollTop = chatBox.scrollHeight;
        renderAllVisuals(messageElem);
    };

    const fetchAndStream = async () => {
        const assistantMsgDiv = document.createElement('div');
        assistantMsgDiv.classList.add('message', 'assistant-message');
        chatBox.appendChild(assistantMsgDiv);
        let fullContent = '';
        try {
            const response = await fetch('/v1/chat/completions', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${apiKeyInput.value}`
                },
                body: JSON.stringify({
                    model: 'mymap-ai',
                    messages: messages,
                    stream: true,
                    user: userIdInput.value
                })
            });

            const reader = response.body.getReader();
            const decoder = new TextDecoder();

            while (true) {
                const { value, done } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value, { stream: true });
                const lines = chunk.split('\n').filter(line => line.trim());

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const dataStr = line.substring(6);
                        if (dataStr === '[DONE]') {
                            messages.push({ role: 'assistant', content: fullContent });
                            renderAllVisuals(assistantMsgDiv);
                            return;
                        }
                        try {
                            const data = JSON.parse(dataStr);
                            if (data.choices && data.choices[0].delta.content) {
                                fullContent += data.choices[0].delta.content;
                                assistantMsgDiv.innerHTML = marked.parse(fullContent);
                                chatBox.scrollTop = chatBox.scrollHeight;
                            }
                        } catch (e) {
                            console.error('Error parsing JSON:', dataStr);
                        }
                    }
                }
            }
        } catch (error) {
            console.error('Fetch error:', error);
            assistantMsgDiv.innerText = 'Error fetching response.';
        } finally {
            messages.push({ role: 'assistant', content: fullContent });
            renderAllVisuals(assistantMsgDiv);
        }
    };
    
    const sendMessage = async () => {
        const content = messageInput.value.trim();
        if (!content) return;
        addMessageToChat('user', content);
        messages.push({ role: 'user', content: content });
        messageInput.value = '';
        await fetchAndStream();
    };

    function fileToBase64(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.readAsDataURL(file);
            reader.onload = () => resolve(reader.result);
            reader.onerror = error => reject(error);
        });
    }

    uploadBtn.addEventListener('click', () => fileInput.click());
    fileInput.addEventListener('change', async (event) => {
        const file = event.target.files[0];
        if (!file) return;

        const base64String = await fileToBase64(file);
        
        addMessageToChat('user', `[已上传文件: ${file.name}]`);
        
        messages.push({
            role: 'user',
            content: [
                { type: 'text', text: `分析文件 ${file.name}` },
                { type: 'image_url', image_url: { url: base64String } }
            ]
        });

        await fetchAndStream();
    });

    sendBtn.addEventListener('click', sendMessage);
    messageInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
});
