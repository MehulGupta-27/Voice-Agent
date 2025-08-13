document.addEventListener("DOMContentLoaded", () => {
    const generateBtn = document.getElementById("generateBtn");
    const textInput = document.getElementById("textInput");
    const audioResult = document.getElementById("audioResult");

    generateBtn.addEventListener("click", async () => {
        const text = textInput.value.trim();

        const payload = {
            text: text,
            voiceId: "en-US-marcus",
            format: "MP3"
        };

        try {
            const res = await fetch("http://localhost:8000/generate-audio", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(payload)
            });

            const result = await res.json();
            console.log("Response:", result);

            const audioUrl = result.audio?.audioFile;

            if (audioUrl) {
                const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
                const ttsFilename = `tts_audio_${timestamp}.mp3`;

                audioResult.innerHTML = `
                    <div style="
                        background: #f0f9ff;
                        border: 2px solid #0ea5e9;
                        border-radius: 12px;
                        padding: 12px;
                        margin: 8px 0;
                        width: 100%;
                        max-width: 100%;
                        box-sizing: border-box;
                        position: relative;
                        display: block !important;
                        visibility: visible !important;
                        opacity: 1 !important;
                    ">
                        <h3 style="color: #0ea5e9; margin: 0 0 8px 0; font-size: 18px; text-align: center;">🎵 Audio Generated!</h3>
                        
                        <div style="background: white; padding: 10px; border-radius: 8px; border: 1px solid #ddd;">
                            <audio controls src="${audioUrl}" style="width: 100%; margin: 0;"></audio>
                        </div>
                    </div>
                `;

            } else {
                audioResult.innerHTML = `
                    <div style="
                        background: #fef2f2;
                        border: 3px solid #ef4444;
                        border-radius: 12px;
                        padding: 20px;
                        margin: 20px 0;
                        position: relative;
                        display: block !important;
                        visibility: visible !important;
                        opacity: 1 !important;
                    ">
                        <h3 style="color: #ef4444; margin: 0 0 15px 0; font-size: 20px;">❌ Generation Failed!</h3>
                        <div style="background: white; padding: 15px; border-radius: 8px; margin: 15px 0; border: 1px solid #ddd;">
                            <p style="color: #ef4444; font-weight: bold;">Failed to get audio URL from server.</p>
                            <p style="color: #6b7280; margin-top: 10px;">Please check your text input and try again.</p>
                        </div>
                        <p style="margin: 15px 0 0 0; font-size: 12px; color: #666; text-align: center; font-style: italic;">
                            Failed at: ${new Date().toLocaleString()}
                        </p>
                    </div>
                `;
            }
        } catch (err) {
            console.error(err);
            audioResult.innerHTML = `
                <div style="
                    background: #fef2f2;
                    border: 3px solid #ef4444;
                    border-radius: 12px;
                    padding: 20px;
                    margin: 20px 0;
                    position: relative;
                    display: block !important;
                    visibility: visible !important;
                    opacity: 1 !important;
                ">
                    <h3 style="color: #ef4444; margin: 0 0 15px 0; font-size: 20px;">❌ Network Error!</h3>
                    <div style="background: white; padding: 15px; border-radius: 8px; margin: 15px 0; border: 1px solid #ddd;">
                        <p style="color: #ef4444; font-weight: bold;">Error contacting server.</p>
                        <p style="color: #6b7280; margin-top: 10px;">Please check your internet connection and server status.</p>
                        <p style="color: #6b7280; font-size: 12px; margin-top: 5px;">Error: ${err.message}</p>
                    </div>
                    <p style="margin: 15px 0 0 0; font-size: 12px; color: #666; text-align: center; font-style: italic;">
                        Error occurred at: ${new Date().toLocaleString()}
                    </p>
                </div>
            `;
        }
    });

    const startBtn = document.getElementById("startRecording");
    const stopBtn = document.getElementById("stopRecording");
    const recordingResult = document.getElementById("recordingResult");
    const uploadResults = document.getElementById("uploadResults");

    let mediaRecorder;
    let audioChunks = [];

    startBtn.addEventListener("click", async (event) => {
        event.preventDefault();
        try {
            console.log("Start recording clicked");
            recordingResult.innerHTML = '<div class="status-message status-recording">🎤 Recording in progress...</div>';

            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            console.log("Got media stream");

            mediaRecorder = new MediaRecorder(stream);
            audioChunks = [];

            mediaRecorder.ondataavailable = event => {
                console.log("Data available:", event.data.size);
                if (event.data.size > 0) {
                    audioChunks.push(event.data);
                }
            };

            mediaRecorder.onstop = () => {
                console.log("Recording stopped");
                const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
                const audioUrl = URL.createObjectURL(audioBlob);

                const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
                const filename = `recording_${timestamp}.webm`;

                console.log('Audio blob created:', audioBlob.size, 'bytes');

                recordingResult.innerHTML = `
                    <div style="
                        background: #f0fff4;
                        border: 3px solid #10b981;
                        border-radius: 12px;
                        padding: 20px;
                        margin: 20px 0;
                        width: 100%;
                        max-width: 100%;
                        box-sizing: border-box;
                        position: relative;
                        display: block !important;
                        visibility: visible !important;
                        opacity: 1 !important;
                    ">
                        <h3 style="color: #10b981; margin: 0 0 15px 0; font-size: 20px;">🎤 Recording Complete!</h3>
                        
                        <div style="background: white; padding: 15px; border-radius: 8px; margin: 15px 0; border: 1px solid #ddd;">
                            <p style="margin: 0 0 10px 0; font-weight: bold; color: #374151;">📁 Audio File Details:</p>
                            <p style="margin: 5px 0;"><strong>Filename:</strong> ${filename}</p>
                            <p style="margin: 5px 0;"><strong>Size:</strong> ${audioBlob.size} bytes (${(audioBlob.size / 1024).toFixed(2)} KB)</p>
                            <p style="margin: 5px 0;"><strong>Type:</strong> audio/webm</p>
                            <p style="margin: 5px 0;"><strong>Status:</strong> Ready for upload</p>
                        </div>

                        <div style="background: white; padding: 15px; border-radius: 8px; margin: 15px 0; border: 1px solid #ddd;">
                            <p style="margin: 0 0 10px 0; font-weight: bold; color: #374151;">🎵 Audio Player:</p>
                            <audio controls src="${audioUrl}" style="width: 100%; margin: 10px 0;"></audio>
                        </div>
                        
                        <p style="margin: 15px 0 0 0; font-size: 12px; color: #666; text-align: center; font-style: italic;">
                            Recorded at: ${new Date().toLocaleString()}
                        </p>
                    </div>
                `;

                console.log('Recording details displayed - should stay visible');

                const recordingHTML = recordingResult.innerHTML;

                const protectRecording = () => {
                    if (!recordingResult.innerHTML.includes('Recording Complete')) {
                        console.log('🔄 Restoring recording details...');
                        recordingResult.innerHTML = recordingHTML;
                    }
                };

                const protectionInterval = setInterval(protectRecording, 100);
                setTimeout(() => clearInterval(protectionInterval), 10000);

                setTimeout(() => {
                    if (recordingResult.innerHTML.includes('Recording Complete')) {
                        console.log('✅ Recording details still visible after 2 seconds');
                    } else {
                        console.log('❌ Recording details disappeared!');
                        console.log('Current content:', recordingResult.innerHTML);
                        recordingResult.innerHTML = recordingHTML;
                    }
                }, 2000);

                setTimeout(async () => {
                    console.log('🔄 Starting echo bot...');
                    await processEchoBot(audioBlob, filename);
                }, 1000);
            };

            mediaRecorder.start();
            console.log("Recording started");
            startBtn.disabled = true;
            stopBtn.disabled = false;
        } catch (err) {
            console.error("Recording error:", err);
            recordingResult.innerHTML = `<p style="color:red;">Microphone access denied or not supported: ${err.message}</p>`;
        }
    });

    stopBtn.addEventListener("click", (event) => {
        event.preventDefault();
        console.log("Stop recording clicked");
        if (mediaRecorder && mediaRecorder.state !== "inactive") {
            mediaRecorder.stop();
            startBtn.disabled = false;
            stopBtn.disabled = true;
            console.log("Recording stopped by user");
        }
    });

    async function uploadAudio(audioBlob) {
        console.log('Starting upload process...');

        if (!uploadResults) {
            console.error('Upload results container not found');
            return;
        }

        console.log('Recording result content before upload:', recordingResult.innerHTML.length, 'characters');

        try {
            const formData = new FormData();
            const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
            const filename = `recording_${timestamp}.webm`;
            formData.append('file', audioBlob, filename);

            console.log('Uploading file:', filename, 'Size:', audioBlob.size);

            uploadResults.innerHTML = '<div class="status-message status-uploading">🔄 Uploading audio to server...</div>';

            const response = await fetch('http://localhost:8000/upload-audio', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();
            console.log('Upload response:', result);

            if (response.ok && result.filename) {
                uploadResults.innerHTML = `
                    <div class="result-card success">
                        <h3 style="color: #10b981;">✅ Upload Successful!</h3>
                        <div class="details">
                            <p style="margin: 0 0 12px 0; font-weight: bold; color: #374151;">📤 Upload Details:</p>
                            <p><strong>📁 Filename:</strong> ${result.filename}</p>
                            <p><strong>📄 Content Type:</strong> ${result.content_type}</p>
                            <p><strong>📊 Size:</strong> ${result.size} bytes (${(result.size / 1024).toFixed(2)} KB)</p>
                            <p><strong>💬 Message:</strong> ${result.message}</p>
                            <p><strong>🌐 Server:</strong> localhost:8000</p>
                        </div>
                        <p class="timestamp">Upload completed at: ${new Date().toLocaleString()}</p>
                    </div>
                `;

                console.log('Upload successful - permanent display created');

            } else {
                uploadResults.innerHTML = `
                    <div class="result-card error">
                        <h3 style="color: #ef4444;">❌ Upload Failed</h3>
                        <div class="details">
                            <p style="color: #ef4444; font-weight: bold;">${result.error || 'Unknown error'}</p>
                        </div>
                        <p class="timestamp">Failed at: ${new Date().toLocaleString()}</p>
                    </div>
                `;
            }
        } catch (error) {
            console.error('Upload error:', error);
            uploadResults.innerHTML = `
                <div class="result-card error">
                    <h3 style="color: #ef4444;">❌ Network Error</h3>
                    <div class="details">
                        <p style="color: #ef4444; font-weight: bold;">${error.message}</p>
                        <p style="color: #6b7280;">Please check your internet connection and server status.</p>
                    </div>
                    <p class="timestamp">Error occurred at: ${new Date().toLocaleString()}</p>
                </div>
            `;
        }
    }

    async function transcribeAudio(audioBlob, filename) {
        try {
            console.log('Starting transcription process...');

            if (!uploadResults) {
                console.error('Upload results container not found');
                return;
            }

            const formData = new FormData();
            formData.append('file', audioBlob, filename);

            console.log('Sending audio for transcription:', filename, 'Size:', audioBlob.size);

            uploadResults.innerHTML = `
                <div style="
                    border: 2px solid #f59e0b; 
                    padding: 15px; 
                    margin: 15px 0; 
                    background: #fef3c7; 
                    border-radius: 10px;
                    animation: pulse 2s infinite;
                ">
                    <h3 style="color: #d97706; margin: 0 0 10px 0; font-size: 18px;">🎙️ Transcribing Audio...</h3>
                    <p style="margin: 0; color: #92400e;">Please wait while we convert your speech to text using AssemblyAI</p>
                </div>
            `;

            const response = await fetch('http://localhost:8000/transcribe/file', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();
            console.log('Transcription response:', result);

            if (response.ok && result.status === 'completed') {
                uploadResults.innerHTML = `
                    <div style="
                        border: 3px solid #10b981; 
                        padding: 20px; 
                        margin: 15px 0; 
                        background: #d1fae5; 
                        border-radius: 10px;
                        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
                    ">
                        <h3 style="color: #10b981; margin: 0 0 15px 0; font-size: 18px;">🎙️ Transcription Complete!</h3>
                        
                        <div style="background: white; padding: 15px; border-radius: 8px; margin: 15px 0; border: 1px solid #ddd;">
                            <p style="margin: 0 0 10px 0; font-weight: bold; color: #374151;">📝 Transcript:</p>
                            <div style="
                                background: #f9fafb; 
                                padding: 15px; 
                                border-radius: 6px; 
                                border-left: 4px solid #10b981;
                                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                                line-height: 1.6;
                                color: #1f2937;
                                font-size: 16px;
                            ">
                                "${result.transcript || 'No speech detected in the audio.'}"
                            </div>
                        </div>

                        <div style="background: white; padding: 15px; border-radius: 8px; margin: 15px 0; border: 1px solid #ddd;">
                            <p style="margin: 0 0 10px 0; font-weight: bold; color: #374151;">📊 Transcription Details:</p>
                            <p style="margin: 5px 0; font-size: 14px;"><strong>📁 Filename:</strong> ${result.filename}</p>
                            <p style="margin: 5px 0; font-size: 14px;"><strong>⏱️ Duration:</strong> ${result.audio_duration ? result.audio_duration.toFixed(2) + 's' : 'N/A'}</p>
                            <p style="margin: 5px 0; font-size: 14px;"><strong>📝 Words Count:</strong> ${result.words_count}</p>
                            <p style="margin: 5px 0; font-size: 14px;"><strong>🤖 Service:</strong> AssemblyAI</p>
                        </div>
                        
                        <p style="margin: 15px 0 0 0; font-size: 12px; color: #666; text-align: center; font-style: italic;">
                            Transcribed at: ${new Date().toLocaleString()}
                        </p>
                    </div>
                `;

                console.log('Transcription successful - results displayed');

            } else {
                uploadResults.innerHTML = `
                    <div style="
                        border: 3px solid #ef4444; 
                        padding: 15px; 
                        margin: 10px 0; 
                        background: #fef2f2; 
                        border-radius: 8px;
                    ">
                        <h3 style="color: #ef4444; margin: 0 0 15px 0; font-size: 18px;">❌ Transcription Failed</h3>
                        <div style="background: white; padding: 15px; border-radius: 8px; border: 1px solid #ddd;">
                            <p style="color: #ef4444; font-weight: bold;">${result.error || 'Unknown transcription error'}</p>
                            <p style="color: #6b7280; margin-top: 10px;">Please check your AssemblyAI API key and try again.</p>
                        </div>
                        <p style="margin: 15px 0 0 0; font-size: 12px; color: #666; text-align: center; font-style: italic;">
                            Failed at: ${new Date().toLocaleString()}
                        </p>
                    </div>
                `;
            }
        } catch (error) {
            console.error('Transcription error:', error);
            uploadResults.innerHTML = `
                <div style="
                    border: 3px solid #ef4444; 
                    padding: 15px; 
                    margin: 10px 0; 
                    background: #fef2f2; 
                    border-radius: 8px;
                ">
                    <h3 style="color: #ef4444; margin: 0 0 15px 0; font-size: 18px;">❌ Network Error</h3>
                    <div style="background: white; padding: 15px; border-radius: 8px; border: 1px solid #ddd;">
                        <p style="color: #ef4444; font-weight: bold;">${error.message}</p>
                        <p style="color: #6b7280; margin-top: 10px;">Please check your internet connection and server status.</p>
                    </div>
                    <p style="margin: 15px 0 0 0; font-size: 12px; color: #666; text-align: center; font-style: italic;">
                        Error occurred at: ${new Date().toLocaleString()}
                    </p>
                </div>
            `;
        }
    }
});
async function processEchoBot(audioBlob, filename) {
    try {
        console.log('Starting echo bot process...');

        if (!uploadResults) {
            console.error('Upload results container not found');
            return;
        }

        const formData = new FormData();
        formData.append('file', audioBlob, filename);

        console.log('Sending audio for echo bot:', filename, 'Size:', audioBlob.size);

        uploadResults.innerHTML = `
                <div style="
                    border: 2px solid #8b5cf6; 
                    padding: 15px; 
                    margin: 15px 0; 
                    background: #f3e8ff; 
                    border-radius: 10px;
                    animation: pulse 2s infinite;
                ">
                    <h3 style="color: #7c3aed; margin: 0 0 10px 0; font-size: 18px;">🔄 Processing Echo Bot...</h3>
                    <p style="margin: 0; color: #6b46c1;">Transcribing your speech and generating Murf voice response...</p>
                </div>
            `;

        const response = await fetch('http://localhost:8000/tts/echo', {
            method: 'POST',
            body: formData
        });

        const result = await response.json();
        console.log('Echo bot response:', result);

        if (response.ok && result.status === 'success') {
            uploadResults.innerHTML = `
                    <div style="
                        border: 3px solid #8b5cf6; 
                        padding: 20px; 
                        margin: 15px 0; 
                        background: #f3e8ff; 
                        border-radius: 10px;
                        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
                    ">
                        <h3 style="color: #7c3aed; margin: 0 0 15px 0; font-size: 18px;">🎭 Echo Bot Complete!</h3>
                        
                        <div style="background: white; padding: 15px; border-radius: 8px; margin: 15px 0; border: 1px solid #ddd;">
                            <p style="margin: 0 0 10px 0; font-weight: bold; color: #374151;">🗣️ What You Said:</p>
                            <div style="
                                background: #f9fafb; 
                                padding: 15px; 
                                border-radius: 6px; 
                                border-left: 4px solid #8b5cf6;
                                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                                line-height: 1.6;
                                color: #1f2937;
                                font-size: 16px;
                            ">
                                "${result.transcribed_text || 'No speech detected in the audio.'}"
                            </div>
                        </div>

                        <div style="background: white; padding: 15px; border-radius: 8px; margin: 15px 0; border: 1px solid #ddd;">
                            <p style="margin: 0 0 10px 0; font-weight: bold; color: #374151;">🎵 Echo Response (Murf Voice):</p>
                            <audio controls src="${result.audio_url}" style="width: 100%; margin: 10px 0;"></audio>
                        </div>

                        <div style="background: white; padding: 15px; border-radius: 8px; margin: 15px 0; border: 1px solid #ddd;">
                            <p style="margin: 0 0 10px 0; font-weight: bold; color: #374151;">📊 Echo Details:</p>
                            <p style="margin: 5px 0; font-size: 14px;"><strong>📁 Original File:</strong> ${result.original_filename}</p>
                            <p style="margin: 5px 0; font-size: 14px;"><strong>🎤 Voice:</strong> ${result.voice_id}</p>
                            <p style="margin: 5px 0; font-size: 14px;"><strong>⏱️ Duration:</strong> ${result.audio_duration ? result.audio_duration.toFixed(2) + 's' : 'N/A'}</p>
                            <p style="margin: 5px 0; font-size: 14px;"><strong>📝 Words Count:</strong> ${result.words_count}</p>
                            <p style="margin: 5px 0; font-size: 14px;"><strong>🤖 Services:</strong> AssemblyAI + Murf</p>
                        </div>
                        
                        <p style="margin: 15px 0 0 0; font-size: 12px; color: #666; text-align: center; font-style: italic;">
                            Echo completed at: ${new Date().toLocaleString()}
                        </p>
                    </div>
                `;

            console.log('Echo bot successful - results displayed');

        } else {
            uploadResults.innerHTML = `
                    <div style="
                        border: 3px solid #ef4444; 
                        padding: 15px; 
                        margin: 10px 0; 
                        background: #fef2f2; 
                        border-radius: 8px;
                    ">
                        <h3 style="color: #ef4444; margin: 0 0 15px 0; font-size: 18px;">❌ Echo Bot Failed</h3>
                        <div style="background: white; padding: 15px; border-radius: 8px; border: 1px solid #ddd;">
                            <p style="color: #ef4444; font-weight: bold;">${result.error || 'Unknown echo bot error'}</p>
                            <p style="color: #6b7280; margin-top: 10px;">Please check your API keys and try again.</p>
                        </div>
                        <p style="margin: 15px 0 0 0; font-size: 12px; color: #666; text-align: center; font-style: italic;">
                            Failed at: ${new Date().toLocaleString()}
                        </p>
                    </div>
                `;
        }
    } catch (error) {
        console.error('Echo bot error:', error);
        uploadResults.innerHTML = `
                <div style="
                    border: 3px solid #ef4444; 
                    padding: 15px; 
                    margin: 10px 0; 
                    background: #fef2f2; 
                    border-radius: 8px;
                ">
                    <h3 style="color: #ef4444; margin: 0 0 15px 0; font-size: 18px;">❌ Network Error</h3>
                    <div style="background: white; padding: 15px; border-radius: 8px; border: 1px solid #ddd;">
                        <p style="color: #ef4444; font-weight: bold;">${error.message}</p>
                        <p style="color: #6b7280; margin-top: 10px;">Please check your internet connection and server status.</p>
                    </div>
                    <p style="margin: 15px 0 0 0; font-size: 12px; color: #666; text-align: center; font-style: italic;">
                        Error occurred at: ${new Date().toLocaleString()}
                    </p>
                </div>
            `;
    }
}

const startLLMBtn = document.getElementById("startLLMRecording");
const stopLLMBtn = document.getElementById("stopLLMRecording");
const llmRecordingResult = document.getElementById("llmRecordingResult");
const llmResults = document.getElementById("llmResults");

let llmMediaRecorder;
let llmAudioChunks = [];

startLLMBtn.addEventListener("click", async (event) => {
    event.preventDefault();
    try {
        console.log("Start LLM recording clicked");
        llmRecordingResult.innerHTML = '<div class="status-message status-recording">🎤 Ask your question...</div>';

        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        console.log("Got media stream for LLM");

        llmMediaRecorder = new MediaRecorder(stream);
        llmAudioChunks = [];

        llmMediaRecorder.ondataavailable = event => {
            console.log("LLM data available:", event.data.size);
            if (event.data.size > 0) {
                llmAudioChunks.push(event.data);
            }
        };

        llmMediaRecorder.onstop = () => {
            console.log("LLM recording stopped");
            const audioBlob = new Blob(llmAudioChunks, { type: 'audio/webm' });
            const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
            const filename = `llm_query_${timestamp}.webm`;

            console.log('LLM audio blob created:', audioBlob.size, 'bytes');

            llmRecordingResult.innerHTML = `
                    <div style="
                        background: #f0f9ff;
                        border: 3px solid #0ea5e9;
                        border-radius: 12px;
                        padding: 20px;
                        margin: 20px 0;
                        width: 100%;
                        max-width: 100%;
                        box-sizing: border-box;
                        position: relative;
                        display: block !important;
                        visibility: visible !important;
                        opacity: 1 !important;
                    ">
                        <h3 style="color: #0ea5e9; margin: 0 0 15px 0; font-size: 20px;">🎤 Question Recorded!</h3>
                        
                        <div style="background: white; padding: 15px; border-radius: 8px; margin: 15px 0; border: 1px solid #ddd;">
                            <p style="margin: 0 0 10px 0; font-weight: bold; color: #374151;">📁 Audio Details:</p>
                            <p style="margin: 5px 0;"><strong>Filename:</strong> ${filename}</p>
                            <p style="margin: 5px 0;"><strong>Size:</strong> ${audioBlob.size} bytes (${(audioBlob.size / 1024).toFixed(2)} KB)</p>
                            <p style="margin: 5px 0;"><strong>Status:</strong> Processing with AI...</p>
                        </div>
                        
                        <p style="margin: 15px 0 0 0; font-size: 12px; color: #666; text-align: center; font-style: italic;">
                            Recorded at: ${new Date().toLocaleString()}
                        </p>
                    </div>
                `;

            setTimeout(async () => {
                console.log('🧠 Starting LLM processing...');
                await processVoiceLLM(audioBlob, filename);
            }, 1000);
        };

        llmMediaRecorder.start();
        console.log("LLM recording started");
        startLLMBtn.disabled = true;
        stopLLMBtn.disabled = false;
    } catch (err) {
        console.error("LLM recording error:", err);
        llmRecordingResult.innerHTML = `<p style="color:red;">Microphone access denied or not supported: ${err.message}</p>`;
    }
});

stopLLMBtn.addEventListener("click", (event) => {
    event.preventDefault();
    console.log("Stop LLM recording clicked");
    if (llmMediaRecorder && llmMediaRecorder.state !== "inactive") {
        llmMediaRecorder.stop();
        startLLMBtn.disabled = false;
        stopLLMBtn.disabled = true;
        console.log("LLM recording stopped by user");
    }
});

function handleFallbackAudio(audioUrl, fallbackText) {
    if (audioUrl && audioUrl.startsWith('web-speech:')) {
        const base64Text = audioUrl.replace('web-speech:', '');
        const text = atob(base64Text);

        console.log('Using Web Speech API fallback for:', text);

        if ('speechSynthesis' in window) {
            const utterance = new SpeechSynthesisUtterance(text);
            // Optimize settings to match Murf voice characteristics
            utterance.rate = 1.1;    // Faster rate to match Murf speed
            utterance.pitch = 1.0;   // Natural pitch
            utterance.volume = 0.9;  // Higher volume

            // Wait for voices to load, then select best voice
            const setVoiceAndSpeak = () => {
                const voices = speechSynthesis.getVoices();
                
                // Prefer voices that sound more like Murf (male, clear, American)
                const preferredVoice = voices.find(voice => 
                    (voice.name.includes('Microsoft David') || 
                     voice.name.includes('Google US English Male') ||
                     voice.name.includes('Alex') ||
                     voice.name.includes('Daniel') ||
                     voice.name.includes('Microsoft Mark')) &&
                    voice.lang.startsWith('en')
                ) || voices.find(voice => 
                    voice.lang.startsWith('en-US') && voice.name.includes('Male')
                ) || voices.find(voice => 
                    voice.lang.startsWith('en-US')
                ) || voices.find(voice => 
                    voice.lang.startsWith('en')
                );
                
                if (preferredVoice) {
                    utterance.voice = preferredVoice;
                    console.log('Using optimized voice:', preferredVoice.name);
                }
                
                speechSynthesis.speak(utterance);
            };
            
            // Handle voice loading
            if (speechSynthesis.getVoices().length > 0) {
                setVoiceAndSpeak();
            } else {
                speechSynthesis.addEventListener('voiceschanged', setVoiceAndSpeak, { once: true });
            }

            return `
                    <div style="background: #fef3c7; padding: 10px; border-radius: 6px; margin: 10px 0; border-left: 4px solid #f59e0b;">
                        <p style="margin: 0; color: #92400e; font-size: 14px;">
                            🔊 <strong>Fallback Audio:</strong> Using optimized browser speech (faster speed, better voice)
                        </p>
                        <p style="margin: 5px 0 0 0; color: #92400e; font-size: 12px; font-style: italic;">
                            "${text}"
                        </p>
                    </div>
                `;
        } else {
            return `
                    <div style="background: #fef2f2; padding: 10px; border-radius: 6px; margin: 10px 0; border-left: 4px solid #ef4444;">
                        <p style="margin: 0; color: #dc2626; font-size: 14px;">
                            📝 <strong>Text Response:</strong> Audio not available
                        </p>
                        <p style="margin: 5px 0 0 0; color: #dc2626; font-size: 12px;">
                            "${text}"
                        </p>
                    </div>
                `;
        }
    } else if (audioUrl && (audioUrl.startsWith('data:audio/') || audioUrl.startsWith('http'))) {
        // Regular audio URL (including Murf fallback audio)
        return `<audio controls src="${audioUrl}" style="width: 100%; margin: 10px 0;" autoplay></audio>`;
    } else {
        return `
                <div style="background: #fef2f2; padding: 10px; border-radius: 6px; margin: 10px 0; border-left: 4px solid #ef4444;">
                    <p style="margin: 0; color: #dc2626; font-size: 14px;">
                        📝 <strong>Text Response:</strong> Audio generation failed
                    </p>
                    <p style="margin: 5px 0 0 0; color: #dc2626; font-size: 12px;">
                        "${fallbackText || 'Audio not available'}"
                    </p>
                </div>
            `;
    }
}

function showProcessingStatus(retryCount = 0, maxRetries = 3) {
    llmResults.innerHTML = `
            <div style="
                border: 2px solid #0ea5e9; 
                padding: 15px; 
                margin: 15px 0; 
                background: #f0f9ff; 
                border-radius: 10px;
                animation: pulse 2s infinite;
            ">
                <h3 style="color: #0369a1; margin: 0 0 10px 0; font-size: 18px;">🧠 AI is thinking...</h3>
                <p style="margin: 0; color: #0369a1;">Transcribing → Generating AI response → Converting to speech...</p>
                ${retryCount > 0 ? `<p style="margin: 5px 0 0 0; color: #f59e0b; font-size: 12px;">Retry attempt ${retryCount}/${maxRetries}</p>` : ''}
            </div>
        `;
}

function showRetryStatus(retryCount, maxRetries, error, isTimeoutError, isNetworkError) {
    const errorType = isTimeoutError ? 'Timeout' : isNetworkError ? 'Connection' : 'Processing';
    llmResults.innerHTML = `
            <div style="
                border: 2px solid #f59e0b; 
                padding: 15px; 
                margin: 15px 0; 
                background: #fef3c7; 
                border-radius: 10px;
            ">
                <h3 style="color: #d97706; margin: 0 0 10px 0; font-size: 18px;">🔄 Retrying...</h3>
                <p style="margin: 0; color: #92400e;">${errorType} error occurred. Retrying in 2 seconds... (${retryCount}/${maxRetries})</p>
                <p style="margin: 5px 0 0 0; font-size: 12px; color: #92400e;">Error: ${error.message}</p>
            </div>
        `;
}

function showSuccessResponse(result, filename) {
    llmResults.innerHTML = `
            <div style="
                border: 3px solid #0ea5e9; 
                padding: 20px; 
                margin: 15px 0; 
                background: #f0f9ff; 
                border-radius: 10px;
                box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            ">
                <h3 style="color: #0369a1; margin: 0 0 15px 0; font-size: 18px;">🧠 AI Response Complete!</h3>
                
                <div style="background: white; padding: 15px; border-radius: 8px; margin: 15px 0; border: 1px solid #ddd;">
                    <p style="margin: 0 0 10px 0; font-weight: bold; color: #374151;">❓ Your Question:</p>
                    <div style="
                        background: #f9fafb; 
                        padding: 15px; 
                        border-radius: 6px; 
                        border-left: 4px solid #0ea5e9;
                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                        line-height: 1.6;
                        color: #1f2937;
                        font-size: 16px;
                    ">
                        "${result.user_query || 'No speech detected.'}"
                    </div>
                </div>

                <div style="background: white; padding: 15px; border-radius: 8px; margin: 15px 0; border: 1px solid #ddd;">
                    <p style="margin: 0 0 10px 0; font-weight: bold; color: #374151;">🤖 AI Response:</p>
                    <div style="
                        background: #f0f9ff; 
                        padding: 15px; 
                        border-radius: 6px; 
                        border-left: 4px solid #10b981;
                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                        line-height: 1.6;
                        color: #1f2937;
                        font-size: 16px;
                        margin-bottom: 15px;
                    ">
                        "${result.llm_response || 'No response generated.'}"
                    </div>
                    ${handleFallbackAudio(result.audioFile, result.llm_response)}
                </div>

                <div style="background: white; padding: 15px; border-radius: 8px; margin: 15px 0; border: 1px solid #ddd;">
                    <p style="margin: 0 0 10px 0; font-weight: bold; color: #374151;">📊 Processing Details:</p>
                    <p style="margin: 5px 0; font-size: 14px;"><strong>📁 Original File:</strong> ${result.original_filename}</p>
                    <p style="margin: 5px 0; font-size: 14px;"><strong>🎤 Voice:</strong> ${result.voice_id}</p>
                    <p style="margin: 5px 0; font-size: 14px;"><strong>🤖 Model:</strong> ${result.model}</p>
                    <p style="margin: 5px 0; font-size: 14px;"><strong>⏱️ Duration:</strong> ${result.audio_duration ? result.audio_duration.toFixed(2) + 's' : 'N/A'}</p>
                    <p style="margin: 5px 0; font-size: 14px;"><strong>🔧 Services:</strong> AssemblyAI + Gemini + Murf</p>
                </div>
                
                <p style="margin: 15px 0 0 0; font-size: 12px; color: #666; text-align: center; font-style: italic;">
                    AI response completed at: ${new Date().toLocaleString()}
                </p>
            </div>
        `;

    setTimeout(() => {
        const audioElement = document.querySelector('#llmResults audio');
        if (audioElement) {
            audioElement.play().catch(e => console.log('Auto-play blocked:', e));
        } else if (result.audioFile && result.audioFile.startsWith('web-speech:')) {
            console.log('Web Speech API fallback audio already playing');
        }
    }, 500);
}

function showPartialSuccessResponse(result, filename) {
    const serviceIssues = [];
    if (result.service_status && !result.service_status.llm) serviceIssues.push('AI Response');
    if (result.service_status && !result.service_status.tts) serviceIssues.push('Voice Generation');

    llmResults.innerHTML = `
            <div style="
                border: 3px solid #f59e0b; 
                padding: 20px; 
                margin: 15px 0; 
                background: #fef3c7; 
                border-radius: 10px;
                box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            ">
                <h3 style="color: #d97706; margin: 0 0 15px 0; font-size: 18px;">⚠️ Partial Success - Using Fallback</h3>
                
                ${serviceIssues.length > 0 ? `
                <div style="background: #fef2f2; padding: 10px; border-radius: 6px; margin: 10px 0; border-left: 4px solid #ef4444;">
                    <p style="margin: 0; color: #dc2626; font-size: 14px;">
                        <strong>Service Issues:</strong> ${serviceIssues.join(', ')} - using fallback responses
                    </p>
                </div>
                ` : ''}
                
                <div style="background: white; padding: 15px; border-radius: 8px; margin: 15px 0; border: 1px solid #ddd;">
                    <p style="margin: 0 0 10px 0; font-weight: bold; color: #374151;">❓ Your Question:</p>
                    <div style="
                        background: #f9fafb; 
                        padding: 15px; 
                        border-radius: 6px; 
                        border-left: 4px solid #f59e0b;
                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                        line-height: 1.6;
                        color: #1f2937;
                        font-size: 16px;
                    ">
                        "${result.user_query || 'No speech detected.'}"
                    </div>
                </div>

                <div style="background: white; padding: 15px; border-radius: 8px; margin: 15px 0; border: 1px solid #ddd;">
                    <p style="margin: 0 0 10px 0; font-weight: bold; color: #374151;">🤖 AI Response:</p>
                    <div style="
                        background: #fef3c7; 
                        padding: 15px; 
                        border-radius: 6px; 
                        border-left: 4px solid #f59e0b;
                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                        line-height: 1.6;
                        color: #1f2937;
                        font-size: 16px;
                        margin-bottom: 15px;
                    ">
                        "${result.llm_response || result.fallback_message || 'Fallback response used.'}"
                    </div>
                    ${result.audioFile ? handleFallbackAudio(result.audioFile, result.llm_response || result.fallback_message) : ''}
                </div>
                
                <p style="margin: 15px 0 0 0; font-size: 12px; color: #666; text-align: center; font-style: italic;">
                    Response completed with fallback at: ${new Date().toLocaleString()}
                </p>
            </div>
        `;
}

function showErrorWithFallbackAudio(result, filename) {
    llmResults.innerHTML = `
        <div style="
            border: 3px solid #ef4444; 
            padding: 20px; 
            margin: 15px 0; 
            background: #fef2f2; 
            border-radius: 10px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        ">
            <h3 style="color: #ef4444; margin: 0 0 15px 0; font-size: 18px;">🔧 Service Error - Playing Fallback Audio</h3>
            
            <div style="background: #fef2f2; padding: 15px; border-radius: 8px; margin: 15px 0; border: 1px solid #ef4444;">
                <p style="margin: 0 0 10px 0; font-weight: bold; color: #dc2626;">⚠️ What happened:</p>
                <p style="margin: 0; color: #dc2626;">
                    ${result.error || "Service temporarily unavailable"}
                </p>
            </div>

            <div style="background: white; padding: 15px; border-radius: 8px; margin: 15px 0; border: 1px solid #ddd;">
                <p style="margin: 0 0 10px 0; font-weight: bold; color: #374151;">🔊 Fallback Audio Response:</p>
                ${handleFallbackAudio(result.audioFile, result.fallback_message)}
            </div>

            <div style="background: white; padding: 15px; border-radius: 8px; margin: 15px 0; border: 1px solid #ddd;">
                <p style="margin: 0 0 10px 0; font-weight: bold; color: #374151;">💡 What you can try:</p>
                <ul style="margin: 0; padding-left: 20px; color: #374151; line-height: 1.6;">
                    <li>Check your internet connection</li>
                    <li>Try recording a shorter message</li>
                    <li>Wait a moment and try again</li>
                    <li>Speak more clearly if the audio wasn't understood</li>
                </ul>
            </div>
            
            <p style="margin: 15px 0 0 0; font-size: 12px; color: #666; text-align: center; font-style: italic;">
                Error with fallback audio at: ${new Date().toLocaleString()}
            </p>
        </div>
    `;

    // Auto-play fallback audio
    setTimeout(() => {
        const audioElement = document.querySelector('#llmResults audio');
        if (audioElement) {
            audioElement.play().catch(e => console.log('Auto-play blocked:', e));
        } else if (result.audioFile && result.audioFile.startsWith('web-speech:')) {
            console.log('Web Speech API fallback audio already playing');
        }
    }, 500);
}

function showFallbackResponse(result, filename) {
    llmResults.innerHTML = `
            <div style="
                border: 3px solid #ef4444; 
                padding: 20px; 
                margin: 15px 0; 
                background: #fef2f2; 
                border-radius: 10px;
                box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            ">
                <h3 style="color: #ef4444; margin: 0 0 15px 0; font-size: 18px;">🔧 Using Fallback Response</h3>
                
                <div style="background: #fef2f2; padding: 15px; border-radius: 8px; margin: 15px 0; border: 1px solid #ef4444;">
                    <p style="margin: 0 0 10px 0; font-weight: bold; color: #dc2626;">⚠️ Service Status:</p>
                    <p style="margin: 0; color: #dc2626;">
                        ${result.fallback_message || "I'm having trouble connecting right now, but I'm still here to help!"}
                    </p>
                </div>

                <div style="background: white; padding: 15px; border-radius: 8px; margin: 15px 0; border: 1px solid #ddd;">
                    <p style="margin: 0 0 10px 0; font-weight: bold; color: #374151;">💡 What you can try:</p>
                    <ul style="margin: 0; padding-left: 20px; color: #374151; line-height: 1.6;">
                        <li>Check your internet connection</li>
                        <li>Try recording a shorter message</li>
                        <li>Wait a moment and try again</li>
                        <li>Speak more clearly if the audio wasn't understood</li>
                    </ul>
                </div>
                
                <p style="margin: 15px 0 0 0; font-size: 12px; color: #666; text-align: center; font-style: italic;">
                    Fallback response at: ${new Date().toLocaleString()}
                </p>
            </div>
        `;
}

function showFinalError(error, filename, isTimeoutError = false, isNetworkError = false) {
    const errorType = isTimeoutError ? 'Timeout' : isNetworkError ? 'Network' : 'Processing';

    llmResults.innerHTML = `
            <div style="
                border: 3px solid #ef4444; 
                padding: 20px; 
                margin: 15px 0; 
                background: #fef2f2; 
                border-radius: 10px;
                box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            ">
                <h3 style="color: #ef4444; margin: 0 0 15px 0; font-size: 18px;">
                    ${isTimeoutError ? '⏱️ Request Timed Out' : isNetworkError ? '🌐 Connection Failed' : '❌ AI Processing Failed'}
                </h3>
                
                <div style="background: white; padding: 15px; border-radius: 8px; margin: 15px 0; border: 1px solid #ddd;">
                    <p style="margin: 0 0 10px 0; font-weight: bold; color: #374151;">🔍 What happened:</p>
                    <div style="
                        background: #fef2f2; 
                        padding: 15px; 
                        border-radius: 6px; 
                        border-left: 4px solid #ef4444;
                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                        line-height: 1.6;
                        color: #dc2626;
                        font-size: 14px;
                    ">
                        ${isTimeoutError ?
            "I'm having trouble connecting right now. The request took too long to complete." :
            isNetworkError ?
                "I'm having trouble connecting right now. Please check your internet connection." :
                `I'm having trouble processing your request: ${error.message}`
        }
                    </div>
                </div>

                <div style="background: white; padding: 15px; border-radius: 8px; margin: 15px 0; border: 1px solid #ddd;">
                    <p style="margin: 0 0 10px 0; font-weight: bold; color: #374151;">💡 What you can try:</p>
                    <ul style="margin: 0; padding-left: 20px; color: #374151; line-height: 1.6;">
                        <li>Check your internet connection</li>
                        <li>Try recording a shorter message</li>
                        <li>Wait a moment and try again</li>
                        <li>Speak more clearly if the audio wasn't understood</li>
                        ${isTimeoutError ? '<li>The server might be busy - try again in a few minutes</li>' : ''}
                    </ul>
                </div>

                <div style="background: white; padding: 15px; border-radius: 8px; margin: 15px 0; border: 1px solid #ddd;">
                    <p style="margin: 0 0 10px 0; font-weight: bold; color: #374151;">📊 Error Details:</p>
                    <p style="margin: 5px 0; font-size: 14px;"><strong>📁 File:</strong> ${filename}</p>
                    <p style="margin: 5px 0; font-size: 14px;"><strong>🔄 Retries:</strong> 3 attempts made</p>
                    <p style="margin: 5px 0; font-size: 14px;"><strong>⚠️ Error Type:</strong> ${errorType}</p>
                </div>
                
                <div style="text-align: center; margin-top: 20px;">
                    <button onclick="location.reload()" style="
                        background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
                        color: white;
                        border: none;
                        padding: 12px 24px;
                        border-radius: 8px;
                        cursor: pointer;
                        font-weight: 600;
                        font-size: 14px;
                    ">🔄 Refresh Page</button>
                </div>
                
                <p style="margin: 15px 0 0 0; font-size: 12px; color: #666; text-align: center; font-style: italic;">
                    Error occurred at: ${new Date().toLocaleString()}
                </p>
            </div>
        `;
}

async function processVoiceLLM(audioBlob, filename) {
    let retryCount = 0;
    const maxRetries = 3;
    const retryDelay = 2000;

    while (retryCount <= maxRetries) {
        try {
            console.log('Starting voice LLM process... (Attempt ' + (retryCount + 1) + '/' + (maxRetries + 1) + ')');

            if (!llmResults) {
                console.error('LLM results container not found');
                showFinalError(new Error('UI Error: Results container not found'), filename);
                return;
            }

            if (!audioBlob || audioBlob.size === 0) {
                showFinalError(new Error('No audio data to process'), filename);
                return;
            }

            const formData = new FormData();
            formData.append('file', audioBlob, filename);

            console.log('Sending audio for LLM processing:', filename, 'Size:', audioBlob.size);

            showProcessingStatus(retryCount, maxRetries);

            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 60000);

            const response = await fetch('http://localhost:8000/llm/query', {
                method: 'POST',
                body: formData,
                signal: controller.signal
            });

            clearTimeout(timeoutId);

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const result = await response.json();
            console.log('Voice LLM response:', result);

            if (result.status === 'success') {
                showSuccessResponse(result, filename);
                return;
            } else if (result.status === 'partial_success') {
                showPartialSuccessResponse(result, filename);
                return;
            } else if (result.status === 'fallback') {
                showFallbackResponse(result, filename);
                return;
            } else if (result.status === 'error' && result.audioFile) {
                // Handle error with fallback audio
                showErrorWithFallbackAudio(result, filename);
                return;
            } else {
                throw new Error(result.error || 'Unknown server error');
            }

        } catch (error) {
            console.error('Voice LLM error (attempt ' + (retryCount + 1) + '):', error);

            const isNetworkError = error.name === 'AbortError' ||
                error.message.includes('fetch') ||
                error.message.includes('network') ||
                error.message.includes('Failed to fetch');

            const isTimeoutError = error.name === 'AbortError';

            if (retryCount < maxRetries) {
                retryCount++;
                console.log(`Retrying in ${retryDelay / 1000} seconds... (${retryCount}/${maxRetries})`);

                showRetryStatus(retryCount, maxRetries, error, isTimeoutError, isNetworkError);

                await new Promise(resolve => setTimeout(resolve, retryDelay));
                continue;
            } else {
                showFinalError(error, filename, isTimeoutError, isNetworkError);
                return;
            }
        }
    }
}

const startConversationBtn = document.getElementById("startConversation");
const stopConversationBtn = document.getElementById("stopConversation");
const newSessionBtn = document.getElementById("newSession");
const conversationStatus = document.getElementById("conversationStatus");
const conversationHistory = document.getElementById("conversationHistory");
const sessionInfo = document.getElementById("sessionInfo");

let conversationRecorder;
let conversationChunks = [];
let currentSessionId = null;
let isAutoRecording = false;
let conversationMessages = [];

function initializeSession() {
    const urlParams = new URLSearchParams(window.location.search);
    currentSessionId = urlParams.get('session') || generateSessionId();

    const newUrl = new URL(window.location);
    newUrl.searchParams.set('session', currentSessionId);
    window.history.replaceState({}, '', newUrl);

    updateSessionInfo();
    loadChatHistory();
}

function generateSessionId() {
    return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
}

function updateSessionInfo() {
    sessionInfo.innerHTML = `Session ID: ${currentSessionId} | Messages: ${conversationMessages.length}`;
}

async function loadChatHistory() {
    try {
        const response = await fetch(`http://localhost:8000/agent/chat/${currentSessionId}/history`);
        const result = await response.json();

        if (result.status === 'active') {
            conversationMessages = result.messages;
            displayConversationHistory();
            updateSessionInfo();
        }
    } catch (error) {
        console.error('Error loading chat history:', error);
    }
}

