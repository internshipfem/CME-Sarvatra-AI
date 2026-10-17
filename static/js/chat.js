/**
 * Air-Gapped Ollama ChatGPT Client Application
 * 100% Self-Contained Offline JavaScript
 */

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
    initMarkdownAndHighlighting();
    initExistingMessages();
    setupTextareaAutoresize();
    setupDragAndDrop();
    setupSidebarToggle();
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
    return enhanceCodeBlocks(html);
}

function enhanceCodeBlocks(html) {
    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = html;

    tempDiv.querySelectorAll('pre code').forEach((codeBlock) => {
        const pre = codeBlock.parentElement;
        const codeText = codeBlock.textContent;

        // Try highlighting with highlight.js if available
        if (typeof hljs !== 'undefined') {
            try {
                hljs.highlightElement(codeBlock);
            } catch (e) {
                // Ignore highlight errors
            }
        }

        // Get language
        let lang = 'code';
        const classes = codeBlock.className.split(' ');
        for (const c of classes) {
            if (c.startsWith('language-')) {
                lang = c.replace('language-', '');
                break;
            }
        }

        // Create sleek wrapper with header & copy button
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

        const copyBtn = header.querySelector('.btn-copy-code');
        copyBtn.addEventListener('click', () => {
            copyToClipboard(codeText, copyBtn);
        });

        // Insert wrapper
        pre.parentNode.insertBefore(wrapper, pre);
        wrapper.appendChild(header);
        wrapper.appendChild(pre);
    });

    return tempDiv.innerHTML;
}

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

    } catch (err) {
        if (err.name === 'AbortError') {
            bubbleTarget.innerHTML = renderMarkdownText(accumulatedText + '\n\n*(Generation stopped by user)*');
        } else {
            bubbleTarget.innerHTML = renderMarkdownText(accumulatedText + `\n\n**Error:** ${err.message}`);
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
        <div class="message-avatar">🤖</div>
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
            <div class="message-metrics-bar"></div>
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
        html += `<span class="metric-pill speed" title="Total response generation time">⚡ ${metrics.total_time}s</span>`;
    }
    if (metrics.tokens_per_second) {
        html += `<span class="metric-pill speed" title="Generation speed">🚀 ${metrics.tokens_per_second} tok/s</span>`;
    }
    if (metrics.eval_count) {
        html += `<span class="metric-pill" title="Tokens evaluated">📊 ${metrics.eval_count} tokens</span>`;
    }
    if (metrics.load_time) {
        html += `<span class="metric-pill" title="Model load latency">⏱️ Load: ${metrics.load_time}s</span>`;
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
        html += `
            <div class="staged-file-badge">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#3b82f6" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                    <polyline points="14 2 14 8 20 8"></polyline>
                </svg>
                <span>${escapeHtml(f.name)} (${escapeHtml(f.size)})</span>
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

function setupSidebarToggle() {
    const toggleBtn = document.getElementById('sidebarToggle');
    const sidebar = document.getElementById('sidebar');
    if (toggleBtn && sidebar) {
        toggleBtn.addEventListener('click', () => {
            sidebar.classList.toggle('open');
        });
    }
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
