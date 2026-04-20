/* ══════════ Utilidades WAV ══════════ */

function _audioBufferToWav(buffer) {
    const numChannels = buffer.numberOfChannels;
    const sampleRate = buffer.sampleRate;
    const bitDepth = 16;
    let pcm;
    if (numChannels === 2) {
        const L = buffer.getChannelData(0);
        const R = buffer.getChannelData(1);
        pcm = new Float32Array(L.length + R.length);
        for (let i = 0, j = 0; i < L.length; i++) {
            pcm[j++] = L[i];
            pcm[j++] = R[i];
        }
    } else {
        pcm = buffer.getChannelData(0);
    }
    const dataLen = pcm.length * 2;
    const ab = new ArrayBuffer(44 + dataLen);
    const view = new DataView(ab);
    const ws = (off, s) => { for (let i = 0; i < s.length; i++) view.setUint8(off + i, s.charCodeAt(i)); };
    ws(0, 'RIFF'); view.setUint32(4, 36 + dataLen, true);
    ws(8, 'WAVE'); ws(12, 'fmt '); view.setUint32(16, 16, true);
    view.setUint16(20, 1, true); view.setUint16(22, numChannels, true);
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, sampleRate * numChannels * 2, true);
    view.setUint16(32, numChannels * 2, true); view.setUint16(34, bitDepth, true);
    ws(36, 'data'); view.setUint32(40, dataLen, true);
    let off = 44;
    for (let i = 0; i < pcm.length; i++, off += 2) {
        const s = Math.max(-1, Math.min(1, pcm[i]));
        view.setInt16(off, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
    }
    return ab;
}

