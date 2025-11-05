/**
 * ═══════════════════════════════════════════════════════════════════════════
 * 🤖 PROFESSIONAL CHATBOT - REAL API INTEGRATION
 * ═══════════════════════════════════════════════════════════════════════════
 * 
 * Features:
 * - Real-time API integration with onboarding-kyc-flow.js
 * - PDF OCR via /api/vision endpoint
 * - Session management
 * - File upload with drag & drop
 * - Progress tracking
 * - Error handling with retry
 * 
 * ═══════════════════════════════════════════════════════════════════════════
 */

// API Configuration
const API_BASE = window.location.origin;
const ONBOARDING_API = `${API_BASE}/api/onboarding`;
const VISION_API = `${API_BASE}/api/vision`;

// State Management
class ChatState {
    constructor() {
        this.sessionId = null;
        this.messages = [];
        this.userData = {};
        this.currentInputType = null;
        this.isProcessing = false;
        this.progress = { current: 0, total: 10 };
    }

    addMessage(type, text, options = {}) {
        const message = {
            id: Date.now(),
            type, // 'bot', 'user', 'system', 'error'
            text,
            timestamp: new Date().toISOString(),
            ...options
        };
        this.messages.push(message);
        return message;
    }

    updateProgress(current, label) {
        this.progress.current = current;
        this.progress.label = label;
        const percent = Math.round((current / this.progress.total) * 100);
        updateProgressBar(percent, label);
    }
}

const state = new ChatState();

// DOM Elements
const elements = {
    messagesWrapper: document.getElementById('messagesWrapper'),
    messagesContainer: document.getElementById('messagesContainer'),
    inputContainer: document.getElementById('inputContainer'),
    textInputWrapper: document.getElementById('textInputWrapper'),
    fileUploadWrapper: document.getElementById('fileUploadWrapper'),
    messageInput: document.getElementById('messageInput'),
    sendBtn: document.getElementById('sendBtn'),
    startBtn: document.getElementById('startBtn'),
    startButtonContainer: document.getElementById('startButtonContainer'),
    typingIndicator: document.getElementById('typingIndicator'),
    progressFill: document.getElementById('progressFill'),
    progressLabel: document.getElementById('progressLabel'),
    progressPercent: document.getElementById('progressPercent'),
    fileDropZone: document.getElementById('fileDropZone'),
    fileInput: document.getElementById('fileInput'),
    browseBtn: document.getElementById('browseBtn'),
    filePreview: document.getElementById('filePreview'),
    fileName: document.getElementById('fileName'),
    fileSize: document.getElementById('fileSize'),
    fileRemoveBtn: document.getElementById('fileRemoveBtn'),
    uploadBtn: document.getElementById('uploadBtn')
};

let selectedFile = null;

// ═══════════════════════════════════════════════════════════════════════════
// INITIALIZATION
// ═══════════════════════════════════════════════════════════════════════════

document.addEventListener('DOMContentLoaded', () => {
    console.log('🤖 Chatbot initialized');
    setupEventListeners();
});

function setupEventListeners() {
    // Start button
    elements.startBtn.addEventListener('click', startOnboarding);

    // Text input
    elements.messageInput.addEventListener('input', (e) => {
        elements.sendBtn.disabled = !e.target.value.trim();
    });

    elements.messageInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    elements.sendBtn.addEventListener('click', sendMessage);

    // File upload
    elements.browseBtn.addEventListener('click', () => elements.fileInput.click());
    elements.fileInput.addEventListener('change', handleFileSelect);
    elements.fileRemoveBtn.addEventListener('click', clearFileSelection);
    elements.uploadBtn.addEventListener('click', uploadFile);

    // Drag & drop
    elements.fileDropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        elements.fileDropZone.classList.add('drag-over');
    });

    elements.fileDropZone.addEventListener('dragleave', () => {
        elements.fileDropZone.classList.remove('drag-over');
    });

    elements.fileDropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        elements.fileDropZone.classList.remove('drag-over');
        const file = e.dataTransfer.files[0];
        if (file) {
            handleFile(file);
        }
    });

    elements.fileDropZone.addEventListener('click', () => {
        elements.fileInput.click();
    });
}

