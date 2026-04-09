/* ══════════ Registro de Eventos Ganaderos ══════════ */

// Estado del proceso de registro de evento
const eventState = {
    signatureData: null,
    faceData: null,
    voiceData: null,
    currentStep: 0,
};

// Campos dinámicos por tipo de evento
const EVENT_FIELDS = {
    nacimiento: [
        { id: 'peso_nacimiento', label: 'Peso al nacer (kg)', type: 'number' },
        { id: 'observaciones', label: 'Observaciones', type: 'textarea' },
    ],
    vacunacion: [
        { id: 'vacuna', label: 'Nombre de la vacuna', type: 'text' },
        { id: 'dosis', label: 'Dosis', type: 'text' },
        { id: 'lote', label: 'Lote', type: 'text' },
    ],
    desparacitacion: [
        { id: 'producto', label: 'Producto', type: 'text' },
        { id: 'dosis', label: 'Dosis', type: 'text' },
    ],
    traslado: [
        { id: 'origen', label: 'Origen', type: 'text' },
        { id: 'destino', label: 'Destino', type: 'text' },
        { id: 'motivo', label: 'Motivo', type: 'text' },
    ],
    cambio_propietario: [
        { id: 'nuevo_propietario', label: 'Nuevo propietario', type: 'text' },
        { id: 'motivo', label: 'Motivo', type: 'text' },
    ],
    certificacion_sanitaria: [
        { id: 'tipo_certificado', label: 'Tipo de certificado', type: 'text' },
        { id: 'resultado', label: 'Resultado', type: 'text' },
    ],
    muerte: [
        { id: 'causa', label: 'Causa de muerte', type: 'text' },
        { id: 'observaciones', label: 'Observaciones', type: 'textarea' },
    ],
    venta: [
        { id: 'comprador', label: 'Comprador', type: 'text' },
        { id: 'precio', label: 'Precio', type: 'number' },
        { id: 'observaciones', label: 'Observaciones', type: 'textarea' },
    ],
    auditoria: [
        { id: 'tipo_auditoria', label: 'Tipo de auditoría', type: 'text' },
        { id: 'observaciones', label: 'Observaciones', type: 'textarea' },
    ],
};

async function loadAnimalsForSelect() {
    try {
        const res = await apiFetch('/animales');
        if (!res.ok) return;
        const animals = await res.json();
        const select = document.getElementById('event-animal');
        select.innerHTML = '<option value="">Seleccionar animal...</option>';
        animals.forEach(a => {
            select.innerHTML += `<option value="${a.id_animales}">${a.codigo_unico} - ${a.nombre || a.especie}</option>`;
        });
    } catch (e) { /* silent */ }
}

function updateEventFields() {
    const tipo = document.getElementById('event-tipo').value;
    const container = document.getElementById('event-dynamic-fields');
    const fields = EVENT_FIELDS[tipo] || [];

    container.innerHTML = fields.map(f => `
        <div class="form-group">
            <label>${f.label}</label>
            ${f.type === 'textarea'
                ? `<textarea id="event-field-${f.id}" rows="2"></textarea>`
                : `<input type="${f.type}" id="event-field-${f.id}">`
            }
        </div>
    `).join('');
}

// ── Validación biométrica ──

function startBiometricValidation() {
    const animalId = document.getElementById('event-animal').value;
    const tipo = document.getElementById('event-tipo').value;
    if (!animalId || !tipo) {
        showToast('Seleccione un animal y tipo de evento', 'warning');
        return;
    }

    eventState.currentStep = 1;
    eventState.signatureData = null;
    eventState.faceData = null;
    eventState.voiceData = null;

    document.getElementById('event-step-0').classList.add('hidden');
    document.getElementById('event-biometric-steps').classList.remove('hidden');
    document.getElementById('event-step-1').classList.remove('hidden');
    document.getElementById('event-step-2').classList.add('hidden');
    document.getElementById('event-step-3').classList.add('hidden');
    document.getElementById('event-step-submit').classList.add('hidden');
    document.getElementById('event-result').classList.add('hidden');

    // Reset steps
    document.querySelectorAll('.step').forEach(s => {
        s.classList.remove('active', 'completed', 'failed');
    });
    document.getElementById('step-firma-indicator').classList.add('active');

    initSignatureCanvas('signature-canvas');
}

