/* ══════════ Registro Biométrico ══════════ */

let bioSignatureCtx = null;
let bioIsDrawing = false;
let bioFaceStream = null;
let bioFaceData = null;
let bioMediaRecorder = null;
let bioAudioChunks = [];
let bioIsRecording = false;
let bioVoiceData = null;

async function checkBiometricStatus() {
    if (!state.user) return;
    try {
        const res = await apiFetch(`/biometria/estado/${state.user.id_users}`);
        if (!res.ok) return;
        const data = await res.json();

        const statusDiv = document.getElementById('bio-status');
        if (data.registrado) {
            statusDiv.innerHTML = `
                <h3 style="color:var(--success)">\u2705 Biometría Registrada</h3>
                <p>Sus datos biométricos están registrados en el sistema.</p>
                <div class="mt-1">
                    <div><strong>Algoritmo firma:</strong> ${data.algoritmo_firma}</div>
                    <div><strong>Algoritmo facial:</strong> ${data.algoritmo_facial}</div>
                    <div><strong>Algoritmo voz:</strong> ${data.algoritmo_voz}</div>
                    <div><strong>Registrado:</strong> ${new Date(data.registrado_en).toLocaleString('es')}</div>
                </div>
            `;
            document.getElementById('bio-register-form').classList.add('hidden');
        } else {
            statusDiv.innerHTML = `
                <h3 style="color:var(--warning)">\u26A0 Biometría No Registrada</h3>
                <p>Debe registrar sus datos biométricos para poder crear eventos ganaderos.</p>
            `;
            document.getElementById('bio-register-form').classList.remove('hidden');
            initBioSignatureCanvas();
            startBioCamera();
        }
    } catch (e) { /* silent */ }
}

// ── Firma ──

function initBioSignatureCanvas() {
    const canvas = document.getElementById('bio-signature-canvas');
    bioSignatureCtx = canvas.getContext('2d');
    bioSignatureCtx.fillStyle = 'white';
    bioSignatureCtx.fillRect(0, 0, canvas.width, canvas.height);
    bioSignatureCtx.strokeStyle = '#000';
    bioSignatureCtx.lineWidth = 2;
    bioSignatureCtx.lineCap = 'round';

    canvas.addEventListener('mousedown', bioStartDraw);
    canvas.addEventListener('mousemove', bioDraw);
    canvas.addEventListener('mouseup', bioStopDraw);
    canvas.addEventListener('mouseout', bioStopDraw);

    canvas.addEventListener('touchstart', (e) => {
        e.preventDefault();
        const rect = canvas.getBoundingClientRect();
        const touch = e.touches[0];
        bioStartDraw({ offsetX: touch.clientX - rect.left, offsetY: touch.clientY - rect.top });
    });
    canvas.addEventListener('touchmove', (e) => {
        e.preventDefault();
        const rect = canvas.getBoundingClientRect();
        const touch = e.touches[0];
        bioDraw({ offsetX: touch.clientX - rect.left, offsetY: touch.clientY - rect.top });
    });
    canvas.addEventListener('touchend', (e) => { e.preventDefault(); bioStopDraw(); });
}

function bioStartDraw(e) {
    bioIsDrawing = true;
    bioSignatureCtx.beginPath();
    bioSignatureCtx.moveTo(e.offsetX, e.offsetY);
}
function bioDraw(e) {
    if (!bioIsDrawing) return;
    bioSignatureCtx.lineTo(e.offsetX, e.offsetY);
    bioSignatureCtx.stroke();
}
function bioStopDraw() { bioIsDrawing = false; }

function clearBioSignature() {
    const canvas = document.getElementById('bio-signature-canvas');
    bioSignatureCtx.fillStyle = 'white';
    bioSignatureCtx.fillRect(0, 0, canvas.width, canvas.height);
}

// ── Rostro ──

async function startBioCamera() {
    try {
        bioFaceStream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'user' } });
        document.getElementById('bio-face-video').srcObject = bioFaceStream;
    } catch (e) {
        showToast('No se pudo acceder a la cámara', 'error');
    }
}

