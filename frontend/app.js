// Detección automática de entorno Docker vs Local
const isLocalhost = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
const API_URL = isLocalhost ? 'http://localhost:5000' : `http://${window.location.hostname}:5000`;
const RASA_URL = isLocalhost ? 'http://localhost:5005/webhooks/rest/webhook' : `http://${window.location.hostname}:5005/webhooks/rest/webhook`;

console.log(`🌐 Entorno: ${isLocalhost ? 'LOCAL' : 'DOCKER/PRODUCCIÓN'}`);
console.log(`📡 API_URL: ${API_URL}`);
console.log(`🤖 RASA_URL: ${RASA_URL}`);

let currentUser = null;
let businessData = null;
let recognition = null;
let isListening = false;
let isVoiceMode = false; 

// --- FUNCIONES DE UI ---
function openModal(id) { document.getElementById(id).classList.remove('hidden'); }
function closeModal(id) { document.getElementById(id).classList.add('hidden'); }

// --- AUTH (Específico para el chat) ---
async function handleLogin(e) {
    e.preventDefault();
    const email = document.getElementById('login-email').value;
    const password = document.getElementById('login-password').value;
    try {
        const res = await fetch(`${API_URL}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });
        const data = await res.json();
        if (res.ok) {
            saveUserSession(data);
            closeModal('modal-login');
            Swal.fire({ title: '¡Hola de nuevo!', text: `Conectado como ${data.nombre}`, icon: 'success', confirmButtonColor: '#4f46e5' });
        } else { Swal.fire('Error', data.error, 'error'); }
    } catch (err) { Swal.fire('Error', 'Error de conexión', 'error'); }
}

async function handleRegister(e) {
    e.preventDefault();
    const formData = new FormData();
    formData.append('nombre', document.getElementById('reg-name').value);
    formData.append('email', document.getElementById('reg-email').value);
    formData.append('password', document.getElementById('reg-password').value);
    formData.append('rol', document.getElementById('reg-rol').value);
    const fileInput = document.getElementById('reg-photo-file');
    if(fileInput.files[0]) formData.append('foto_perfil', fileInput.files[0]);

    try {
        const res = await fetch(`${API_URL}/auth/register`, { method: 'POST', body: formData });
        const data = await res.json();
        if (res.ok) {
            saveUserSession(data);
            closeModal('modal-register');
            Swal.fire({ title: '¡Bienvenido!', text: `Cuenta creada para ${data.nombre}`, icon: 'success', confirmButtonColor: '#4f46e5' });
        } else { Swal.fire('Error', data.error, 'error'); }
    } catch (err) { Swal.fire('Error', 'Error al registrarse', 'error'); }
}

function saveUserSession(userData) {
    localStorage.setItem('sector_mind_user', JSON.stringify(userData));
    currentUser = userData;
    updateUI(); 
}

// --- INIT ---
window.onload = async () => {
    console.log('onload start');
    lucide.createIcons();
    
    // 1. Cargar Usuario
    const userStr = localStorage.getItem('sector_mind_user');
    if (userStr) currentUser = JSON.parse(userStr);
    
    updateUI(); 

    // 2. Cargar Negocio
    businessData = null;
    const urlParams = new URLSearchParams(window.location.search);
    const negocioId = urlParams.get('id');
    if (negocioId) {
        // Fetch the business data from API
        try {
            const res = await fetch(`${API_URL}/negocios/${negocioId}`);
            if (res.ok) {
                businessData = await res.json();
                localStorage.setItem('selected_business', JSON.stringify(businessData));
            } else {
                console.error('Failed to fetch business');
                window.location.href = '/';
                return;
            }
        } catch (e) {
            console.error(e);
            window.location.href = '/';
            return;
        }
    } else {
        const storedBiz = localStorage.getItem('selected_business');
        if (!storedBiz) { window.location.href = '/'; return; }
        try {
            businessData = JSON.parse(storedBiz);
        } catch (e) {
            console.error('Error parsing stored business data:', e);
            window.location.href = '/';
            return;
        }
        if (!businessData || typeof businessData !== 'object') {
            console.error('Invalid business data:', businessData);
            window.location.href = '/';
            return;
        }
    }
    
    renderBusinessInfo(businessData);
    
    // 3. ESPERA DE RASA
    setupVoiceRecognition();
    await waitForRasaToBeReady(businessData.nombre);
};

// --- LÓGICA DE ESPERA DE RASA ---
async function waitForRasaToBeReady(nombreNegocio) {
    const loader = document.getElementById('ai-loader');
    const statusText = document.getElementById('loader-status');
    const RASA_BASE = 'http://localhost:5005'; 

    if(loader) loader.classList.remove('hidden');

    let isReady = false;
    let attempts = 0;

    while (!isReady) {
        try {
            const response = await fetch(`${RASA_BASE}/version`);
            if (response.ok) {
                isReady = true;
                statusText.innerText = "¡Conectado! Iniciando conversación...";
            }
        } catch (error) {
            attempts++;
            statusText.innerText = "Servidor cargando...";
            console.log("Esperando a Rasa Server en localhost:5005...");
        }

        if (!isReady) await new Promise(r => setTimeout(r, 2000));
    }

    await sendToRasa(`/greet{"negocio": "${nombreNegocio}"}`, true);
    
    if(loader) loader.classList.add('hidden');
    addMsg('bot', `¡Hola! Soy el agente de IA de ${nombreNegocio}, ¿en qué puedo ayudarte?`);
}

function updateUI() {
    if (currentUser) {
        document.getElementById('user-menu').classList.remove('hidden');
        document.getElementById('user-menu').classList.add('flex');
        document.getElementById('auth-buttons').classList.add('hidden');
        document.getElementById('user-name-display').innerText = currentUser.nombre;
        const avatar = currentUser.foto_perfil_base64 || `https://ui-avatars.com/api/?name=${currentUser.nombre}&background=random`;
        document.getElementById('user-avatar-display').src = avatar;
    } else {
        document.getElementById('user-menu').classList.add('hidden');
        document.getElementById('auth-buttons').classList.remove('hidden');
        document.getElementById('auth-buttons').classList.add('flex');
    }

    const lockScreen = document.getElementById('lock-screen');
    const aiContainer = document.getElementById('ai-container');
    
    if (currentUser) {
        lockScreen.classList.add('hidden'); 
        aiContainer.classList.remove('blur-sm', 'pointer-events-none'); 
    } else {
        lockScreen.classList.remove('hidden'); 
        aiContainer.classList.add('blur-sm', 'pointer-events-none'); 
    }
}

function renderBusinessInfo(biz) {
    console.log('Rendering business:', biz);
    if (!biz) {
        console.error('No business data');
        return;
    }
    if (!biz.nombre) biz.nombre = 'Negocio sin nombre';
    document.getElementById('biz-name').innerText = biz.nombre;
    document.getElementById('biz-desc').innerText = biz.descripcion || "Sin descripción.";
    document.getElementById('biz-address').innerHTML = `<i data-lucide="map-pin" class="w-4 h-4 mr-2"></i> ${biz.direccion || 'Dirección no disponible'}`;
    document.getElementById('biz-type').innerText = biz.tipo_negocio;
    document.getElementById('ai-agent-title').innerText = `Agente IA de ${biz.nombre}`;
    const imgUrl = biz.foto_base64 || 'https://images.unsplash.com/photo-1560066984-138dadb4c035?auto=format&fit=crop&w=1200&q=80';
    document.getElementById('biz-img').src = imgUrl;

    if (biz.servicios) renderServices(biz.servicios);
    else fetchServices(biz.id);
}

async function fetchServices(negocioId) {
    try {
        const res = await fetch(`${API_URL}/negocios/${negocioId}/servicios`);
        const servicios = await res.json();
        renderServices(servicios);
    } catch (e) { console.error(e); }
}

function renderServices(servicios) {
    const list = document.getElementById('services-list');
    list.innerHTML = '';
    if (!servicios || servicios.length === 0) { list.innerHTML = '<p class=\"text-slate-400 italic\">No hay servicios.</p>'; return; }
    servicios.forEach(s => {
        const div = document.createElement('div');
        div.className = "flex justify-between items-center p-4 border-2 border-slate-100 rounded-2xl hover:border-indigo-300 hover:bg-indigo-50 hover:shadow-md transition cursor-pointer group";
        div.onclick = () => openBookingModal(s);
        div.innerHTML = `
            <div>
                <h4 class="font-bold text-slate-800 group-hover:text-indigo-700 transition">${s.nombre}</h4>
                <p class="text-xs text-slate-500 flex items-center gap-1">
                    <i data-lucide="clock" class="w-3 h-3"></i> ${s.duracion_minutos} min
                </p>
            </div>
            <div class="text-right">
                <span class="block font-bold text-indigo-600 bg-indigo-50 px-3 py-1 rounded-lg group-hover:bg-indigo-100 transition">${s.precio}€</span>
            </div>
        `;
        list.appendChild(div);
    });
    lucide.createIcons();
}

// --- CHAT & VOICE ---
function switchMode(mode) {
    const chatUI = document.getElementById('chat-interface');
    const voiceUI = document.getElementById('voice-interface');
    const btnChat = document.getElementById('tab-chat');
    const btnVoice = document.getElementById('tab-voice');

    if (mode === 'chat') {
        isVoiceMode = false;
        chatUI.classList.remove('hidden');
        voiceUI.classList.add('hidden'); voiceUI.classList.remove('flex');
        btnChat.classList.add('bg-indigo-600', 'text-white', 'shadow'); btnChat.classList.remove('text-slate-400');
        btnVoice.classList.remove('bg-indigo-600', 'text-white', 'shadow'); btnVoice.classList.add('text-slate-400');
        if(isListening && recognition) recognition.stop();
    } else {
        isVoiceMode = true;
        chatUI.classList.add('hidden');
        voiceUI.classList.remove('hidden'); voiceUI.classList.add('flex');
        btnVoice.classList.add('bg-indigo-600', 'text-white', 'shadow'); btnVoice.classList.remove('text-slate-400');
        btnChat.classList.remove('bg-indigo-600', 'text-white', 'shadow'); btnChat.classList.add('text-slate-400');
    }
}

async function handleChatSubmit(e) {
    e.preventDefault();
    const input = document.getElementById('chat-input');
    const msg = input.value.trim();
    if (!msg) return;
    addMsg('user', msg);
    input.value = '';
    const typingId = showTyping();
    await sendToRasa(msg, false, typingId);
}

async function sendToRasa(msg, hidden = false, typingElementId = null) {
    try {
        // Construir payload con metadatos para Rasa
        const payload = { 
            sender: currentUser ? currentUser.id.toString() : "anonimo", 
            message: msg,
            metadata: {
                cliente_id: currentUser ? currentUser.id : null,
                negocio_id: businessData ? businessData.id : null,
                negocio_nombre: businessData ? businessData.nombre : null
            }
        };
        
        const res = await fetch(RASA_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (typingElementId && document.getElementById(typingElementId)) document.getElementById(typingElementId).remove();
        if (!hidden) {
            if (data.length === 0) handleBotResponse('Ups, no he entendido eso. ¿Puedes repetirlo?');
            else data.forEach(rta => handleBotResponse(rta.text));
        } else {
            // Si hidden, solo procesar mensajes de slots
            if (Array.isArray(data)) {
                data.forEach(rta => {
                    if (typeof rta.text === 'string' && rta.text.startsWith('[SLOTS]')) {
                        handleBotResponse(rta.text);
                    }
                });
            }
        }
    } catch (err) {
        if (typingElementId) document.getElementById(typingElementId).remove();
        if (!hidden) handleBotResponse('Error de conexión con la IA.');
    }
}

function handleBotResponse(text) {
    // Si el mensaje contiene los slots, mostrar solo en consola
    if (typeof text === 'string' && text.startsWith('[SLOTS]')) {
        try {
            const slotsStr = text.replace('[SLOTS]', '').trim();
            const slots = JSON.parse(slotsStr.replace(/'/g, '"'));
            console.log('🎯 SLOTS RASA:', slots);
        } catch (e) {
            console.warn('No se pudo parsear los slots:', text);
        }
        return;
    }
    addMsg('bot', text);
    if (isVoiceMode) {
        const voiceResBox = document.getElementById('voice-response-box');
        document.getElementById('voice-response-text').innerText = text;
        voiceResBox.classList.remove('hidden');
        speakText(text);
    }
}

function addMsg(sender, text) {
    const container = document.getElementById('chat-messages');
    const div = document.createElement('div');
    div.className = sender === 'user' ? "flex gap-3 flex-row-reverse fade-in" : "flex gap-3 fade-in";
    
    // Convertir markdown simple a HTML
    const formattedText = formatMarkdown(text);
    
    div.innerHTML = sender === 'user' 
        ? `<div class=\"w-8 h-8 rounded-full bg-slate-900 text-white flex items-center justify-center text-xs font-bold flex-shrink-0\">YO</div><div class=\"bg-indigo-600 text-white p-3 rounded-2xl rounded-tr-none shadow-md text-sm max-w-[80%]\">${formattedText}</div>`
        : `<div class=\"w-8 h-8 rounded-full bg-indigo-100 text-indigo-600 flex items-center justify-center text-xs font-bold flex-shrink-0\">IA</div><div class=\"bg-white text-slate-600 p-3 rounded-2xl rounded-tl-none shadow-sm border border-slate-100 text-sm max-w-[80%]\">${formattedText}</div>`;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}

function formatMarkdown(text) {
    if (!text) return '';
    
    // Convertir **texto** a <strong>
    text = text.replace(/\*\*(.*?)\*\*/g, '<strong class="font-bold">$1</strong>');
    
    // Convertir *texto* a <em>
    text = text.replace(/\*(.*?)\*/g, '<em class="italic">$1</em>');
    
    // Convertir saltos de línea \n\n a <br><br>
    text = text.replace(/\n\n/g, '<br><br>');
    
    // Convertir saltos de línea simples \n a <br>
    text = text.replace(/\n/g, '<br>');
    
    // Convertir emojis de check ✅ y cruz ❌ (mantenerlos)
    // Ya están en el texto, no necesitan conversión
    
    // Convertir 📅 y otros emojis (mantenerlos también)
    
    return text;
}

function showTyping() {
    const container = document.getElementById('chat-messages');
    const id = 'typing-' + Date.now();
    const div = document.createElement('div');
    div.id = id;
    div.className = "flex gap-3 fade-in";
    div.innerHTML = `<div class=\"w-8 h-8 rounded-full bg-indigo-100 text-indigo-600 flex items-center justify-center text-xs font-bold flex-shrink-0\">IA</div><div class=\"bg-white p-4 rounded-2xl rounded-tl-none shadow-sm border border-slate-100 flex gap-1 items-center\"><div class=\"w-2 h-2 bg-slate-400 rounded-full typing-dot\"></div><div class=\"w-2 h-2 bg-slate-400 rounded-full typing-dot\"></div><div class=\"w-2 h-2 bg-slate-400 rounded-full typing-dot\"></div></div>`;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
    return id;
}

function setupVoiceRecognition() {
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
        document.getElementById('voice-status').innerText = "Tu navegador no soporta voz.";
        return;
    }
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    recognition = new SpeechRecognition();
    recognition.lang = 'es-ES';
    recognition.continuous = false; 
    recognition.onstart = () => {
        isListening = true;
        document.getElementById('voice-status').innerText = "Escuchando...";
        document.getElementById('mic-bg').classList.add('mic-pulse', 'opacity-100');
    };
    recognition.onend = () => {
        isListening = false;
        document.getElementById('voice-status').innerText = "Pulsa para hablar";
        document.getElementById('mic-bg').classList.remove('mic-pulse', 'opacity-100');
    };
    recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        document.getElementById('voice-transcript').innerText = `"${transcript}"`;
        sendToRasa(transcript);
    };
}

function toggleVoice() {
    if (!recognition) return;
    if (isListening) recognition.stop();
    else { window.speechSynthesis.cancel(); recognition.start(); }
}

function speakText(text) {
    if (!('speechSynthesis' in window)) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = 'es-ES';
    window.speechSynthesis.speak(utterance);
}

// ============================================
// RESERVA MANUAL DE CITAS (MODAL)
// ============================================

let selectedService = null;
let selectedDate = null;
let selectedTime = null;
let availableDates = {};

async function openBookingModal(servicio) {
    if (!currentUser) {
        Swal.fire({
            icon: 'warning',
            title: 'Inicia sesión',
            text: 'Debes iniciar sesión para reservar una cita',
            confirmButtonColor: '#4f46e5'
        });
        return;
    }

    selectedService = servicio;
    selectedDate = null;
    selectedTime = null;
    availableDates = {};

    const modal = document.getElementById('modal-booking');
    const serviceInfo = document.getElementById('booking-service-info');
    
    serviceInfo.querySelector('span').textContent = `${servicio.nombre} - ${servicio.precio}€ (${servicio.duracion_minutos} min)`;
    
    // Ocultar sección de horarios
    document.getElementById('booking-time-section').classList.add('hidden');
    document.getElementById('booking-time-slots').innerHTML = '';
    
    // Deshabilitar botón de confirmar
    const confirmBtn = document.getElementById('booking-confirm-btn');
    confirmBtn.disabled = true;
    confirmBtn.className = "w-full bg-slate-300 text-slate-500 py-4 rounded-xl font-bold cursor-not-allowed transition shadow-lg flex items-center justify-center gap-2";
    confirmBtn.innerHTML = '<i data-lucide="check-circle" class="w-5 h-5"></i> Selecciona fecha y hora';
    
    modal.classList.remove('hidden');
    
    // Cargar calendario inteligente
    await loadSmartCalendar();
    
    lucide.createIcons();
}

async function loadSmartCalendar() {
    const calendarContainer = document.getElementById('booking-calendar');
    calendarContainer.innerHTML = '<div class="col-span-7 text-center py-8"><div class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div><p class="text-slate-500 mt-3">Cargando días disponibles...</p></div>';
    
    const today = new Date();
    const daysToShow = 21; // Tres semanas
    
    // Obtener disponibilidad para los próximos días
    const disponibilidadPromises = [];
    for (let i = 0; i < daysToShow; i++) {
        const date = new Date(today);
        date.setDate(today.getDate() + i);
        const dateStr = date.toISOString().split('T')[0];
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 10000); // 10s timeout
        disponibilidadPromises.push(
            fetch(`${API_URL}/disponibilidad`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    negocio_id: businessData.id,
                    servicio_id: selectedService.id,
                    fecha: dateStr
                }),
                signal: controller.signal
            })
                .then(res => {
                    clearTimeout(timeoutId);
                    return res.ok ? res.json() : null;
                })
                .then(data => {
                    const horarios = data && data.disponibles ? data.disponibles : [];
                    return { date: dateStr, hasSlots: horarios.length > 0, horarios };
                })
                .catch(() => ({ date: dateStr, hasSlots: false, horarios: [] }))
        );
    }
    
    const results = await Promise.all(disponibilidadPromises);
    
    // Guardar datos de disponibilidad
    results.forEach(result => {
        if (result.hasSlots) {
            availableDates[result.date] = result.horarios;
        }
    });
    
    // Limpiar y crear estructura del calendario
    calendarContainer.innerHTML = '';
    
    // Headers de días
    const dayHeaders = ['Dom', 'Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb'];
    dayHeaders.forEach(day => {
        const header = document.createElement('div');
        header.className = 'text-center text-xs font-bold text-slate-400 py-2';
        header.textContent = day;
        calendarContainer.appendChild(header);
    });
    
    // Añadir espacios vacíos para alinear el primer día
    const firstDate = new Date(today);
    const firstDayOfWeek = firstDate.getDay();
    for (let i = 0; i < firstDayOfWeek; i++) {
        const emptyCell = document.createElement('div');
        calendarContainer.appendChild(emptyCell);
    }
    
    // Renderizar días
    results.forEach(result => {
        const date = new Date(result.date);
        const dayButton = document.createElement('button');
        dayButton.type = 'button';
        dayButton.className = result.hasSlots 
            ? 'p-3 rounded-lg border-2 border-green-200 bg-green-50 hover:border-green-500 hover:bg-green-100 transition text-sm font-medium text-green-700 hover:text-green-900'
            : 'p-3 rounded-lg border border-slate-100 bg-slate-50 text-slate-300 cursor-not-allowed';
        
        const dayNum = date.getDate();
        const monthShort = date.toLocaleDateString('es-ES', { month: 'short' });
        
        dayButton.innerHTML = `<div class="text-lg font-bold">${dayNum}</div><div class="text-xs">${monthShort}</div>`;
        
        if (result.hasSlots) {
            dayButton.onclick = () => selectDate(result.date, dayButton);
        } else {
            dayButton.disabled = true;
        }
        
        calendarContainer.appendChild(dayButton);
    });
}