async function _webmBlobToWavBlob(webmBlob) {
    const arrayBuffer = await webmBlob.arrayBuffer();
    const audioCtx = new AudioContext();
    const audioBuffer = await audioCtx.decodeAudioData(arrayBuffer);
    audioCtx.close();
    const wavAb = _audioBufferToWav(audioBuffer);
    return new Blob([wavAb], { type: 'audio/wav' });
}

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
                <h3 style="color:var(--success)">✅ Biometría Registrada</h3>
                <p>Sus datos biométricos están registrados en el sistema.</p>
                <div class="mt-1">
                    <div><strong>Algoritmo firma:</strong> ${data.algoritmo_firma}</div>
                    <div><strong>Algoritmo facial:</strong> ${data.algoritmo_facial}</div>
                    <div><strong>Algoritmo voz:</strong> ${data.algoritmo_voz}</div>
                    <div><strong>Registrado:</strong> ${new Date(data.registrado_en).toLocaleString('es')}</div>
                </div>
                <div class="bio-change-btns mt-1">
                    <button class="btn-cambio-cred" onclick="abrirModalCambioBio('firma')">
                        ✏️ Cambiar Firma
                    </button>
                    <button class="btn-cambio-cred" onclick="abrirModalCambioBio('rostro')">
                        📷 Cambiar Rostro
                    </button>
                    <button class="btn-cambio-cred" onclick="abrirModalCambioBio('voz')">
                        🎙️ Cambiar Voz
                    </button>
                </div>
            `;
            document.getElementById('bio-register-form').classList.add('hidden');
        } else {
            statusDiv.innerHTML = `
                <h3 style="color:var(--warning)">⚠️ Biometría No Registrada</h3>
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

        bioMediaRecorder.onstop = async () => {
            const webmBlob = new Blob(bioAudioChunks, { type: 'audio/webm' });
            try {
                const wavBlob = await _webmBlobToWavBlob(webmBlob);
                const url = URL.createObjectURL(wavBlob);
                const playback = document.getElementById('bio-voice-playback');
                playback.src = url;
                playback.classList.remove('hidden');

                const reader = new FileReader();
                reader.onload = () => { bioVoiceData = reader.result; };
                reader.readAsDataURL(wavBlob);
            } catch (e) {
                showToast('Error al procesar el audio', 'error');
            }

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
    formData.append('voz', voiceBlob, 'voz.wav');

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


/* ══════════════════════════════════════════════════════════════════
   CAMBIO DE CREDENCIALES BIOMÉTRICAS
   Flujo: abrirModal → solicitarCódigo (email) → capturar + confirmar
══════════════════════════════════════════════════════════════════ */

// Estado del módulo de cambio
let cambioBioTipo = null;          // 'firma' | 'rostro' | 'voz'
let cambioBioFaceStream = null;
let cambioBioFaceData = null;
let cambioBioVoiceData = null;
let cambioBioMediaRecorder = null;
let cambioBioAudioChunks = [];
let cambioBioIsRecording = false;
let cambioBioSignatureCtx = null;
let cambioBioSignatureIsDrawing = false;

const NOMBRES_CRED = {
    firma:  'Firma Manuscrita',
    rostro: 'Reconocimiento Facial',
    voz:    'Verificación de Voz',
};

// ── Abrir modal ──────────────────────────────────────────────────

function abrirModalCambioBio(tipo) {
    cambioBioTipo      = tipo;
    cambioBioFaceData  = null;
    cambioBioVoiceData = null;
    cambioBioAudioChunks = [];
    cambioBioIsRecording = false;

    const nombre = NOMBRES_CRED[tipo] || tipo;

    document.getElementById('modal-cambio-bio-titulo').textContent =
        `Cambiar credencial: ${nombre}`;
    document.getElementById('cambio-paso-1-desc').textContent =
        `Vas a reemplazar tu credencial de ${nombre}. Para continuar confirma tu identidad mediante un código enviado a tu correo.`;

    // Ocultar/mostrar pasos
    _mostrarPasoCambio(1);

    // Ocultar todos los bloques de captura; se mostrarán en paso 2
    ['cambio-firma-capture','cambio-rostro-capture','cambio-voz-capture']
        .forEach(id => document.getElementById(id).classList.add('hidden'));

    document.getElementById('cambio-paso-1-error').classList.add('hidden');
    document.getElementById('modal-cambio-bio').classList.remove('hidden');
}

function cerrarModalCambioBio(evt) {
    // Si se hace clic en el overlay (no en el box interno), cerrar
    if (evt && evt.target !== document.getElementById('modal-cambio-bio')) return;
    _detenerRecursosCambio();
    document.getElementById('modal-cambio-bio').classList.add('hidden');
}

function _detenerRecursosCambio() {
    if (cambioBioFaceStream) {
        cambioBioFaceStream.getTracks().forEach(t => t.stop());
        cambioBioFaceStream = null;
    }
    if (cambioBioMediaRecorder && cambioBioMediaRecorder.state === 'recording') {
        cambioBioMediaRecorder.stop();
    }
}

function _mostrarPasoCambio(n) {
    [1, 2, 3].forEach(i => {
        const el = document.getElementById(`cambio-paso-${i}`);
        el.classList.toggle('hidden', i !== n);
    });
}

// ── Paso 1: Solicitar código ─────────────────────────────────────

async function solicitarCodigoCambio() {
    const errDiv = document.getElementById('cambio-paso-1-error');
    errDiv.classList.add('hidden');

    try {
        showToast('Enviando código...', 'info');
        const res = await apiFetch('/biometria/solicitar-cambio', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ tipo_credencial: cambioBioTipo }),
        });
        const data = await res.json();

        if (!res.ok) {
            errDiv.textContent = data.detail || 'Error al solicitar el código.';
            errDiv.classList.remove('hidden');
            return;
        }

        // Mostrar a qué correo se envió (enmascarado)
        document.getElementById('cambio-email-destino').textContent = data.email_destino;

        // Limpiar campo código
        document.getElementById('cambio-codigo-input').value = '';
        document.getElementById('cambio-paso-2-error').classList.add('hidden');

        // Mostrar bloque de captura correspondiente y arrancar recursos
        _iniciarCapturaCambio(cambioBioTipo);

        _mostrarPasoCambio(2);
        showToast(`Código enviado a ${data.email_destino}`, 'success');
    } catch (e) {
        errDiv.textContent = 'Error de conexión. Inténtalo de nuevo.';
        errDiv.classList.remove('hidden');
    }
}

function _iniciarCapturaCambio(tipo) {
    if (tipo === 'firma') {
        document.getElementById('cambio-firma-capture').classList.remove('hidden');
        _initCambioSignatureCanvas();
    } else if (tipo === 'rostro') {
        document.getElementById('cambio-rostro-capture').classList.remove('hidden');
        _iniciarCamaraCambio();
    } else if (tipo === 'voz') {
        document.getElementById('cambio-voz-capture').classList.remove('hidden');
        document.getElementById('cambio-voice-status').textContent = 'Listo para grabar';
        document.getElementById('btn-cambio-record-voice').textContent = '🎙️ Grabar voz';
        document.getElementById('cambio-voice-playback').classList.add('hidden');
        document.getElementById('cambio-voice-indicator').classList.remove('recording');
    }
}

// ── Canvas de firma (cambio) ─────────────────────────────────────