// ═══════════════════════════════════════════════════════════════════════════
// ONBOARDING FLOW
// ═══════════════════════════════════════════════════════════════════════════

async function startOnboarding() {
    try {
        elements.startBtn.disabled = true;
        elements.startBtn.classList.add('loading');

        showTypingIndicator();

        // Call /api/onboarding/start
        const response = await fetch(`${ONBOARDING_API}/start`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Failed to start session');
        }

        state.sessionId = data.sessionId;
        console.log('✅ Session started:', state.sessionId);

        // Hide start button
        elements.startButtonContainer.style.display = 'none';

        // Show bot response
        hideTypingIndicator();
        addBotMessage(data.text);

        // Update progress
        state.updateProgress(1, 'Email collection');

        // Show appropriate input
        showInput(data.inputType || 'text');

    } catch (error) {
        console.error('❌ Start error:', error);
        hideTypingIndicator();
        addErrorMessage('Failed to start session. Please refresh and try again.');
        elements.startBtn.disabled = false;
        elements.startBtn.classList.remove('loading');
    }
}

async function sendMessage() {
    const message = elements.messageInput.value.trim();
    if (!message || state.isProcessing) return;

    try {
        state.isProcessing = true;
        elements.sendBtn.disabled = true;

        // Add user message to UI
        addUserMessage(message);

        // Clear input
        elements.messageInput.value = '';

        // Hide input temporarily
        hideInput();

        // Show typing indicator
        showTypingIndicator();

        // Call /api/onboarding/message
        const response = await fetch(`${ONBOARDING_API}/message`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                sessionId: state.sessionId,
                message
            })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Failed to send message');
        }

        // Hide typing indicator
        hideTypingIndicator();

        // Show bot response
        addBotMessage(data.text);

        // Update progress
        updateProgressFromState(data);

        // Show appropriate input
        if (data.requiresInput) {
            showInput(data.inputType || 'text');
        }

        // Store data
        if (data.vendorCode) {
            state.userData.vendorCode = data.vendorCode;
            console.log('✅ Vendor Code:', data.vendorCode);
        }

    } catch (error) {
        console.error('❌ Send error:', error);
        hideTypingIndicator();
        addErrorMessage(error.message);
        showInput('text');
    } finally {
        state.isProcessing = false;
    }
}

// ═══════════════════════════════════════════════════════════════════════════
// FILE UPLOAD
// ═══════════════════════════════════════════════════════════════════════════

function handleFileSelect(e) {
    const file = e.target.files[0];
    if (file) {
        handleFile(file);
    }
}

function handleFile(file) {
    // Validate file
    const maxSize = 10 * 1024 * 1024; // 10MB
    const allowedTypes = ['application/pdf', 'image/jpeg', 'image/png', 'image/jpg'];

    if (!allowedTypes.includes(file.type)) {
        addErrorMessage('Invalid file type. Please upload PDF, JPG, or PNG.');
        return;
    }

    if (file.size > maxSize) {
        addErrorMessage('File too large. Maximum size is 10MB.');
        return;
    }

    selectedFile = file;

    // Show preview
    elements.fileName.textContent = file.name;
    elements.fileSize.textContent = formatFileSize(file.size);
    elements.fileDropZone.style.display = 'none';
    elements.filePreview.style.display = 'block';
}

function clearFileSelection() {
    selectedFile = null;
    elements.fileInput.value = '';
    elements.fileDropZone.style.display = 'block';
    elements.filePreview.style.display = 'none';
}

async function uploadFile() {
    if (!selectedFile || state.isProcessing) return;

    try {
        state.isProcessing = true;
        elements.uploadBtn.disabled = true;
        elements.uploadBtn.classList.add('loading');

        // Add user message
        addUserMessage(`📄 Uploaded: ${selectedFile.name}`);

        // Hide file input
        hideInput();

        // Show processing message
        showTypingIndicator();
        addSystemMessage('Processing your document... This may take a moment.');

        // Check if it's a PDF (needs OCR) or image
        const isPDF = selectedFile.type === 'application/pdf';

        if (isPDF) {
            // Use /api/vision for PDF OCR
            await uploadGSTPDF();
        } else {
            // Use /api/onboarding/upload-file for images
            await uploadRegularFile();
        }

    } catch (error) {
        console.error('❌ Upload error:', error);
        hideTypingIndicator();
        addErrorMessage(error.message);
        showInput('file');
    } finally {
        state.isProcessing = false;
        elements.uploadBtn.disabled = false;
        elements.uploadBtn.classList.remove('loading');
        clearFileSelection();
    }
}