function closeBookingModal() {
    document.getElementById('modal-booking').classList.add('hidden');
    selectedService = null;
    selectedDate = null;
    selectedTime = null;
}

function selectDate(dateStr, buttonElement) {
    // Remover selección previa
    document.querySelectorAll('#booking-calendar button').forEach(btn => {
        if (btn.className.includes('green')) {
            btn.className = 'p-3 rounded-lg border-2 border-green-200 bg-green-50 hover:border-green-500 hover:bg-green-100 transition text-sm font-medium text-green-700 hover:text-green-900';
        }
    });
    
    // Marcar como seleccionado
    buttonElement.className = 'p-3 rounded-lg border-2 border-indigo-600 bg-indigo-600 text-white transition text-sm font-bold shadow-md';
    
    selectedDate = dateStr;
    selectedTime = null;
    
    // Mostrar horarios disponibles
    const timeSlotsContainer = document.getElementById('booking-time-slots');
    const timeSection = document.getElementById('booking-time-section');
    
    timeSection.classList.remove('hidden');
    timeSlotsContainer.innerHTML = '';
    
    let horarios = availableDates[dateStr] || [];
    // Filtrar horarios pasados si la fecha es hoy
    const now = new Date();
    const selectedDateObj = new Date(dateStr);
    if (
        selectedDateObj.getFullYear() === now.getFullYear() &&
        selectedDateObj.getMonth() === now.getMonth() &&
        selectedDateObj.getDate() === now.getDate()
    ) {
        horarios = horarios.filter(hora => {
            const horaObj = new Date(hora);
            return horaObj > now;
        });
    }
    if (horarios.length === 0) {
        timeSlotsContainer.innerHTML = '<div class="col-span-full text-center py-4 text-slate-400">No hay horarios disponibles</div>';
        updateBookingButton();
        return;
    }
    horarios.forEach(hora => {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = "p-3 border-2 border-slate-200 rounded-lg hover:border-indigo-500 hover:bg-indigo-50 transition text-sm font-medium text-slate-700 hover:text-indigo-700";
        // Extraer solo la hora (HH:MM) del formato completo
        const horaFormateada = new Date(hora).toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' });
        button.textContent = horaFormateada;
        button.onclick = () => selectTimeSlot(hora, button);
        timeSlotsContainer.appendChild(button);
    });
    updateBookingButton();
    lucide.createIcons();
}

