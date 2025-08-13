 document.addEventListener("DOMContentLoaded", () => {
    const recordButton = document.getElementById("recordButton");
    const conversationStatus = document.getElementById("conversationStatus");
    const conversationHistory = document.getElementById("conversationHistory");
    const newSessionBtn = document.getElementById("newSession");
    const clearHistoryBtn = document.getElementById("clearHistory");

    const sessionInfo = document.getElementById("sessionInfo");
    const connectionStatus = document.getElementById("connectionStatus");
    const emptyState = document.getElementById("emptyState");

    let isRecording = false;
    let mediaRecorder = null;
    let audioChunks = [];
    let sessionId = generateSessionId();
    let conversationCount = 0;
    const continuousMode = true;

    updateSessionInfo();
    checkConnection();

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