async function uploadGSTPDF() {
    try {
        console.log('📄 Processing GST PDF with Vision API...');
        
        // Step 1: Convert PDF to images using PDF.js (same as Vision OCR page)
        console.log('🔄 Converting PDF to images...');
        const pdfImages = await convertPDFToImages(selectedFile);
        console.log(`✅ Converted PDF to ${pdfImages.length} images`);
        
        // Step 2: Call Vision API for each page (or just first few pages)
        console.log('🔍 Calling Vision API for OCR extraction...');
        
        let allExtractedText = '';
        
        // Process all pages (or limit to first 3 for speed)
        const pagesToProcess = Math.min(pdfImages.length, 3);
        
        for (let i = 0; i < pagesToProcess; i++) {
            console.log(`📄 Processing page ${i + 1}/${pagesToProcess}...`);
            
            const visionResponse = await fetch(VISION_API, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    imageBase64: pdfImages[i],
                    prompt: `Extract all information from this GST certificate page. Please provide:
1. GSTIN (GST Identification Number)
2. Legal Name (company legal name)
3. Trade Name
4. Constitution of Business (e.g., Private Limited Company, Partnership, etc.)
5. Complete Address (floor, building, street, city, state, pincode)
6. Directors/Partners names
7. Date of registration
8. Any other relevant details

Format the response clearly with all extracted information.`
                })
            });

            const visionData = await visionResponse.json();

            if (!visionResponse.ok) {
                console.error(`❌ Vision API error on page ${i + 1}:`, visionData);
                console.error('❌ Error details:', {
                    status: visionResponse.status,
                    error: visionData.error,
                    details: visionData.details,
                    hint: visionData.hint
                });
                throw new Error(visionData.error || visionData.hint || 'OCR failed. Please try again.');
            }

            allExtractedText += `\n\n=== PAGE ${i + 1} ===\n${visionData.content}`;
            console.log(`✅ Page ${i + 1} processed successfully!`);
        }

        console.log('✅ All pages processed successfully!');
        
        // Step 3: Upload to backend with the file
        console.log('📤 Uploading GST data to backend...');
        const formData = new FormData();
        formData.append('file', selectedFile);
        formData.append('sessionId', state.sessionId);
        
        // Include the combined OCR result for backend processing
        if (allExtractedText) {
            formData.append('ocrText', allExtractedText);
        }

        const uploadResponse = await fetch(`${ONBOARDING_API}/upload-gst`, {
            method: 'POST',
            body: formData
        });

        const uploadData = await uploadResponse.json();

        if (!uploadResponse.ok) {
            throw new Error(uploadData.error || 'Upload failed');
        }

        console.log('✅ GST data uploaded successfully');
        hideTypingIndicator();

        // Show extracted data from Vision API
        if (allExtractedText) {
            addBotMessage(`✅ Successfully extracted GST information from ${pagesToProcess} pages!\n\n${allExtractedText.substring(0, 600)}...`);
        }

        // Show extracted structured data if available from backend
        if (uploadData.gstData) {
            const gst = uploadData.gstData;
            setTimeout(() => {
                addBotMessage(`📋 **Structured Data:**\n\n` +
                    `**Company:** ${gst.legalName}\n` +
                    `**GSTIN:** ${gst.gstin}\n` +
                    `**Address:** ${gst.address?.city}, ${gst.address?.state}\n` +
                    `**Directors:** ${gst.directors?.slice(0, 2).join(', ')}${gst.directors?.length > 2 ? '...' : ''}`
                );
            }, 500);
        }

        // Show next message
        if (uploadData.text) {
            setTimeout(() => addBotMessage(uploadData.text), 1000);
        }

        // Update progress
        state.updateProgress(5, 'GST verification complete');

        // Show next input
        if (uploadData.requiresInput) {
            showInput(uploadData.inputType || 'text');
        }

        // Store vendor code
        if (uploadData.vendorCode) {
            state.userData.vendorCode = uploadData.vendorCode;
        }

    } catch (error) {
        console.error('❌ Upload error:', error);
        throw error;
    }
}