function selectTimeSlot(hora, buttonElement) {
    // Remover selección previa
    document.querySelectorAll('#booking-time-slots button').forEach(btn => {
        btn.className = "p-3 border-2 border-slate-200 rounded-lg hover:border-indigo-500 hover:bg-indigo-50 transition text-sm font-medium text-slate-700 hover:text-indigo-700";
    });
    
    // Marcar como seleccionado
    buttonElement.className = "p-3 border-2 border-indigo-600 bg-indigo-600 rounded-lg text-white font-bold text-sm shadow-md";
    
    selectedTime = hora;
    updateBookingButton();
}

function updateBookingButton() {
    const confirmBtn = document.getElementById('booking-confirm-btn');
    
    if (selectedDate && selectedTime) {
        confirmBtn.disabled = false;
        confirmBtn.className = "w-full bg-indigo-600 hover:bg-indigo-700 text-white py-4 rounded-xl font-bold transition shadow-lg hover:shadow-xl flex items-center justify-center gap-2";
        confirmBtn.innerHTML = '<i data-lucide="check-circle" class="w-5 h-5"></i> Confirmar Reserva';
        lucide.createIcons();
    } else {
        confirmBtn.disabled = true;
        confirmBtn.className = "w-full bg-slate-300 text-slate-500 py-4 rounded-xl font-bold cursor-not-allowed transition shadow-lg flex items-center justify-center gap-2";
        confirmBtn.innerHTML = '<i data-lucide="check-circle" class="w-5 h-5"></i> Selecciona fecha y hora';
        lucide.createIcons();
    }
}

