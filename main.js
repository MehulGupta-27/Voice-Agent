// FIXED main.js with proper live transcription handling

document.addEventListener("DOMContentLoaded", () => {
    const recordButton = document.getElementById("recordButton");
    const streamingButton = document.getElementById("streamingButton");
    const conversationStatus = document.getElementById("conversationStatus");
    const conversationHistory = document.getElementById("conversationHistory");
    const newSessionBtn = document.getElementById("newSession");
    const clearHistoryBtn = document.getElementById("clearHistory");
    const streamingTranscript = document.getElementById("streamingTranscript");
    const transcriptText = document.getElementById("transcriptText");
    const partialTranscript = document.getElementById("partialTranscript");
    const sessionInfo = document.getElementById("sessionInfo");
    const connectionStatus = document.getElementById("connectionStatus");
    const emptyState = document.getElementById("emptyState");

    let isRecording = false;
    let isStreaming = false;
    let mediaRecorder = null;
    let audioChunks = [];
    let sessionId = generateSessionId();
    let conversationCount = 0;
    const continuousMode = true;

    // Streaming variables
    let websocket = null;
    let audioContext = null;
    let audioWorkletNode = null;
    let microphone = null;
    let mediaStream = null;

    updateSessionInfo();
    checkConnection();

    recordButton.addEventListener("click", toggleRecording);
    streamingButton.addEventListener("click", toggleStreaming);
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

        // Stop any active streaming
        if (isStreaming) {
            stopStreaming();
        }

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

        // Stop any active streaming
        if (isStreaming) {
            stopStreaming();
        }
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

    // REGULAR RECORDING FUNCTIONS
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

    // STREAMING FUNCTIONS - FIXED FOR LIVE TRANSCRIPTION
    async function toggleStreaming() {
        if (!isStreaming) {
            await startStreaming();
        } else {
            stopStreaming();
        }
    }

async function startStreaming() {
  // 1. Show UI
  streamingTranscript.style.display = 'block';
  transcriptText.textContent = 'Waiting for speech...';
  partialTranscript.textContent = 'Partial transcripts will appear here';

  // 2. Open socket and bind handlers *before* audio setup
  websocket = new WebSocket('ws://localhost:8000/ws/streaming-transcribe');
  websocket.onmessage = event => {
    const data = JSON.parse(event.data);
    handleStreamingMessage(data);
  };
  websocket.onerror = err => {
    updateStatus("Streaming connection error", "status-error");
    stopStreaming();
  };
  websocket.onclose = () => {
    if (isStreaming) stopStreaming();
  };

  // 3. Wait for open, then wire audio
  await new Promise(resolve => {
    websocket.onopen = () => resolve();
    // optional timeout...
  });

  updateStatus("🎙️ Connected to streaming – start speaking!", "status-streaming");
  await setupModernStreamingAudio();
}


    async function setupModernStreamingAudio() {
        try {
            // Get microphone access with optimal constraints
            mediaStream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    sampleRate: 16000,
                    channelCount: 1,
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true,
                    latency: 0.01,
                    volume: 1.0
                }
            });

            // Create AudioContext with optimal settings
            audioContext = new (window.AudioContext || window.webkitAudioContext)({
                sampleRate: 16000,
                latencyHint: 'interactive'
            });

            // Handle audio context state
            if (audioContext.state === 'suspended') {
                await audioContext.resume();
            }

            console.log(`🎵 Audio context created: ${audioContext.sampleRate}Hz`);
            microphone = audioContext.createMediaStreamSource(mediaStream);

            // Try to use AudioWorklet first, fallback to ScriptProcessor if needed
            try {
                await setupAudioWorklet();
            } catch (workletError) {
                console.warn('AudioWorklet failed, falling back to ScriptProcessor:', workletError);
                setupScriptProcessor();
            }

            // Update UI
            isStreaming = true;
            streamingButton.classList.add("streaming");
            updateStatus("🎙️ Streaming active - speak now!", "status-streaming");
            console.log('✅ Streaming audio setup complete');

        } catch (error) {
            console.error("Error setting up streaming audio:", error);
            throw error;
        }
    }

    // AudioWorklet setup (modern approach)
    async function setupAudioWorklet() {
        try {
            // Register the AudioWorklet processor
            const processorCode = `
                class AudioProcessor extends AudioWorkletProcessor {
                    constructor() {
                        super();
                        this.bufferSize = 800; // ~50ms at 16kHz
                        this.buffer = new Float32Array(0);
                    }
                    
                    process(inputs, outputs, parameters) {
                        const input = inputs[0];
                        if (input.length > 0) {
                            const audioData = input[0]; // First channel
                            
                            // Accumulate audio data
                            const newBuffer = new Float32Array(this.buffer.length + audioData.length);
                            newBuffer.set(this.buffer);
                            newBuffer.set(audioData, this.buffer.length);
                            this.buffer = newBuffer;
                            
                            // Send chunks when we have enough data
                            while (this.buffer.length >= this.bufferSize) {
                                const chunk = this.buffer.slice(0, this.bufferSize);
                                this.buffer = this.buffer.slice(this.bufferSize);
                                
                                // Send to main thread
                                this.port.postMessage({
                                    type: 'audioData',
                                    data: chunk
                                });
                            }
                        }
                        return true;
                    }
                }
                
                registerProcessor('audio-processor', AudioProcessor);
            `;

            const blob = new Blob([processorCode], { type: 'application/javascript' });
            const processorUrl = URL.createObjectURL(blob);
            await audioContext.audioWorklet.addModule(processorUrl);

            // Create the AudioWorkletNode
            audioWorkletNode = new AudioWorkletNode(audioContext, 'audio-processor');

            // Handle messages from the processor
            audioWorkletNode.port.onmessage = (event) => {
                if (event.data.type === 'audioData') {
                    const audioData = event.data.data;
                    const pcmData = convertFloat32ToInt16(audioData);
                    sendAudioToServer(pcmData);
                }
            };

            // Connect the audio pipeline
            microphone.connect(audioWorkletNode);
            // Note: Don't connect to destination to avoid feedback

            console.log('✅ AudioWorklet setup successful');
        } catch (error) {
            console.error('AudioWorklet setup failed:', error);
            throw error;
        }
    }

    // ScriptProcessor setup (fallback for older browsers)
    function setupScriptProcessor() {
        console.log('🔄 Setting up ScriptProcessor fallback');
        const bufferSize = 2048; // Smaller buffer for lower latency
        audioWorkletNode = audioContext.createScriptProcessor(bufferSize, 1, 1);

        // Audio processing with optimized chunking
        let audioBuffer = new Float32Array(0);
        const targetSamples = 800; // ~50ms at 16kHz

        audioWorkletNode.onaudioprocess = function(event) {
            if (isStreaming && websocket && websocket.readyState === WebSocket.OPEN) {
                const audioData = event.inputBuffer.getChannelData(0);
                
                // Accumulate audio data
                const newBuffer = new Float32Array(audioBuffer.length + audioData.length);
                newBuffer.set(audioBuffer);
                newBuffer.set(audioData, audioBuffer.length);
                audioBuffer = newBuffer;

                // Send chunks of optimal size
                while (audioBuffer.length >= targetSamples) {
                    const chunk = audioBuffer.slice(0, targetSamples);
                    audioBuffer = audioBuffer.slice(targetSamples);

                    // Convert and send chunk
                    const pcmData = convertFloat32ToInt16(chunk);
                    sendAudioToServer(pcmData);
                }
            }
        };

        // Connect the audio pipeline
        microphone.connect(audioWorkletNode);
        audioWorkletNode.connect(audioContext.destination);

        console.log('✅ ScriptProcessor fallback setup complete');
    }

    function convertFloat32ToInt16(float32Array) {
        const int16Array = new Int16Array(float32Array.length);
        for (let i = 0; i < float32Array.length; i++) {
            const sample = Math.max(-1, Math.min(1, float32Array[i]));
            int16Array[i] = sample * (sample < 0 ? 0x8000 : 0x7FFF) | 0;
        }
        return int16Array;
    }

    function sendAudioToServer(audioData) {
        if (websocket && websocket.readyState === WebSocket.OPEN) {
            try {
                const uint8Array = new Uint8Array(audioData.buffer);
                const audioBase64 = btoa(String.fromCharCode.apply(null, uint8Array));

                // Send audio data in the expected format
                websocket.send(JSON.stringify({
                    type: 'audio',
                    audio: audioBase64
                }));
            } catch (error) {
                console.error('Error sending audio data:', error);
            }
        }
    }

    function stopStreaming() {
        console.log('🛑 Stopping streaming transcription');
        isStreaming = false;
        streamingButton.classList.remove("streaming");

        // If there's an open WebSocket, send stop and close
        if (websocket) {
            try {
                if (websocket.readyState === WebSocket.OPEN) {
                    websocket.send(JSON.stringify({ type: 'stop' }));
                    setTimeout(() => {
                        if (websocket && websocket.readyState === WebSocket.OPEN) {
                            websocket.close(1000, 'User stopped streaming');
                        }
                    }, 100);
                }
            } catch (e) {
                console.error('Error closing streaming websocket:', e);
            }
            // Null out our reference so we don't accidentally reuse it
            websocket = null;
        }

        // Clean up audio resources
        if (audioWorkletNode) {
            try {
                if (audioWorkletNode.port) audioWorkletNode.port.close();
                audioWorkletNode.disconnect();
            } catch (e) {
                console.error('Error disconnecting audio processor:', e);
            }
            audioWorkletNode = null;
        }

        if (microphone) {
            try {
                microphone.disconnect();
            } catch (e) {
                console.error('Error disconnecting microphone:', e);
            }
            microphone = null;
        }

        if (mediaStream) {
            try {
                mediaStream.getTracks().forEach(t => t.stop());
                console.log('🛑 Stopped audio track');
            } catch (e) {
                console.error('Error stopping media stream:', e);
            }
            mediaStream = null;
        }

        if (audioContext) {
            try {
                audioContext.close();
                console.log('🔇 Audio context closed');
            } catch (e) {
                console.error('Error closing audio context:', e);
            }
            audioContext = null;
        }

        // FIXED: Hide streaming transcript area
        if (streamingTranscript) {
            streamingTranscript.style.display = 'none';
            console.log('✅ Live transcription area hidden');
        }

        updateStatus("Streaming stopped", "status-ready");
        console.log('✅ Streaming transcription stopped and cleaned up');
    }

    // FIXED: Enhanced message handling for live transcription
    function handleStreamingMessage(data) {
        console.log('📨 Universal-Streaming received:', data);
        
        switch (data.status) {
            case 'ready':
                console.log('✅ Universal-Streaming service ready');
                updateStatus("🎙️ Universal-Streaming ready - speak now!", "status-streaming");
                break;

            case 'session_opened':
                console.log('🎙️ Universal-Streaming session opened:', data.session_id);
                updateStatus("🎙️ Universal-Streaming session active", "status-streaming");
                break;

            case 'transcript':
                console.log('📝 Transcript received:', data);
                
                if (data.message_type === 'FinalTranscript') {
                    console.log('🎯 FINAL TRANSCRIPT (Universal-Streaming):', data.text);
                    
                    // FIXED: Update final transcript display
                    if (transcriptText) {
                        const currentText = transcriptText.textContent;
                        const newText = currentText === 'Waiting for speech...' ? 
                            data.text : 
                            currentText + (currentText ? ' ' : '') + data.text;
                        transcriptText.textContent = newText;
                        transcriptText.style.fontWeight = 'bold';
                        transcriptText.style.color = '#2c3e50';
                    }
                    
                    // Clear partial transcript
                    if (partialTranscript) {
                        partialTranscript.textContent = '';
                    }

                    // Add message to conversation
                    addMessage("user", data.text);
                    conversationCount++;
                    updateSessionInfo();
                    
                } else if (data.message_type === 'PartialTranscript') {
                    console.log('📝 PARTIAL (Universal-Streaming):', data.text);
                    
                    // FIXED: Update partial transcript display
                    if (partialTranscript) {
                        partialTranscript.textContent = data.text;
                        partialTranscript.style.fontStyle = 'italic';
                        partialTranscript.style.color = '#7f8c8d';
                    }
                }
                break;

            case 'error':
                console.error('❌ Universal-Streaming error:', data.error || data.message);
                updateStatus("Universal-Streaming error: " + (data.error || data.message), "status-error");
                break;

            case 'session_closed':
                console.log('🔴 Universal-Streaming session closed');
                if (isStreaming) {
                    stopStreaming();
                }
                break;

            case 'force_endpoint_sent':
                console.log('🔄 Force endpoint sent to Universal-Streaming');
                break;

            case 'pong':
                console.log('🏓 Universal-Streaming pong received');
                break;

            default:
                console.log('📨 Unknown Universal-Streaming message:', data);
        }
    }

    // MESSAGE DISPLAY FUNCTIONS
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
});