// ── Paso 1: Firma manuscrita ──

let signatureCtx = null;
let isDrawing = false;

function initSignatureCanvas(canvasId) {
    const canvas = document.getElementById(canvasId);
    signatureCtx = canvas.getContext('2d');
    signatureCtx.fillStyle = 'white';
    signatureCtx.fillRect(0, 0, canvas.width, canvas.height);
    signatureCtx.strokeStyle = '#000';
    signatureCtx.lineWidth = 2;
    signatureCtx.lineCap = 'round';

    // Mouse events
    canvas.addEventListener('mousedown', startDraw);
    canvas.addEventListener('mousemove', draw);
    canvas.addEventListener('mouseup', stopDraw);
    canvas.addEventListener('mouseout', stopDraw);

    // Touch events
    canvas.addEventListener('touchstart', (e) => { e.preventDefault(); startDraw(getTouchEvent(e, canvas)); });
    canvas.addEventListener('touchmove', (e) => { e.preventDefault(); draw(getTouchEvent(e, canvas)); });
    canvas.addEventListener('touchend', (e) => { e.preventDefault(); stopDraw(); });
}

function getTouchEvent(e, canvas) {
    const rect = canvas.getBoundingClientRect();
    const touch = e.touches[0];
    return {
        offsetX: touch.clientX - rect.left,
        offsetY: touch.clientY - rect.top,
    };
}

function startDraw(e) {
    isDrawing = true;
    signatureCtx.beginPath();
    signatureCtx.moveTo(e.offsetX, e.offsetY);
}

function draw(e) {
    if (!isDrawing) return;
    signatureCtx.lineTo(e.offsetX, e.offsetY);
    signatureCtx.stroke();
}

function stopDraw() { isDrawing = false; }

function clearSignature() {
    const canvas = document.getElementById('signature-canvas');
    signatureCtx.fillStyle = 'white';
    signatureCtx.fillRect(0, 0, canvas.width, canvas.height);
}

function confirmSignature() {
    const canvas = document.getElementById('signature-canvas');
    canvas.toBlob((blob) => {
        const reader = new FileReader();
        reader.onload = () => {
            eventState.signatureData = reader.result.split(',')[1]; // base64
            showToast('Firma capturada', 'success');

            // Avanzar al paso 2
            document.getElementById('step-firma-indicator').classList.remove('active');
            document.getElementById('step-firma-indicator').classList.add('completed');
            document.getElementById('step-rostro-indicator').classList.add('active');
            document.getElementById('event-step-1').classList.add('hidden');
            document.getElementById('event-step-2').classList.remove('hidden');
            startCamera();
        };
        reader.readAsDataURL(blob);
    }, 'image/png');
}

// ── Paso 2: Reconocimiento facial ──

let faceStream = null;

async function startCamera() {
    try {
        faceStream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'user' } });
        document.getElementById('face-video').srcObject = faceStream;
    } catch (e) {
        showToast('No se pudo acceder a la cámara', 'error');
    }
}

