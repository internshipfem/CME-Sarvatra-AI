
function detectDocumentIntent(text) {
    if (!text || typeof text !== 'string') return null;
    const lower = text.toLowerCase();
    
    if (/\b(leave|casual leave|annual leave|station leave|sick leave)\b/.test(lower)) {
        return { type: 'leave_application', label: 'Leave Application' };
    }
    if (/\b(letter|formal letter|doh letter|demi official|hq letter)\b/.test(lower) && /\b(draft|write|compose|prepare|generate|format|create|send)\b/.test(lower)) {
        return { type: 'formal_letter', label: 'Formal Military Letter' };
    }
    if (/\b(memo|memorandum|circular)\b/.test(lower)) {
        return { type: 'office_memo', label: 'Office Memorandum' };
    }
    if (/\b(mom|minutes|meeting minutes|conference minutes)\b/.test(lower)) {
        return { type: 'meeting_minutes', label: 'Minutes of Meeting' };
    }
    if (/\b(note sheet|office note|file note)\b/.test(lower)) {
        return { type: 'office_note', label: 'Office Note / Note Sheet' };
    }
    if (/\b(order|office order|promulgate|promulgation)\b/.test(lower)) {
        return { type: 'office_order', label: 'Office Order' };
    }
    if (/\b(technical report|trial report|evaluation report)\b/.test(lower)) {
        return { type: 'technical_report', label: 'Technical Report' };
    }
    return null;
}

/**
 * Air-Gapped Ollama ChatGPT Client Application
 * 100% Self-Contained Offline JavaScript
 */

/* ==========================================================================
   Theme Management (Tactical Dark <-> Command Center Light)
   ========================================================================== */

function initTheme() {
    const saved = localStorage.getItem('sarvatra_theme') || 'dark';
    setTheme(saved);
}

function setTheme(theme) {
    const text = document.getElementById('themeToggleText');
    if (theme === 'light') {
        document.documentElement.setAttribute('data-theme', 'light');
        localStorage.setItem('sarvatra_theme', 'light');
        if (text) text.textContent = 'Dark';
    } else {
        document.documentElement.removeAttribute('data-theme');
        localStorage.setItem('sarvatra_theme', 'dark');
        if (text) text.textContent = 'Light';
    }
}

function toggleAppTheme() {
    const current = document.documentElement.getAttribute('data-theme');
    if (current === 'light') {
        setTheme('dark');
    } else {
        setTheme('light');
    }
}
window.toggleAppTheme = toggleAppTheme;
initTheme();

let activeConversationId = window.ACTIVE_CONVERSATION_ID || null;
let stagedFiles = []; // { id, name, size }
let currentAbortController = null;
let isGenerating = false;

// Helper to retrieve CSRF token from window or cookies
function getCsrfToken() {
    if (window.CSRF_TOKEN && window.CSRF_TOKEN.length > 0) {
        return window.CSRF_TOKEN;
    }
    const name = 'csrftoken';
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue || '';
}

function setupTextareaAutoresize() {
    const ta = document.getElementById('chatTextarea');
    if (ta) {
        autoResizeTextarea(ta);
    }
}

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    loadSignatureAssets();
    try {
        localStorage.removeItem('sarvatra_sidebar_collapsed');
    } catch (e) {}
    initMarkdownAndHighlighting();
    initExistingMessages();
    setupTextareaAutoresize();
    setupDragAndDrop();
    setupCopyButtonDelegation();
    setupEventHandlers();
    scrollToBottom();

    // Auto-focus chat input
    const textarea = document.getElementById('chatTextarea');
    if (textarea) textarea.focus();
});

/* ==========================================================================
   Markdown & Code Highlighting Engine
   ========================================================================== */

function initMarkdownAndHighlighting() {
    if (typeof marked !== 'undefined') {
        marked.setOptions({
            breaks: true,
            gfm: true,
            headerIds: false
        });
    }
}

function renderMarkdownText(rawMarkdown) {
    if (typeof marked === 'undefined') {
        return escapeHtml(rawMarkdown).replace(/\n/g, '<br>');
    }
    const html = marked.parse(rawMarkdown);
    return enhanceMarkdownElements(html);
}

function enhanceMarkdownElements(html) {
    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = html;

    // 1. Enhance Code Blocks with Language Header & Copy Button
    tempDiv.querySelectorAll('pre code').forEach((codeBlock) => {
        const pre = codeBlock.parentElement;
        if (pre.parentElement && pre.parentElement.classList.contains('code-block-wrapper')) {
            return;
        }
        const codeText = codeBlock.textContent;

        if (typeof hljs !== 'undefined') {
            try {
                hljs.highlightElement(codeBlock);
            } catch (e) {
                // Ignore highlight errors
            }
        }

        let lang = 'code';
        const classes = codeBlock.className.split(' ');
        for (const c of classes) {
            if (c.startsWith('language-')) {
                lang = c.replace('language-', '');
                break;
            }
        }

        const wrapper = document.createElement('div');
        wrapper.className = 'code-block-wrapper';

        const header = document.createElement('div');
        header.className = 'code-header';
        header.innerHTML = `
            <span>${escapeHtml(lang)}</span>
            <button class="btn-copy-code" type="button" title="Copy code to clipboard">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                </svg>
                <span>Copy</span>
            </button>
        `;

        pre.parentNode.insertBefore(wrapper, pre);
        wrapper.appendChild(header);
        wrapper.appendChild(pre);
    });

    // 2. Enhance Tables with Header, Table Data Label & Copy Table Button
    tempDiv.querySelectorAll('table').forEach((table) => {
        if (table.parentElement && table.parentElement.classList.contains('table-responsive-wrapper')) {
            return;
        }

        const wrapper = document.createElement('div');
        wrapper.className = 'table-block-wrapper';

        const header = document.createElement('div');
        header.className = 'table-header';
        header.innerHTML = `
            <div class="table-title">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
                    <line x1="3" y1="9" x2="21" y2="9"></line>
                    <line x1="3" y1="15" x2="21" y2="15"></line>
                    <line x1="9" y1="3" x2="9" y2="21"></line>
                    <line x1="15" y1="3" x2="15" y2="21"></line>
                </svg>
                <span>Table Data</span>
            </div>
            <button class="btn-copy-table" type="button" title="Copy table data (Excel / Word / Sheets compatible)">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                </svg>
                <span>Copy Table</span>
            </button>
        `;

        const scrollContainer = document.createElement('div');
        scrollContainer.className = 'table-responsive-wrapper';

        table.parentNode.insertBefore(wrapper, table);
        scrollContainer.appendChild(table);
        wrapper.appendChild(header);
        wrapper.appendChild(scrollContainer);
    });

    return tempDiv.innerHTML;
}

function copyTableData(table, buttonElement) {
    if (!table) return;
    const rows = Array.from(table.querySelectorAll('tr'));
    if (rows.length === 0) return;

    const rowTexts = rows.map(row => {
        const cells = Array.from(row.querySelectorAll('th, td'));
        return cells.map(c => {
            let text = c.innerText.replace(/[\r\n]+/g, ' ').trim();
            if (text.includes('\t') || text.includes('"')) {
                text = `"${text.replace(/"/g, '""')}"`;
            }
            return text;
        }).join('\t');
    });

    const tsvContent = rowTexts.join('\n');
    copyToClipboard(tsvContent, buttonElement);
}
window.copyTableData = copyTableData;

function copyCompleteMessage(buttonElement) {
    const messageWrapper = buttonElement.closest('.message-content-wrapper');
    if (!messageWrapper) return;

    const bubble = messageWrapper.querySelector('.message-bubble');
    if (!bubble) return;

    let textToCopy = '';

    const renderedTarget = bubble.querySelector('.rendered-markdown');
    const rawScript = bubble.querySelector('.raw-markdown-data');

    if (renderedTarget && renderedTarget.dataset.raw) {
        textToCopy = renderedTarget.dataset.raw.trim();
    } else if (rawScript && rawScript.textContent.trim()) {
        textToCopy = rawScript.textContent.trim();
    } else if (bubble.dataset.raw) {
        textToCopy = bubble.dataset.raw.trim();
    } else {
        // Fallback: clone bubble, remove headers and buttons, and grab innerText
        const clone = bubble.cloneNode(true);
        clone.querySelectorAll('.code-header, .table-header, .btn-copy-code, .btn-copy-table').forEach(el => el.remove());
        textToCopy = clone.innerText.trim();
    }

    if (textToCopy) {
        copyToClipboard(textToCopy, buttonElement);
    }
}
window.copyCompleteMessage = copyCompleteMessage;

function initExistingMessages() {
    document.querySelectorAll('.message-bubble.markdown-content').forEach((bubble) => {
        const rawScript = bubble.querySelector('.raw-markdown-data');
        const renderedTarget = bubble.querySelector('.rendered-markdown');
        if (renderedTarget) {
            let raw = '';
            if (rawScript) {
                raw = rawScript.textContent;
            } else {
                raw = bubble.getAttribute('data-raw') || '';
            }
            if (raw) {
                // Unescape any escaped unicode newlines or literals
                raw = raw.replace(/\\u000A/g, '\n').replace(/\\u000a/g, '\n');
                renderedTarget.innerHTML = renderMarkdownText(raw);
            }
        }
    });
}

function copyToClipboard(text, buttonElement) {
    if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(text).then(() => showCopiedFeedback(buttonElement));
    } else {
        // Fallback for non-https or air-gapped intranet
        const ta = document.createElement('textarea');
        ta.value = text;
        ta.style.position = 'fixed';
        ta.style.left = '-999999px';
        document.body.appendChild(ta);
        ta.focus();
        ta.select();
        try {
            document.execCommand('copy');
            showCopiedFeedback(buttonElement);
        } catch (err) {
            console.error('Fallback copy failed', err);
        }
        document.body.removeChild(ta);
    }
}

function showCopiedFeedback(buttonElement) {
    const originalHtml = buttonElement.innerHTML;
    buttonElement.innerHTML = `
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="20 6 9 17 4 12"></polyline>
        </svg>
        <span style="color:#10b981; font-weight:600;">Copied!</span>
    `;
    setTimeout(() => {
        buttonElement.innerHTML = originalHtml;
    }, 2000);
}

/* ==========================================================================
   Chat Interactions & Streaming Pipeline
   ========================================================================== */