async function confirmBooking() {
    if (!selectedService || !selectedDate || !selectedTime) {
        console.error('Faltan datos:', { selectedService, selectedDate, selectedTime });
        return;
    }
    
    // selectedTime ya viene como 'YYYY-MM-DD HH:MM:SS' desde el backend
    const fecha_hora_cita = selectedTime;
    
    console.log('Enviando reserva:', {
        cliente_id: currentUser.id,
        negocio_id: businessData.id,
        servicio_id: selectedService.id,
        servicio_nombre: selectedService.nombre,
        fecha_hora_cita: fecha_hora_cita
    });
    
    try {
        const response = await fetch(`${API_URL}/citas`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                cliente_id: currentUser.id,
                negocio_id: businessData.id,
                servicio_id: selectedService.id,
                fecha_hora_cita: fecha_hora_cita,
                estado: 'confirmada'
            })
        });
        
        if (response.ok) {
            // Guardar datos antes de cerrar el modal
            const servicioInfo = {
                nombre: selectedService.nombre,
                precio: selectedService.precio,
                duracion_minutos: selectedService.duracion_minutos
            };
            
            closeBookingModal();
            
            const dateObj = new Date(fecha_hora_cita);
            const fechaLegible = dateObj.toLocaleDateString('es-ES', { 
                weekday: 'long', 
                year: 'numeric', 
                month: 'long', 
                day: 'numeric' 
            });
            const horaLegible = dateObj.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' });
            
            Swal.fire({
                icon: 'success',
                title: '¡Cita Reservada!',
                html: `
                    <div class="text-center">
                        <p class="text-lg mb-4">Tu cita ha sido confirmada</p>
                        <div class="bg-indigo-50 p-6 rounded-xl">
                            <p class="text-sm text-indigo-600 font-bold uppercase mb-2">${servicioInfo.nombre}</p>
                            <p class="text-2xl font-bold text-indigo-900 mb-1">${fechaLegible}</p>
                            <p class="text-xl text-indigo-700">a las ${horaLegible}</p>
                            <div class="mt-4 pt-4 border-t border-indigo-200">
                                <p class="text-indigo-600"><span class="font-bold">${servicioInfo.precio}€</span> • ${servicioInfo.duracion_minutos} minutos</p>
                            </div>
                        </div>
                    </div>
                `,
                confirmButtonText: '¡Perfecto!',
                confirmButtonColor: '#4f46e5'
            });
        } else {
            const error = await response.json();
            Swal.fire({
                icon: 'error',
                title: 'Error al reservar',
                text: error.error || 'No se pudo completar la reserva',
                confirmButtonColor: '#4f46e5'
            });
        }
    } catch (error) {
        console.error('Error completo:', error);
        Swal.fire({
            icon: 'error',
            title: 'Error de conexión',
            text: `No se pudo conectar con el servidor: ${error.message}`,
            confirmButtonColor: '#4f46e5'
        });
    }
}