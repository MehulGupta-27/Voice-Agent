document.addEventListener("DOMContentLoaded", () => {
    const generateBtn = document.getElementById("generateBtn");
    const textInput = document.getElementById("textInput");
    const audioResult = document.getElementById("audioResult");

    generateBtn.addEventListener("click", async () => {
        const text = textInput.value.trim();

        // if (!text) {
        //     alert("Please enter some text.");
        //     return;
        // }

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
                // Generate filename for TTS audio
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

    // Recording functionality
    const startBtn = document.getElementById("startRecording");
    const stopBtn = document.getElementById("stopRecording");
    const recordingResult = document.getElementById("recordingResult");
    const uploadResults = document.getElementById("uploadResults");

    let mediaRecorder;
    let audioChunks = [];

    startBtn.addEventListener("click", async () => {
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

                // Generate filename with timestamp
                const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
                const filename = `recording_${timestamp}.webm`;

                console.log('Audio blob created:', audioBlob.size, 'bytes');

                // Create simple, stable HTML without complex CSS classes
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

                // Test if content is still there after 2 seconds
                setTimeout(() => {
                    if (recordingResult.innerHTML.includes('Recording Complete')) {
                        console.log('✅ Recording details still visible after 2 seconds');
                    } else {
                        console.log('❌ Recording details disappeared!');
                        console.log('Current content:', recordingResult.innerHTML);
                    }
                }, 2000);

                // Upload the recorded audio to server
                setTimeout(async () => {
                    await uploadAudio(audioBlob);
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

    stopBtn.addEventListener("click", () => {
        console.log("Stop recording clicked");
        if (mediaRecorder && mediaRecorder.state !== "inactive") {
            mediaRecorder.stop();
            startBtn.disabled = false;
            stopBtn.disabled = true;
            console.log("Recording stopped by user");
        }
    });

    // Upload function - simplified to avoid interference
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

            // Show upload status with new styling
            uploadResults.innerHTML = '<div class="status-message status-uploading">🔄 Uploading audio to server...</div>';

            const response = await fetch('http://localhost:8000/upload-audio', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();
            console.log('Upload response:', result);

            if (response.ok && result.filename) {
                // SUCCESS - Show permanent results with new styling
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
                // ERROR with new styling
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
});