async function sendMessage() {
    if (isGenerating) {
        stopGeneration();
        return;
    }

    const textarea = document.getElementById('chatTextarea');
    const prompt = textarea.value.trim();
    const modelSelect = document.getElementById('modelSelect');
    const selectedModel = modelSelect ? modelSelect.value : 'llama3:latest';

    if (!prompt && stagedFiles.length === 0) {
        return;
    }

    // Hide empty state if present
    const emptyState = document.getElementById('emptyState');
    if (emptyState) {
        emptyState.remove();
    }

    // Auto-create conversation if none is selected
    if (!activeConversationId) {
        try {
            const res = await fetch('/api/conversations/create/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken()
                },
                body: JSON.stringify({
                    title: prompt.slice(0, 30) || 'New Conversation',
                    model_name: selectedModel,
                    force: true
                })
            });
            const data = await res.json();
            activeConversationId = data.id;
            history.pushState(null, '', `/c/${data.id}/`);
            addNewChatToSidebar(data.id, data.title);
        } catch (e) {
            alert('Failed to initialize conversation: ' + e);
            return;
        }
    }

    // Update local header and sidebar title if it's currently a placeholder
    const currentHeader = document.getElementById('currentChatTitle');
    if (currentHeader && (currentHeader.textContent.trim() === 'New Chat' || currentHeader.textContent.trim() === 'New Conversation')) {
        const newTitle = prompt.split('\n')[0].slice(0, 35) + (prompt.length > 35 ? '...' : '');
        currentHeader.textContent = newTitle;
        if (activeConversationId) {
            const sideItem = document.getElementById(`chat-item-${activeConversationId}`);
            if (sideItem) {
                const titleSpan = sideItem.querySelector('.chat-item-title');
                if (titleSpan) {
                    titleSpan.textContent = newTitle;
                    titleSpan.title = newTitle;
                }
            }
        }
    }

    // Keep snapshot of staged files for this message
    const currentFiles = [...stagedFiles];
    stagedFiles = [];
    renderStagedFiles();

    // Append User Message to UI
    appendUserMessageToUI(prompt, currentFiles);
    textarea.value = '';
    autoResizeTextarea(textarea);

    // Create Assistant Message Placeholder
    const assistantRow = createAssistantMessagePlaceholder();
    const bubbleTarget = assistantRow.querySelector('.rendered-markdown');
    const metricsContainer = assistantRow.querySelector('.message-metrics-bar');

    // UI state: generating
    setGeneratingState(true);
    currentAbortController = new AbortController();

    let accumulatedText = '';
    const fileIds = currentFiles.map(f => f.id);

    try {
        const response = await fetch(`/api/conversations/${activeConversationId}/send/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify({
                prompt: prompt,
                model_name: selectedModel,
                file_ids: fileIds
            }),
            signal: currentAbortController.signal
        });

        if (!response.ok) {
            throw new Error(`Server returned status ${response.status}`);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder('utf-8');
        let buffer = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop(); // keep remainder

            for (const line of lines) {
                const trimmed = line.trim();
                if (!trimmed || !trimmed.startsWith('data: ')) continue;
                
                try {
                    const payload = JSON.parse(trimmed.slice(6));
                    
                    if (payload.chunk) {
                        accumulatedText += payload.chunk;
                        bubbleTarget.innerHTML = renderMarkdownText(accumulatedText);
                        scrollToBottom();
                    }

                    if (payload.done && payload.metrics) {
                        displayPerformanceTelemetry(metricsContainer, payload.metrics);
                    }
                } catch (jsonErr) {
                    // Ignore transient chunk parse errors
                }
            }
        }

        // Final render check
        bubbleTarget.innerHTML = renderMarkdownText(accumulatedText);
        bubbleTarget.dataset.raw = accumulatedText;

        // Bridge: Offer one-click Document Formulation Studio if prompt contains document intent
        const detectedDoc = detectDocumentIntent(prompt);
        if (detectedDoc && !bubbleTarget.parentElement.querySelector('.chat-doc-suggestion-card')) {
            const safePrompt = prompt.replace(/'/g, "\\'").replace(/"/g, '&quot;');
            const suggestionCard = document.createElement('div');
            suggestionCard.className = 'chat-doc-suggestion-card';
            suggestionCard.style.cssText = 'margin-top: 10px; padding: 10px 14px; background: rgba(15, 23, 42, 0.9); border: 1px solid #3b82f6; border-radius: 8px; display: flex; align-items: center; justify-content: space-between; gap: 12px;';
            suggestionCard.innerHTML = `
                <div style="display: flex; align-items: center; gap: 10px;">
                    <div style="width: 28px; height: 28px; border-radius: 6px; background: #1e3a8a; display: flex; align-items: center; justify-content: center; font-size: 14px;">📄</div>
                    <div>
                        <div style="font-size: 0.82rem; font-weight: 600; color: #f8fafc;">Military Document Archetype: ${escapeHtml(detectedDoc.label)}</div>
                        <div style="font-size: 0.72rem; color: #94a3b8;">Format, digitally sign, and export authentic A4 DOCX/PDF with AES-256.</div>
                    </div>
                </div>
                <button type="button" onclick="startDocumentCreation('${detectedDoc.type}', '${safePrompt}')" class="btn-sec-unlock" style="padding: 6px 14px; font-size: 0.75rem; white-space: nowrap; cursor: pointer;">Open Studio</button>
            `;
            bubbleTarget.parentElement.appendChild(suggestionCard);
            scrollToBottom();
        }

    } catch (err) {
        if (err.name === 'AbortError') {
            const finalTxt = accumulatedText + '\n\n*(Generation stopped by user)*';
            bubbleTarget.innerHTML = renderMarkdownText(finalTxt);
            bubbleTarget.dataset.raw = finalTxt;
        } else {
            const finalTxt = accumulatedText + `\n\n**Error:** ${err.message}`;
            bubbleTarget.innerHTML = renderMarkdownText(finalTxt);
            bubbleTarget.dataset.raw = finalTxt;
        }
    } finally {
        setGeneratingState(false);
        currentAbortController = null;
        scrollToBottom();
    }
}

function stopGeneration() {
    if (currentAbortController) {
        currentAbortController.abort();
    }
}

function setGeneratingState(generating) {
    isGenerating = generating;
    const sendBtn = document.getElementById('btnSend');
    if (!sendBtn) return;

    if (generating) {
        sendBtn.classList.add('btn-stop');
        sendBtn.title = "Stop generation";
        sendBtn.innerHTML = `
            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                <rect x="6" y="6" width="12" height="12" rx="2"></rect>
            </svg>
        `;
    } else {
        sendBtn.classList.remove('btn-stop');
        sendBtn.title = "Send Message";
        sendBtn.innerHTML = `
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <line x1="22" y1="2" x2="11" y2="13"></line>
                <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
            </svg>
        `;
    }
}

/* ==========================================================================
   UI DOM Helpers
   ========================================================================== */

function appendUserMessageToUI(content, files) {
    const wrapper = document.getElementById('messagesWrapper');
    const row = document.createElement('div');
    row.className = 'message-row user';

    let attachmentsHtml = '';
    if (files && files.length > 0) {
        attachmentsHtml = '<div class="bubble-attachments">';
        for (const f of files) {
            attachmentsHtml += `
                <div class="file-chip">
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                        <polyline points="14 2 14 8 20 8"></polyline>
                    </svg>
                    <span>${escapeHtml(f.name)}</span>
                    <span style="color:var(--text-muted)">(${escapeHtml(f.size)})</span>
                </div>
            `;
        }
        attachmentsHtml += '</div>';
    }

    row.innerHTML = `
        <div class="message-avatar">${window.USER_INITIAL || 'U'}</div>
        <div class="message-content-wrapper">
            ${attachmentsHtml}
            <div class="message-bubble">
                <p style="white-space: pre-wrap;">${escapeHtml(content)}</p>
            </div>
            <div class="message-actions-bar">
                <button type="button" class="btn-copy-msg" title="Copy complete message" onclick="copyCompleteMessage(this)">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                        <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                    </svg>
                    <span>Copy</span>
                </button>
            </div>
        </div>
    `;

    wrapper.appendChild(row);
    scrollToBottom();
}

function createAssistantMessagePlaceholder() {
    const wrapper = document.getElementById('messagesWrapper');
    const row = document.createElement('div');
    row.className = 'message-row assistant';

    row.innerHTML = `
        <div class="message-avatar"><span class="assistant-badge">AI</span></div>
        <div class="message-content-wrapper">
            <div class="message-bubble markdown-content">
                <div class="rendered-markdown">
                    <div class="typing-indicator">
                        <span class="typing-dot"></span>
                        <span class="typing-dot"></span>
                        <span class="typing-dot"></span>
                    </div>
                </div>
            </div>
            <div class="message-actions-bar">
                <button type="button" class="btn-copy-msg" title="Copy complete message" onclick="copyCompleteMessage(this)">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                        <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                    </svg>
                    <span>Copy</span>
                </button>
                <div class="message-metrics-bar"></div>
            </div>
        </div>
    `;

    wrapper.appendChild(row);
    scrollToBottom();
    return row;
}

function displayPerformanceTelemetry(container, metrics) {
    if (!container || !metrics) return;

    let html = '';
    if (metrics.total_time) {
        html += `<span class="metric-pill speed" title="Total response generation time">${metrics.total_time}s</span>`;
    }
    if (metrics.tokens_per_second) {
        html += `<span class="metric-pill speed" title="Generation speed">${metrics.tokens_per_second} tok/s</span>`;
    }
    if (metrics.eval_count) {
        html += `<span class="metric-pill" title="Tokens evaluated">${metrics.eval_count} tok</span>`;
    }
    if (metrics.load_time) {
        html += `<span class="metric-pill" title="Model load latency">load: ${metrics.load_time}s</span>`;
    }
    if (metrics.model) {
        html += `<span class="metric-pill model">${escapeHtml(metrics.model)}</span>`;
    }

    container.innerHTML = html;
}

/* ==========================================================================
   File Upload Handling
   ========================================================================== */

async function handleFileSelect(event) {
    const files = event.target.files;
    if (!files || files.length === 0) return;

    for (const file of files) {
        await uploadSingleFile(file);
    }
    event.target.value = ''; // Reset input
}

async function uploadSingleFile(file) {
    const formData = new FormData();
    formData.append('file', file);
    if (activeConversationId) {
        formData.append('conversation_id', activeConversationId);
    }

    // Temporary placeholder badge
    const tempId = 'temp-' + Date.now();
    stagedFiles.push({
        id: tempId,
        name: file.name,
        size: 'Uploading...',
        isUploading: true
    });
    renderStagedFiles();

    try {
        const response = await fetch('/api/upload/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCsrfToken()
            },
            body: formData
        });

        const data = await response.json();
        if (response.ok) {
            // Replace placeholder with saved file
            const idx = stagedFiles.findIndex(f => f.id === tempId);
            if (idx !== -1) {
                stagedFiles[idx] = {
                    id: data.id,
                    name: data.name,
                    size: data.size,
                    preview: data.preview,
                    charCount: data.char_count
                };
            }
        } else {
            alert('File upload failed: ' + (data.error || 'Unknown error'));
            stagedFiles = stagedFiles.filter(f => f.id !== tempId);
        }
    } catch (e) {
        alert('File upload failed: ' + e);
        stagedFiles = stagedFiles.filter(f => f.id !== tempId);
    }

    renderStagedFiles();
}

function renderStagedFiles() {
    const bar = document.getElementById('stagedFilesBar');
    if (!bar) return;

    if (stagedFiles.length === 0) {
        bar.innerHTML = '';
        return;
    }

    let html = '';
    stagedFiles.forEach((f, idx) => {
        let statusBadge = '';
        if (f.isUploading) {
            statusBadge = '<span style="color:var(--text-muted); font-size:0.75rem;">Uploading...</span>';
        } else if (f.charCount > 0) {
            statusBadge = `<span style="color:#10b981; font-size:0.75rem; font-weight:600;">✓ ${f.charCount.toLocaleString()} chars</span>`;
        } else {
            statusBadge = '<span style="color:#f59e0b; font-size:0.75rem;" title="No selectable text found (image scan)">⚠️ 0 text chars</span>';
        }

        const tooltip = f.preview ? `Extracted preview:\n${f.preview}` : f.name;

        html += `
            <div class="staged-file-badge" title="${escapeHtml(tooltip)}">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#3b82f6" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                    <polyline points="14 2 14 8 20 8"></polyline>
                </svg>
                <span>${escapeHtml(f.name)} (${escapeHtml(f.size)})</span>
                ${statusBadge}
                <button type="button" class="btn-remove-staged-file" onclick="removeStagedFile(${idx})" title="Remove attachment">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <line x1="18" y1="6" x2="6" y2="18"></line>
                        <line x1="6" y1="6" x2="18" y2="18"></line>
                    </svg>
                </button>
            </div>
        `;
    });

    bar.innerHTML = html;
}

function removeStagedFile(index) {
    stagedFiles.splice(index, 1);
    renderStagedFiles();
}

function setupDragAndDrop() {
    const dropArea = document.querySelector('.chat-workspace');
    if (!dropArea) return;

    ['dragenter', 'dragover'].forEach(eventName => {
        dropArea.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropArea.style.border = '2px dashed #3b82f6';
        }, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropArea.style.border = 'none';
        }, false);
    });

    dropArea.addEventListener('drop', (e) => {
        const dt = e.dataTransfer;
        const files = dt.files;
        if (files && files.length > 0) {
            for (const file of files) {
                uploadSingleFile(file);
            }
        }
    });
}

/* ==========================================================================
   Conversations & Model Management
   ========================================================================== */

function setupEventHandlers() {
    // New chat button
    const btnNewChat = document.getElementById('btnNewChat');
    if (btnNewChat) {
        btnNewChat.addEventListener('click', (e) => {
            e.preventDefault();
            startNewConversation();
        });
    }

    // Refresh models button
    const btnRefreshModels = document.getElementById('btnRefreshModels');
    if (btnRefreshModels) {
        btnRefreshModels.addEventListener('click', refreshOllamaModels);
    }

    // Global click listener: clicking outside cancels any active inline rename or delete confirmation
    document.addEventListener('click', (e) => {
        if (!e.target.closest('.chat-item-inline-edit') && !e.target.closest('.chat-item-delete-confirm') && !e.target.closest('.btn-icon-sm')) {
            cancelAllInlineActions();
        }
    });
}

function handleChatItemClick(event, url) {
    // If clicking on an input or inline action button, do not navigate
    if (event.target.closest('.chat-item-inline-edit') || event.target.closest('.chat-item-delete-confirm') || event.target.closest('.chat-item-actions')) {
        return;
    }
    const item = event.currentTarget;
    if (item && (item.classList.contains('inline-editing') || item.classList.contains('inline-deleting'))) {
        return;
    }
    window.location.href = url;
}
window.handleChatItemClick = handleChatItemClick;

function cancelAllInlineActions() {
    // Restore any inline editing
    document.querySelectorAll('.chat-item.inline-editing').forEach(item => {
        const id = item.id.replace('chat-item-', '');
        cancelInlineRename(null, id);
    });
    // Restore any inline delete confirmations
    document.querySelectorAll('.chat-item.inline-deleting').forEach(item => {
        const id = item.id.replace('chat-item-', '');
        cancelInlineDelete(null, id);
    });
}

/* --- Inline Rename (Happens in place in sidebar) --- */

function startInlineRename(event, id) {
    if (event) {
        event.preventDefault();
        event.stopPropagation();
    }
    cancelAllInlineActions();

    const item = document.getElementById(`chat-item-${id}`);
    if (!item) return;

    const titleSpan = item.querySelector('.chat-item-title');
    const currentTitle = titleSpan ? titleSpan.textContent.trim() : 'Conversation';

    item.dataset.originalTitle = currentTitle;
    item.classList.add('inline-editing');

    item.innerHTML = `
        <div class="chat-item-inline-edit" onclick="event.stopPropagation()">
            <input type="text" class="chat-rename-input" id="rename-input-${id}" value="${escapeHtml(currentTitle)}" maxlength="100" />
            <button type="button" class="btn-inline-action btn-inline-save" title="Save" onclick="saveInlineRename(event, '${id}')">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                    <polyline points="20 6 9 17 4 12"></polyline>
                </svg>
            </button>
            <button type="button" class="btn-inline-action btn-inline-cancel" title="Cancel" onclick="cancelInlineRename(event, '${id}')">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                    <line x1="18" y1="6" x2="6" y2="18"></line>
                    <line x1="6" y1="6" x2="18" y2="18"></line>
                </svg>
            </button>
        </div>
    `;

    const input = document.getElementById(`rename-input-${id}`);
    if (input) {
        input.focus();
        input.select();
        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                saveInlineRename(e, id);
            } else if (e.key === 'Escape') {
                e.preventDefault();
                cancelInlineRename(e, id);
            }
        });
    }
}
window.startInlineRename = startInlineRename;

async function saveInlineRename(event, id) {
    if (event) {
        event.preventDefault();
        event.stopPropagation();
    }
    const item = document.getElementById(`chat-item-${id}`);
    if (!item) return;

    const input = document.getElementById(`rename-input-${id}`);
    const newTitle = input ? input.value.trim() : '';
    const originalTitle = item.dataset.originalTitle || 'Conversation';

    if (!newTitle || newTitle === originalTitle) {
        cancelInlineRename(event, id);
        return;
    }

    try {
        const res = await fetch(`/api/conversations/${id}/rename/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify({ title: newTitle })
        });

        if (res.ok) {
            const data = await res.json();
            renderNormalChatItem(item, id, data.title);
            if (activeConversationId === id) {
                const headerTitle = document.getElementById('currentChatTitle');
                if (headerTitle) headerTitle.textContent = data.title;
                document.title = `${data.title} - Sarvatra AI`;
            }
        } else {
            const errData = await res.json().catch(() => ({}));
            alert('Rename failed: ' + (errData.message || res.statusText));
            cancelInlineRename(event, id);
        }
    } catch (e) {
        alert('Rename failed: ' + e);
        cancelInlineRename(event, id);
    }
}
window.saveInlineRename = saveInlineRename;

function cancelInlineRename(event, id) {
    if (event) {
        event.preventDefault();
        event.stopPropagation();
    }
    const item = document.getElementById(`chat-item-${id}`);
    if (!item) return;
    const title = item.dataset.originalTitle || 'Conversation';
    renderNormalChatItem(item, id, title);
}
window.cancelInlineRename = cancelInlineRename;

/* --- Inline Delete (Nearby delete button, no browser prompt) --- */

function startInlineDelete(event, id) {
    if (event) {
        event.preventDefault();
        event.stopPropagation();
    }
    cancelAllInlineActions();

    const item = document.getElementById(`chat-item-${id}`);
    if (!item) return;

    const titleSpan = item.querySelector('.chat-item-title');
    const title = titleSpan ? titleSpan.textContent.trim() : 'Conversation';
    item.dataset.originalTitle = title;

    item.classList.add('inline-deleting');

    // Replace the actions area with an inline confirmation bar right next to the delete button
    const actionsArea = item.querySelector('.chat-item-actions');
    if (actionsArea) {
        actionsArea.style.display = 'flex';
        actionsArea.innerHTML = `
            <div class="chat-item-delete-confirm" onclick="event.stopPropagation()">
                <span class="delete-confirm-label">Delete?</span>
                <button type="button" class="btn-inline-action btn-inline-delete" title="Confirm Delete" onclick="confirmInlineDelete(event, '${id}')">
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                        <polyline points="20 6 9 17 4 12"></polyline>
                    </svg>
                </button>
                <button type="button" class="btn-inline-action btn-inline-cancel" title="Cancel" onclick="cancelInlineDelete(event, '${id}')">
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                        <line x1="18" y1="6" x2="6" y2="18"></line>
                        <line x1="6" y1="6" x2="18" y2="18"></line>
                    </svg>
                </button>
            </div>
        `;
    }
}
window.startInlineDelete = startInlineDelete;

