document.addEventListener("DOMContentLoaded", () => {
    // Existing variables
    const recordButton = document.getElementById("recordButton");
    const conversationStatus = document.getElementById("conversationStatus");
    const conversationHistory = document.getElementById("conversationHistory");
    const newSessionBtn = document.getElementById("newSession");
    const clearHistoryBtn = document.getElementById("clearHistory");
    const sessionInfo = document.getElementById("sessionInfo");
    const connectionStatus = document.getElementById("connectionStatus");
    const emptyState = document.getElementById("emptyState");

    // Streaming variables
    let websocket = null;
    let isStreamingMode = false;
    let audioContext = null;
    let processor = null;
    let input = null;
    let streamingTranscriptDiv = null;

    // Existing variables
    let isRecording = false;
    let mediaRecorder = null;
    let audioChunks = [];
    let sessionId = generateSessionId();
    let conversationCount = 0;
    const continuousMode = true;

    updateSessionInfo();
    checkConnection();
    addStreamingButton(); // Add streaming button

    // Event listeners
    recordButton.addEventListener("click", toggleRecording);
    newSessionBtn.addEventListener("click", startNewSession);
    clearHistoryBtn.addEventListener("click", clearHistory);

    function generateSessionId() {
        return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }

    function addStreamingButton() {
        // Check if streaming button already exists
        if (document.getElementById('streamingBtn')) {
            return;
        }

        const headerActions = document.querySelector('.header-actions');
        
        const streamingBtn = document.createElement('button');
        streamingBtn.id = 'streamingBtn';
        streamingBtn.className = 'btn btn-primary';
        streamingBtn.innerHTML = '🎤 Start Streaming';
        streamingBtn.style.marginLeft = '12px';
        streamingBtn.addEventListener('click', toggleStreaming);
        
        headerActions.appendChild(streamingBtn);
    }

    async function toggleStreaming() {
        const streamingBtn = document.getElementById('streamingBtn');
        
        if (!isStreamingMode) {
            await startStreamingMode();
            streamingBtn.innerHTML = '⏹️ Stop Streaming';
            streamingBtn.className = 'btn btn-secondary';
        } else {
            await stopStreamingMode();
            streamingBtn.innerHTML = '🎤 Start Streaming';
            streamingBtn.className = 'btn btn-primary';
        }
    }

    async function startStreamingMode() {
        try {
            updateStatus("Starting streaming mode...", "status-processing");
            
            // Create streaming transcript display
            createStreamingTranscriptDisplay();
            
            // Connect WebSocket
            const wsUrl = `ws://localhost:8000/ws/stream/${sessionId}`;
            websocket = new WebSocket(wsUrl);
            
            websocket.onopen = () => {
                console.log('✅ WebSocket connected for streaming');
                updateStatus("WebSocket connected, starting audio...", "status-processing");
                startStreamingAudio();
            };
            
            websocket.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    handleStreamingMessage(data);
                } catch (e) {
                    console.error('Error parsing WebSocket message:', e);
                }
            };
            
            websocket.onerror = (error) => {
                console.error('❌ WebSocket error:', error);
                updateStatus("WebSocket connection failed", "status-error");
            };
            
            websocket.onclose = () => {
                console.log('🔴 WebSocket closed');
                if (isStreamingMode) {
                    updateStatus("WebSocket connection closed", "status-error");
                }
            };
            
        } catch (error) {
            console.error('Error starting streaming mode:', error);
            updateStatus("Failed to start streaming", "status-error");
        }
    }

    async function startStreamingAudio() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ 
                audio: {
                    sampleRate: 16000,
                    channelCount: 1,
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true
                }
            });
            
            // Create audio context
            audioContext = new (window.AudioContext || window.webkitAudioContext)({
                sampleRate: 16000
            });
            
            input = audioContext.createMediaStreamSource(stream);
            
            // Create script processor for audio data
            processor = audioContext.createScriptProcessor(1024, 1, 1);
            
            processor.onaudioprocess = (e) => {
                if (websocket && websocket.readyState === WebSocket.OPEN) {
                    const inputBuffer = e.inputBuffer.getChannelData(0);
                    
                    // Convert float32 to int16 PCM
                    const pcmData = new Int16Array(inputBuffer.length);
                    for (let i = 0; i < inputBuffer.length; i++) {
                        // Clamp and convert to 16-bit PCM
                        const sample = Math.max(-1, Math.min(1, inputBuffer[i]));
                        pcmData[i] = sample * 32767;
                    }
                    
                    // Send binary audio data
                    websocket.send(pcmData.buffer);
                }
            };
            
            // Connect audio nodes
            input.connect(processor);
            processor.connect(audioContext.destination);
            
            isStreamingMode = true;
            updateStatus("🎤 Streaming live audio - speak now!", "status-recording");
            
        } catch (error) {
            console.error('Error starting streaming audio:', error);
            updateStatus("Microphone access failed", "status-error");
        }
    }

    function createStreamingTranscriptDisplay() {
        // Remove existing transcript display if present
        const existing = document.getElementById('streamingTranscript');
        if (existing) {
            existing.remove();
        }
        
        // Hide empty state
        hideEmptyState();
        
        // Create streaming transcript container
        streamingTranscriptDiv = document.createElement('div');
        streamingTranscriptDiv.id = 'streamingTranscript';
        streamingTranscriptDiv.innerHTML = `
            <div class="streaming-transcript">
                <h3>🎤 Live Transcription</h3>
                <div class="transcript-partial" id="partialTranscript">Listening for speech...</div>
                <div class="transcript-final" id="finalTranscript"></div>
            </div>
        `;
        
        // Insert at the beginning of messages
        conversationHistory.insertBefore(streamingTranscriptDiv, conversationHistory.firstChild);
        
        // Add CSS styles if not already added
        if (!document.getElementById('streamingStyles')) {
            const style = document.createElement('style');
            style.id = 'streamingStyles';
            style.textContent = `
                .streaming-transcript {
                    background: linear-gradient(135deg, #e8f4fd, #f0f9ff);
                    border: 2px solid #3498db;
                    border-radius: 12px;
                    padding: 20px;
                    margin-bottom: 20px;
                    box-shadow: 0 4px 12px rgba(52, 152, 219, 0.2);
                    animation: slideIn 0.3s ease-out;
                }
                .streaming-transcript h3 {
                    color: #2c3e50;
                    margin-bottom: 12px;
                    font-size: 16px;
                    font-weight: 600;
                }
                .transcript-partial {
                    background: rgba(241, 196, 15, 0.1);
                    padding: 12px;
                    border-radius: 8px;
                    margin-bottom: 8px;
                    color: #f39c12;
                    font-style: italic;
                    min-height: 24px;
                    border-left: 3px solid #f39c12;
                    transition: all 0.3s ease;
                }
                .transcript-final {
                    background: rgba(39, 174, 96, 0.1);
                    padding: 12px;
                    border-radius: 8px;
                    color: #27ae60;
                    font-weight: 500;
                    max-height: 200px;
                    overflow-y: auto;
                    border-left: 3px solid #27ae60;
                    min-height: 40px;
                }
                .transcript-final .final-item {
                    margin-bottom: 8px;
                    padding: 6px;
                    background: rgba(39, 174, 96, 0.05);
                    border-radius: 4px;
                    animation: slideIn 0.3s ease-out;
                }
            `;
            document.head.appendChild(style);
        }
    }

    function handleStreamingMessage(data) {
        console.log('📨 Streaming message received:', data);
        
        switch (data.type) {
            case 'ready':
                console.log('✅ Streaming ready:', data.message);
                updateStatus("🎤 Live streaming active - speak now!", "status-ready");
                break;
                
            case 'transcription':
                handleTranscriptionData(data.data);
                break;
                
            case 'error':
                console.error('❌ Streaming error:', data.message);
                updateStatus(`Streaming error: ${data.message}`, "status-error");
                break;
                
            case 'pong':
                console.log('🏓 WebSocket keepalive');
                break;
        }
    }

    function handleTranscriptionData(transcript) {
        const partialDiv = document.getElementById('partialTranscript');
        const finalDiv = document.getElementById('finalTranscript');
        
        if (!partialDiv || !finalDiv) return;
        
        if (transcript.type === 'partial') {
            // Update partial transcript (real-time)
            partialDiv.textContent = transcript.text || 'Listening for speech...';
            partialDiv.style.opacity = transcript.text ? '1' : '0.6';
            
            // Log to console for screenshot
            console.log(`⚪ PARTIAL: "${transcript.text}"`);
            
        } else if (transcript.type === 'final') {
            // Add final transcript to the final section
            const finalItem = document.createElement('div');
            finalItem.className = 'final-item';
            finalItem.innerHTML = `
                <strong>Final:</strong> ${transcript.text}
                ${transcript.confidence ? `<br><small>Confidence: ${(transcript.confidence * 100).toFixed(1)}%</small>` : ''}
            `;
            finalDiv.appendChild(finalItem);
            
            // Clear partial transcript
            partialDiv.textContent = 'Listening for speech...';
            partialDiv.style.opacity = '0.6';
            
            // Auto-scroll final transcript
            finalDiv.scrollTop = finalDiv.scrollHeight;
            
            // Log to console with emphasis for screenshot
            console.log(`🔵 FINAL: "${transcript.text}"`);
            if (transcript.confidence) {
                console.log(`📊 Confidence: ${(transcript.confidence * 100).toFixed(1)}%`);
            }
            console.log('---');
        }
    }

    async function stopStreamingMode() {
        try {
            updateStatus("Stopping streaming mode...", "status-processing");
            
            // Stop audio processing
            if (processor) {
                processor.disconnect();
                processor = null;
            }
            
            if (input) {
                input.disconnect();
                input = null;
            }
            
            if (audioContext && audioContext.state !== 'closed') {
                await audioContext.close();
                audioContext = null;
            }
            
            // Close WebSocket
            if (websocket && websocket.readyState === WebSocket.OPEN) {
                websocket.send(JSON.stringify({ type: 'stop' }));
                setTimeout(() => {
                    if (websocket) websocket.close();
                }, 100);
            }
            websocket = null;
            
            // Remove streaming transcript display
            const streamingTranscript = document.getElementById('streamingTranscript');
            if (streamingTranscript) {
                streamingTranscript.remove();
            }
            
            isStreamingMode = false;
            updateStatus("Streaming mode stopped", "status-ready");
            
            // Show empty state if no messages
            if (conversationHistory.children.length === 0) {
                showEmptyState();
            }
            
        } catch (error) {
            console.error('Error stopping streaming mode:', error);
            updateStatus("Error stopping streaming", "status-error");
        }
    }

    // Rest of your existing functions remain the same...
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
            addMessage("ai", "Hello! I'm your AI assistant. How can I help you today?", null, true);
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

    async function toggleRecording() {
        if (!isRecording) {
            await startRecording();
        } else {
            stopRecording();
        }
    }

    async function startRecording() {
        try {
            updateStatus("Starting microphone...", "status-processing");
            
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            
            mediaRecorder = new MediaRecorder(stream);
            audioChunks = [];
            
            mediaRecorder.ondataavailable = event => {
                if (event.data.size > 0) {
                    audioChunks.push(event.data);
                }
            };
            
            mediaRecorder.onstop = async () => {
                const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
                await processConversation(audioBlob);
                
                stream.getTracks().forEach(track => track.stop());
            };
            
            mediaRecorder.start();
            isRecording = true;
            
            recordButton.classList.add("recording");
            updateStatus("Listening... tap to stop", "status-recording");
            
        } catch (error) {
            console.error("Error starting recording:", error);
            updateStatus("Microphone access denied", "status-error");
        }
    }

    function stopRecording() {
        if (mediaRecorder && mediaRecorder.state !== "inactive") {
            mediaRecorder.stop();
            isRecording = false;
            
            recordButton.classList.remove("recording");
            updateStatus("Processing your message...", "status-processing");
        }
    }

    async function processConversation(audioBlob) {
        try {
            const formData = new FormData();
            const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
            const filename = `conversation_${timestamp}.webm`;
            formData.append('file', audioBlob, filename);
            formData.append('session_id', sessionId);

            updateStatus("Getting AI response...", "status-processing");

            const response = await fetch('http://localhost:8000/conversation/query', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();

            if (response.ok && result.status === 'success') {
                addMessage("user", result.user_query);
                addMessage("ai", result.ai_response, result.audioFile);
                
                conversationCount++;
                updateSessionInfo();
                updateStatus("Ready for your next message", "status-ready");
                
                if (result.audioFile && !result.audioFile.startsWith('web-speech:')) {
                    setTimeout(() => {
                        const audioElements = conversationHistory.querySelectorAll('audio');
                        const lastAudio = audioElements[audioElements.length - 1];
                        if (lastAudio) {
                            lastAudio.play().catch(e => console.log("Auto-play prevented"));
                            
                            lastAudio.addEventListener('ended', () => {
                                if (continuousMode && !isRecording) {
                                    setTimeout(() => {
                                        updateStatus("Ready for next input", "status-ready");
                                        setTimeout(() => {
                                            if (continuousMode && !isRecording) {
                                                startRecording();
                                            }
                                        }, 1500);
                                    }, 500);
                                }
                            });
                        }
                    }, 500);
                } else if (continuousMode) {
                    setTimeout(() => {
                        if (!isRecording) {
                            updateStatus("Ready for next input", "status-ready");
                            setTimeout(() => {
                                if (continuousMode && !isRecording) {
                                    startRecording();
                                }
                            }, 2000);
                        }
                    }, 1000);
                }
                
            } else {
                const errorMessage = result.error || "Sorry, I couldn't process your message.";
                addMessage("ai", errorMessage, result.audioFile);
                updateStatus("Error occurred. Try again.", "status-error");
            }

        } catch (error) {
            console.error("Error processing conversation:", error);
            addMessage("ai", "I'm having trouble connecting right now. Please try again.");
            updateStatus("Connection error. Try again.", "status-error");
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
        
        if (sender === "ai" && audioUrl && !audioUrl.startsWith('web-speech:')) {
            const audioDiv = document.createElement("div");
            audioDiv.className = "audio-player";
            
            const audio = document.createElement("audio");
            audio.src = audioUrl;
            audio.preload = "auto";
            
            const customPlayer = document.createElement("div");
            customPlayer.className = "custom-audio-player";
            
            const playBtn = document.createElement("button");
            playBtn.className = "audio-play-btn";
            playBtn.innerHTML = '▶';
            
            const progressContainer = document.createElement("div");
            progressContainer.className = "audio-progress-container";
            
            const progressBar = document.createElement("div");
            progressBar.className = "audio-progress-bar";
            progressContainer.appendChild(progressBar);
            
            const timeDisplay = document.createElement("div");
            timeDisplay.className = "audio-time";
            timeDisplay.textContent = "0:00";
            
            customPlayer.appendChild(playBtn);
            customPlayer.appendChild(progressContainer);
            customPlayer.appendChild(timeDisplay);
            
            let isPlaying = false;
            
            playBtn.addEventListener('click', () => {
                if (isPlaying) {
                    audio.pause();
                } else {
                    audio.play();
                }
            });
            
            audio.addEventListener('play', () => {
                isPlaying = true;
                playBtn.innerHTML = '⏸';
                playBtn.classList.add('playing');
            });
            
            audio.addEventListener('pause', () => {
                isPlaying = false;
                playBtn.innerHTML = '▶';
                playBtn.classList.remove('playing');
            });
            
            audio.addEventListener('timeupdate', () => {
                if (audio.duration) {
                    const progress = (audio.currentTime / audio.duration) * 100;
                    progressBar.style.width = progress + '%';
                    
                    const minutes = Math.floor(audio.currentTime / 60);
                    const seconds = Math.floor(audio.currentTime % 60);
                    timeDisplay.textContent = `${minutes}:${seconds.toString().padStart(2, '0')}`;
                }
            });
            
            audio.addEventListener('ended', () => {
                isPlaying = false;
                playBtn.innerHTML = '▶';
                playBtn.classList.remove('playing');
                progressBar.style.width = '0%';
                timeDisplay.textContent = "0:00";
                
                if (continuousMode && !isRecording) {
                    setTimeout(() => {
                        updateStatus("Ready for next input", "status-ready");
                        setTimeout(() => {
                            if (continuousMode && !isRecording) {
                                startRecording();
                            }
                        }, 1500);
                    }, 500);
                }
            });
            
            progressContainer.addEventListener('click', (e) => {
                if (audio.duration) {
                    const rect = progressContainer.getBoundingClientRect();
                    const clickX = e.clientX - rect.left;
                    const width = rect.width;
                    const clickTime = (clickX / width) * audio.duration;
                    audio.currentTime = clickTime;
                }
            });
            
            audioDiv.appendChild(audio);
            audioDiv.appendChild(customPlayer);
            messageDiv.appendChild(audioDiv);
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

    setTimeout(() => {
        if (conversationHistory.children.length <= 1) {
            hideEmptyState();
            addMessage("ai", "Hello! I'm your AI assistant. How can I help you today?", null, true);
            updateStatus("Ready to chat - press the microphone to start!", "status-ready");
        }
    }, 1000);

    setInterval(checkConnection, 30000);
});