async function uploadRegularFile() {
    const formData = new FormData();
    formData.append('file', selectedFile);

    const response = await fetch(`${ONBOARDING_API}/upload-file`, {
        method: 'POST',
        body: formData
    });

    const data = await response.json();

    if (!response.ok) {
        throw new Error(data.error || 'Upload failed');
    }

    hideTypingIndicator();
    addBotMessage(`✅ File uploaded successfully!`);

    // Continue with the flow
    // The backend will handle the next step
}

// ═══════════════════════════════════════════════════════════════════════════
// UI HELPERS
// ═══════════════════════════════════════════════════════════════════════════

function addBotMessage(text) {
    const messageGroup = document.createElement('div');
    messageGroup.className = 'message-group bot-group';
    messageGroup.innerHTML = `
        <div class="message-avatar">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                <circle cx="12" cy="12" r="12" fill="#4F46E5"/>
                <path d="M12 6C9.514 6 7.5 8.014 7.5 10.5V12C7.5 14.486 9.514 16.5 12 16.5C14.486 16.5 16.5 14.486 16.5 12V10.5C16.5 8.014 14.486 6 12 6Z" fill="white"/>
                <circle cx="10.5" cy="11.25" r="1" fill="#4F46E5"/>
                <circle cx="13.5" cy="11.25" r="1" fill="#4F46E5"/>
            </svg>
        </div>
        <div class="message-content">
            <div class="message bot-message">${formatMessage(text)}</div>
            <div class="message-time">${formatTime(new Date())}</div>
        </div>
    `;
    elements.messagesWrapper.appendChild(messageGroup);
    scrollToBottom();
    state.addMessage('bot', text);
}

function addUserMessage(text) {
    const messageGroup = document.createElement('div');
    messageGroup.className = 'message-group user-group';
    messageGroup.innerHTML = `
        <div class="message-content">
            <div class="message user-message">${escapeHtml(text)}</div>
            <div class="message-time">${formatTime(new Date())}</div>
        </div>
    `;
    elements.messagesWrapper.appendChild(messageGroup);
    scrollToBottom();
    state.addMessage('user', text);
}

function addSystemMessage(text) {
    const messageGroup = document.createElement('div');
    messageGroup.className = 'message-group';
    messageGroup.innerHTML = `
        <div class="message-content" style="width: 100%; max-width: 100%;">
            <div class="message system-message">${escapeHtml(text)}</div>
        </div>
    `;
    elements.messagesWrapper.appendChild(messageGroup);
    scrollToBottom();
}

function addErrorMessage(text) {
    const messageGroup = document.createElement('div');
    messageGroup.className = 'message-group';
    messageGroup.innerHTML = `
        <div class="message-content" style="width: 100%; max-width: 100%;">
            <div class="message error-message">⚠️ ${escapeHtml(text)}</div>
        </div>
    `;
    elements.messagesWrapper.appendChild(messageGroup);
    scrollToBottom();
}

function showInput(type) {
    elements.inputContainer.style.display = 'block';
    state.currentInputType = type;

    if (type === 'file') {
        elements.textInputWrapper.style.display = 'none';
        elements.fileUploadWrapper.style.display = 'block';
    } else {
        elements.textInputWrapper.style.display = 'flex';
        elements.fileUploadWrapper.style.display = 'none';
        elements.messageInput.focus();

        // Set input type
        if (type === 'email') {
            elements.messageInput.type = 'email';
            elements.messageInput.placeholder = 'Enter your email...';
        } else if (type === 'tel') {
            elements.messageInput.type = 'tel';
            elements.messageInput.placeholder = 'Enter your phone number...';
        } else {
            elements.messageInput.type = 'text';
            elements.messageInput.placeholder = 'Type your message...';
        }
    }
}

function hideInput() {
    elements.inputContainer.style.display = 'none';
}