async function confirmInlineDelete(event, id) {
    if (event) {
        event.preventDefault();
        event.stopPropagation();
    }
    const item = document.getElementById(`chat-item-${id}`);

    try {
        const res = await fetch(`/api/conversations/${id}/delete/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            }
        });

        if (res.ok) {
            if (item) item.remove();
            if (activeConversationId === id) {
                window.location.href = '/';
            } else {
                const nav = document.getElementById('conversationsNav');
                if (nav && nav.querySelectorAll('.chat-item').length === 0) {
                    const notice = document.createElement('div');
                    notice.className = 'no-chats-notice';
                    notice.style.cssText = 'padding: 16px; color: var(--text-muted); font-size: 0.85rem; text-align: center;';
                    notice.textContent = 'No chats yet. Start a new one!';
                    nav.appendChild(notice);
                }
            }
        } else {
            const errData = await res.json().catch(() => ({}));
            alert('Delete failed: ' + (errData.message || res.statusText));
            cancelInlineDelete(event, id);
        }
    } catch (e) {
        alert('Delete failed: ' + e);
        cancelInlineDelete(event, id);
    }
}
window.confirmInlineDelete = confirmInlineDelete;

function cancelInlineDelete(event, id) {
    if (event) {
        event.preventDefault();
        event.stopPropagation();
    }
    const item = document.getElementById(`chat-item-${id}`);
    if (!item) return;

    item.classList.remove('inline-deleting');
    const titleSpan = item.querySelector('.chat-item-title');
    const title = titleSpan ? titleSpan.textContent.trim() : (item.dataset.originalTitle || 'Conversation');
    renderNormalChatItem(item, id, title);
}
window.cancelInlineDelete = cancelInlineDelete;

function renderNormalChatItem(item, id, title) {
    item.classList.remove('inline-editing');
    item.classList.remove('inline-deleting');
    item.innerHTML = `
        <span class="chat-item-title" title="${escapeHtml(title)}">${escapeHtml(title)}</span>
        <div class="chat-item-actions">
            <button type="button" class="btn-icon-sm rename-chat-btn" data-id="${id}" title="Rename" onclick="startInlineRename(event, '${id}')">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M17 3a2.828 2.828 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5L17 3z"></path>
                </svg>
            </button>
            <button type="button" class="btn-icon-sm delete delete-chat-btn" data-id="${id}" title="Delete" onclick="startInlineDelete(event, '${id}')">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <polyline points="3 6 5 6 21 6"></polyline>
                    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                </svg>
            </button>
        </div>
    `;
}

async function startNewConversation() {
    if (isGenerating) {
        stopGeneration();
    }

    // Reset any staged attachments
    stagedFiles = [];
    renderStagedFiles();

    const btnNewChat = document.getElementById('btnNewChat');
    if (btnNewChat) {
        btnNewChat.style.opacity = '0.6';
        btnNewChat.style.pointerEvents = 'none';
    }

    // Check if we are already in an empty conversation (no messages)
    const existingMessages = document.querySelectorAll('.message-row');
    if (activeConversationId && existingMessages.length === 0) {
        const ta = document.getElementById('chatTextarea');
        if (ta) {
            ta.value = '';
            ta.focus();
        }
        if (btnNewChat) {
            btnNewChat.style.opacity = '1';
            btnNewChat.style.pointerEvents = 'auto';
        }
        return;
    }

    const modelSelect = document.getElementById('modelSelect');
    const selectedModel = modelSelect ? modelSelect.value : 'llama3:latest';

    try {
        const res = await fetch('/api/conversations/create/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify({
                title: 'New Conversation',
                model_name: selectedModel
            })
        });

        if (res.ok) {
            const data = await res.json();
            if (data && data.id) {
                window.location.href = `/c/${data.id}/`;
                return;
            }
        }
    } catch (e) {
        console.error('Error creating conversation:', e);
    } finally {
        if (btnNewChat) {
            btnNewChat.style.opacity = '1';
            btnNewChat.style.pointerEvents = 'auto';
        }
    }

    // Fallback: navigate to home
    window.location.href = '/';
}
window.startNewConversation = startNewConversation;

async function refreshOllamaModels() {
    const btn = document.getElementById('btnRefreshModels');
    if (btn) btn.style.transform = 'rotate(180deg)';

    try {
        const res = await fetch('/api/models/');
        const data = await res.json();

        // Update dropdown
        const select = document.getElementById('modelSelect');
        const currentVal = select.value;
        select.innerHTML = '';

        if (data.models && data.models.length > 0) {
            data.models.forEach(m => {
                const opt = document.createElement('option');
                opt.value = m;
                opt.textContent = m;
                if (m === currentVal) opt.selected = true;
                select.appendChild(opt);
            });
        } else {
            const opt = document.createElement('option');
            opt.value = 'llama3:latest';
            opt.textContent = 'No models detected';
            select.appendChild(opt);
        }

        // Update status badge
        const badge = document.getElementById('ollamaStatusBadge');
        const text = document.getElementById('ollamaStatusText');
        if (badge && text) {
            if (data.healthy) {
                badge.className = 'status-indicator status-online';
                text.textContent = 'Local Online';
            } else {
                badge.className = 'status-indicator status-offline';
                text.textContent = 'Offline';
            }
        }

    } catch (e) {
        console.error('Failed to reload models', e);
    } finally {
        if (btn) {
            setTimeout(() => { btn.style.transform = 'none'; }, 300);
        }
    }
}

function addNewChatToSidebar(id, title) {
    const nav = document.getElementById('conversationsNav');
    if (!nav) return;

    // Remove empty notice if present
    const emptyNotice = nav.querySelector('.no-chats-notice');
    if (emptyNotice) {
        emptyNotice.remove();
    }

    const item = document.createElement('div');
    item.className = 'chat-item active';
    item.id = `chat-item-${id}`;
    item.style.cursor = 'pointer';
    item.onclick = (e) => { handleChatItemClick(e, `/c/${id}/`); };
    renderNormalChatItem(item, id, title);

    // Remove active class from others
    nav.querySelectorAll('.chat-item').forEach(i => i.classList.remove('active'));

    const sectionTitle = nav.querySelector('.nav-section-title');
    if (sectionTitle && sectionTitle.nextSibling) {
        nav.insertBefore(item, sectionTitle.nextSibling);
    } else {
        nav.appendChild(item);
    }
}

/* ==========================================================================
   Utilities
   ========================================================================== */

function handleTextareaKeydown(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
    }
}

function autoResizeTextarea(textarea) {
    textarea.style.height = 'auto';
    textarea.style.height = Math.min(textarea.scrollHeight, 200) + 'px';
}

function setPrompt(text) {
    const ta = document.getElementById('chatTextarea');
    if (ta) {
        ta.value = text;
        autoResizeTextarea(ta);
        ta.focus();
    }
}

function scrollToBottom() {
    const container = document.getElementById('messagesContainer');
    if (container) {
        container.scrollTop = container.scrollHeight;
    }
}

function setupCopyButtonDelegation() {
    // Document-level event delegation for Copy Buttons (Code, Table, Message)
    document.addEventListener('click', (e) => {
        // Copy Code button
        const copyCodeBtn = e.target.closest('.btn-copy-code');
        if (copyCodeBtn) {
            e.preventDefault();
            e.stopPropagation();
            const wrapper = copyCodeBtn.closest('.code-block-wrapper');
            if (wrapper) {
                const codeEl = wrapper.querySelector('pre code') || wrapper.querySelector('pre');
                if (codeEl) copyToClipboard(codeEl.textContent, copyCodeBtn);
            }
            return;
        }

        // Copy Table button
        const copyTableBtn = e.target.closest('.btn-copy-table');
        if (copyTableBtn) {
            e.preventDefault();
            e.stopPropagation();
            const wrapper = copyTableBtn.closest('.table-block-wrapper');
            if (wrapper) {
                const table = wrapper.querySelector('table');
                if (table) copyTableData(table, copyTableBtn);
            }
            return;
        }

        // Copy Message button
        const copyMsgBtn = e.target.closest('.btn-copy-msg');
        if (copyMsgBtn) {
            e.preventDefault();
            e.stopPropagation();
            copyCompleteMessage(copyMsgBtn);
            return;
        }
    });
}

function escapeHtml(text) {
    if (!text) return '';
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.toString().replace(/[&<>"']/g, m => map[m]);
}


/* ==========================================================================
   Document Creation Agent Engine (Option Picking & 1-LLM DOCX Generation)
   ========================================================================== */

let currentDocType = 'formal_letter';
let currentDocSession = null;
let currentGeneratedDocId = null;
let currentDocIsLocked = false;
let currentDocLockHint = '';
let currentDocEncryptExport = false;
let pendingUnlockDocId = null;
let activeSessionPasscode = '';

let isDocumentDirty = false;
let paperAutoSaveTimer = null;

function getDocTypeSvg(type) {
    switch (type) {
        case 'formal_letter':
            return '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"></path><polyline points="22,6 12,13 2,6"></polyline></svg>';
        case 'office_memo':
            return '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"></path><rect x="8" y="2" width="8" height="4" rx="1" ry="1"></rect></svg>';
        case 'meeting_minutes':
            return '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect><line x1="16" y1="2" x2="16" y2="6"></line><line x1="8" y1="2" x2="8" y2="6"></line><line x1="3" y1="10" x2="21" y2="10"></line></svg>';
        case 'office_note':
            return '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line></svg>';
        case 'office_order':
            return '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path></svg>';
        case 'technical_report':
            return '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"></path><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"></path></svg>';
        default:
            return '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline></svg>';
    }
}

const CLASSIFICATION_LEVELS = [
    { key: 'NONE', label: 'NONE', btnClass: 'class-none', stampClass: 'stamp-none' },
    { key: 'CONFIDENTIAL', label: 'CONFIDENTIAL', btnClass: 'class-confidential', stampClass: 'stamp-confidential' },
    { key: 'RESTRICTED', label: 'RESTRICTED', btnClass: 'class-restricted', stampClass: 'stamp-restricted' },
    { key: 'SECRET', label: 'SECRET', btnClass: 'class-secret', stampClass: 'stamp-secret' },
    { key: 'UNCLASSIFIED', label: 'UNCLASSIFIED', btnClass: 'class-unclassified', stampClass: 'stamp-unclassified' }
];

let currentClassification = 'NONE';

function cycleClassification() {
    const currentIndex = CLASSIFICATION_LEVELS.findIndex(c => c.key === currentClassification);
    const nextIndex = (currentIndex + 1) % CLASSIFICATION_LEVELS.length;
    currentClassification = CLASSIFICATION_LEVELS[nextIndex].key;
    applyClassificationState();
}

function setClassification(levelKey) {
    const target = CLASSIFICATION_LEVELS.find(c => c.key === levelKey);
    if (target) {
        currentClassification = target.key;
    } else {
        currentClassification = 'NONE';
    }
    applyClassificationState();
}

function applyClassificationState() {
    const current = CLASSIFICATION_LEVELS.find(c => c.key === currentClassification) || CLASSIFICATION_LEVELS[0];
    const btn = document.getElementById('btnToggleClass');
    const textEl = document.getElementById('currentClassText');
    const selectEl = document.getElementById('selectClassification');

    if (textEl) {
        textEl.textContent = current.label;
    }

    if (btn) {
        btn.className = `studio-class-btn ${current.btnClass}`;
        btn.setAttribute('title', `Active: ${current.label} (Click to toggle)`);
    }

    if (selectEl && selectEl.value !== current.key) {
        selectEl.value = current.key;
    }

    // Update Paper sheet stamps (Hide completely if NONE)
    const topStamp = document.getElementById('docPaperClassTop');
    const bottomStamp = document.getElementById('docPaperClassBottom');
    [topStamp, bottomStamp].forEach(el => {
        if (el) {
            if (current.key === 'NONE') {
                el.style.display = 'none';
                el.textContent = '';
            } else {
                el.style.display = '';
                el.textContent = current.label;
                el.className = `paper-classified-badge ${current.stampClass}`;
            }
        }
    });
}

function triggerStudioDatePicker(e) {
    const picker = document.getElementById('formDatePicker');
    if (!picker) return;
    if (typeof picker.showPicker === 'function') {
        try {
            picker.showPicker();
            return;
        } catch (err) {}
    }
    picker.focus();
}

function handleDatePickerClick(e) {
    const picker = e.target || document.getElementById('formDatePicker');
    if (picker && typeof picker.showPicker === 'function') {
        try {
            picker.showPicker();
        } catch (err) {}
    }
}

function syncDateToPicker(dateStr) {
    if (!dateStr) return;
    const picker = document.getElementById('formDatePicker');
    if (!picker) return;
    const clean = dateStr.trim();
    if (/^\d{4}-\d{2}-\d{2}$/.test(clean)) {
        picker.value = clean;
        return;
    }
    const months = { jan: '01', feb: '02', mar: '03', apr: '04', may: '05', jun: '06', jul: '07', aug: '08', sep: '09', oct: '10', nov: '11', dec: '12' };
    const match = clean.match(/^(\d{1,2})\s+([A-Za-z]{3})\s+(\d{4})$/);
    if (match) {
        const d = match[1].padStart(2, '0');
        const m = months[match[2].toLowerCase()] || '01';
        const y = match[3];
        picker.value = `${y}-${m}-${d}`;
    }
}

function onDateSelected(isoValue) {
    if (!isoValue) return;
    const parts = isoValue.split('-');
    if (parts.length === 3) {
        const year = parts[0];
        const monthIndex = parseInt(parts[1], 10) - 1;
        const day = parts[2];
        const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
        const formatted = `${day} ${months[monthIndex]} ${year}`;
        const displayText = document.getElementById('formDateText');
        const hiddenInput = document.getElementById('formDate');
        const paperDate = document.getElementById('docPaperDate');
        const paperSignDate = document.getElementById('docPaperSignDate');

        if (displayText) displayText.textContent = formatted;
        if (hiddenInput) hiddenInput.value = formatted;
        if (paperDate) paperDate.textContent = formatted;
        if (paperSignDate) paperSignDate.textContent = formatted;

        if (typeof saveDocumentContentChanges === 'function' && typeof currentGeneratedDocId !== 'undefined' && currentGeneratedDocId) {
            saveDocumentContentChanges();
        }
    }
}

window.setClassification = setClassification;
window.cycleClassification = cycleClassification;
window.onDateSelected = onDateSelected;
window.triggerStudioDatePicker = triggerStudioDatePicker;
window.handleDatePickerClick = handleDatePickerClick;
window.syncDateToPicker = syncDateToPicker;
window.autoExpandTextarea = autoExpandTextarea;
window.resetStudioScroll = resetStudioScroll;
window.updateRegenerateButtonLabel = updateRegenerateButtonLabel;
window.handleDocumentRegenerate = handleDocumentRegenerate;
window.handleDocumentDownload = handleDocumentDownload;
window.handleDocumentPdfDownload = handleDocumentPdfDownload;
window.switchModalDocType = switchModalDocType;
window.openDocumentPickerModal = openDocumentPickerModal;
window.closeDocumentModal = closeDocumentModal;

function autoExpandTextarea(el) {
    if (!el) return;
    el.style.height = 'auto';
    const newHeight = Math.max(el.scrollHeight, 72);
    if (newHeight > 280) {
        el.style.height = '280px';
        el.style.overflowY = 'auto';
    } else {
        el.style.height = `${newHeight}px`;
        el.style.overflowY = 'hidden';
    }
}

function resetStudioScroll() {
    const modalBody = document.querySelector('.doc-modal-body');
    if (modalBody) modalBody.scrollLeft = 0;
    const studioGrid = document.querySelector('.studio-grid');
    if (studioGrid) studioGrid.scrollLeft = 0;
    const formCard = document.querySelector('.studio-form-card');
    if (formCard) formCard.scrollLeft = 0;
    const canvasWrap = document.querySelector('.studio-canvas-wrapper');
    if (canvasWrap) canvasWrap.scrollLeft = 0;
}

const DOC_DEFINITIONS = {
    formal_letter: {
        title: 'Formal Military Letter',
        required: [
            { name: 'to_name', label: 'To', placeholder: 'Recipient designation...' },
            { name: 'subject', label: 'Subject', placeholder: 'Official subject line...' },
            { name: 'key_points', label: 'Directives', type: 'textarea', placeholder: 'Enter directives or key bullet points...' }
        ],
        optional: [
            { name: 'cc_list', label: 'Copy to', placeholder: 'Copy to...' },
            { name: 'enclosures', label: 'Enclosures', placeholder: 'List enclosures...' }
        ]
    },
    office_memo: {
        title: 'Office Memorandum',
        required: [
            { name: 'to', label: 'To', placeholder: 'Branch / personnel...' },
            { name: 'subject', label: 'Subject', placeholder: 'Subject line...' },
            { name: 'key_points', label: 'Directives', type: 'textarea', placeholder: 'Enter memorandum directives...' }
        ],
        optional: [
            { name: 'action_required', label: 'Action Required', placeholder: 'Required action...' }
        ]
    },
    meeting_minutes: {
        title: 'Minutes of Meeting',
        required: [
            { name: 'meeting_title', label: 'Meeting Title', placeholder: 'Meeting title...' },
            { name: 'venue', label: 'Venue', placeholder: 'Venue location...' },
            { name: 'chairperson', label: 'Chairperson', placeholder: 'Chairperson name & rank...' },
            { name: 'attendees', label: 'Attendees', placeholder: 'Attendees list...' },
            { name: 'agenda_items', label: 'Discussions & Resolutions', type: 'textarea', placeholder: 'Record discussion points & decisions...' }
        ],
        optional: [
            { name: 'action_items', label: 'Action Items', type: 'textarea', placeholder: 'Action items & responsible officers...' },
            { name: 'next_meeting', label: 'Next Meeting', placeholder: 'Next meeting date...' }
        ]
    },
    office_note: {
        title: 'Office Note',
        required: [
            { name: 'subject', label: 'Subject', placeholder: 'Subject of proposal...' },
            { name: 'key_points', label: 'Justification & Proposal', type: 'textarea', placeholder: 'Brief background, justification & proposal...' }
        ],
        optional: [
            { name: 'references', label: 'References', placeholder: 'Reference files...' }
        ]
    },
    office_order: {
        title: 'Office Order',
        required: [
            { name: 'subject', label: 'Subject', placeholder: 'Order subject...' },
            { name: 'authority', label: 'Authority', placeholder: 'Reference order / authority...' },
            { name: 'key_points', label: 'Order Directives', type: 'textarea', placeholder: 'Order directives & instructions...' }
        ],
        optional: [
            { name: 'effective_date', label: 'Effective Date', placeholder: 'Effective date...' },
            { name: 'distribution', label: 'Distribution List', placeholder: 'Distribution list...' }
        ]
    },
    technical_report: {
        title: 'Technical Report',
        required: [
            { name: 'title', label: 'Report Title', placeholder: 'Report title...' },
            { name: 'key_points', label: 'Technical Content', type: 'textarea', placeholder: 'Enter technical assessment & findings...' }
        ],
        optional: [
            { name: 'abstract', label: 'Executive Summary', type: 'textarea', placeholder: 'Executive summary...' }
        ]
    }
};

function openDocumentPickerModal() {
    loadSignatureAssets();
    startDocumentCreation('formal_letter');
    setTimeout(resetStudioScroll, 50);
}

function closeDocumentModal(e) {
    if (e && e.target !== e.currentTarget && !e.target.classList.contains('doc-modal-close') && !e.target.classList.contains('btn-modal-cancel')) {
        return;
    }
    const overlay = document.getElementById('documentModalOverlay');
    if (overlay) overlay.classList.remove('active');
}

const ARCHETYPE_FORM_CODES = {
    formal_letter: 'Form: LTR-MIL',
    office_memo: 'Form: MEMO-MIL',
    meeting_minutes: 'Form: MOM-CONF',
    office_note: 'Form: NOTE-SHEET',
    office_order: 'Form: ORDER-GEN',
    technical_report: 'Form: TECH-REP'
};

function switchModalDocType(docType, preserveDoc = false) {
    currentDocType = docType;
    resetStudioScroll();

    if (!preserveDoc) {
        currentGeneratedDocId = null;
        isDocumentDirty = false;
        currentDocIsLocked = false;
        currentDocLockHint = '';
        currentDocEncryptExport = false;
        activeSessionPasscode = '';
        updateStudioLockState(false, false);
    }
    
    // Update pill buttons
    document.querySelectorAll('.doc-type-selector-pills .pill-btn').forEach(btn => {
        if (btn.getAttribute('data-type') === docType) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });

    const def = DOC_DEFINITIONS[docType] || DOC_DEFINITIONS.formal_letter;
    const modalIcon = document.getElementById('docModalIcon');
    const modalTitle = document.getElementById('docModalTitle');
    const formTag = document.getElementById('docFormTag');

    if (modalIcon) modalIcon.innerHTML = getDocTypeSvg(docType);
    if (modalTitle) modalTitle.textContent = def.title;
    if (formTag) formTag.textContent = ARCHETYPE_FORM_CODES[docType] || 'Form: MIL-STD';

    if (!preserveDoc) {
        // Reset status badges
        const saveStatus = document.getElementById('paperSaveStatus');
        if (saveStatus) {
            saveStatus.textContent = 'Draft Ready';
            saveStatus.classList.remove('dirty');
        }
        const sizeBadge = document.getElementById('downloadFileSizeBadge');
        if (sizeBadge) sizeBadge.textContent = 'Draft';
        const metaEl = document.getElementById('docResultMeta');
        if (metaEl) metaEl.textContent = '';
    }

    renderModalFields(def);

    if (!preserveDoc) {
        // Render fresh blank draft formulation sheet (no fake prebuilt text)
        const container = document.getElementById('docPreviewContainer');
        if (container) {
            const dummyDoc = {
                doc_type: docType,
                title: def.title,
                generated_content: ''
            };
            const fields = collectCurrentFormFields();
            container.innerHTML = renderDocumentPaperPreview(dummyDoc, fields);
        }
    }

    setupLivePreviewSync();
    const commentInput = document.getElementById('docRegenerateComment');
    if (commentInput) commentInput.value = '';
    updateRegenerateButtonLabel();
    applyClassificationState();
    setTimeout(resetStudioScroll, 20);
}

function renderModalFields(def) {
    const container = document.getElementById('dynamicFormFields');
    if (!container) return;
    container.innerHTML = '';

    // Render required fields
    def.required.forEach(field => {
        const group = document.createElement('div');
        group.className = 'form-group';

        const label = document.createElement('label');
        label.className = 'doc-label';
        label.innerHTML = `${escapeHtml(field.label)} <span class="req">*</span>`;

        let input;
        if (field.type === 'textarea') {
            input = document.createElement('textarea');
            input.className = 'doc-textarea';
            input.rows = 2;
            input.addEventListener('input', function() {
                autoExpandTextarea(this);
            });
            setTimeout(() => autoExpandTextarea(input), 15);
        } else {
            input = document.createElement('input');
            input.type = 'text';
            input.className = 'doc-input';
        }
        input.name = field.name;
        input.id = `doc_field_${field.name}`;
        input.placeholder = field.placeholder || '';
        input.required = true;

        group.appendChild(label);
        group.appendChild(input);
        container.appendChild(group);
    });

    // Render optional fields
    const optContainer = document.getElementById('dynamicOptionalFields');
    if (optContainer) {
        optContainer.innerHTML = '';
        if (def.optional && def.optional.length > 0) {
            def.optional.forEach(field => {
                const group = document.createElement('div');
                group.className = 'form-group';

                const label = document.createElement('label');
                label.className = 'doc-label';
                label.textContent = field.label;

                let input;
                if (field.type === 'textarea') {
                    input = document.createElement('textarea');
                    input.className = 'doc-textarea';
                    input.rows = 2;
                    input.addEventListener('input', function() {
                        autoExpandTextarea(this);
                    });
                    setTimeout(() => autoExpandTextarea(input), 15);
                } else {
                    input = document.createElement('input');
                    input.type = 'text';
                    input.className = 'doc-input';
                }
                input.name = field.name;
                input.id = `doc_field_${field.name}`;
                input.placeholder = field.placeholder || '';

                group.appendChild(label);
                group.appendChild(input);
                optContainer.appendChild(group);
            });
        }
    }
}

function toggleOptionalFields() {
    const wrap = document.getElementById('dynamicOptionalFields');
    const icon = document.getElementById('optionalToggleIcon');
    if (!wrap) return;
    if (wrap.style.display === 'none') {
        wrap.style.display = 'flex';
        if (icon) {
            icon.textContent = '▲';
            icon.style.transform = 'rotate(180deg)';
        }
    } else {
        wrap.style.display = 'none';
        if (icon) {
            icon.textContent = '▼';
            icon.style.transform = 'rotate(0deg)';
        }
    }
}

function toggleSignatoryFields() {
    const wrap = document.getElementById('dynamicSignatoryFields');
    const icon = document.getElementById('signatoryToggleIcon');
    if (!wrap) return;
    if (wrap.style.display === 'none') {
        wrap.style.display = 'block';
        if (icon) {
            icon.textContent = '▲';
            icon.style.transform = 'rotate(180deg)';
        }
    } else {
        wrap.style.display = 'none';
        if (icon) {
            icon.textContent = '▼';
            icon.style.transform = 'rotate(0deg)';
        }
    }
}
window.toggleSignatoryFields = toggleSignatoryFields;

function collectCurrentFormFields() {
    const fields = {};
    const refInput = document.getElementById('formRefNo');
    const dateInput = document.getElementById('formDate');
    if (refInput && refInput.value) fields.reference_number = refInput.value.trim();
    if (dateInput && dateInput.value) fields.date = dateInput.value.trim();
    fields.classification = currentClassification;

    const form = document.getElementById('docGeneratorForm');
    if (form) {
        const fd = new FormData(form);
        for (const [k, v] of fd.entries()) {
            if (v && v.trim().length > 0) fields[k] = v.trim();
        }
    }

    // Explicitly read signatory & station fields
    const fromNameInput = document.getElementById('doc_field_from_name');
    if (fromNameInput && fromNameInput.value) fields.from_name = fromNameInput.value.trim();

    const fromRankInput = document.getElementById('doc_field_from_rank');
    if (fromRankInput && fromRankInput.value) fields.from_rank = fromRankInput.value.trim();

    const fromAppInput = document.getElementById('doc_field_from_appointment');
    if (fromAppInput && fromAppInput.value) fields.from_appointment = fromAppInput.value.trim();

    const fromAuthInput = document.getElementById('doc_field_from_authority');
    if (fromAuthInput && fromAuthInput.value) fields.from_authority = fromAuthInput.value.trim();

    const deptInput = document.getElementById('doc_field_from_department');
    if (deptInput && deptInput.value) fields.from_department = deptInput.value.trim();

    const stationInput = document.getElementById('doc_field_station');
    if (stationInput && stationInput.value) fields.station = stationInput.value.trim();

    if (currentDocSession && currentDocSession.auto_filled) {
        for (const [k, v] of Object.entries(currentDocSession.auto_filled)) {
            if (!fields[k]) fields[k] = v;
        }
    }

    if (!fields.from_name && window.USER_NAME) fields.from_name = window.USER_NAME;
    if (!fields.from_department) fields.from_department = window.USER_DEPT || 'Combat Engineering Wing';
    if (!fields.from_employee_id) fields.from_employee_id = window.USER_EMP_ID || 'EMP-001';

    fields.signature_style = currentPreviewSigStyle || window.USER_SIG_STYLE || 'military';
    const sigAssetVal = activeSignatureAssetId || document.getElementById('doc_field_signature_asset')?.value || '';
    if (sigAssetVal === 'none') {
        fields._signature_asset_id = 'none';
        fields._no_signature = true;
    } else if (sigAssetVal) {
        fields._signature_asset_id = sigAssetVal;
        fields._no_signature = false;
    }
    return fields;
}

function updateSignSeparator() {
    const sep = document.getElementById('docPaperSignSep');
    const rankEl = document.getElementById('docPaperSignRank');
    const appEl = document.getElementById('docPaperSignAppointment');
    if (!sep) return;
    const hasRank = Boolean(rankEl && rankEl.textContent.trim().length > 0);
    const hasApp = Boolean(appEl && appEl.textContent.trim().length > 0);
    sep.textContent = (hasRank && hasApp) ? ', ' : '';
}

function setupLivePreviewSync() {
    const refInput = document.getElementById('formRefNo');
    const dateInput = document.getElementById('formDate');

    if (refInput) {
        refInput.oninput = () => {
            const el = document.getElementById('docPaperRef');
            if (el) el.textContent = refInput.value.trim() || 'CME/GEN/2026/0001';
        };
    }

    if (dateInput) {
        dateInput.oninput = () => {
            const el = document.getElementById('docPaperDate');
            if (el) el.textContent = dateInput.value.trim() || 'Today';
            const signDate = document.getElementById('docPaperSignDate');
            if (signDate) signDate.textContent = dateInput.value.trim() || 'Today';
        };
    }

    const toInput = document.getElementById('doc_field_to') || document.getElementById('doc_field_to_name');
    if (toInput) {
        toInput.oninput = () => {
            const el = document.getElementById('docPaperTo');
            if (el) {
                if (toInput.value.trim().length > 0) {
                    el.style.color = '';
                    el.style.fontStyle = '';
                    el.innerHTML = escapeHtml(toInput.value).replace(/\n/g, '<br/>');
                } else {
                    el.style.color = '#94a3b8';
                    el.style.fontStyle = 'italic';
                    el.innerHTML = '[Recipient Designation &amp; HQ Address]';
                }
            }
        };
    }

    const subInput = document.getElementById('doc_field_subject') || document.getElementById('doc_field_title') || document.getElementById('doc_field_meeting_title');
    if (subInput) {
        subInput.oninput = () => {
            const el = document.getElementById('docPaperSubjectText');
            if (el) {
                el.textContent = subInput.value.trim().toUpperCase() || '[OFFICIAL SUBJECT LINE WILL APPEAR HERE]';
            }
        };
    }

    const nameInput = document.getElementById('doc_field_from_name');
    if (nameInput) {
        nameInput.oninput = () => {
            const el = document.getElementById('docPaperSignName');
            if (el) el.textContent = nameInput.value.trim();
        };
    }

    const rankInput = document.getElementById('doc_field_from_rank');
    if (rankInput) {
        rankInput.oninput = () => {
            const el = document.getElementById('docPaperSignRank');
            if (el) el.textContent = rankInput.value.trim();
            updateSignSeparator();
        };
    }

    const appInput = document.getElementById('doc_field_from_appointment');
    if (appInput) {
        appInput.oninput = () => {
            const el = document.getElementById('docPaperSignAppointment');
            if (el) el.textContent = appInput.value.trim();
            updateSignSeparator();
        };
    }

    const authInput = document.getElementById('doc_field_from_authority');
    if (authInput) {
        authInput.oninput = () => {
            const el = document.getElementById('docPaperSignAuthority');
            if (el) el.textContent = authInput.value.trim();
        };
    }

    const deptInput = document.getElementById('doc_field_from_department');
    if (deptInput) {
        deptInput.oninput = () => {
            const el = document.getElementById('docPaperWing');
            if (el) el.textContent = deptInput.value.trim() || 'Combat Engineering Wing';
        };
    }

    const stnInput = document.getElementById('doc_field_station');
    if (stnInput) {
        stnInput.oninput = () => {
            const el = document.getElementById('docPaperStation');
            if (el) el.textContent = stnInput.value.trim() || 'CME, Pune – 411031';
        };
    }

    const enclInput = document.getElementById('doc_field_enclosures');
    if (enclInput) {
        enclInput.oninput = () => {
            const el = document.getElementById('docPaperEncl');
            if (el) el.textContent = enclInput.value.trim() || 'As stated';
        };
    }

    const ccInput = document.getElementById('doc_field_cc_list') || document.getElementById('doc_field_cc');
    if (ccInput) {
        ccInput.oninput = () => {
            const el = document.getElementById('docPaperCc');
            if (el) el.textContent = ccInput.value.trim();
        };
    }
}

async function startDocumentCreation(docType, initialMessage = '') {
    currentDocType = docType || 'formal_letter';
    currentGeneratedDocId = null;
    isDocumentDirty = false;

    const overlay = document.getElementById('documentModalOverlay');
    if (overlay) overlay.classList.add('active');

    switchModalDocType(currentDocType);
    applyClassificationState();
    setTimeout(resetStudioScroll, 50);

    // Call /api/agent/start/ to get smart defaults
    try {
        const resp = await fetch('/api/agent/start/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify({
                doc_type: currentDocType,
                initial_message: initialMessage
            })
        });

        if (resp.ok) {
            const data = await resp.json();
            currentDocSession = data;

            const refInput = document.getElementById('formRefNo');
            const dateInput = document.getElementById('formDate');

            if (refInput && data.auto_filled && data.auto_filled.reference_number) {
                refInput.value = data.auto_filled.reference_number;
            }
            if (dateInput && data.auto_filled && data.auto_filled.date) {
                dateInput.value = data.auto_filled.date;
                const dateText = document.getElementById('formDateText');
                if (dateText) dateText.textContent = data.auto_filled.date;
                syncDateToPicker(data.auto_filled.date);
            }

            // Pre-fill extracted fields if any was provided in initial chat
            if (data.collected_fields) {
                for (const [key, val] of Object.entries(data.collected_fields)) {
                    const el = document.getElementById(`doc_field_${key}`);
                    if (el && val) el.value = val;
                }
            }

            // Re-render draft sheet with updated autofill headers (clean slate, no fake content)
            const container = document.getElementById('docPreviewContainer');
            if (container) {
                const dummyDoc = {
                    doc_type: currentDocType,
                    title: DOC_DEFINITIONS[currentDocType]?.title || 'Military Document',
                    generated_content: ''
                };
                container.innerHTML = renderDocumentPaperPreview(dummyDoc, collectCurrentFormFields());
                setupLivePreviewSync();
            }
        }
    } catch (err) {
        console.warn('Could not initialize document session defaults:', err);
    }
}

async function submitGenerateDocument() {
    const form = document.getElementById('docGeneratorForm');
    if (!form) return;

    const collectedFields = collectCurrentFormFields();

    // Model selection
    const modelSelect = document.getElementById('modelSelect');
    const selectedModel = modelSelect ? modelSelect.value : 'llama3:latest';

    // Show generating progress in generate button
    const btnSubmit = document.getElementById('btnSubmitGenerate');
    const btnText = document.getElementById('btnSubmitGenerateText');
    const saveStatus = document.getElementById('paperSaveStatus');

    if (btnSubmit) btnSubmit.disabled = true;
    if (btnText) btnText.textContent = 'Generating with local Ollama...';
    if (saveStatus) saveStatus.textContent = 'Generating...';

    try {
        const selectedSigId = activeSignatureAssetId || document.getElementById('doc_field_signature_asset')?.value || '';
        const resp = await fetch('/api/agent/generate/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify({
                doc_type: currentDocType,
                collected_fields: collectedFields,
                model_name: selectedModel,
                conversation_id: activeConversationId,
                security_pin: activeSessionPasscode || '',
                lock_hint: currentDocLockHint || '',
                encrypt_export: currentDocEncryptExport || false,
                signature_asset_id: (selectedSigId && selectedSigId !== 'none') ? selectedSigId : '',
                no_signature: selectedSigId === 'none'
            })
        });

        const data = await resp.json();

        if (resp.ok && data.status === 'ok') {
            const doc = data.document;
            currentGeneratedDocId = doc.document_id;

            // Render live authentic A4 document in the studio preview
            const container = document.getElementById('docPreviewContainer');
            if (container) {
                container.innerHTML = renderDocumentPaperPreview(doc, collectedFields);
                attachPaperEditListeners();
            }

            const metaEl = document.getElementById('docResultMeta');
            if (metaEl) metaEl.textContent = `Generated in ${doc.generation_time}s • ${doc.model_used}`;

            const sizeBadge = document.getElementById('downloadFileSizeBadge');
            if (sizeBadge && doc.file_size) sizeBadge.textContent = doc.file_size;

            isDocumentDirty = false;
            if (saveStatus) {
                saveStatus.textContent = 'Word doc synced';
                saveStatus.classList.remove('dirty');
            }

            const commentInput = document.getElementById('docRegenerateComment');
            if (commentInput) commentInput.value = '';
            updateRegenerateButtonLabel();

            addDocumentToSidebar(doc);

            // Ensure preview window remains open and active
            const overlay = document.getElementById('documentModalOverlay');
            if (overlay) overlay.classList.add('active');
            setTimeout(resetStudioScroll, 50);

            const emptyState = document.getElementById('emptyState');
            if (emptyState) emptyState.style.display = 'none';
        } else {
            alert('Generation error: ' + (data.error || 'Unknown error'));
        }
    } catch (err) {
        alert('Communication error: ' + err.message);
    } finally {
        if (btnSubmit) btnSubmit.disabled = false;
        if (btnText) btnText.textContent = 'Generate Document';
    }
}

/* ==========================================================================
   Editable Document Preview & Auto-Sync
   ========================================================================== */

function syncPaperToFormFields(sel, el) {
    const text = (el.innerText || el.textContent || '').trim();
    if (sel === '#docPaperRef') {
        const input = document.getElementById('formRefNo');
        if (input) input.value = text;
    } else if (sel === '#docPaperDate') {
        const dateText = document.getElementById('formDateText');
        if (dateText) dateText.textContent = text;
        const signDate = document.getElementById('docPaperSignDate');
        if (signDate) signDate.textContent = text;
        const formDate = document.getElementById('formDate');
        if (formDate) formDate.value = text;
        syncDateToPicker(text);
    } else if (sel === '#docPaperTo') {
        const input = document.getElementById('doc_field_to_name') || document.getElementById('doc_field_to');
        if (input && !text.startsWith('[')) input.value = text;
    } else if (sel === '#docPaperSubjectText') {
        const input = document.getElementById('doc_field_subject') || document.getElementById('doc_field_meeting_title') || document.getElementById('doc_field_title');
        if (input && !text.startsWith('[')) input.value = text;
    } else if (sel === '#docPaperWing') {
        const input = document.getElementById('doc_field_from_department');
        if (input) input.value = text;
    } else if (sel === '#docPaperStation') {
        const input = document.getElementById('doc_field_station');
        if (input) input.value = text;
    } else if (sel === '#docPaperEncl') {
        const input = document.getElementById('doc_field_enclosures');
        if (input) input.value = text;
    } else if (sel === '#docPaperCc') {
        const input = document.getElementById('doc_field_cc_list') || document.getElementById('doc_field_cc');
        if (input) input.value = text.replace(/^copy to:\s*/i, '');
    } else if (sel === '#docPaperSignName') {
        const input = document.getElementById('doc_field_from_name');
        if (input) input.value = text.replace(/[()]/g, '').trim();
    } else if (sel === '#docPaperSignRank') {
        const input = document.getElementById('doc_field_from_rank');
        if (input) input.value = text;
        updateSignSeparator();
    } else if (sel === '#docPaperSignAppointment') {
        const input = document.getElementById('doc_field_from_appointment');
        if (input) input.value = text;
        updateSignSeparator();
    } else if (sel === '#docPaperSignAuthority') {
        const input = document.getElementById('doc_field_from_authority');
        if (input) input.value = text;
    }
}

function attachPaperEditListeners() {
    const saveStatus = document.getElementById('paperSaveStatus');
    const editableSelectors = [
        '#paperBodyContent',
        '#docPaperRef',
        '#docPaperWing',
        '#docPaperStation',
        '#docPaperDate',
        '#docPaperTo',
        '#docPaperSubjectText',
        '#docPaperSalutation',
        '#docPaperEncl',
        '#docPaperCc',
        '#docPaperSignName',
        '#docPaperSignRank',
        '#docPaperSignAppointment',
        '#docPaperSignAuthority',
        '#docPaperOrg',
        '#docPaperSub',
        '#docPaperTele'
    ];

    editableSelectors.forEach(sel => {
        const el = document.querySelector(sel);
        if (!el) return;

        el.addEventListener('input', () => {
            isDocumentDirty = true;
            if (saveStatus) {
                saveStatus.textContent = 'Unsaved changes';
                saveStatus.classList.add('dirty');
            }

            syncPaperToFormFields(sel, el);

            if (paperAutoSaveTimer) clearTimeout(paperAutoSaveTimer);
            paperAutoSaveTimer = setTimeout(() => {
                saveDocumentContentChanges();
            }, 800);
        });

        el.addEventListener('blur', () => {
            if (isDocumentDirty) {
                saveDocumentContentChanges();
            }
        });
    });
}

function extractPaperBodyText() {
    const bodyEl = document.getElementById('paperBodyContent');
    if (!bodyEl) return '';

    const paras = bodyEl.querySelectorAll('.paper-para');
    if (paras.length > 0) {
        const lines = [];
        paras.forEach(p => {
            const t = p.innerText.trim();
            if (t.length > 0) lines.push(t);
        });
        return lines.join('\n\n');
    }

    return bodyEl.innerText.split('\n')
        .map(l => l.trim())
        .filter(l => l.length > 0)
        .join('\n\n');
}

function extractPaperAllFields() {
    const fields = collectCurrentFormFields();

    const ref = document.getElementById('docPaperRef')?.innerText?.trim();
    if (ref) fields.reference_number = ref;

    const date = document.getElementById('docPaperDate')?.innerText?.trim();
    if (date) fields.date = date;

    const to = document.getElementById('docPaperTo')?.innerText?.trim();
    if (to && !to.startsWith('[')) {
        fields.to_name = to;
        fields.to = to;
    }

    const sub = document.getElementById('docPaperSubjectText')?.innerText?.trim();
    if (sub && !sub.startsWith('[')) {
        fields.subject = sub;
    }

    const sal = document.getElementById('docPaperSalutation')?.innerText?.trim();
    if (sal) fields.salutation = sal;

    const encl = document.getElementById('docPaperEncl')?.innerText?.trim();
    if (encl) fields.enclosures = encl;

    const cc = document.getElementById('docPaperCc')?.innerText?.replace(/^copy to:\s*/i, '').trim();
    if (cc) {
        fields.cc = cc;
        fields.cc_list = cc;
    }

    const signName = document.getElementById('docPaperSignName')?.innerText?.replace(/[()]/g, '').trim();
    if (signName && signName !== 'Issuing Officer') fields.from_name = signName;

    const signRank = document.getElementById('docPaperSignRank')?.innerText?.trim();
    if (signRank) fields.from_rank = signRank;

    const signApp = document.getElementById('docPaperSignAppointment')?.innerText?.trim();
    if (signApp) fields.from_appointment = signApp;

    const signAuth = document.getElementById('docPaperSignAuthority')?.innerText?.trim();
    if (signAuth) fields.from_authority = signAuth;

    const wing = document.getElementById('docPaperWing')?.innerText?.trim();
    if (wing) fields.from_department = wing;

    const station = document.getElementById('docPaperStation')?.innerText?.trim();
    if (station) fields.station = station;

    fields.signature_style = currentPreviewSigStyle || window.USER_SIG_STYLE || 'military';
    return fields;
}

async function saveDocumentContentChanges() {
    if (!currentGeneratedDocId) return;
    const saveStatus = document.getElementById('paperSaveStatus');
    const text = extractPaperBodyText();
    const fields = extractPaperAllFields();

    if (saveStatus) {
        saveStatus.textContent = 'Saving to Word doc...';
        saveStatus.classList.remove('dirty');
    }

    try {
        const resp = await fetch(`/api/documents/${currentGeneratedDocId}/update-text/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify({
                content: text || ' ',
                fields: fields
            })
        });

        const data = await resp.json();
        if (resp.ok && data.status === 'ok') {
            isDocumentDirty = false;
            if (saveStatus) {
                saveStatus.textContent = 'Word doc synced';
                saveStatus.classList.remove('dirty');
            }
            showToast('Document saved', 'success');
            const sizeBadge = document.getElementById('downloadFileSizeBadge');
            if (sizeBadge && data.file_size) {
                sizeBadge.textContent = data.file_size;
            }
        } else {
            if (saveStatus) {
                saveStatus.textContent = 'Sync failed';
                saveStatus.classList.add('dirty');
            }
        }
    } catch (err) {
        console.warn('Document sync error:', err);
        if (saveStatus) {
            saveStatus.textContent = 'Sync error';
            saveStatus.classList.add('dirty');
        }
    }
}