function captureFace() {
    const video = document.getElementById('face-video');
    const canvas = document.getElementById('face-canvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext('2d').drawImage(video, 0, 0);

    const dataUrl = canvas.toDataURL('image/png');
    document.getElementById('face-preview-img').src = dataUrl;
    document.getElementById('face-preview').classList.remove('hidden');
    document.getElementById('btn-capture-face').classList.add('hidden');
    document.getElementById('btn-retry-face').classList.remove('hidden');
    document.getElementById('btn-confirm-face').classList.remove('hidden');
}

function retryFace() {
    document.getElementById('face-preview').classList.add('hidden');
    document.getElementById('btn-capture-face').classList.remove('hidden');
    document.getElementById('btn-retry-face').classList.add('hidden');
    document.getElementById('btn-confirm-face').classList.add('hidden');
}

function confirmFace() {
    const canvas = document.getElementById('face-canvas');
    eventState.faceData = canvas.toDataURL('image/png').split(',')[1];
    showToast('Rostro capturado', 'success');

    // Detener cámara
    if (faceStream) {
        faceStream.getTracks().forEach(t => t.stop());
    }

    // Avanzar al paso 3
    document.getElementById('step-rostro-indicator').classList.remove('active');
    document.getElementById('step-rostro-indicator').classList.add('completed');
    document.getElementById('step-voz-indicator').classList.add('active');
    document.getElementById('event-step-2').classList.add('hidden');
    document.getElementById('event-step-3').classList.remove('hidden');
}

// ── Paso 3: Verificación de voz ──

let mediaRecorder = null;
let audioChunks = [];
let isRecording = false;

async function toggleVoiceRecording() {
    if (isRecording) {
        stopVoiceRecording();
    } else {
        startVoiceRecording();
    }
}

async function startVoiceRecording() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
        audioChunks = [];

        mediaRecorder.ondataavailable = (e) => {
            if (e.data.size > 0) audioChunks.push(e.data);
        };

        mediaRecorder.onstop = () => {
            const blob = new Blob(audioChunks, { type: 'audio/webm' });
            const url = URL.createObjectURL(blob);
            const playback = document.getElementById('voice-playback');
            playback.src = url;
            playback.classList.remove('hidden');

            // Convertir a base64
            const reader = new FileReader();
            reader.onload = () => {
                eventState.voiceData = reader.result.split(',')[1];
            };
            reader.readAsDataURL(blob);

            document.getElementById('btn-confirm-voice').classList.remove('hidden');
            stream.getTracks().forEach(t => t.stop());
        };

        mediaRecorder.start();
        isRecording = true;
        document.getElementById('voice-indicator').classList.add('recording');
        document.getElementById('voice-status').textContent = 'Grabando...';
        document.getElementById('btn-record-voice').textContent = 'Detener';
    } catch (e) {
        showToast('No se pudo acceder al micrófono', 'error');
    }
}

function stopVoiceRecording() {
    if (mediaRecorder && mediaRecorder.state === 'recording') {
        mediaRecorder.stop();
    }
    isRecording = false;
    document.getElementById('voice-indicator').classList.remove('recording');
    document.getElementById('voice-status').textContent = 'Grabación completada';
    document.getElementById('btn-record-voice').textContent = 'Grabar de nuevo';
}

function confirmVoice() {
    showToast('Voz capturada', 'success');

    // Avanzar al paso de envío
    document.getElementById('step-voz-indicator').classList.remove('active');
    document.getElementById('step-voz-indicator').classList.add('completed');
    document.getElementById('event-step-3').classList.add('hidden');
    document.getElementById('event-step-submit').classList.remove('hidden');

    // Actualizar resumen
    updateValidationSummary();
}

function updateValidationSummary() {
    const items = [
        { id: 'val-firma', ok: !!eventState.signatureData },
        { id: 'val-rostro', ok: !!eventState.faceData },
        { id: 'val-voz', ok: !!eventState.voiceData },
    ];
    items.forEach(item => {
        const el = document.getElementById(item.id);
        el.classList.add(item.ok ? 'success' : 'failed');
        el.querySelector('.val-icon').textContent = item.ok ? '\u2705' : '\u274C';
    });
}

// ── Enviar evento ──