function displayConversationHistory() {
    if (conversationMessages.length === 0) {
        conversationHistory.innerHTML = '<p style="color: #6b7280; font-style: italic; text-align: center;">No conversation yet. Start speaking to begin!</p>';
        return;
    }

    const historyHTML = conversationMessages.map((message, index) => {
        const isUser = message.role === 'user';
        const bgColor = isUser ? '#f3f4f6' : '#f0f9ff';
        const borderColor = isUser ? '#3b82f6' : '#10b981';
        const icon = isUser ? '👤' : '🤖';
        const label = isUser ? 'You' : 'AI Assistant';

        return `
                <div style="
                    background: ${bgColor};
                    padding: 15px;
                    border-radius: 12px;
                    border-left: 4px solid ${borderColor};
                    margin: 10px 0;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                ">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                        <span style="font-weight: bold; color: #374151; font-size: 14px;">${icon} ${label}</span>
                        <span style="font-size: 12px; color: #6b7280;">${new Date(message.timestamp).toLocaleString()}</span>
                    </div>
                    <p style="margin: 0; color: #1f2937; line-height: 1.5;">${message.content}</p>
                </div>
            `;
    }).join('');

    conversationHistory.innerHTML = historyHTML;

    conversationHistory.scrollTop = conversationHistory.scrollHeight;
}

