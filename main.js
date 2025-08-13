document.addEventListener("DOMContentLoaded", () => {
    initMatrixBackground();
    
    const recordButton = document.getElementById("recordButton");
    const conversationStatus = document.getElementById("conversationStatus");
    const conversationHistory = document.getElementById("conversationHistory");
    const newSessionBtn = document.getElementById("newSession");
    const clearHistoryBtn = document.getElementById("clearHistory");
    const continuousModeBtn = document.getElementById("continuousMode");
    const sessionInfo = document.getElementById("sessionInfo");
    const connectionStatus = document.getElementById("connectionStatus");
    const emptyState = document.getElementById("emptyState");

    let isRecording = false;
    let mediaRecorder = null;
    let audioChunks = [];
    let sessionId = generateSessionId();
    let conversationCount = 0;
    let continuousMode = true; // Start with continuous mode enabled

    updateSessionInfo();
    checkConnection();

    recordButton.addEventListener("click", toggleRecording);
    newSessionBtn.addEventListener("click", startNewSession);
    clearHistoryBtn.addEventListener("click", clearHistory);
    continuousModeBtn.addEventListener("click", toggleContinuousMode);

    function generateSessionId() {
        return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }

    function updateSessionInfo() {
        sessionInfo.textContent = `NEURAL-${sessionId.split('_')[1].slice(-4).toUpperCase()} • MSG: ${conversationCount.toString().padStart(3, '0')}`;
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
        }, 1000);
    }

    function clearHistory() {
        conversationHistory.innerHTML = '';
        showEmptyState();
        conversationCount = 0;
        updateSessionInfo();
        updateStatus("MEMORY BANKS CLEARED • SYSTEM RESET COMPLETE", "status-ready");
    }

    function toggleContinuousMode() {
        continuousMode = !continuousMode;
        
        if (continuousMode) {
            continuousModeBtn.classList.add('active');
            continuousModeBtn.querySelector('.btn-text').textContent = 'CONTINUOUS';
            updateStatus("CONTINUOUS MODE ACTIVATED • AUTO-LISTENING ENABLED", "status-ready");
        } else {
            continuousModeBtn.classList.remove('active');
            continuousModeBtn.querySelector('.btn-text').textContent = 'MANUAL';
            updateStatus("MANUAL MODE ACTIVATED • CLICK TO TALK", "status-ready");
        }
    }

    function showEmptyState() {
        if (emptyState) {
            emptyState.style.display = 'block';
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
        const connectionText = connectionStatus.querySelector('.connection-text');
        const signalBars = connectionStatus.querySelectorAll('.bar');
        
        if (isConnected) {
            connectionText.textContent = 'ONLINE';
            signalBars.forEach(bar => {
                bar.style.background = '#00ff88';
            });
        } else {
            connectionText.textContent = 'OFFLINE';
            signalBars.forEach(bar => {
                bar.style.background = '#ff0044';
            });
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
            updateStatus("NEURAL LINK ACTIVE • VOICE INPUT DETECTED", "status-recording");
            
        } catch (error) {
            console.error("Error starting recording:", error);
            updateStatus("Microphone access denied. Please allow microphone access and try again.", "status-error");
        }
    }

    function stopRecording() {
        if (mediaRecorder && mediaRecorder.state !== "inactive") {
            mediaRecorder.stop();
            isRecording = false;
            
            recordButton.classList.remove("recording");
            updateStatus("NEURAL PROCESSING • ANALYZING VOICE DATA", "status-processing");
        }
    }

    async function processConversation(audioBlob) {
        try {
            const formData = new FormData();
            const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
            const filename = `conversation_${timestamp}.webm`;
            formData.append('file', audioBlob, filename);
            formData.append('session_id', sessionId);

            updateStatus("🧠 Getting AI response...", "status-processing");

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
                updateStatus("VOICE RECOGNITION READY • NEURAL LINK STABLE", "status-ready");
                
                if (result.audioFile && !result.audioFile.startsWith('web-speech:')) {
                    setTimeout(() => {
                        const audioElements = conversationHistory.querySelectorAll('audio');
                        const lastAudio = audioElements[audioElements.length - 1];
                        if (lastAudio) {
                            // Play the audio
                            lastAudio.play().catch(e => console.log("Auto-play prevented by browser"));
                            
                            // Start listening again after audio finishes (if continuous mode is on)
                            lastAudio.addEventListener('ended', () => {
                                setTimeout(() => {
                                    if (!isRecording && continuousMode) {
                                        updateStatus("🎤 READY FOR NEXT INPUT • AUTO-LISTENING ENABLED", "status-ready");
                                        // Auto-start recording after a brief pause
                                        setTimeout(() => {
                                            if (!isRecording && continuousMode) {
                                                startRecording();
                                            }
                                        }, 1500);
                                    } else if (!continuousMode) {
                                        updateStatus("🎤 MANUAL MODE • CLICK TO TALK", "status-ready");
                                    }
                                }, 500);
                            });
                        }
                    }, 500);
                } else {
                    // If no audio, start listening again after a brief delay (if continuous mode is on)
                    setTimeout(() => {
                        if (!isRecording && continuousMode) {
                            updateStatus("🎤 READY FOR NEXT INPUT • AUTO-LISTENING ENABLED", "status-ready");
                            setTimeout(() => {
                                if (!isRecording && continuousMode) {
                                    startRecording();
                                }
                            }, 2000);
                        } else if (!continuousMode) {
                            updateStatus("🎤 MANUAL MODE • CLICK TO TALK", "status-ready");
                        }
                    }, 1000);
                }
                
            } else {
                const errorMessage = result.error || "Sorry, I couldn't process your message.";
                addMessage("ai", errorMessage, result.audioFile);
                updateStatus("NEURAL LINK ERROR • SYSTEM RECOVERY INITIATED", "status-error");
            }

        } catch (error) {
            console.error("Error processing conversation:", error);
            addMessage("ai", "I'm having trouble connecting right now. Please try again in a moment.");
            updateStatus("CRITICAL ERROR • NEURAL NETWORK DISCONNECTED", "status-error");
        } finally {
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
            playBtn.innerHTML = '<div class="play-icon">▶</div>';
            
            const progressContainer = document.createElement("div");
            progressContainer.className = "audio-progress-container";
            
            const progressBar = document.createElement("div");
            progressBar.className = "audio-progress-bar";
            progressContainer.appendChild(progressBar);
            
            const timeDisplay = document.createElement("div");
            timeDisplay.className = "audio-time";
            timeDisplay.textContent = "0:00";
            
            const waveform = document.createElement("div");
            waveform.className = "audio-waveform";
            for (let i = 0; i < 7; i++) {
                const bar = document.createElement("div");
                bar.className = "wave-bar";
                waveform.appendChild(bar);
            }
            
            customPlayer.appendChild(playBtn);
            customPlayer.appendChild(progressContainer);
            customPlayer.appendChild(timeDisplay);
            customPlayer.appendChild(waveform);
            
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
                playBtn.innerHTML = '<div class="pause-icon">⏸</div>';
                playBtn.classList.add('playing');
                customPlayer.classList.add('playing');
            });
            
            audio.addEventListener('pause', () => {
                isPlaying = false;
                playBtn.innerHTML = '<div class="play-icon">▶</div>';
                playBtn.classList.remove('playing');
                customPlayer.classList.remove('playing');
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
                playBtn.innerHTML = '<div class="play-icon">▶</div>';
                playBtn.classList.remove('playing');
                customPlayer.classList.remove('playing');
                progressBar.style.width = '0%';
                timeDisplay.textContent = "0:00";
                
                // Trigger auto-listening after audio ends (if continuous mode is on)
                setTimeout(() => {
                    if (!isRecording && continuousMode) {
                        updateStatus("🎤 READY FOR NEXT INPUT • AUTO-LISTENING ENABLED", "status-ready");
                        // Auto-start recording after a brief pause
                        setTimeout(() => {
                            if (!isRecording && continuousMode) {
                                startRecording();
                            }
                        }, 1500);
                    } else if (!continuousMode) {
                        updateStatus("🎤 MANUAL MODE • CLICK TO TALK", "status-ready");
                    }
                }, 500);
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
        conversationStatus.className = `activation-status ${className}`;
    }

    setTimeout(() => {
        hideEmptyState();
        addMessage("ai", "Hello! I'm your AI assistant. How can I help you today?", null, true);
        updateStatus("VOICE RECOGNITION READY • NEURAL PROCESSING ONLINE", "status-ready");
    }, 2000);

    setInterval(checkConnection, 30000);
});

function initMatrixBackground() {
    const canvas = document.getElementById('matrixCanvas');
    const ctx = canvas.getContext('2d');
    
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
    
    const matrix = "ABCDEFGHIJKLMNOPQRSTUVWXYZ123456789@#$%^&*()*&^%+-/~{[|`]}";
    const matrixArray = matrix.split("");
    
    const fontSize = 10;
    const columns = canvas.width / fontSize;
    
    const drops = [];
    for(let x = 0; x < columns; x++) {
        drops[x] = 1;
    }
    
    function draw() {
        ctx.fillStyle = 'rgba(0, 0, 0, 0.04)';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        
        ctx.fillStyle = '#00ff88';
        ctx.font = fontSize + 'px monospace';
        
        for(let i = 0; i < drops.length; i++) {
            const text = matrixArray[Math.floor(Math.random() * matrixArray.length)];
            ctx.fillText(text, i * fontSize, drops[i] * fontSize);
            
            if(drops[i] * fontSize > canvas.height && Math.random() > 0.975) {
                drops[i] = 0;
            }
            drops[i]++;
        }
    }
    
    setInterval(draw, 35);
    
    window.addEventListener('resize', () => {
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
    });
}