async function submitEvent() {
    if (!eventState.signatureData || !eventState.faceData || !eventState.voiceData) {
        showToast('Debe completar las 3 validaciones biométricas', 'error');
        return;
    }

    // Recolectar datos del evento
    const tipo = document.getElementById('event-tipo').value;
    const fields = EVENT_FIELDS[tipo] || [];
    const datos_evento = {};
    fields.forEach(f => {
        const el = document.getElementById(`event-field-${f.id}`);
        if (el && el.value) datos_evento[f.id] = el.value;
    });

    const body = {
        id_animales: document.getElementById('event-animal').value,
        tipo_evento: tipo,
        datos_evento: datos_evento,
        ubicacion: document.getElementById('event-ubicacion').value || null,
        firma_imagen: eventState.signatureData,
        rostro_imagen: eventState.faceData,
        audio_voz: eventState.voiceData,
    };

    try {
        showToast('Procesando validación biométrica y registro...', 'info');
        const res = await apiFetch('/eventos/', {
            method: 'POST',
            body: JSON.stringify(body),
        });
        const data = await res.json();
        const resultDiv = document.getElementById('event-result');
        resultDiv.classList.remove('hidden');

        if (res.ok) {
            resultDiv.innerHTML = `
                <div class="event-result-success">
                    <h4>\u2705 Evento registrado exitosamente</h4>
                    <p>${data.mensaje}</p>
                    <div class="mt-1">
                        <strong>Hash del evento:</strong>
                        <div class="hash-display">${data.evento.hash_evento}</div>
                    </div>
                    <div class="mt-1">
                        <strong>Hash anterior:</strong>
                        <div class="hash-display">${data.evento.hash_evento_pasado || 'GENESIS (primer evento)'}</div>
                    </div>
                    <div class="mt-1">
                        <strong>Firma digital:</strong>
                        <div class="hash-display">${data.evento.firma_digital}</div>
                    </div>
                    <div class="validation-items mt-1">
                        <div class="validation-item success">
                            <span class="val-icon">\u2705</span>
                            Firma: Score ${(data.validacion_biometrica.score_firma * 100).toFixed(1)}%
                        </div>
                        <div class="validation-item success">
                            <span class="val-icon">\u2705</span>
                            Rostro: Score ${(data.validacion_biometrica.score_rostro * 100).toFixed(1)}%
                        </div>
                        <div class="validation-item success">
                            <span class="val-icon">\u2705</span>
                            Voz: Score ${(data.validacion_biometrica.score_voz * 100).toFixed(1)}%
                        </div>
                    </div>
                </div>
            `;
            showToast('Evento registrado con triple validación', 'success');
            loadRecentEvents();
        } else {
            const detail = typeof data.detail === 'object' ? data.detail : { mensaje: data.detail };
            resultDiv.innerHTML = `
                <div class="event-result-error">
                    <h4>\u274C Registro denegado</h4>
                    <p>${detail.mensaje || data.detail}</p>
                    ${detail.llave_fallida ? `<p><strong>Llave fallida:</strong> ${detail.llave_fallida}</p>` : ''}
                    ${detail.score !== undefined ? `<p><strong>Score:</strong> ${(detail.score * 100).toFixed(1)}%</p>` : ''}
                </div>
            `;
            showToast('Validación biométrica rechazada', 'error');
        }

        // Reset para siguiente evento
        document.getElementById('event-step-submit').classList.add('hidden');
    } catch (err) {
        showToast('Error de conexión', 'error');
    }
}

// ── Eventos recientes ──

async function loadRecentEvents() {
    try {
        const res = await apiFetch('/eventos');
        if (!res.ok) return;
        const events = await res.json();
        renderEventsList(events);
    } catch (e) { /* silent */ }
}

function renderEventsList(events) {
    const container = document.getElementById('events-list');
    if (events.length === 0) {
        container.innerHTML = '<p class="text-muted">No hay eventos registrados.</p>';
        return;
    }

    container.innerHTML = `
        <table>
            <thead>
                <tr>
                    <th>Fecha</th>
                    <th>Tipo</th>
                    <th>Animal</th>
                    <th>Actor</th>
                    <th>Hash</th>
                </tr>
            </thead>
            <tbody>
                ${events.slice(0, 20).map(e => `
                    <tr>
                        <td>${new Date(e.registrado_en).toLocaleString('es')}</td>
                        <td><span class="badge">${e.tipo_evento}</span></td>
                        <td>${e.id_animales.substring(0, 8)}...</td>
                        <td>${e.actor_nombre || 'N/A'}</td>
                        <td class="hash-display">${e.hash_evento.substring(0, 16)}...</td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;
}

// ── Reset flujo de evento ──
function resetEventFlow() {
    document.getElementById('event-step-0').classList.remove('hidden');
    document.getElementById('event-biometric-steps').classList.add('hidden');
    document.getElementById('event-result').classList.add('hidden');
    eventState.signatureData = null;
    eventState.faceData = null;
    eventState.voiceData = null;
}
