// Open WebUI Voice Integration v2
// Features: Web Speech API + VOICEVOX fallback, auto-read, controls
// Embedded in Open WebUI via Docker mount

(function () {
    'use strict';

    console.log('[Remi Voice v2] Initializing...');

    // ============================================================
    // Configuration
    // ============================================================
    const CONFIG = {
        autoSpeak: true,
        engine: 'browser',  // 'browser' or 'voicevox'
        browser: {
            rate: 1.1,
            pitch: 1.0,
            volume: 1.0,
            lang: 'ja-JP'
        },
        voicevox: {
            apiUrl: window.location.origin.replace(/:\d+$/, ':5050'),
            speaker: 0,  // 0=Zundamon
            speed: 1.1
        },
        maxTextLength: 500
    };

    // ============================================================
    // State
    // ============================================================
    let isSpeaking = false;
    let messageQueue = [];
    let currentAudio = null;
    let processedMessages = new Set();

    // ============================================================
    // Web Speech API
    // ============================================================
    const synth = window.speechSynthesis || null;

    function speakBrowser(text) {
        if (!synth) return Promise.reject('No Web Speech API');
        return new Promise((resolve, reject) => {
            synth.cancel();
            const utt = new SpeechSynthesisUtterance(text);
            utt.lang = CONFIG.browser.lang;
            utt.rate = CONFIG.browser.rate;
            utt.pitch = CONFIG.browser.pitch;
            utt.volume = CONFIG.browser.volume;
            utt.onend = resolve;
            utt.onerror = reject;
            synth.speak(utt);
        });
    }

    // ============================================================
    // VOICEVOX TTS
    // ============================================================
    async function speakVoicevox(text) {
        try {
            const url = CONFIG.voicevox.apiUrl + '/tts?text=' +
                encodeURIComponent(text) +
                '&speaker=' + CONFIG.voicevox.speaker +
                '&speed=' + CONFIG.voicevox.speed;

            const resp = await fetch(url, { method: 'POST' });
            if (!resp.ok) throw new Error('TTS request failed');

            const contentType = resp.headers.get('content-type');
            if (!contentType || !contentType.includes('audio')) {
                throw new Error('Not audio response');
            }

            const blob = await resp.blob();
            const audioUrl = URL.createObjectURL(blob);

            return new Promise((resolve, reject) => {
                if (currentAudio) {
                    currentAudio.pause();
                    currentAudio = null;
                }
                const audio = new Audio(audioUrl);
                currentAudio = audio;
                audio.onended = () => {
                    URL.revokeObjectURL(audioUrl);
                    currentAudio = null;
                    resolve();
                };
                audio.onerror = reject;
                audio.play();
            });
        } catch (err) {
            console.warn('[Remi Voice] VOICEVOX failed, falling back to browser TTS:', err.message);
            return speakBrowser(text);
        }
    }

    // ============================================================
    // Unified speak function
    // ============================================================
    async function speak(text) {
        if (!text || text.trim().length === 0) return;

        // Truncate very long texts
        if (text.length > CONFIG.maxTextLength) {
            text = text.substring(0, CONFIG.maxTextLength) + '...';
        }

        isSpeaking = true;
        updateButtonState();

        try {
            if (CONFIG.engine === 'voicevox') {
                await speakVoicevox(text);
            } else {
                await speakBrowser(text);
            }
        } catch (err) {
            console.error('[Remi Voice] Speak error:', err);
        }

        isSpeaking = false;
        updateButtonState();

        // Process queue
        if (messageQueue.length > 0) {
            const next = messageQueue.shift();
            setTimeout(() => speak(next), 200);
        }
    }

    function queueMessage(text) {
        if (isSpeaking) {
            messageQueue.push(text);
        } else {
            speak(text);
        }
    }

    function stopSpeaking() {
        if (synth) synth.cancel();
        if (currentAudio) {
            currentAudio.pause();
            currentAudio = null;
        }
        messageQueue = [];
        isSpeaking = false;
        updateButtonState();
    }

    // ============================================================
    // Message Observer (Open WebUI specific)
    // ============================================================
    function cleanText(element) {
        const clone = element.cloneNode(true);
        // Remove code blocks
        clone.querySelectorAll('pre, code, .katex, svg').forEach(el => el.remove());
        let text = clone.textContent.trim();
        // Remove markdown artifacts
        text = text.replace(/```[\s\S]*?```/g, '');
        text = text.replace(/`[^`]*`/g, '');
        text = text.replace(/\[([^\]]+)\]\([^)]+\)/g, '$1');
        text = text.replace(/#{1,6}\s/g, '');
        text = text.replace(/\*{1,2}([^*]+)\*{1,2}/g, '$1');
        return text.trim();
    }

    function observeMessages() {
        const observer = new MutationObserver((mutations) => {
            if (!CONFIG.autoSpeak) return;

            for (const mutation of mutations) {
                for (const node of mutation.addedNodes) {
                    if (node.nodeType !== 1) continue;

                    // Look for assistant message containers
                    const assistantMsgs = [];

                    // Direct match
                    if (node.getAttribute && node.getAttribute('data-role') === 'assistant') {
                        assistantMsgs.push(node);
                    }
                    // Search children
                    if (node.querySelectorAll) {
                        node.querySelectorAll('[data-role="assistant"]').forEach(el => assistantMsgs.push(el));
                    }

                    // Alternative selectors for Open WebUI
                    if (assistantMsgs.length === 0 && node.querySelectorAll) {
                        node.querySelectorAll('.prose, .markdown-body, .assistant-message').forEach(el => {
                            assistantMsgs.push(el);
                        });
                    }

                    for (const msg of assistantMsgs) {
                        // Generate unique key
                        const text = cleanText(msg);
                        if (!text || text.length < 2) continue;

                        const key = text.substring(0, 100);
                        if (processedMessages.has(key)) continue;
                        processedMessages.add(key);

                        // Keep set from growing too large
                        if (processedMessages.size > 100) {
                            const first = processedMessages.values().next().value;
                            processedMessages.delete(first);
                        }

                        console.log('[Remi Voice] New message:', text.substring(0, 60) + '...');
                        queueMessage(text);
                    }
                }
            }
        });

        // Observe the whole document
        observer.observe(document.body, {
            childList: true,
            subtree: true
        });

        console.log('[Remi Voice] Observer active');
    }

    // ============================================================
    // UI Controls
    // ============================================================
    let toggleBtn = null;
    let engineBtn = null;

    function updateButtonState() {
        if (!toggleBtn) return;
        if (CONFIG.autoSpeak) {
            toggleBtn.textContent = isSpeaking ? '...' : 'ON';
            toggleBtn.style.background = isSpeaking ? '#FF9800' : '#4CAF50';
        } else {
            toggleBtn.textContent = 'OFF';
            toggleBtn.style.background = '#666';
        }
    }

    function addControlButtons() {
        // Remove existing
        const existing = document.getElementById('remi-voice-controls');
        if (existing) existing.remove();

        const container = document.createElement('div');
        container.id = 'remi-voice-controls';
        container.style.cssText = [
            'position:fixed',
            'bottom:80px',
            'right:16px',
            'z-index:99999',
            'display:flex',
            'flex-direction:column',
            'gap:8px',
            'align-items:flex-end'
        ].join(';');

        const btnStyle = [
            'border:none',
            'border-radius:50%',
            'width:48px',
            'height:48px',
            'color:white',
            'font-size:12px',
            'font-weight:bold',
            'cursor:pointer',
            'box-shadow:0 4px 12px rgba(0,0,0,0.4)',
            'transition:all 0.2s',
            'display:flex',
            'align-items:center',
            'justify-content:center'
        ].join(';');

        // Toggle button
        toggleBtn = document.createElement('button');
        toggleBtn.style.cssText = btnStyle;
        toggleBtn.onclick = () => {
            CONFIG.autoSpeak = !CONFIG.autoSpeak;
            if (!CONFIG.autoSpeak) stopSpeaking();
            updateButtonState();
        };
        updateButtonState();

        // Stop button
        const stopBtn = document.createElement('button');
        stopBtn.textContent = 'x';
        stopBtn.style.cssText = btnStyle;
        stopBtn.style.background = '#f44336';
        stopBtn.style.width = '36px';
        stopBtn.style.height = '36px';
        stopBtn.style.fontSize = '14px';
        stopBtn.onclick = stopSpeaking;

        // Engine switch button
        engineBtn = document.createElement('button');
        engineBtn.textContent = CONFIG.engine === 'voicevox' ? 'VV' : 'BR';
        engineBtn.style.cssText = btnStyle;
        engineBtn.style.background = CONFIG.engine === 'voicevox' ? '#9C27B0' : '#2196F3';
        engineBtn.style.width = '36px';
        engineBtn.style.height = '36px';
        engineBtn.style.fontSize = '10px';
        engineBtn.onclick = () => {
            CONFIG.engine = CONFIG.engine === 'voicevox' ? 'browser' : 'voicevox';
            engineBtn.textContent = CONFIG.engine === 'voicevox' ? 'VV' : 'BR';
            engineBtn.style.background = CONFIG.engine === 'voicevox' ? '#9C27B0' : '#2196F3';
            console.log('[Remi Voice] Engine:', CONFIG.engine);
        };

        container.appendChild(toggleBtn);
        container.appendChild(stopBtn);
        container.appendChild(engineBtn);
        document.body.appendChild(container);

        console.log('[Remi Voice] Controls added');
    }

    // ============================================================
    // Init
    // ============================================================
    function init() {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', init);
            return;
        }

        setTimeout(() => {
            addControlButtons();
            observeMessages();
            console.log('[Remi Voice v2] Ready! Engine:', CONFIG.engine);
        }, 1500);
    }

    init();

    // Expose API
    window.remiVoice = {
        speak: speak,
        stop: stopSpeaking,
        config: CONFIG,
        setEngine: (e) => { CONFIG.engine = e; }
    };
})();