async function handleDocumentDownload() {
    // If not generated yet, auto-generate first!
    if (!currentGeneratedDocId) {
        await submitGenerateDocument();
        if (!currentGeneratedDocId) {
            return;
        }
    }

    // Ensure any unsaved edits in the preview are synced to DOCX before downloading
    if (isDocumentDirty) {
        await saveDocumentContentChanges();
    }

    let downloadUrl = `/api/documents/${currentGeneratedDocId}/download/`;
    if (currentDocIsLocked && currentDocEncryptExport && activeSessionPasscode) {
        downloadUrl += `?passcode=${encodeURIComponent(activeSessionPasscode)}`;
    } else {
        downloadUrl += `?decrypted=1`;
    }

    window.location.href = downloadUrl;
}

async function handleDocumentPdfDownload() {
    // If not generated yet, auto-generate first!
    if (!currentGeneratedDocId) {
        await submitGenerateDocument();
        if (!currentGeneratedDocId) {
            return;
        }
    }

    // Ensure any unsaved edits in the preview are synced before exporting
    if (isDocumentDirty) {
        await saveDocumentContentChanges();
    }

    let downloadUrl = `/api/documents/${currentGeneratedDocId}/pdf/`;
    if (currentDocIsLocked && currentDocEncryptExport && activeSessionPasscode) {
        downloadUrl += `?passcode=${encodeURIComponent(activeSessionPasscode)}`;
    } else {
        downloadUrl += `?decrypted=1`;
    }

    window.location.href = downloadUrl;
}