function captureBioFace() {
    const video = document.getElementById('bio-face-video');
    const canvas = document.getElementById('bio-face-canvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext('2d').drawImage(video, 0, 0);

    bioFaceData = canvas.toDataURL('image/png');
    document.getElementById('bio-face-preview-img').src = bioFaceData;
    document.getElementById('bio-face-preview').classList.remove('hidden');
    document.getElementById('btn-bio-capture-face').classList.add('hidden');
    document.getElementById('btn-bio-retry-face').classList.remove('hidden');
    showToast('Rostro capturado', 'success');
}

function retryBioFace() {
    bioFaceData = null;
    document.getElementById('bio-face-preview').classList.add('hidden');
    document.getElementById('btn-bio-capture-face').classList.remove('hidden');
    document.getElementById('btn-bio-retry-face').classList.add('hidden');
}

// ── Voz ──

async function toggleBioVoiceRecording() {
    if (bioIsRecording) {
        stopBioVoiceRecording();
    } else {
        startBioVoiceRecording();
    }
}

async function startBioVoiceRecording() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        bioMediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
        bioAudioChunks = [];

        bioMediaRecorder.ondataavailable = (e) => {
            if (e.data.size > 0) bioAudioChunks.push(e.data);
        };

        bioMediaRecorder.onstop = () => {
            const blob = new Blob(bioAudioChunks, { type: 'audio/webm' });
            const url = URL.createObjectURL(blob);
            const playback = document.getElementById('bio-voice-playback');
            playback.src = url;
            playback.classList.remove('hidden');

            const reader = new FileReader();
            reader.onload = () => { bioVoiceData = reader.result; };
            reader.readAsDataURL(blob);

            stream.getTracks().forEach(t => t.stop());
            showToast('Voz capturada', 'success');
        };

        bioMediaRecorder.start();
        bioIsRecording = true;
        document.getElementById('bio-voice-indicator').classList.add('recording');
        document.getElementById('bio-voice-status').textContent = 'Grabando...';
        document.getElementById('btn-bio-record-voice').textContent = 'Detener';
    } catch (e) {
        showToast('No se pudo acceder al micrófono', 'error');
    }
}

function stopBioVoiceRecording() {
    if (bioMediaRecorder && bioMediaRecorder.state === 'recording') {
        bioMediaRecorder.stop();
    }
    bioIsRecording = false;
    document.getElementById('bio-voice-indicator').classList.remove('recording');
    document.getElementById('bio-voice-status').textContent = 'Grabación completada';
    document.getElementById('btn-bio-record-voice').textContent = 'Grabar de nuevo';
}

// ── Registro ──

async function registerBiometrics() {
    // Obtener firma como blob
    const canvas = document.getElementById('bio-signature-canvas');
    const firmaBlob = await new Promise(resolve => canvas.toBlob(resolve, 'image/png'));

    if (!firmaBlob) {
        showToast('Dibuje su firma primero', 'warning');
        return;
    }
    if (!bioFaceData) {
        showToast('Capture su rostro primero', 'warning');
        return;
    }
    if (!bioVoiceData) {
        showToast('Grabe su voz primero', 'warning');
        return;
    }

    // Convertir face a blob
    const faceBlob = await fetch(bioFaceData).then(r => r.blob());

    // Convertir voice a blob
    const voiceBlob = await fetch(bioVoiceData).then(r => r.blob());

    const formData = new FormData();
    formData.append('firma', firmaBlob, 'firma.png');
    formData.append('rostro', faceBlob, 'rostro.png');
    formData.append('voz', voiceBlob, 'voz.webm');

    try {
        showToast('Registrando datos biométricos...', 'info');
        const res = await fetch(`${API_URL}/biometria/registrar`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${state.token}` },
            body: formData,
        });
        const data = await res.json();

        if (res.ok) {
            showToast('Biometría registrada exitosamente', 'success');
            // Detener cámara
            if (bioFaceStream) {
                bioFaceStream.getTracks().forEach(t => t.stop());
            }
            checkBiometricStatus();
        } else {
            showToast(data.detail || 'Error al registrar biometría', 'error');
        }
    } catch (err) {
        showToast('Error de conexión', 'error');
    }
}