startConversationBtn.addEventListener("click", async (event) => {
    event.preventDefault();
    await startRecording();
});

stopConversationBtn.addEventListener("click", (event) => {
    event.preventDefault();
    stopRecording();
});

newSessionBtn.addEventListener("click", (event) => {
    event.preventDefault();
    startNewSession();
});

function startNewSession() {
    currentSessionId = generateSessionId();
    conversationMessages = [];

    const newUrl = new URL(window.location);
    newUrl.searchParams.set('session', currentSessionId);
    window.history.replaceState({}, '', newUrl);

    updateSessionInfo();
    displayConversationHistory();
    conversationStatus.innerHTML = 'New session started. Ready to chat!';
}

async function startRecording() {
    try {
        console.log("Starting conversation recording");
        conversationStatus.innerHTML = '<div class="status-message status-recording">🎤 Listening... Speak now!</div>';

        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        console.log("Got media stream for conversation");

        conversationRecorder = new MediaRecorder(stream);
        conversationChunks = [];

        conversationRecorder.ondataavailable = event => {
            console.log("Conversation data available:", event.data.size);
            if (event.data.size > 0) {
                conversationChunks.push(event.data);
            }
        };

        conversationRecorder.onstop = async () => {
            console.log("Conversation recording stopped");
            const audioBlob = new Blob(conversationChunks, { type: 'audio/webm' });
            const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
            const filename = `conversation_${currentSessionId}_${timestamp}.webm`;

            console.log('Conversation audio blob created:', audioBlob.size, 'bytes');

            conversationStatus.innerHTML = '<div class="status-message status-processing">🤖 AI is thinking...</div>';

            await processConversation(audioBlob, filename);
        };

        conversationRecorder.start();
        console.log("Conversation recording started");
        startConversationBtn.disabled = true;
        stopConversationBtn.disabled = false;
    } catch (err) {
        console.error("Conversation recording error:", err);
        conversationStatus.innerHTML = `<div class="status-message status-error">❌ Microphone access denied: ${err.message}</div>`;
    }
}