function updateRegenerateButtonLabel() {
    const input = document.getElementById('docRegenerateComment');
    const label = document.getElementById('btnRegenerateText');
    if (!label) return;
    if (input && input.value && input.value.trim().length > 0) {
        label.textContent = 'Apply Changes';
    } else {
        label.textContent = 'Regenerate';
    }
}

async function handleDocumentRegenerate() {
    if (!currentGeneratedDocId) {
        submitGenerateDocument();
        return;
    }

    const commentInput = document.getElementById('docRegenerateComment');
    const instruction = commentInput ? commentInput.value.trim() : '';

    const btn = document.getElementById('btnDocRegenerate');
    const saveStatus = document.getElementById('paperSaveStatus');

    if (btn) btn.disabled = true;
    if (saveStatus) saveStatus.textContent = instruction ? 'Applying revision...' : 'Regenerating...';

    try {
        const resp = await fetch(`/api/agent/revise/${currentGeneratedDocId}/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify({ instruction })
        });

        const data = await resp.json();
        if (resp.ok && data.status === 'ok') {
            const doc = data.document;
            currentGeneratedDocId = doc.document_id;
            isDocumentDirty = false;

            const container = document.getElementById('docPreviewContainer');
            if (container) {
                container.innerHTML = renderDocumentPaperPreview(doc, collectCurrentFormFields());
                attachPaperEditListeners();
            }

            const metaEl = document.getElementById('docResultMeta');
            if (metaEl) {
                const label = instruction ? `Revised (v${doc.version})` : `Regenerated (v${doc.version})`;
                metaEl.textContent = `${label} in ${doc.generation_time}s • ${doc.model_used}`;
            }

            const sizeBadge = document.getElementById('downloadFileSizeBadge');
            if (sizeBadge && doc.file_size) sizeBadge.textContent = doc.file_size;

            if (saveStatus) {
                saveStatus.textContent = 'Word doc synced';
                saveStatus.classList.remove('dirty');
            }

            if (commentInput) commentInput.value = '';
            updateRegenerateButtonLabel();

            addDocumentToSidebar(doc);
        } else {
            alert('Regeneration error: ' + (data.error || 'Failed'));
        }
    } catch (err) {
        alert('Communication error: ' + err.message);
    } finally {
        if (btn) btn.disabled = false;
    }
}

function renderDocumentPaperPreview(doc, fields) {
    fields = fields || {};
    const isLetter = doc.doc_type === 'formal_letter';
    const isMemo = doc.doc_type === 'office_memo';
    const isMoM = doc.doc_type === 'meeting_minutes';
    const isNote = doc.doc_type === 'office_note';
    const isOrder = doc.doc_type === 'office_order';
    const isLeave = doc.doc_type === 'leave_application';

    let docTypeBanner = '';
    if (isMemo) docTypeBanner = '<div class="paper-subject" style="font-size:0.95rem; margin: 4px 0;">OFFICE MEMORANDUM</div>';
    else if (isMoM) docTypeBanner = '<div class="paper-subject" style="font-size:0.95rem; margin: 4px 0;">MINUTES OF MEETING</div>';
    else if (isNote) docTypeBanner = '<div class="paper-subject" style="font-size:0.95rem; margin: 4px 0;">OFFICE NOTE / NOTE SHEET</div>';
    else if (isOrder) docTypeBanner = '<div class="paper-subject" style="font-size:0.95rem; margin: 4px 0;">OFFICE ORDER</div>';
    else if (isLeave) docTypeBanner = '<div class="paper-subject" style="font-size:0.95rem; margin: 4px 0;">APPLICATION FOR LEAVE</div>';

    let headerHtml = `
        <div class="paper-header">
            <div class="paper-org paper-editable" id="docPaperOrg" contenteditable="true" spellcheck="false" title="Click to edit organization">${escapeHtml(fields.organization || 'COLLEGE OF MILITARY ENGINEERING')}</div>
            <div class="paper-sub paper-editable" id="docPaperSub" contenteditable="true" spellcheck="false" title="Click to edit subtitle">${escapeHtml(fields.sub_header || 'Dapodi, Pune – 411031 • Corps of Engineers')}</div>
            ${docTypeBanner}
            <div class="paper-divider"></div>
        </div>
    `;

    let metaHtml = `
        <div class="paper-meta-row">
            <div style="display: flex; flex-direction: column; gap: 2px;">
                <span id="docPaperTele" contenteditable="true" spellcheck="false" class="paper-editable" title="Click to edit Tele">${escapeHtml(fields.tele || 'Tele: 020-27146000/2204')}</span>
                <span>Ref: <strong id="docPaperRef" contenteditable="true" spellcheck="false" class="paper-editable" placeholder="Ref No." title="Click to edit Ref No">${escapeHtml(fields.reference_number || 'CME/CEW/2026/1104')}</strong></span>
            </div>
            <div style="display: flex; flex-direction: column; text-align: right; gap: 2px;">
                <span id="docPaperWing" contenteditable="true" spellcheck="false" class="paper-editable" placeholder="Wing / Department" title="Click to edit Wing">${escapeHtml(fields.from_department || 'Combat Engineering Wing')}</span>
                <span id="docPaperStation" contenteditable="true" spellcheck="false" class="paper-editable" placeholder="Station" title="Click to edit Station">${escapeHtml(fields.station || 'CME, Pune – 411031')}</span>
                <span id="docPaperDate" contenteditable="true" spellcheck="false" class="paper-editable" placeholder="Date" title="Click to edit Date">${escapeHtml(fields.date || 'Today')}</span>
            </div>
        </div>
    `;

    let recipientHtml = '';
    let toVal = fields.to_name || fields.to || '';
    if (isLeave && !toVal.trim()) {
        toVal = 'The Commandant,\nCollege of Military Engineering,\nDapodi, Pune – 411031';
    }
    recipientHtml = `
        <div class="paper-to">
            <strong>To,</strong><br>
            <div id="docPaperTo" contenteditable="true" spellcheck="false" class="paper-editable" placeholder="[Recipient Designation &amp; HQ Address]" title="Click to edit Addressee">${toVal.trim().length > 0 ? escapeHtml(toVal).replace(/\n/g, '<br/>') : ''}</div>
        </div>
    `;

    let subjectClean = fields.subject || fields.meeting_title || fields.title || '';
    if (isLeave && !subjectClean.trim()) {
        subjectClean = `APPLICATION FOR ${(fields.leave_type || 'CASUAL LEAVE').toUpperCase()}`;
    }
    subjectClean = subjectClean.replace(/key\s+points\s*:?/gi, '').replace(/^subject\s*:?/gi, '').trim();

    let subjectHtml = `
        <div class="paper-subject" id="docPaperSubject">
            <strong>SUBJECT:</strong> <u><span id="docPaperSubjectText" contenteditable="true" spellcheck="false" class="paper-editable" placeholder="[OFFICIAL SUBJECT LINE]" title="Click to edit Subject">${escapeHtml(subjectClean.toUpperCase())}</span></u>
        </div>
    `;

    const hasContent = Boolean(doc && doc.generated_content && doc.generated_content.trim().length > 0);

    let paragraphsHtml = '';
    if (hasContent) {
        paragraphsHtml = (doc.generated_content || '').split('\n')
            .map(p => p.trim())
            .filter(p => p.length > 0)
            .map(p => `<p class="paper-para">${escapeHtml(p)}</p>`)
            .join('');
    } else {
        paragraphsHtml = `
            <div class="paper-draft-placeholder">
                <div class="placeholder-watermark">
                    <svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                        <polyline points="14 2 14 8 20 8"></polyline>
                        <line x1="16" y1="13" x2="8" y2="13"></line>
                        <line x1="16" y1="17" x2="8" y2="17"></line>
                    </svg>
                    <div class="placeholder-title">Awaiting Formulation Directives</div>
                    <div class="placeholder-sub">
                        Enter addressee, subject, and operational brief on the left, then click <strong>"Generate Document"</strong> to draft your official military document.
                    </div>
                </div>
            </div>
        `;
    }

    const fromName = fields.from_name || '';
    const fromRank = fields.from_rank || '';
    const fromApp = fields.from_appointment || '';
    const fromAuth = fields.from_authority || '';
    const dateStr = fields.date || 'Today';

    const currentSigId = fields._signature_asset_id !== undefined ? fields._signature_asset_id : (activeSignatureAssetId || document.getElementById('doc_field_signature_asset')?.value || '');
    let activeSigAsset = null;
    if (currentSigId && currentSigId !== 'none' && Array.isArray(userSignatureAssets)) {
        activeSigAsset = userSignatureAssets.find(s => s.id === currentSigId);
    }
    if (!activeSigAsset && currentSigId !== 'none' && Array.isArray(userSignatureAssets)) {
        activeSigAsset = userSignatureAssets.find(s => s.is_default);
    }

    let sigGraphicHtml = '';
    if (currentSigId === 'none' || fields._no_signature) {
        sigGraphicHtml = '<div class="mil-signature-line" style="height: 38px;"></div>';
    } else if (activeSigAsset && activeSigAsset.url) {
        sigGraphicHtml = `
            <div class="mil-signature-line" style="min-height: 40px; display: flex; justify-content: flex-end; align-items: center; margin-bottom: 3px;">
                <img src="${activeSigAsset.url}" alt="${escapeHtml(activeSigAsset.label)}" style="height: 38px; max-width: 140px; object-fit: contain; display: block;" />
            </div>
        `;
    } else {
        sigGraphicHtml = `
            <div class="mil-signature-line">
                <svg class="signature-svg" viewBox="0 0 160 40" fill="none" stroke="#1e3a8a" stroke-width="1.6" stroke-linecap="round">
                    <path d="M12 28 C 28 14, 34 8, 48 14 C 58 18, 52 30, 68 22 C 82 14, 78 8, 98 16 C 112 22, 118 14, 134 11 C 142 9, 146 22, 154 20"></path>
                    <path d="M42 21 C 62 21, 102 23, 138 19" stroke-width="1.1"></path>
                </svg>
            </div>
        `;
    }

    const sigStyle = fields.signature_style || window.USER_SIG_STYLE || 'military';
    let rightSignBlockHtml = '';

    if (sigStyle === 'eoffice') {
        rightSignBlockHtml = `
            <div class="eoffice-dsc-box">
                <div class="paper-sig-quick-actions no-print">
                    <button type="button" class="sig-action-btn" onclick="openSignatureQuickModal()" title="Modify Signatory Credentials">
                        <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/></svg>
                        <span>Edit</span>
                    </button>
                    <button type="button" class="sig-action-btn" onclick="togglePreviewSigStyle()" title="Switch to Classic Military format">
                        <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="16 3 21 3 21 8"/><line x1="4" y1="20" x2="21" y2="3"/><polyline points="21 16 21 21 16 21"/><line x1="15" y1="15" x2="21" y2="21"/></svg>
                        <span>Switch to Military</span>
                    </button>
                </div>
                <div class="eoffice-dsc-header">DIGITALLY SIGNED CERTIFICATE (DSC)</div>
                ${activeSigAsset && activeSigAsset.url ? `<div style="text-align: center; margin: 4px 0;"><img src="${activeSigAsset.url}" style="height: 32px; max-width: 120px; object-fit: contain;" /></div>` : ""}
                <table class="eoffice-dsc-table">
                    <tr>
                        <td class="dsc-label">Signed by:</td>
                        <td class="dsc-val"><strong>(<span id="docPaperSignName" contenteditable="true" spellcheck="false" class="paper-editable" title="Click to edit">${escapeHtml(fromName || 'Issuing Officer')}</span>)</strong></td>
                    </tr>
                    ${(fromRank || fromApp) ? `
                    <tr>
                        <td class="dsc-label">Role:</td>
                        <td class="dsc-val"><span id="docPaperSignRank" contenteditable="true" spellcheck="false" class="paper-editable" title="Click to edit rank">${escapeHtml(fromRank)}</span>${(fromRank && fromApp) ? ', ' : ''}<span id="docPaperSignAppointment" contenteditable="true" spellcheck="false" class="paper-editable" title="Click to edit appointment">${escapeHtml(fromApp)}</span></td>
                    </tr>` : ''}
                    ${fromAuth ? `
                    <tr>
                        <td class="dsc-label">Authority:</td>
                        <td class="dsc-val"><span id="docPaperSignAuthority" contenteditable="true" spellcheck="false" class="paper-editable" title="Click to edit authority">${escapeHtml(fromAuth)}</span></td>
                    </tr>` : ''}
                    <tr>
                        <td class="dsc-label">Location:</td>
                        <td class="dsc-val">${escapeHtml(fields.station || 'CME, Dapodi, Pune')}</td>
                    </tr>
                    <tr>
                        <td class="dsc-label">Date:</td>
                        <td class="dsc-val"><span id="docPaperSignDate">${escapeHtml(dateStr)}</span> IST</td>
                    </tr>
                </table>
            </div>
        `;
    } else {
        // Authentic Indian Army Military Staff Duties Format
        rightSignBlockHtml = `
            <div class="paper-signature-mil">
                <div class="paper-sig-quick-actions no-print">
                    <button type="button" class="sig-action-btn" onclick="openSignatureQuickModal()" title="Modify Signatory Credentials & Style">
                        <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/></svg>
                        <span>Edit Signatory</span>
                    </button>
                    <button type="button" class="sig-action-btn" onclick="togglePreviewSigStyle()" title="Switch to e-Office DSC Certificate format">
                        <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="16 3 21 3 21 8"/><line x1="4" y1="20" x2="21" y2="3"/><polyline points="21 16 21 21 16 21"/><line x1="15" y1="15" x2="21" y2="21"/></svg>
                        <span>Switch to DSC Stamp</span>
                    </button>
                </div>
${sigGraphicHtml}
                <div class="mil-signer-name">
                    (<span id="docPaperSignName" contenteditable="true" spellcheck="false" class="paper-editable" title="Click to edit Signatory Name">${escapeHtml(fromName || 'Issuing Officer')}</span>)
                </div>
                ${(fromRank || fromApp) ? `
                <div class="mil-signer-role">
                    <span id="docPaperSignRank" contenteditable="true" spellcheck="false" class="paper-editable" title="Click to edit Rank">${escapeHtml(fromRank)}</span>${(fromRank && fromApp) ? ', ' : ''}<span id="docPaperSignAppointment" contenteditable="true" spellcheck="false" class="paper-editable" title="Click to edit Appointment">${escapeHtml(fromApp)}</span>
                </div>` : ''}
                ${fromAuth ? `
                <div class="mil-signer-auth">
                    <span id="docPaperSignAuthority" contenteditable="true" spellcheck="false" class="paper-editable" title="Click to edit Authority">${escapeHtml(fromAuth)}</span>
                </div>` : ''}
            </div>
        `;
    }

    let signHtml = `
        <div class="paper-signature-block">
            <div class="paper-encl-summary">
                ${fields.enclosures ? `<div class="paper-encl-title">Encl: <span id="docPaperEncl" contenteditable="true" spellcheck="false" class="paper-editable" title="Click to edit enclosures">${escapeHtml(fields.enclosures)}</span></div>` : ''}
                ${(fields.cc || fields.cc_list) ? `<div id="docPaperCcWrapper" style="margin-top: 4px; font-size: 0.76rem; color: #475569;">Copy to: <span id="docPaperCc" contenteditable="true" spellcheck="false" class="paper-editable" title="Click to edit CC list">${escapeHtml(fields.cc || fields.cc_list)}</span></div>` : ''}
            </div>
            ${rightSignBlockHtml}
        </div>
    `;

    const isNoneClass = currentClassification === 'NONE';
    const topBadgeHtml = isNoneClass ? '' : `<span class="paper-classified-badge stamp-${currentClassification.toLowerCase()}" id="docPaperClassTop">${currentClassification}</span>`;
    const botBadgeHtml = isNoneClass ? '' : `<span class="paper-classified-badge stamp-${currentClassification.toLowerCase()}" id="docPaperClassBottom">${currentClassification}</span>`;

    return `
        <div class="paper-sheet">
            <div class="paper-classified-header">
                ${topBadgeHtml}
            </div>
            ${headerHtml}
            ${metaHtml}
            ${recipientHtml}
            ${subjectHtml}
            ${isLetter ? `<div class="paper-salutation"><span id="docPaperSalutation" contenteditable="true" spellcheck="false" class="paper-editable" title="Click to edit Salutation">${escapeHtml(fields.salutation || 'Sir,')}</span></div>` : ''}
            <div class="paper-body" id="paperBodyContent" ${hasContent ? 'contenteditable="true" spellcheck="true" title="Click anywhere to edit text directly"' : ''}>${paragraphsHtml}</div>
            ${signHtml}
            <div class="paper-classified-footer" style="${isNoneClass ? 'margin-top: 8px;' : 'margin-top: 24px;'}">
                ${botBadgeHtml}
            </div>
        </div>
    `;
}

function addDocumentToSidebar(doc) {
    const list = document.getElementById('sidebarDocList');
    if (!list) return;

    const docId = doc.document_id || doc.id;
    if (!docId) return;

    // Check if item already exists in sidebar
    const existing = list.querySelector(`.doc-sidebar-item[data-doc-id="${docId}"]`);
    if (existing) {
        const titleSpan = existing.querySelector('.doc-item-title');
        const metaSpan = existing.querySelector('.doc-item-meta');
        if (titleSpan) {
            titleSpan.innerHTML = `${escapeHtml(doc.title)} ${doc.is_locked ? '<span class="sidebar-lock-badge">🔒</span>' : ''}`;
        }
        if (metaSpan) {
            metaSpan.textContent = `${doc.file_size} • v${doc.version || 1}${doc.is_locked ? ' • Locked' : ''}`;
        }
        return;
    }

    const item = document.createElement('a');
    item.href = '#';
    item.className = `doc-sidebar-item ${doc.is_locked ? 'is-locked' : ''}`;
    item.setAttribute('data-doc-id', docId);
    item.setAttribute('data-locked', doc.is_locked ? 'true' : 'false');
    item.title = doc.is_locked ? `🔒 Locked Document: ${doc.title}` : `Click to preview ${doc.title}`;
    item.onclick = (e) => handleArchiveDocumentClick(e, docId, Boolean(doc.is_locked));

    const lockBadge = doc.is_locked ? '<span class="sidebar-lock-badge">🔒</span>' : '';
    item.innerHTML = `
        <span class="doc-item-icon">
            ${doc.is_locked ? 
                `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" class="text-maroon">
                    <rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect>
                    <path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
                </svg>` : 
                `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                    <polyline points="14 2 14 8 20 8"></polyline>
                    <line x1="16" y1="13" x2="8" y2="13"></line>
                    <line x1="16" y1="17" x2="8" y2="17"></line>
                </svg>`
            }
        </span>
        <div class="doc-item-info">
            <span class="doc-item-title">${escapeHtml(doc.title)} ${lockBadge}</span>
            <span class="doc-item-meta">${doc.file_size} • v${doc.version || 1}${doc.is_locked ? ' • Locked' : ''}</span>
        </div>
    `;

    // Remove "No documents yet" notice if present
    const emptyNotice = list.querySelector('div');
    if (emptyNotice && emptyNotice.textContent.includes('No documents')) {
        emptyNotice.remove();
    }

    list.insertBefore(item, list.firstChild);

    // Update count badge
    const badge = document.getElementById('docCountBadge');
    if (badge) {
        const current = parseInt(badge.textContent || '0', 10);
        badge.textContent = current + 1;
    }
}


/* ==========================================================================
   Document Security Lock & AES-256 Passcode Protection
   ========================================================================== */

function updateStudioLockState(isLocked, encryptExport) {
    currentDocIsLocked = isLocked;
    currentDocEncryptExport = encryptExport;
    const btn = document.getElementById('btnStudioLock');
    const text = document.getElementById('btnStudioLockText');
    const pdfBadge = document.getElementById('pdfEncBadge');
    const pdfBtn = document.getElementById('btnDownloadPdf');

    if (btn && text) {
        if (isLocked) {
            btn.classList.add('is-locked');
            text.textContent = encryptExport ? 'Locked (AES-256) 🔒' : 'PIN Locked 🔒';
            btn.setAttribute('title', 'Document is secured with an Officer PIN. Click to manage.');
        } else {
            btn.classList.remove('is-locked');
            text.textContent = 'Passcode Lock';
            btn.setAttribute('title', 'Set an Officer PIN & AES-256 PDF/DOCX encryption.');
        }
    }

    if (pdfBadge) {
        if (isLocked && encryptExport) {
            pdfBadge.textContent = 'Locked 🔒';
            pdfBadge.classList.add('is-locked');
        } else {
            pdfBadge.textContent = 'A4';
            pdfBadge.classList.remove('is-locked');
        }
    }

    if (pdfBtn) {
        if (isLocked && encryptExport) {
            pdfBtn.classList.add('is-locked');
        } else {
            pdfBtn.classList.remove('is-locked');
        }
    }
}

async function openDocumentSecurityModal() {
    const modal = document.getElementById('docSecurityModal');
    if (!modal) return;

    const activeBanner = document.getElementById('secLockActiveBanner');
    const removeBtn = document.getElementById('btnSecRemoveLock');
    const applyBtnText = document.querySelector('#btnSecApplyLock span');
    const hintInput = document.getElementById('secLockHint');
    const pinInput = document.getElementById('secLockPin');
    const checkEnc = document.getElementById('secCheckEncryptExport');
    const checkArch = document.getElementById('secCheckLockArchive');

    // If already generated, fetch status from server
    if (currentGeneratedDocId) {
        try {
            const resp = await fetch(`/api/documents/${currentGeneratedDocId}/detail/`);
            if (resp.ok) {
                const data = await resp.json();
                const isLocked = Boolean(data.document && data.document.is_locked);
                const hint = (data.document && data.document.lock_hint) || '';
                const encExport = Boolean(data.document && data.document.encrypt_export);

                if (isLocked) {
                    currentDocIsLocked = true;
                    currentDocLockHint = hint;
                    currentDocEncryptExport = encExport;
                }
            }
        } catch (err) {
            console.warn('Could not inspect document lock status:', err);
        }
    }

    if (currentDocIsLocked) {
        if (activeBanner) activeBanner.style.display = 'flex';
        if (removeBtn) removeBtn.style.display = 'block';
        if (applyBtnText) applyBtnText.textContent = 'Update Security Lock 🔒';
        if (hintInput) hintInput.value = currentDocLockHint || '';
        if (checkEnc) checkEnc.checked = currentDocEncryptExport;
    } else {
        if (activeBanner) activeBanner.style.display = 'none';
        if (removeBtn) removeBtn.style.display = 'none';
        if (applyBtnText) applyBtnText.textContent = 'Apply Security Lock 🔒';
        if (hintInput) hintInput.value = '';
        if (checkEnc) checkEnc.checked = true;
        if (checkArch) checkArch.checked = true;
    }

    if (pinInput) pinInput.value = activeSessionPasscode || '';

    const feedback = document.getElementById('secLockFeedback');
    if (feedback) feedback.style.display = 'none';

    modal.style.display = 'flex';
    if (pinInput) pinInput.focus();
}

function closeDocumentSecurityModal() {
    const modal = document.getElementById('docSecurityModal');
    if (modal) modal.style.display = 'none';
}

function togglePasscodeVisibility(inputId) {
    const el = document.getElementById(inputId);
    if (!el) return;
    el.type = el.type === 'password' ? 'text' : 'password';
}

async function handleApplyDocumentLock() {
    const pinInput = document.getElementById('secLockPin');
    const hintInput = document.getElementById('secLockHint');
    const checkEnc = document.getElementById('secCheckEncryptExport');

    const pin = pinInput ? pinInput.value.trim() : '';
    const hint = hintInput ? hintInput.value.trim() : '';
    const encryptExport = checkEnc ? checkEnc.checked : true;

    if (pin.length < 4) {
        alert('Security PIN / Passcode must be at least 4 characters long.');
        if (pinInput) pinInput.focus();
        return;
    }

    activeSessionPasscode = pin;
    currentDocIsLocked = true;
    currentDocLockHint = hint;
    currentDocEncryptExport = encryptExport;
    updateStudioLockState(true, encryptExport);

    if (currentGeneratedDocId) {
        try {
            const resp = await fetch(`/api/documents/${currentGeneratedDocId}/lock/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken()
                },
                body: JSON.stringify({
                    action: 'lock',
                    pin: pin,
                    hint: hint,
                    encrypt_export: encryptExport
                })
            });

            const data = await resp.json();
            if (resp.ok && data.status === 'ok') {
                const sidebarItem = document.querySelector(`.doc-sidebar-item[data-doc-id="${currentGeneratedDocId}"]`) || document.querySelector(`.doc-sidebar-item[href*="${currentGeneratedDocId}"]`);
                if (sidebarItem) {
                    sidebarItem.classList.add('is-locked');
                    sidebarItem.setAttribute('data-locked', 'true');
                    sidebarItem.title = `🔒 Locked Document: ${sidebarItem.querySelector('.doc-item-title')?.textContent?.trim() || 'document'}`;
                    sidebarItem.onclick = (e) => handleArchiveDocumentClick(e, currentGeneratedDocId, true);
                    const titleEl = sidebarItem.querySelector('.doc-item-title');
                    if (titleEl && !titleEl.innerHTML.includes('sidebar-lock-badge')) {
                        titleEl.innerHTML += ' <span class="sidebar-lock-badge">🔒</span>';
                    }
                    const iconSvg = sidebarItem.querySelector('.doc-item-icon');
                    if (iconSvg) {
                        iconSvg.innerHTML = `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" class="text-maroon">
                            <rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect>
                            <path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
                        </svg>`;
                    }
                }
            }
        } catch (err) {
            console.warn('Error saving lock to server:', err);
        }
    }

    closeDocumentSecurityModal();
}