function showTypingIndicator() {
    elements.typingIndicator.style.display = 'flex';
    scrollToBottom();
}

function hideTypingIndicator() {
    elements.typingIndicator.style.display = 'none';
}

function updateProgressBar(percent, label) {
    elements.progressFill.style.width = `${percent}%`;
    elements.progressPercent.textContent = `${percent}%`;
    if (label) {
        elements.progressLabel.textContent = label;
    }
}

function updateProgressFromState(data) {
    // Map states to progress
    const stateProgress = {
        'ask_email': 1,
        'ask_mobile': 2,
        'create_password': 3,
        'call_onboarding': 4,
        'ask_gst_upload': 4,
        'parse_gst': 5,
        'patch_onboarding': 6,
        'ask_aadhaar': 7,
        'ask_aadhaar_image': 7,
        'ask_otp': 8,
        'ask_pans': 8,
        'ask_bank': 9,
        'submit_kyc': 10,
        'done': 10
    };

    const stateLabels = {
        'ask_email': 'Email collection',
        'ask_mobile': 'Phone collection',
        'create_password': 'Creating password',
        'ask_gst_upload': 'GST upload',
        'parse_gst': 'Processing GST',
        'patch_onboarding': 'Creating account',
        'ask_aadhaar': 'Aadhaar verification',
        'ask_otp': 'OTP verification',
        'ask_pans': 'PAN verification',
        'ask_bank': 'Bank details',
        'submit_kyc': 'Submitting KYC',
        'done': 'Complete!'
    };

    if (data.state && stateProgress[data.state]) {
        state.updateProgress(stateProgress[data.state], stateLabels[data.state]);
    }
}

function scrollToBottom() {
    setTimeout(() => {
        elements.messagesContainer.scrollTop = elements.messagesContainer.scrollHeight;
    }, 100);
}

// ═══════════════════════════════════════════════════════════════════════════
// UTILITY FUNCTIONS
// ═══════════════════════════════════════════════════════════════════════════

function formatMessage(text) {
    // Convert markdown-style formatting
    return escapeHtml(text)
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\n/g, '<br>');
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatTime(date) {
    const now = new Date();
    const diff = now - date;

    if (diff < 60000) return 'Just now';
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;

    return date.toLocaleTimeString('en-US', {
        hour: 'numeric',
        minute: '2-digit',
        hour12: true
    });
}

function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

function fileToBase64(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result);
        reader.onerror = reject;
        reader.readAsDataURL(file);
    });
}

async function convertPDFToImages(file) {
    return new Promise(async (resolve, reject) => {
        try {
            // Set up PDF.js worker
            pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
            
            // Read file as ArrayBuffer
            const arrayBuffer = await file.arrayBuffer();
            
            // Load PDF
            const pdf = await pdfjsLib.getDocument({ data: arrayBuffer }).promise;
            console.log(`📄 PDF loaded: ${pdf.numPages} pages`);
            
            const images = [];
            
            // Convert each page to image
            for (let pageNum = 1; pageNum <= pdf.numPages; pageNum++) {
                const page = await pdf.getPage(pageNum);
                
                // Set scale for high quality
                const scale = 2.0;
                const viewport = page.getViewport({ scale });
                
                // Create canvas
                const canvas = document.createElement('canvas');
                const context = canvas.getContext('2d');
                canvas.width = viewport.width;
                canvas.height = viewport.height;
                
                // Render page to canvas
                await page.render({
                    canvasContext: context,
                    viewport: viewport
                }).promise;
                
                // Convert canvas to base64 image
                const imageBase64 = canvas.toDataURL('image/png');
                images.push(imageBase64);
                
                console.log(`✅ Page ${pageNum} converted to image`);
            }
            
            resolve(images);
        } catch (error) {
            console.error('❌ PDF conversion error:', error);
            reject(error);
        }
    });
}

// ═══════════════════════════════════════════════════════════════════════════
// EXPORT FOR DEBUGGING
// ═══════════════════════════════════════════════════════════════════════════

window.chatbot = {
    state,
    elements,
    startOnboarding,
    sendMessage,
    uploadFile,
    convertPDFToImages
};