function stopRecording() {
    console.log("Stop conversation clicked");
    if (conversationRecorder && conversationRecorder.state !== "inactive") {
        conversationRecorder.stop();
        startConversationBtn.disabled = false;
        stopConversationBtn.disabled = true;
        console.log("Conversation recording stopped by user");
    }
}

async function processConversation(audioBlob, filename) {
    try {
        console.log('Starting conversation processing...');

        const formData = new FormData();
        formData.append('file', audioBlob, filename);

        console.log('Sending audio for conversation:', filename, 'Size:', audioBlob.size);

        const response = await fetch(`http://localhost:8000/agent/chat/${currentSessionId}`, {
            method: 'POST',
            body: formData
        });

        const result = await response.json();
        console.log('Conversation response:', result);

        if (response.ok && result.status === 'success') {
            conversationMessages.push({
                role: 'user',
                content: result.user_message,
                timestamp: result.timestamp
            });

            conversationMessages.push({
                role: 'assistant',
                content: result.ai_response,
                timestamp: result.timestamp
            });

            displayConversationHistory();
            updateSessionInfo();

            conversationStatus.innerHTML = '<div class="status-message status-success">✅ Response ready! Listening for next message...</div>';

            const audio = new Audio(result.audioFile);

            audio.addEventListener('ended', () => {
                console.log('AI response finished playing, auto-starting recording...');
                setTimeout(() => {
                    if (!conversationRecorder || conversationRecorder.state === "inactive") {
                        startRecording();
                    }
                }, 1000);
            });

            audio.play().catch(e => console.log('Auto-play blocked:', e));

        } else {
            conversationStatus.innerHTML = `<div class="status-message status-error">❌ Conversation failed: ${result.error || 'Unknown error'}</div>`;
        }
    } catch (error) {
        console.error('Conversation error:', error);
        conversationStatus.innerHTML = `<div class="status-message status-error">❌ Network error: ${error.message}</div>`;
    }
}

initializeSession();