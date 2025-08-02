document.addEventListener('DOMContentLoaded', () => {
    const chatForm = document.getElementById('chatForm');
    const messageInput = document.getElementById('messageInput');
    const sendButton = document.getElementById('sendButton');
    const chatBox = document.getElementById('chatBox');
    const loaderContainer = document.getElementById('loaderContainer');

    const pdfForm = document.getElementById('pdfForm');
    const pdfResult = document.getElementById('pdfResult');
    const uploadBtn = document.getElementById('uploadBtn');
    const pdfFileInput = document.getElementById('pdfFile');

    const sessionId = "web-user-123";

    const websocket = new WebSocket(`ws://localhost:8000/ws?session_id=${sessionId}`);

    websocket.onopen = () => {
        console.log("WebSocket connected.");
    };

    websocket.onmessage = (event) => {
        const botMessage = event.data;
        hideLoader();
        appendMessage(botMessage, 'bot-message', '🤖');
        enableInput();
    };

    websocket.onclose = () => {
        hideLoader();
        appendMessage("Chat session ended. Please refresh to restart.", 'bot-message', '⚠️');
        disableInput();
        console.log("WebSocket closed.");
    };

    websocket.onerror = (err) => {
        hideLoader();
        appendMessage("An error occurred with the chat connection.", 'bot-message', '❌');
        disableInput();
        console.error("WebSocket error:", err);
    };

    chatForm.addEventListener('submit', (e) => {
        e.preventDefault();
        sendMessage();
    });

    pdfForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        if (!pdfFileInput.files.length) {
            pdfResult.textContent = "Please choose a PDF file.";
            return;
        }

        uploadBtn.disabled = true;
        pdfResult.textContent = "Uploading and extracting...";
        const formData = new FormData(pdfForm);

        // normalize the checkbox into boolean
        if (!pdfForm.use_ocr.checked) {
            formData.delete("use_ocr");
        } else {
            formData.set("use_ocr", "true");
        }

        try {
            const resp = await fetch('/upload-pdf', {
                method: 'POST',
                body: formData,
            });
            const json = await resp.json();
            if (json.download_endpoint) {
                pdfResult.innerHTML = `
                    ✅ Extraction complete. <a href="${json.download_endpoint}" target="_blank" rel="noreferrer">Download CSV</a>
                `;
            } else {
                pdfResult.textContent = `Error: ${json.error || 'Unknown error'}`;
            }
        } catch (err) {
            console.error(err);
            pdfResult.textContent = "Upload failed. Check console for details.";
        } finally {
            uploadBtn.disabled = false;
        }
    });

    function sendMessage() {
        const message = messageInput.value.trim();
        if (!message) return;

        appendMessage(message, 'user-message', '😀');
        websocket.send(message);
        messageInput.value = '';
        showLoader();
        disableInput();
    }

    function appendMessage(text, type, avatarChar) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message', type);

        const avatarSpan = document.createElement('span');
        avatarSpan.classList.add('avatar', type === 'user-message' ? 'user-avatar' : 'bot-avatar');
        avatarSpan.textContent = avatarChar;

        const contentDiv = document.createElement('div');
        contentDiv.classList.add('message-content');
        contentDiv.textContent = text;

        if (type === 'user-message') {
            messageDiv.appendChild(contentDiv);
            messageDiv.appendChild(avatarSpan);
        } else {
            messageDiv.appendChild(avatarSpan);
            messageDiv.appendChild(contentDiv);
        }

        chatBox.appendChild(messageDiv);
        chatBox.scrollTop = chatBox.scrollHeight;
    }

    function showLoader() {
        loaderContainer.style.display = 'flex';
        chatBox.scrollTop = chatBox.scrollHeight;
    }

    function hideLoader() {
        loaderContainer.style.display = 'none';
    }

    function disableInput() {
        messageInput.disabled = true;
        sendButton.disabled = true;
        messageInput.placeholder = "Please wait...";
    }

    function enableInput() {
        messageInput.disabled = false;
        sendButton.disabled = false;
        messageInput.placeholder = "Ask me anything...";
        messageInput.focus();
    }
});