function _initCambioSignatureCanvas() {
    const canvas = document.getElementById('cambio-signature-canvas');
    cambioBioSignatureCtx = canvas.getContext('2d');
    cambioBioSignatureCtx.fillStyle = 'white';
    cambioBioSignatureCtx.fillRect(0, 0, canvas.width, canvas.height);
    cambioBioSignatureCtx.strokeStyle = '#000';
    cambioBioSignatureCtx.lineWidth = 2;
    cambioBioSignatureCtx.lineCap = 'round';

    // Limpiar listeners previos clonando el nodo
    const newCanvas = canvas.cloneNode(true);
    canvas.parentNode.replaceChild(newCanvas, canvas);
    cambioBioSignatureCtx = newCanvas.getContext('2d');
    cambioBioSignatureCtx.fillStyle = 'white';
    cambioBioSignatureCtx.fillRect(0, 0, newCanvas.width, newCanvas.height);
    cambioBioSignatureCtx.strokeStyle = '#000';
    cambioBioSignatureCtx.lineWidth = 2;
    cambioBioSignatureCtx.lineCap = 'round';

    newCanvas.addEventListener('mousedown', _cambioStartDraw);
    newCanvas.addEventListener('mousemove', _cambioDraw);
    newCanvas.addEventListener('mouseup', _cambioStopDraw);
    newCanvas.addEventListener('mouseout', _cambioStopDraw);
    newCanvas.addEventListener('touchstart', (e) => {
        e.preventDefault();
        const rect = newCanvas.getBoundingClientRect();
        const t = e.touches[0];
        _cambioStartDraw({ offsetX: t.clientX - rect.left, offsetY: t.clientY - rect.top });
    });
    newCanvas.addEventListener('touchmove', (e) => {
        e.preventDefault();
        const rect = newCanvas.getBoundingClientRect();
        const t = e.touches[0];
        _cambioDraw({ offsetX: t.clientX - rect.left, offsetY: t.clientY - rect.top });
    });
    newCanvas.addEventListener('touchend', (e) => { e.preventDefault(); _cambioStopDraw(); });
}

function _cambioStartDraw(e) {
    cambioBioSignatureIsDrawing = true;
    cambioBioSignatureCtx.beginPath();
    cambioBioSignatureCtx.moveTo(e.offsetX, e.offsetY);
}
function _cambioDraw(e) {
    if (!cambioBioSignatureIsDrawing) return;
    cambioBioSignatureCtx.lineTo(e.offsetX, e.offsetY);
    cambioBioSignatureCtx.stroke();
}
function _cambioStopDraw() { cambioBioSignatureIsDrawing = false; }

function limpiarCambioFirma() {
    const canvas = document.getElementById('cambio-signature-canvas');
    cambioBioSignatureCtx.fillStyle = 'white';
    cambioBioSignatureCtx.fillRect(0, 0, canvas.width, canvas.height);
}

// ── Cámara (cambio de rostro) ────────────────────────────────────

async function _iniciarCamaraCambio() {
    try {
        cambioBioFaceStream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'user' } });
        document.getElementById('cambio-face-video').srcObject = cambioBioFaceStream;
        document.getElementById('btn-cambio-capture-face').classList.remove('hidden');
        document.getElementById('btn-cambio-retry-face').classList.add('hidden');
        document.getElementById('cambio-face-preview').classList.add('hidden');
    } catch (e) {
        showToast('No se pudo acceder a la cámara', 'error');
    }
}

function capturarCambioRostro() {
    const video  = document.getElementById('cambio-face-video');
    const canvas = document.getElementById('cambio-face-canvas');
    canvas.width  = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext('2d').drawImage(video, 0, 0);
    cambioBioFaceData = canvas.toDataURL('image/png');

    document.getElementById('cambio-face-preview-img').src = cambioBioFaceData;
    document.getElementById('cambio-face-preview').classList.remove('hidden');
    document.getElementById('btn-cambio-capture-face').classList.add('hidden');
    document.getElementById('btn-cambio-retry-face').classList.remove('hidden');
    showToast('Rostro capturado', 'success');
}

function reintentarCambioRostro() {
    cambioBioFaceData = null;
    document.getElementById('cambio-face-preview').classList.add('hidden');
    document.getElementById('btn-cambio-capture-face').classList.remove('hidden');
    document.getElementById('btn-cambio-retry-face').classList.add('hidden');
}

// ── Grabación de voz (cambio) ────────────────────────────────────

async function toggleCambioVozRecording() {
    if (cambioBioIsRecording) {
        _detenerCambioVoz();
    } else {
        await _iniciarCambioVoz();
    }
}