async function handleRemoveDocumentLock() {
    if (!currentGeneratedDocId) {
        activeSessionPasscode = '';
        currentDocIsLocked = false;
        currentDocLockHint = '';
        currentDocEncryptExport = false;
        updateStudioLockState(false, false);
        closeDocumentSecurityModal();
        return;
    }

    const pinInput = document.getElementById('secLockPin');
    const pin = (pinInput && pinInput.value.trim()) ? pinInput.value.trim() : (activeSessionPasscode || '');

    try {
        const resp = await fetch(`/api/documents/${currentGeneratedDocId}/lock/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify({
                action: 'unlock',
                pin: pin
            })
        });

        const data = await resp.json();
        if (resp.ok && data.status === 'ok') {
            activeSessionPasscode = '';
            currentDocIsLocked = false;
            currentDocLockHint = '';
            currentDocEncryptExport = false;
            updateStudioLockState(false, false);

            const sidebarItem = document.querySelector(`.doc-sidebar-item[data-doc-id="${currentGeneratedDocId}"]`) || document.querySelector(`.doc-sidebar-item[href*="${currentGeneratedDocId}"]`);
            if (sidebarItem) {
                sidebarItem.classList.remove('is-locked');
                sidebarItem.setAttribute('data-locked', 'false');
                sidebarItem.title = `Click to preview ${sidebarItem.querySelector('.doc-item-title')?.textContent?.trim() || 'document'}`;
                sidebarItem.onclick = (e) => handleArchiveDocumentClick(e, currentGeneratedDocId, false);
                const badge = sidebarItem.querySelector('.sidebar-lock-badge');
                if (badge) badge.remove();
                const iconSvg = sidebarItem.querySelector('.doc-item-icon');
                if (iconSvg) {
                    iconSvg.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                        <polyline points="14 2 14 8 20 8"></polyline>
                        <line x1="16" y1="13" x2="8" y2="13"></line>
                        <line x1="16" y1="17" x2="8" y2="17"></line>
                    </svg>`;
                }
            }

            closeDocumentSecurityModal();
            alert('Security lock removed successfully. Document is now fully unlocked.');
        } else {
            alert('Unlock error: ' + (data.error || 'Incorrect security PIN.'));
        }
    } catch (err) {
        alert('Communication error: ' + err.message);
    }
}

