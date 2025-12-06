const API_URL = 'http://localhost:5000';
const RASA_URL = 'http://localhost:5005/webhooks/rest/webhook';
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
    lucide.createIcons();
    
    // 1. Cargar Usuario
    const userStr = localStorage.getItem('sector_mind_user');
    if (userStr) currentUser = JSON.parse(userStr);
    
    updateUI(); 

    // 2. Cargar Negocio
    const storedBiz = localStorage.getItem('selected_business');
    if (!storedBiz) { window.location.href = '/'; return; }
    businessData = JSON.parse(storedBiz);
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
            statusText.innerText = `Servidor cargando... Intento ${attempts} (Esperando a Rasa)`;
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
        const avatar = currentUser.foto_perfil_url || `https://ui-avatars.com/api/?name=${currentUser.nombre}&background=random`;
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
    document.getElementById('biz-name').innerText = biz.nombre;
    document.getElementById('biz-desc').innerText = biz.descripcion || "Sin descripción.";
    document.getElementById('biz-address').innerHTML = `<i data-lucide="map-pin" class="w-4 h-4 mr-2"></i> ${biz.direccion || 'Dirección no disponible'}`;
    document.getElementById('biz-type').innerText = biz.tipo_negocio;
    document.getElementById('ai-agent-title').innerText = `Agente IA de ${biz.nombre}`;
    const imgUrl = biz.foto_url || 'https://images.unsplash.com/photo-1560066984-138dadb4c035?auto=format&fit=crop&w=1200&q=80';
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
        div.className = "flex justify-between items-center p-4 border border-slate-100 rounded-2xl hover:border-indigo-100 hover:bg-indigo-50/30 transition";
        div.innerHTML = `<div><h4 class=\"font-bold text-slate-800\">${s.nombre}</h4><p class=\"text-xs text-slate-500 flex items-center gap-1\"><i data-lucide=\"clock\" class=\"w-3 h-3\"></i> ${s.duracion_minutos} min</p></div><span class=\"font-bold text-indigo-600 bg-indigo-50 px-3 py-1 rounded-lg\">${s.precio}€</span>`;
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
        }
    } catch (err) {
        if (typingElementId) document.getElementById(typingElementId).remove();
        if (!hidden) handleBotResponse('Error de conexión con la IA.');
    }
}

function handleBotResponse(text) {
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