async function _iniciarCambioVoz() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        cambioBioMediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
        cambioBioAudioChunks = [];

        cambioBioMediaRecorder.ondataavailable = (e) => {
            if (e.data.size > 0) cambioBioAudioChunks.push(e.data);
        };
        cambioBioMediaRecorder.onstop = async () => {
            const webmBlob = new Blob(cambioBioAudioChunks, { type: 'audio/webm' });
            try {
                const wavBlob = await _webmBlobToWavBlob(webmBlob);
                const url = URL.createObjectURL(wavBlob);
                const playback = document.getElementById('cambio-voice-playback');
                playback.src = url;
                playback.classList.remove('hidden');

                const reader = new FileReader();
                reader.onload = () => { cambioBioVoiceData = reader.result; };
                reader.readAsDataURL(wavBlob);
            } catch (e) {
                showToast('Error al procesar el audio', 'error');
            }

            stream.getTracks().forEach(t => t.stop());
            showToast('Voz capturada', 'success');
        };

        cambioBioMediaRecorder.start();
        cambioBioIsRecording = true;
        document.getElementById('cambio-voice-indicator').classList.add('recording');
        document.getElementById('cambio-voice-status').textContent = 'Grabando...';
        document.getElementById('btn-cambio-record-voice').textContent = '⏹ Detener';
    } catch (e) {
        showToast('No se pudo acceder al micrófono', 'error');
    }
}

function _detenerCambioVoz() {
    if (cambioBioMediaRecorder && cambioBioMediaRecorder.state === 'recording') {
        cambioBioMediaRecorder.stop();
    }
    cambioBioIsRecording = false;
    document.getElementById('cambio-voice-indicator').classList.remove('recording');
    document.getElementById('cambio-voice-status').textContent = 'Grabación completada';
    document.getElementById('btn-cambio-record-voice').textContent = '🎙️ Grabar de nuevo';
}

// ── Volver al paso 1 (reenviar código) ──────────────────────────

function volverPaso1CambioBio() {
    _detenerRecursosCambio();
    document.getElementById('cambio-paso-1-error').classList.add('hidden');
    _mostrarPasoCambio(1);
}

// ── Confirmar cambio (paso 2 → submit) ──────────────────────────

async function confirmarCambioBio() {
    const codigo  = document.getElementById('cambio-codigo-input').value.trim();
    const errDiv  = document.getElementById('cambio-paso-2-error');
    errDiv.classList.add('hidden');

    // Validar código
    if (!/^\d{6}$/.test(codigo)) {
        errDiv.textContent = 'Ingresa el código de 6 dígitos.';
        errDiv.classList.remove('hidden');
        return;
    }

    // Construir FormData
    const formData = new FormData();
    formData.append('tipo_credencial', cambioBioTipo);
    formData.append('codigo', codigo);

    if (cambioBioTipo === 'firma') {
        const canvas   = document.getElementById('cambio-signature-canvas');
        const firmaBlob = await new Promise(resolve => canvas.toBlob(resolve, 'image/png'));
        if (!firmaBlob) {
            errDiv.textContent = 'Dibuja tu nueva firma primero.';
            errDiv.classList.remove('hidden');
            return;
        }
        formData.append('nueva_firma', firmaBlob, 'firma.png');

    } else if (cambioBioTipo === 'rostro') {
        if (!cambioBioFaceData) {
            errDiv.textContent = 'Captura tu nuevo rostro primero.';
            errDiv.classList.remove('hidden');
            return;
        }
        const rostroBlob = await fetch(cambioBioFaceData).then(r => r.blob());
        formData.append('nuevo_rostro', rostroBlob, 'rostro.png');

    } else if (cambioBioTipo === 'voz') {
        if (!cambioBioVoiceData) {
            errDiv.textContent = 'Graba tu nueva muestra de voz primero.';
            errDiv.classList.remove('hidden');
            return;
        }
        const vozBlob = await fetch(cambioBioVoiceData).then(r => r.blob());
        formData.append('nueva_voz', vozBlob, 'voz.wav');
    }

    try {
        showToast('Actualizando credencial...', 'info');
        const res = await fetch(`${API_URL}/biometria/cambiar`, {
            method: 'PUT',
            headers: { 'Authorization': `Bearer ${state.token}` },
            body: formData,
        });
        const data = await res.json();

        if (!res.ok) {
            errDiv.textContent = data.detail || 'Error al actualizar la credencial.';
            errDiv.classList.remove('hidden');
            return;
        }

        // Éxito
        _detenerRecursosCambio();
        document.getElementById('cambio-paso-3-msg').textContent =
            `Tu ${NOMBRES_CRED[cambioBioTipo]} ha sido actualizada correctamente.`;
        _mostrarPasoCambio(3);
        showToast('Credencial actualizada', 'success');
        checkBiometricStatus();   // Refrescar tarjeta de estado

    } catch (e) {
        errDiv.textContent = 'Error de conexión. Inténtalo de nuevo.';
        errDiv.classList.remove('hidden');
    }
}