/* ==========================================================================
   Document Archive Access & PIN Verification
   ========================================================================== */

async function handleArchiveDocumentClick(event, docId, isLocked) {
    if (event) {
        event.preventDefault();
        event.stopPropagation();
    }
    pendingUnlockDocId = docId;

    try {
        const resp = await fetch(`/api/documents/${docId}/detail/`);
        const data = await resp.json();

        if (resp.ok) {
            if (data.status === 'locked') {
                // Show PIN prompt modal
                const modal = document.getElementById('docPinUnlockModal');
                const titleEl = document.getElementById('unlockDocTitle');
                const hintWrap = document.getElementById('unlockDocHintWrap');
                const hintText = document.getElementById('unlockDocHintText');
                const pinInput = document.getElementById('unlockDocPin');
                const errEl = document.getElementById('unlockErrorMessage');

                if (titleEl) titleEl.textContent = data.title;
                if (data.lock_hint) {
                    if (hintWrap) hintWrap.style.display = 'block';
                    if (hintText) hintText.textContent = data.lock_hint;
                } else {
                    if (hintWrap) hintWrap.style.display = 'none';
                }

                if (pinInput) pinInput.value = '';
                if (errEl) errEl.style.display = 'none';

                if (modal) modal.style.display = 'flex';
                if (pinInput) pinInput.focus();
            } else if (data.status === 'ok' && data.document) {
                // Already unlocked in this session: load directly into Studio
                loadDocumentIntoStudio(data.document);
            }
        }
    } catch (err) {
        console.warn('Error fetching locked document detail:', err);
    }
}

function closePinUnlockModal() {
    const modal = document.getElementById('docPinUnlockModal');
    if (modal) modal.style.display = 'none';
}

