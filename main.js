document.addEventListener("DOMContentLoaded", () => {
    const recordButton = document.getElementById("recordButton");
    const conversationStatus = document.getElementById("conversationStatus");
    const conversationHistory = document.getElementById("conversationHistory");
    const newSessionBtn = document.getElementById("newSession");
    const clearHistoryBtn = document.getElementById("clearHistory");
    const sessionInfo = document.getElementById("sessionInfo");
    const connectionStatus = document.getElementById("connectionStatus");
    const emptyState = document.getElementById("emptyState");

    // WebSocket and audio streaming variables
    let websocket = null;
    let isRecording = false;
    let mediaRecorder = null;
    let sessionId = generateSessionId();
    let conversationCount = 0;
    let streamingStats = {
        chunksStreamed: 0,
        totalBytesStreamed: 0,
        recordingStartTime: null
    };

    // Initialize
    updateSessionInfo();
    checkConnection();
    initializeWebSocket();

    // Event listeners
    recordButton.addEventListener("click", toggleRecording);
    newSessionBtn.addEventListener("click", startNewSession);
    clearHistoryBtn.addEventListener("click", clearHistory);

    function generateSessionId() {
        return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }

    function updateSessionInfo() {
        sessionInfo.textContent = `Session ${sessionId.split('_')[1].slice(-4)} • ${conversationCount} messages`;
    }

    function startNewSession() {
        sessionId = generateSessionId();
        conversationCount = 0;
        conversationHistory.innerHTML = '';
        showEmptyState();
        updateSessionInfo();
        updateStatus("New conversation started", "status-ready");
        
        setTimeout(() => {
            hideEmptyState();
            addMessage("ai", "Audio streaming ready! Click the microphone to start real-time recording.", null, true);
        }, 800);
    }

    function clearHistory() {
        conversationHistory.innerHTML = '';
        showEmptyState();
        conversationCount = 0;
        updateSessionInfo();
        updateStatus("Conversation cleared", "status-ready");
    }

    function showEmptyState() {
        if (emptyState) {
            emptyState.style.display = 'flex';
        }
    }

    function hideEmptyState() {
        if (emptyState) {
            emptyState.style.display = 'none';
        }
    }

    // WebSocket Management
    function initializeWebSocket() {
        try {
            websocket = new WebSocket(`ws://localhost:8000/ws?client_id=${sessionId}`);
            
            websocket.onopen = function(event) {
                console.log("🔗 WebSocket connected");
                updateConnectionStatus(true);
                updateStatus("WebSocket connected - ready to stream audio", "status-ready");
            };
            
            websocket.onmessage = function(event) {
                try {
                    const data = JSON.parse(event.data);
                    handleWebSocketMessage(data);
                } catch (e) {
                    console.log("Received non-JSON message:", event.data);
                }
            };
            
            websocket.onclose = function(event) {
                console.log("🔌 WebSocket disconnected");
                updateConnectionStatus(false);
                updateStatus("WebSocket disconnected", "status-error");
                
                // Attempt to reconnect after 3 seconds
                setTimeout(() => {
                    console.log("🔄 Attempting to reconnect WebSocket...");
                    initializeWebSocket();
                }, 3000);
            };
            
            websocket.onerror = function(error) {
                console.error("❌ WebSocket error:", error);
                updateConnectionStatus(false);
                updateStatus("WebSocket connection error", "status-error");
            };
            
        } catch (error) {
            console.error("Failed to initialize WebSocket:", error);
            updateConnectionStatus(false);
        }
    }

    function handleWebSocketMessage(data) {
        console.log("📨 WebSocket message:", data);
        
        switch(data.type) {
            case "connection":
                addMessage("system", `Connected: ${data.message}`, null, true);
                break;
                
            case "chunk_received":
                // Update streaming statistics display
                updateStreamingStats(data);
                break;
                
            case "recording_started":
                addMessage("system", `🎬 Recording started: ${data.filename}`);
                updateStatus(`Streaming audio... (${streamingStats.chunksStreamed} chunks sent)`, "status-recording");
                break;
                
            case "recording_saved":
                addMessage("system", `💾 Audio saved: ${data.filename} (${formatBytes(data.file_size)}, ${data.chunks_received} chunks)`);
                updateStatus("Recording saved successfully", "status-ready");
                streamingStats.chunksStreamed = 0;
                streamingStats.totalBytesStreamed = 0;
                break;
                
            case "recording_error":
                addMessage("system", `❌ Recording error: ${data.error}`);
                updateStatus("Recording error", "status-error");
                break;
                
            default:
                console.log("Unknown message type:", data.type);
        }
    }

    function updateStreamingStats(data) {
        streamingStats.chunksStreamed = data.chunk_number;
        streamingStats.totalBytesStreamed = data.total_bytes;
        
        if (isRecording) {
            const elapsed = streamingStats.recordingStartTime ? 
                (Date.now() - streamingStats.recordingStartTime) / 1000 : 0;
            updateStatus(
                `🎤 Streaming: ${data.chunk_number} chunks, ${formatBytes(data.total_bytes)}, ${elapsed.toFixed(1)}s`, 
                "status-recording"
            );
        }
    }

    function formatBytes(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    }

    // Audio Recording with Streaming
    async function toggleRecording() {
        if (!isRecording) {
            await startStreamingRecording();
        } else {
            stopStreamingRecording();
        }
    }

    async function startStreamingRecording() {
        try {
            if (!websocket || websocket.readyState !== WebSocket.OPEN) {
                updateStatus("WebSocket not connected", "status-error");
                return;
            }

            updateStatus("Starting microphone for streaming...", "status-processing");
            
            const stream = await navigator.mediaDevices.getUserMedia({ 
                audio: {
                    echoCancellation: true,
                    noiseSuppression: true,
                    sampleRate: 44100
                } 
            });
            
            // Send start recording command
            websocket.send(JSON.stringify({"type": "start_recording"}));
            
            // Setup MediaRecorder for streaming
            mediaRecorder = new MediaRecorder(stream, {
                mimeType: 'audio/webm;codecs=opus',
                audioBitsPerSecond: 128000
            });
            
            streamingStats.recordingStartTime = Date.now();
            streamingStats.chunksStreamed = 0;
            streamingStats.totalBytesStreamed = 0;
            
            mediaRecorder.ondataavailable = function(event) {
                if (event.data.size > 0 && websocket && websocket.readyState === WebSocket.OPEN) {
                    // Convert blob to array buffer and send as binary data
                    event.data.arrayBuffer().then(buffer => {
                        websocket.send(buffer);
                        console.log(`📤 Sent audio chunk: ${buffer.byteLength} bytes`);
                    });
                }
            };
            
            mediaRecorder.onstop = function() {
                console.log("🛑 MediaRecorder stopped");
                stream.getTracks().forEach(track => track.stop());
                
                // Send stop recording command
                if (websocket && websocket.readyState === WebSocket.OPEN) {
                    websocket.send(JSON.stringify({"type": "stop_recording"}));
                }
            };
            
            mediaRecorder.onerror = function(error) {
                console.error("MediaRecorder error:", error);
                updateStatus("Recording error", "status-error");
            };
            
            // Start recording with small timeslices for real-time streaming
            mediaRecorder.start(100); // Send chunk every 100ms
            isRecording = true;
            
            recordButton.classList.add("recording");
            updateStatus("🎤 Streaming audio in real-time... tap to stop", "status-recording");
            
        } catch (error) {
            console.error("Error starting streaming recording:", error);
            updateStatus("Microphone access denied or WebSocket error", "status-error");
        }
    }

    function stopStreamingRecording() {
        if (mediaRecorder && mediaRecorder.state !== "inactive") {
            mediaRecorder.stop();
            isRecording = false;
            
            recordButton.classList.remove("recording");
            updateStatus("Stopping recording and saving file...", "status-processing");
        }
    }

    async function checkConnection() {
        try {
            const response = await fetch('http://localhost:8000/health');
            if (response.ok) {
                updateConnectionStatus(true);
            } else {
                updateConnectionStatus(false);
            }
        } catch (error) {
            updateConnectionStatus(false);
        }
    }

    function updateConnectionStatus(isConnected) {
        const connectionText = connectionStatus.querySelector('span');
        const connectionDot = connectionStatus.querySelector('.connection-dot');
        
        if (isConnected) {
            connectionText.textContent = 'Online';
            connectionDot.style.background = '#27ae60';
        } else {
            connectionText.textContent = 'Offline';
            connectionDot.style.background = '#e74c3c';
        }
    }

    function addMessage(sender, text, audioUrl = null, isWelcome = false) {
        hideEmptyState();
        
        const messageDiv = document.createElement("div");
        messageDiv.className = `message ${sender}`;
        
        const bubbleDiv = document.createElement("div");
        bubbleDiv.className = "message-bubble";
        bubbleDiv.textContent = text;
        
        const timeDiv = document.createElement("div");
        timeDiv.className = "message-time";
        timeDiv.textContent = isWelcome ? "Welcome" : new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
        
        messageDiv.appendChild(bubbleDiv);
        messageDiv.appendChild(timeDiv);
        
        // Add system message styling
        if (sender === "system") {
            messageDiv.className = "message system";
            bubbleDiv.style.background = "rgba(52, 152, 219, 0.1)";
            bubbleDiv.style.color = "#2980b9";
            bubbleDiv.style.border = "1px solid rgba(52, 152, 219, 0.2)";
            bubbleDiv.style.fontSize = "13px";
        }
        
        conversationHistory.appendChild(messageDiv);
        
        setTimeout(() => {
            conversationHistory.scrollTo({
                top: conversationHistory.scrollHeight,
                behavior: 'smooth'
            });
        }, 100);
    }

    function updateStatus(message, className = "") {
        conversationStatus.textContent = message;
        conversationStatus.className = `status-text ${className}`;
    }

    // Initialize with welcome message
    setTimeout(() => {
        if (conversationHistory.children.length <= 1) {
            hideEmptyState();
            addMessage("ai", "Audio streaming WebSocket ready! Press the microphone to start real-time audio streaming.", null, true);
            updateStatus("Ready to stream audio - press microphone to start!", "status-ready");
        }
    }, 1000);

    // Check connection periodically
    setInterval(checkConnection, 30000);
});