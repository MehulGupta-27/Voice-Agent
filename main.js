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
                audioResult.innerHTML = `
                    <p>Audio generated:</p>
                    <audio controls src="${audioUrl}"></audio>
                `;
            } else {
                audioResult.innerHTML = `<p style="color:red;">Failed to get audio URL.</p>`;
            }
        } catch (err) {
            console.error(err);
            audioResult.innerHTML = `<p style="color:red;">Error contacting server.</p>`;
        }
    });
});