async function handleVerifyPinSubmit(targetAction) {
    if (!pendingUnlockDocId) return;

    const pinInput = document.getElementById('unlockDocPin');
    const errEl = document.getElementById('unlockErrorMessage');
    const pin = pinInput ? pinInput.value.trim() : '';

    if (!pin) {
        if (errEl) {
            errEl.textContent = 'Please enter your Security PIN.';
            errEl.style.display = 'block';
        }
        return;
    }

    try {
        const resp = await fetch(`/api/documents/${pendingUnlockDocId}/verify-pin/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify({ pin: pin })
        });

        const data = await resp.json();
        if (resp.ok && data.status === 'ok') {
            activeSessionPasscode = pin;
            closePinUnlockModal();

            if (targetAction === 'download_pdf') {
                const pdfUrl = data.document.pdf_download_url || `/api/documents/${data.document.document_id}/pdf/?pin=${encodeURIComponent(pin)}&decrypted=1`;
                window.location.href = pdfUrl;
            } else if (targetAction === 'download') {
                const docxUrl = data.document.download_url || `/api/documents/${data.document.document_id}/download/?pin=${encodeURIComponent(pin)}&decrypted=1`;
                window.location.href = docxUrl;
            } else {
                loadDocumentIntoStudio(data.document);
            }
        } else {
            if (errEl) {
                errEl.textContent = data.error || 'Incorrect Security PIN. Unauthorized access denied.';
                errEl.style.display = 'block';
            }
        }
    } catch (err) {
        if (errEl) {
            errEl.textContent = 'Communication error: ' + err.message;
            errEl.style.display = 'block';
        }
    }
}

function loadDocumentIntoStudio(doc) {
    currentGeneratedDocId = doc.document_id || doc.id;
    currentDocIsLocked = Boolean(doc.is_locked);
    currentDocEncryptExport = Boolean(doc.encrypt_export);
    currentDocLockHint = doc.lock_hint || '';

    if (!doc.is_locked) {
        activeSessionPasscode = '';
    }

    switchModalDocType(doc.doc_type, true); // preserve current generated doc context!

    // Pre-populate input fields
    if (doc.fields) {
        for (const [key, val] of Object.entries(doc.fields)) {
            const el = document.getElementById(`doc_field_${key}`);
            if (el && val) el.value = val;
        }
        const refInput = document.getElementById('formRefNo');
        const dateInput = document.getElementById('formDate');
        const dateText = document.getElementById('formDateText');

        if (refInput && doc.fields.reference_number) refInput.value = doc.fields.reference_number;
        if (dateInput && doc.fields.date) {
            dateInput.value = doc.fields.date;
            if (dateText) dateText.textContent = doc.fields.date;
            syncDateToPicker(doc.fields.date);
        }
        if (doc.fields.classification) {
            setClassification(doc.fields.classification);
        }
    }

    // Render live paper preview with actual content
    const container = document.getElementById('docPreviewContainer');
    if (container) {
        container.innerHTML = renderDocumentPaperPreview(doc, doc.fields);
        attachPaperEditListeners();
    }

    const saveStatus = document.getElementById('paperSaveStatus');
    if (saveStatus) {
        saveStatus.textContent = 'Word doc synced';
        saveStatus.classList.remove('dirty');
    }

    const sizeBadge = document.getElementById('downloadFileSizeBadge');
    if (sizeBadge && doc.file_size) sizeBadge.textContent = doc.file_size;

    updateStudioLockState(doc.is_locked, doc.encrypt_export);

    // Open studio modal
    const overlay = document.getElementById('documentModalOverlay');
    if (overlay) overlay.classList.add('active');
    setTimeout(resetStudioScroll, 50);
}


window.openDocumentSecurityModal = openDocumentSecurityModal;
window.closeDocumentSecurityModal = closeDocumentSecurityModal;
window.togglePasscodeVisibility = togglePasscodeVisibility;
window.handleApplyDocumentLock = handleApplyDocumentLock;
window.handleRemoveDocumentLock = handleRemoveDocumentLock;
window.handleArchiveDocumentClick = handleArchiveDocumentClick;
window.handleHistoryDocumentClick = handleArchiveDocumentClick;

// Delegate document link clicks anywhere in the chat to open studio preview window
document.addEventListener('click', (e) => {
    const link = e.target.closest('a[href*="/api/documents/"]');
    if (link && !link.classList.contains('doc-sidebar-item')) {
        const match = link.href.match(/\/api\/documents\/([0-9a-fA-F-]+)\//);
        if (match && match[1]) {
            e.preventDefault();
            handleArchiveDocumentClick(e, match[1], false);
        }
    }
});
window.closePinUnlockModal = closePinUnlockModal;
window.handleVerifyPinSubmit = handleVerifyPinSubmit;
window.loadDocumentIntoStudio = loadDocumentIntoStudio;
window.handleDocumentPdfDownload = handleDocumentPdfDownload;

/* ==========================================================================
   Officer Profile & Digital Signature Management
   ========================================================================== */

function openProfileSettingsModal(e) {
    if (e && typeof e.stopPropagation === 'function') e.stopPropagation();
    const modal = document.getElementById('profileSettingsModal');
    if (!modal) return;

    const fnInput = document.getElementById('profFirstName');
    const lnInput = document.getElementById('profLastName');
    const rankInput = document.getElementById('profRank');
    const appInput = document.getElementById('profAppointment');
    const authInput = document.getElementById('profAuthority');
    const deptInput = document.getElementById('profDepartment');
    const empInput = document.getElementById('profEmployeeId');
    const msgEl = document.getElementById('profSaveMessage');

    if (fnInput) fnInput.value = window.USER_FIRST_NAME || '';
    if (lnInput) lnInput.value = window.USER_LAST_NAME || '';
    if (rankInput) rankInput.value = window.USER_RANK || '';
    if (appInput) appInput.value = window.USER_APPOINTMENT || '';
    if (authInput) authInput.value = window.USER_AUTHORITY || '';
    if (deptInput) deptInput.value = window.USER_DEPT || 'Combat Engineering Wing';
    if (empInput) empInput.value = window.USER_EMP_ID || '';
    if (msgEl) msgEl.style.display = 'none';

    const sigStyle = window.USER_SIG_STYLE || 'military';
    const radios = document.querySelectorAll('input[name="profSigStyle"]');
    radios.forEach(r => {
        r.checked = (r.value === sigStyle);
    });

    modal.style.display = 'flex';
}

function closeProfileSettingsModal() {
    const modal = document.getElementById('profileSettingsModal');
    if (modal) modal.style.display = 'none';
}

async function handleSaveProfileSettings() {
    const fnInput = document.getElementById('profFirstName');
    const lnInput = document.getElementById('profLastName');
    const rankInput = document.getElementById('profRank');
    const appInput = document.getElementById('profAppointment');
    const authInput = document.getElementById('profAuthority');
    const deptInput = document.getElementById('profDepartment');
    const empInput = document.getElementById('profEmployeeId');
    const sigRadio = document.querySelector('input[name="profSigStyle"]:checked');
    const msgEl = document.getElementById('profSaveMessage');
    const btnSave = document.getElementById('btnSaveProfile');

    const payload = {
        first_name: fnInput ? fnInput.value.trim() : '',
        last_name: lnInput ? lnInput.value.trim() : '',
        rank: rankInput ? rankInput.value.trim() : '',
        appointment: appInput ? appInput.value.trim() : '',
        authority: authInput ? authInput.value.trim() : '',
        department: deptInput ? deptInput.value.trim() : 'Combat Engineering Wing',
        employee_id: empInput ? empInput.value.trim() : '',
        signature_style: sigRadio ? sigRadio.value : 'military'
    };

    if (btnSave) btnSave.disabled = true;

    try {
        const resp = await fetch('/api/profile/update/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify(payload)
        });

        const data = await resp.json();
        if (resp.ok && data.status === 'ok') {
            const prof = data.profile;
            window.USER_NAME = prof.display_name;
            window.USER_FIRST_NAME = prof.first_name;
            window.USER_LAST_NAME = prof.last_name;
            window.USER_RANK = prof.rank;
            window.USER_APPOINTMENT = prof.appointment;
            window.USER_AUTHORITY = prof.authority;
            window.USER_DEPT = prof.department;
            window.USER_EMP_ID = prof.employee_id;
            window.USER_SIG_STYLE = prof.signature_style;

            // Update sidebar footer
            const sName = document.getElementById('sidebarUserName');
            const sSub = document.getElementById('sidebarUserSub');
            const sAvatar = document.getElementById('sidebarUserAvatar');
            if (sName) sName.textContent = prof.display_name;
            if (sSub) {
                const parts = [];
                if (prof.rank) parts.push(prof.rank);
                if (prof.department) parts.push(prof.department);
                sSub.textContent = parts.join(' • ') || `ID: ${prof.employee_id || 'User'}`;
            }
            if (sAvatar && prof.display_name) {
                sAvatar.textContent = prof.display_name.charAt(0).toUpperCase();
            }

            // Sync studio left-pane signatory inputs if present
            const inName = document.getElementById('doc_field_from_name');
            const inRank = document.getElementById('doc_field_from_rank');
            const inApp = document.getElementById('doc_field_from_appointment');
            const inAuth = document.getElementById('doc_field_from_authority');
            const inDept = document.getElementById('doc_field_from_department');
            if (inName && !inName.value) inName.value = prof.display_name;
            if (inRank && !inRank.value) inRank.value = prof.rank;
            if (inApp && !inApp.value) inApp.value = prof.appointment;
            if (inAuth && !inAuth.value) inAuth.value = prof.authority;
            if (inDept && !inDept.value) inDept.value = prof.department;

            if (msgEl) {
                msgEl.textContent = 'Officer credentials updated successfully!';
                msgEl.style.color = '#15803d';
                msgEl.style.background = '#dcfce7';
                msgEl.style.display = 'block';
            }

            setTimeout(() => {
                closeProfileSettingsModal();
            }, 600);
        } else {
            if (msgEl) {
                msgEl.textContent = data.error || 'Failed to update profile';
                msgEl.style.color = '#b91c1c';
                msgEl.style.background = '#fee2e2';
                msgEl.style.display = 'block';
            }
        }
    } catch (err) {
        if (msgEl) {
            msgEl.textContent = 'Communication error: ' + err.message;
            msgEl.style.color = '#b91c1c';
            msgEl.style.background = '#fee2e2';
            msgEl.style.display = 'block';
        }
    } finally {
        if (btnSave) btnSave.disabled = false;
    }
}

/* In-Studio Quick Signature Editor */
let currentPreviewSigStyle = 'military';

function openSignatureQuickModal(e) {
    if (e && typeof e.stopPropagation === 'function') e.stopPropagation();
    const modal = document.getElementById('signatureQuickModal');
    if (!modal) return;

    const nameEl = document.getElementById('docPaperSignName');
    const rankEl = document.getElementById('docPaperSignRank');
    const appEl = document.getElementById('docPaperSignAppointment');
    const authEl = document.getElementById('docPaperSignAuthority');

    const qName = document.getElementById('quickSignName');
    const qRank = document.getElementById('quickSignRank');
    const qApp = document.getElementById('quickSignApp');
    const qAuth = document.getElementById('quickSignAuth');

    if (qName) qName.value = nameEl ? nameEl.textContent.replace(/[()]/g, '').trim() : (window.USER_NAME || '');
    if (qRank) qRank.value = rankEl ? rankEl.textContent.trim() : (window.USER_RANK || '');
    if (qApp) qApp.value = appEl ? appEl.textContent.trim() : (window.USER_APPOINTMENT || '');
    if (qAuth) qAuth.value = authEl ? authEl.textContent.trim() : (window.USER_AUTHORITY || '');

    const radios = document.querySelectorAll('input[name="quickSigStyle"]');
    radios.forEach(r => {
        r.checked = (r.value === currentPreviewSigStyle);
    });

    modal.style.display = 'flex';
}

function closeSignatureQuickModal() {
    const modal = document.getElementById('signatureQuickModal');
    if (modal) modal.style.display = 'none';
}

function handleSaveQuickSignature() {
    const qName = document.getElementById('quickSignName');
    const qRank = document.getElementById('quickSignRank');
    const qApp = document.getElementById('quickSignApp');
    const qAuth = document.getElementById('quickSignAuth');
    const qStyle = document.querySelector('input[name="quickSigStyle"]:checked');

    const nameVal = qName ? qName.value.trim() : '';
    const rankVal = qRank ? qRank.value.trim() : '';
    const appVal = qApp ? qApp.value.trim() : '';
    const authVal = qAuth ? qAuth.value.trim() : '';
    if (qStyle) currentPreviewSigStyle = qStyle.value;

    // Update left-pane form fields
    const inName = document.getElementById('doc_field_from_name');
    const inRank = document.getElementById('doc_field_from_rank');
    const inApp = document.getElementById('doc_field_from_appointment');
    const inAuth = document.getElementById('doc_field_from_authority');
    if (inName) inName.value = nameVal;
    if (inRank) inRank.value = rankVal;
    if (inApp) inApp.value = appVal;
    if (inAuth) inAuth.value = authVal;

    // Re-render paper preview with updated fields and style
    const fields = extractPaperAllFields();
    fields.from_name = nameVal;
    fields.from_rank = rankVal;
    fields.from_appointment = appVal;
    fields.from_authority = authVal;
    fields.signature_style = currentPreviewSigStyle;

    const container = document.getElementById('docPreviewContainer');
    if (container) {
        const dummyDoc = {
            doc_type: currentDocType,
            generated_content: extractPaperBodyText()
        };
        container.innerHTML = renderDocumentPaperPreview(dummyDoc, fields);
        attachPaperEditListeners();
    }

    closeSignatureQuickModal();
    saveDocumentContentChanges();
}

function togglePreviewSigStyle() {
    currentPreviewSigStyle = (currentPreviewSigStyle === 'eoffice') ? 'military' : 'eoffice';
    const fields = extractPaperAllFields();
    fields.signature_style = currentPreviewSigStyle;

    const container = document.getElementById('docPreviewContainer');
    if (container) {
        const dummyDoc = {
            doc_type: currentDocType,
            generated_content: extractPaperBodyText()
        };
        container.innerHTML = renderDocumentPaperPreview(dummyDoc, fields);
        attachPaperEditListeners();
    }
    saveDocumentContentChanges();
}

window.openProfileSettingsModal = openProfileSettingsModal;
window.closeProfileSettingsModal = closeProfileSettingsModal;
window.handleSaveProfileSettings = handleSaveProfileSettings;
window.openSignatureQuickModal = openSignatureQuickModal;
window.closeSignatureQuickModal = closeSignatureQuickModal;
window.handleSaveQuickSignature = handleSaveQuickSignature;
window.togglePreviewSigStyle = togglePreviewSigStyle;


// ==============================================================================
// V3.8 Enhancements: Toast, Signature Asset Bank, PDF Preview, Finalize & Shortcuts
// ==============================================================================

function showToast(message, type = 'success') {
    const existing = document.getElementById('sarvatraToast');
    if (existing) existing.remove();

    const toast = document.createElement('div');
    toast.id = 'sarvatraToast';
    toast.className = `toast-${type}`;

    let icon = '✓';
    if (type === 'error') icon = '⚠';
    else if (type === 'info') icon = 'ℹ';

    toast.innerHTML = `<span style="font-weight:700;">${icon}</span> <span>${escapeHtml(message)}</span>`;
    document.body.appendChild(toast);

    setTimeout(() => {
        if (toast && toast.parentNode) {
            toast.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
            toast.style.opacity = '0';
            toast.style.transform = 'translateY(8px)';
            setTimeout(() => toast.remove(), 320);
        }
    }, 2800);
}

let userSignatureAssets = [];
let activeSignatureAssetId = '';

async function loadSignatureAssets() {
    try {
        const resp = await fetch('/api/signatures/');
        if (!resp.ok) return;
        const data = await resp.json();
        userSignatureAssets = data.signatures || [];
        renderSignatureAssetsList(userSignatureAssets);
        populateSignatureAssetDropdown(userSignatureAssets);
    } catch (err) {
        console.warn('Could not fetch signature assets:', err);
    }
}

function renderSignatureAssetsList(sigs) {
    const listEl = document.getElementById('sigAssetList');
    if (!listEl) return;

    if (!sigs.length) {
        listEl.innerHTML = '<div style="font-size: 0.74rem; color: #64748b; padding: 6px 0;">No signature images uploaded yet. Upload a PNG file below.</div>';
        return;
    }

    listEl.innerHTML = sigs.map(s => `
        <div class="sig-asset-card ${s.is_default ? 'sig-asset-default' : ''}" data-id="${s.id}">
            <img src="${s.url}" alt="${escapeHtml(s.label)}" class="sig-asset-img" />
            <div class="sig-asset-label" title="${escapeHtml(s.label)}">${escapeHtml(s.label)}</div>
            <div class="sig-asset-actions">
                ${!s.is_default ? `<button type="button" class="btn-sig-action" onclick="setDefaultSig('${s.id}')" title="Set as default">Default</button>` : '<span style="font-size:0.68rem; color:#22c55e; font-weight:700;">✓ Default</span>'}
                <button type="button" class="btn-sig-action btn-sig-delete" onclick="deleteSig('${s.id}')" title="Delete">Del</button>
            </div>
        </div>
    `).join('');
}

function populateSignatureAssetDropdown(sigs) {
    const sel = document.getElementById('doc_field_signature_asset');
    if (!sel) return;

    const currentVal = sel.value;
    let opts = `
        <option value="">Default Signature (From Profile)</option>
        <option value="none">No Signature (Leave Blank for Physical Signing)</option>
    `;

    sigs.forEach(s => {
        opts += `<option value="${s.id}">${escapeHtml(s.label)}${s.is_default ? ' (Default)' : ''}</option>`;
    });

    sel.innerHTML = opts;
    if (activeSignatureAssetId) {
        sel.value = activeSignatureAssetId;
    } else if (currentVal) {
        sel.value = currentVal;
    }
}

async function handleSignatureFileUpload(event) {
    const file = event.target.files && event.target.files[0];
    if (!file) return;

    const labelInput = document.getElementById('sigAssetLabelInput');
    const label = (labelInput && labelInput.value.trim()) ? labelInput.value.trim() : 'Official Signature';

    const fd = new FormData();
    fd.append('signature_image', file);
    fd.append('label', label);

    try {
        const resp = await fetch('/api/signatures/upload/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCsrfToken()
            },
            body: fd
        });
        const data = await resp.json();
        if (resp.ok && data.status === 'ok') {
            showToast('Signature image uploaded successfully', 'success');
            if (labelInput) labelInput.value = '';
            event.target.value = '';
            loadSignatureAssets();
        } else {
            showToast(data.error || 'Signature upload failed', 'error');
        }
    } catch (e) {
        showToast('Signature upload error', 'error');
    }
}

async function setDefaultSig(id) {
    try {
        const resp = await fetch(`/api/signatures/${id}/set-default/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCsrfToken()
            }
        });
        const data = await resp.json();
        if (resp.ok && data.status === 'ok') {
            showToast('Default signature updated', 'success');
            loadSignatureAssets();
        }
    } catch (e) {
        showToast('Failed to set default signature', 'error');
    }
}

async function deleteSig(id) {
    if (!confirm('Are you sure you want to remove this signature file?')) return;
    try {
        const resp = await fetch(`/api/signatures/${id}/delete/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCsrfToken()
            }
        });
        const data = await resp.json();
        if (resp.ok && data.status === 'ok') {
            showToast('Signature removed', 'info');
            loadSignatureAssets();
        }
    } catch (e) {
        showToast('Failed to delete signature', 'error');
    }
}

function onSignatureAssetChanged(val) {
    activeSignatureAssetId = val;
    const fields = extractPaperAllFields();
    if (val === 'none') {
        fields._signature_asset_id = 'none';
        fields._no_signature = true;
    } else {
        fields._signature_asset_id = val;
        fields._no_signature = false;
    }

    const container = document.getElementById('docPreviewContainer');
    if (container) {
        const dummyDoc = {
            doc_type: currentDocType,
            generated_content: extractPaperBodyText()
        };
        container.innerHTML = renderDocumentPaperPreview(dummyDoc, fields);
        attachPaperEditListeners();
    }
    saveDocumentContentChanges();
}

// Document Finalize Toggle (DRAFT watermark remover)
async function handleToggleFinalDoc() {
    if (!currentGeneratedDocId) {
        showToast('Generate a document first', 'info');
        return;
    }

    try {
        const resp = await fetch(`/api/documents/${currentGeneratedDocId}/toggle-final/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify({})
        });
        const data = await resp.json();
        if (resp.ok && data.status === 'ok') {
            updateFinalizeButtonState(data.is_final);
            showToast(data.message, 'success');
        } else {
            showToast(data.error || 'Could not toggle document status', 'error');
        }
    } catch (e) {
        showToast('Error toggling document status', 'error');
    }
}

function updateFinalizeButtonState(isFinal) {
    const btn = document.getElementById('btnStudioFinal');
    const txt = document.getElementById('btnStudioFinalText');
    const icon = document.getElementById('btnStudioFinalIcon');
    if (!btn) return;

    if (isFinal) {
        btn.classList.add('is-finalized');
        if (txt) txt.textContent = 'Finalized';
        if (icon) icon.textContent = '✓';
        btn.title = 'Document is marked FINAL (No DRAFT watermark). Click to revert to Draft.';
    } else {
        btn.classList.remove('is-finalized');
        if (txt) txt.textContent = 'Mark as Final';
        if (icon) icon.textContent = '📝';
        btn.title = 'Click to finalize document and remove DRAFT watermark on PDF.';
    }
}

// Military PDF Preview Modal
function openPdfPreview(pdfUrl, title = 'Military Document Preview') {
    const modal = document.getElementById('pdfPreviewModal');
    const frame = document.getElementById('pdfPreviewFrame');
    const titleEl = document.getElementById('pdfPreviewTitle');
    if (!modal || !frame) return;

    if (titleEl) titleEl.textContent = title;
    const separator = pdfUrl.includes('?') ? '&' : '?';
    frame.src = `${pdfUrl}${separator}preview=1`;
    modal.style.display = 'flex';
}

function closePdfPreview(e) {
    if (e && e.target && e.target.id !== 'pdfPreviewModal' && !e.target.classList.contains('sec-modal-close')) {
        return;
    }
    const modal = document.getElementById('pdfPreviewModal');
    const frame = document.getElementById('pdfPreviewFrame');
    if (modal) modal.style.display = 'none';
    if (frame) frame.src = '';
}

function openActivePdfPreview() {
    if (!currentGeneratedDocId) {
        showToast('Please formulate or generate a document first', 'info');
        return;
    }
    const docTitle = document.getElementById('docPaperSubj') ? document.getElementById('docPaperSubj').textContent.trim() : 'Official Document';
    openPdfPreview(`/api/documents/${currentGeneratedDocId}/pdf/`, docTitle);
}

function printPdfFrame() {
    const frame = document.getElementById('pdfPreviewFrame');
    if (frame && frame.contentWindow) {
        frame.contentWindow.focus();
        frame.contentWindow.print();
    }
}

// Global Keyboard Shortcuts
document.addEventListener('keydown', function(e) {
    // 1. Ctrl+Enter or Cmd+Enter -> Send message in chat or confirm in studio
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        const chatInput = document.getElementById('chatInput');
        if (document.activeElement === chatInput) {
            e.preventDefault();
            const sendBtn = document.getElementById('sendBtn');
            if (sendBtn) sendBtn.click();
            return;
        }
        const studioRegen = document.getElementById('docRegenerateComment');
        if (document.activeElement === studioRegen) {
            e.preventDefault();
            handleDocumentRegenerate();
            return;
        }
    }

    // 2. Ctrl+D or Cmd+D -> Toggle Document Studio
    if ((e.ctrlKey || e.metaKey) && (e.key === 'd' || e.key === 'D')) {
        // Prevent browser bookmark shortcut
        e.preventDefault();
        const studioOverlay = document.getElementById('documentModalOverlay');
        if (studioOverlay && studioOverlay.classList.contains('active')) {
            closeDocumentModal();
        } else {
            openDocumentPickerModal();
        }
        return;
    }

    // 3. Escape -> Close highest active modal
    if (e.key === 'Escape') {
        const previewModal = document.getElementById('pdfPreviewModal');
        if (previewModal && previewModal.style.display === 'flex') {
            closePdfPreview();
            return;
        }

        const secModal = document.getElementById('docSecurityModal');
        if (secModal && secModal.style.display === 'flex') {
            closeDocumentSecurityModal();
            return;
        }

        const pinModal = document.getElementById('docPinUnlockModal');
        if (pinModal && pinModal.style.display === 'flex') {
            closePinUnlockModal();
            return;
        }

        const quickModal = document.getElementById('signatureQuickModal');
        if (quickModal && quickModal.style.display === 'flex') {
            closeSignatureQuickModal();
            return;
        }

        const profModal = document.getElementById('profileSettingsModal');
        if (profModal && profModal.style.display === 'flex') {
            closeProfileSettingsModal();
            return;
        }

        const studioOverlay = document.getElementById('documentModalOverlay');
        if (studioOverlay && studioOverlay.classList.contains('active')) {
            closeDocumentModal();
            return;
        }
    }
});

// Hook signature loading into profile open
const _origOpenProfModal = openProfileSettingsModal;
openProfileSettingsModal = function(e) {
    _origOpenProfModal(e);
    loadSignatureAssets();
};


window.showToast = showToast;
window.loadSignatureAssets = loadSignatureAssets;
window.handleSignatureFileUpload = handleSignatureFileUpload;
window.setDefaultSig = setDefaultSig;
window.deleteSig = deleteSig;
window.onSignatureAssetChanged = onSignatureAssetChanged;
window.handleToggleFinalDoc = handleToggleFinalDoc;
window.openPdfPreview = openPdfPreview;
window.closePdfPreview = closePdfPreview;
window.openActivePdfPreview = openActivePdfPreview;
window.printPdfFrame = printPdfFrame;
