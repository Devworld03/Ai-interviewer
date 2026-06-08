/**
 * InterviewAI — Frontend Application
 * =====================================
 * Handles: resume upload, interview flow, voice recording, TTS playback, scoring, report
 */

// ── State ──────────────────────────────────────
const state = {
  sessionId: null,
  mode: 'voice',        // 'voice' | 'text' | 'qa'
  isRecording: false,
  mediaRecorder: null,
  audioChunks: [],
  currentTranscript: '',
  totalQuestions: 10,
  currentQuestion: 0,
  runningScores: [],
  ttsEnabled: true,
  isAITalking: false,
  audioQueue: [],
};

// ── API Base ────────────────────────────────────
const API = window.location.origin;

// ══════════════════════════════════════════════════════
// SCREEN MANAGEMENT
// ══════════════════════════════════════════════════════
function showScreen(name) {
  document.querySelectorAll('.screen').forEach(s => {
    s.classList.remove('active');
    s.style.display = 'none';
  });
  const el = document.getElementById(`screen-${name}`);
  if (el) {
    el.style.display = 'flex';
    requestAnimationFrame(() => el.classList.add('active'));
  }
}

// ══════════════════════════════════════════════════════
// UPLOAD SCREEN
// ══════════════════════════════════════════════════════
const uploadZone = document.getElementById('upload-zone');
const resumeInput = document.getElementById('resume-input');

// Drag & drop
uploadZone.addEventListener('dragover', e => { e.preventDefault(); uploadZone.classList.add('drag-over'); });
uploadZone.addEventListener('dragleave', () => uploadZone.classList.remove('drag-over'));
uploadZone.addEventListener('drop', e => {
  e.preventDefault();
  uploadZone.classList.remove('drag-over');
  const file = e.dataTransfer.files[0];
  if (file) handleFileSelect(file);
});
uploadZone.addEventListener('click', () => resumeInput.click());

resumeInput.addEventListener('change', e => {
  if (e.target.files[0]) handleFileSelect(e.target.files[0]);
});

function handleFileSelect(file) {
  const allowed = ['.pdf', '.docx', '.txt'];
  const ext = '.' + file.name.split('.').pop().toLowerCase();
  if (!allowed.includes(ext)) {
    showToast('Please upload a PDF, DOCX, or TXT file', 'error'); return;
  }
  if (file.size > 5 * 1024 * 1024) {
    showToast('File too large. Max 5MB', 'error'); return;
  }

  document.getElementById('file-info').style.display = 'flex';
  document.getElementById('file-name-display').textContent = file.name;
  document.getElementById('file-size-display').textContent = formatBytes(file.size);
  document.getElementById('btn-analyze').style.display = 'flex';
  uploadZone.style.display = 'none';
  resumeInput._selectedFile = file;
}

function clearFile() {
  document.getElementById('file-info').style.display = 'none';
  document.getElementById('btn-analyze').style.display = 'none';
  uploadZone.style.display = 'flex';
  resumeInput.value = '';
  resumeInput._selectedFile = null;
}

async function uploadResume() {
  const file = resumeInput._selectedFile;
  if (!file) { showToast('Please select a file first', 'error'); return; }

  const loader = document.getElementById('upload-loader');
  const btnAnalyze = document.getElementById('btn-analyze');
  btnAnalyze.style.display = 'none';
  loader.style.display = 'flex';

  const loaderTexts = [
    'Parsing your resume...',
    'Extracting skills & experience...',
    'Generating personalized questions...',
    'Almost ready...'
  ];
  let li = 0;
  const loaderInterval = setInterval(() => {
    li = (li + 1) % loaderTexts.length;
    document.getElementById('loader-text').textContent = loaderTexts[li];
  }, 1800);

  try {
    const formData = new FormData();
    formData.append('file', file);

    const res = await fetch(`${API}/api/resume/upload`, { method: 'POST', body: formData });
    const data = await res.json();

    if (!res.ok) throw new Error(data.detail || 'Upload failed');

    state.sessionId = data.session_id;
    state.totalQuestions = data.question_count;

    // Populate ready screen
    document.getElementById('rs-name').textContent = data.candidate_name;
    document.getElementById('rs-qcount').textContent = data.question_count;

    const skillsEl = document.getElementById('rs-skills');
    skillsEl.innerHTML = (data.skills_detected || []).map(s => `<span class="chip">${s}</span>`).join('');

    const focusEl = document.getElementById('rs-focus');
    focusEl.innerHTML = (data.focus_areas || []).map(f => `<span class="chip green">${f}</span>`).join('');

    showScreen('ready');

  } catch (err) {
    showToast(err.message || 'Failed to process resume', 'error');
    btnAnalyze.style.display = 'flex';
  } finally {
    clearInterval(loaderInterval);
    loader.style.display = 'none';
  }
}

// ══════════════════════════════════════════════════════
// READY SCREEN
// ══════════════════════════════════════════════════════
function selectMode(mode) {
  state.mode = mode;
  document.querySelectorAll('.mode-card').forEach(c => c.classList.remove('active'));
  document.getElementById(`mode-${mode}`).classList.add('active');
}

async function startSession() {
  if (state.mode === 'qa') {
    showScreen('qa');
    return;
  }

  showScreen('interview');
  setupInputMode();

  try {
    const res = await fetch(`${API}/api/interview/start/${state.sessionId}`, { method: 'POST' });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail);

    state.currentQuestion = 1;
    state.totalQuestions = data.total_questions;

    updateProgress(1, data.total_questions);
    updateQuestionMeta(data.question_type, data.focus_area);

    appendMessage('ai', data.intro_message);
    await speakText(data.intro_message);

  } catch (err) {
    appendMessage('ai', 'Welcome! Ready to start your interview. Please answer each question thoroughly.');
  }
}

function setupInputMode() {
  const voiceEl = document.getElementById('voice-controls');
  const textEl = document.getElementById('text-controls');
  if (state.mode === 'voice') {
    voiceEl.style.display = 'flex';
    textEl.style.display = 'none';
  } else {
    voiceEl.style.display = 'none';
    textEl.style.display = 'flex';
  }
}

// ══════════════════════════════════════════════════════
// VOICE RECORDING
// ══════════════════════════════════════════════════════
async function toggleRecording() {
  if (state.isRecording) {
    stopRecording();
  } else {
    await startRecording();
  }
}

async function startRecording() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    state.audioChunks = [];
    state.mediaRecorder = new MediaRecorder(stream);

    state.mediaRecorder.ondataavailable = e => {
      if (e.data.size > 0) state.audioChunks.push(e.data);
    };

    state.mediaRecorder.onstop = async () => {
      stream.getTracks().forEach(t => t.stop());
      await processRecording();
    };

    state.mediaRecorder.start();
    state.isRecording = true;

    const btn = document.getElementById('btn-mic');
    const micIcon = document.getElementById('mic-icon');
    const micLabel = document.getElementById('mic-label');
    const viz = document.getElementById('voice-viz');

    btn.classList.add('recording');
    micIcon.textContent = '⏹';
    micLabel.textContent = 'Recording... Click to Stop';
    document.getElementById('voice-status').textContent = '🔴 Recording your answer...';
    viz.classList.add('active');

  } catch (err) {
    showToast('Microphone access denied. Please allow microphone access.', 'error');
  }
}

function stopRecording() {
  if (state.mediaRecorder && state.isRecording) {
    state.mediaRecorder.stop();
    state.isRecording = false;

    const btn = document.getElementById('btn-mic');
    const micIcon = document.getElementById('mic-icon');
    const micLabel = document.getElementById('mic-label');
    const viz = document.getElementById('voice-viz');

    btn.classList.remove('recording');
    micIcon.textContent = '🎤';
    micLabel.textContent = 'Hold to Speak';
    document.getElementById('voice-status').textContent = 'Transcribing your answer...';
    viz.classList.remove('active');
  }
}

async function processRecording() {
  const blob = new Blob(state.audioChunks, { type: 'audio/webm' });
  
  const formData = new FormData();
  formData.append('audio', blob, 'recording.webm');

  try {
    document.getElementById('voice-status').textContent = '⚙️ Transcribing...';
    const res = await fetch(`${API}/api/audio/stt`, { method: 'POST', body: formData });
    const data = await res.json();

    if (!res.ok) throw new Error(data.detail || 'STT failed');

    const transcript = data.transcript.trim();
    if (!transcript) {
      document.getElementById('voice-status').textContent = "Couldn't hear that clearly. Please try again.";
      return;
    }

    state.currentTranscript = transcript;

    // Show transcript preview
    document.getElementById('tp-text').textContent = transcript;
    document.getElementById('transcript-preview').style.display = 'flex';
    document.getElementById('voice-status').textContent = '✓ Transcribed. Review and send your answer.';

  } catch (err) {
    document.getElementById('voice-status').textContent = 'Transcription failed. Please try again.';
    showToast('STT error: ' + (err.message || 'Unknown'), 'error');
  }
}

async function sendTranscript() {
  const transcript = state.currentTranscript;
  if (!transcript) return;

  document.getElementById('transcript-preview').style.display = 'none';
  document.getElementById('voice-status').textContent = 'Press and hold the mic button to record your answer';
  state.currentTranscript = '';

  await submitAnswer(transcript);
}

// ══════════════════════════════════════════════════════
// TEXT ANSWER
// ══════════════════════════════════════════════════════
const textAnswer = document.getElementById('text-answer');
if (textAnswer) {
  textAnswer.addEventListener('input', () => {
    document.getElementById('char-count').textContent = `${textAnswer.value.length} characters`;
  });
}

async function sendTextAnswer() {
  const answer = document.getElementById('text-answer').value.trim();
  if (!answer) { showToast('Please write your answer first', 'error'); return; }
  document.getElementById('text-answer').value = '';
  document.getElementById('char-count').textContent = '0 characters';
  await submitAnswer(answer);
}

// ══════════════════════════════════════════════════════
// SUBMIT ANSWER & FLOW
// ══════════════════════════════════════════════════════
async function submitAnswer(answer) {
  // Show user's answer
  appendMessage('user', answer);

  // Show thinking indicator
  const thinkingId = appendThinking();

  // Disable inputs
  setInputDisabled(true);

  try {
    const res = await fetch(`${API}/api/interview/answer/${state.sessionId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ answer })
    });
    const data = await res.json();

    removeThinking(thinkingId);

    if (!res.ok) throw new Error(data.detail);

    // Update score display
    if (data.score !== undefined) {
      state.runningScores.push(data.score);
      updateRunningScore();
      updateEvalPanel(data.score, data.evaluation);
    }

    // Show AI response
    appendMessage('ai', data.interviewer_response);
    await speakText(data.interviewer_response);

    if (data.interview_complete) {
      setInputDisabled(true);
      setTimeout(() => fetchAndShowReport(), 2000);
      return;
    }

    // Update progress
    state.currentQuestion = data.question_number;
    updateProgress(data.question_number, data.total_questions);
    updateQuestionMeta(data.question_type, data.focus_area);

  } catch (err) {
    removeThinking(thinkingId);
    showToast('Error submitting answer: ' + (err.message || 'Unknown'), 'error');
  } finally {
    setInputDisabled(false);
  }
}

// ══════════════════════════════════════════════════════
// REPORT
// ══════════════════════════════════════════════════════
async function fetchAndShowReport() {
  appendMessage('ai', '📊 Generating your comprehensive interview report...');

  try {
    const res = await fetch(`${API}/api/interview/report/${state.sessionId}`);
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail);

    renderReport(data);
    setTimeout(() => showScreen('report'), 1000);

  } catch (err) {
    showToast('Error generating report: ' + (err.message || ''), 'error');
  }
}

function renderReport(data) {
  const r = data.report;

  document.getElementById('report-name').textContent = data.candidate_name;
  document.getElementById('report-grade').textContent = r.grade || 'B';
  document.getElementById('report-hire').textContent = r.hire_recommendation || '—';
  document.getElementById('report-exec').textContent = r.executive_summary || '';
  document.getElementById('report-feedback').textContent = r.detailed_feedback || '';

  // Score circle
  const score = parseFloat(r.overall_score) || 0;
  document.getElementById('rsc-score').textContent = score.toFixed(1);
  const circumference = 2 * Math.PI * 50; // r=50
  const filled = (score / 10) * circumference;
  setTimeout(() => {
    document.getElementById('rc-fill').style.strokeDasharray = `${filled} ${circumference}`;
  }, 300);

  // Category bars
  const catBars = document.getElementById('category-bars');
  const cats = r.category_scores || {};
  catBars.innerHTML = Object.entries(cats).map(([key, val]) => `
    <div class="cat-bar-row">
      <div class="cat-bar-label">${formatKey(key)}</div>
      <div class="cat-bar-track"><div class="cat-bar-fill" style="width:${val * 10}%"></div></div>
      <div class="cat-bar-score">${val}</div>
    </div>
  `).join('');

  // Lists
  renderList('report-strengths', r.top_strengths || []);
  renderList('report-improvements', r.areas_for_improvement || []);
  renderList('report-nextsteps', r.next_steps || []);
  renderList('report-resources', r.resources_to_study || []);

  // Q&A review
  const qaEl = document.getElementById('qa-review');
  qaEl.innerHTML = (data.qa_history || []).map((qa, i) => `
    <div class="qa-item">
      <div class="qa-item-q">Q${i+1}: ${qa.question}</div>
      <div class="qa-item-a">${qa.answer}</div>
      <div class="qa-item-score">Score: ${qa.score}/10</div>
    </div>
  `).join('');
}

function renderList(elId, items) {
  document.getElementById(elId).innerHTML = items.map(i => `<li>${i}</li>`).join('');
}

// ══════════════════════════════════════════════════════
// QA CHAT
// ══════════════════════════════════════════════════════
async function sendQAMessage() {
  const input = document.getElementById('qa-input');
  const message = input.value.trim();
  if (!message) return;
  input.value = '';

  appendQAMsg('user', message);

  const thinkingEl = document.createElement('div');
  thinkingEl.className = 'qa-msg ai thinking-qa';
  thinkingEl.innerHTML = `
    <div class="qa-avatar">AI</div>
    <div class="qa-bubble"><div class="thinking-dots"><span></span><span></span><span></span></div></div>
  `;
  document.getElementById('qa-chat').appendChild(thinkingEl);
  scrollQAChat();

  try {
    const res = await fetch(`${API}/api/interview/chat/${state.sessionId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message })
    });
    const data = await res.json();

    thinkingEl.remove();

    if (!res.ok) throw new Error(data.detail);
    appendQAMsg('ai', data.response);

  } catch (err) {
    thinkingEl.remove();
    appendQAMsg('ai', 'Sorry, I encountered an error. Please try again.');
  }
}

function appendQAMsg(role, text) {
  const chat = document.getElementById('qa-chat');
  const div = document.createElement('div');
  div.className = `qa-msg ${role}`;
  div.innerHTML = `
    <div class="qa-avatar">${role === 'ai' ? 'AI' : 'You'}</div>
    <div class="qa-bubble">${escapeHtml(text)}</div>
  `;
  chat.appendChild(div);
  scrollQAChat();
}

function scrollQAChat() {
  const chat = document.getElementById('qa-chat');
  chat.scrollTop = chat.scrollHeight;
}

// ══════════════════════════════════════════════════════
// TTS — TEXT TO SPEECH
// ══════════════════════════════════════════════════════
async function speakText(text) {
  if (!state.ttsEnabled) return;

  // Truncate long text for TTS
  const speakable = text.length > 600 ? text.substring(0, 600) + '...' : text;

  try {
    const res = await fetch(`${API}/api/audio/tts`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: speakable })
    });

    if (!res.ok) return; // Silently fail TTS

    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const audio = new Audio(url);
    
    return new Promise((resolve) => {
      audio.onended = () => { URL.revokeObjectURL(url); resolve(); };
      audio.onerror = () => { resolve(); }; // Don't block on TTS errors
      audio.play().catch(() => resolve());
    });

  } catch (err) {
    // TTS failure is non-blocking
    console.warn('TTS error:', err);
  }
}

// ══════════════════════════════════════════════════════
// UI HELPERS
// ══════════════════════════════════════════════════════
function appendMessage(role, text) {
  const chat = document.getElementById('chat-messages');
  const div = document.createElement('div');
  div.className = `chat-msg ${role}`;
  div.innerHTML = `
    <div class="msg-avatar">${role === 'ai' ? 'AI' : 'You'}</div>
    <div class="msg-bubble">${escapeHtml(text).replace(/\n/g, '<br/>')}</div>
  `;
  chat.appendChild(div);
  chat.scrollTop = chat.scrollHeight;
  return div;
}

function appendThinking() {
  const chat = document.getElementById('chat-messages');
  const id = 'thinking-' + Date.now();
  const div = document.createElement('div');
  div.id = id;
  div.className = 'chat-msg ai msg-thinking';
  div.innerHTML = `
    <div class="msg-avatar">AI</div>
    <div class="msg-bubble"><div class="thinking-dots"><span></span><span></span><span></span></div></div>
  `;
  chat.appendChild(div);
  chat.scrollTop = chat.scrollHeight;
  return id;
}

function removeThinking(id) {
  const el = document.getElementById(id);
  if (el) el.remove();
}

function setInputDisabled(disabled) {
  const btn = document.getElementById('btn-mic');
  const textarea = document.getElementById('text-answer');
  if (btn) btn.disabled = disabled;
  if (textarea) textarea.disabled = disabled;
}

function updateProgress(current, total) {
  const pct = (current / total) * 100;
  document.getElementById('progress-fill').style.width = `${pct}%`;
  document.getElementById('progress-text').textContent = `${current} / ${total}`;
}

function updateQuestionMeta(type, focusArea) {
  document.getElementById('qtype-text').textContent = type || '—';
  document.getElementById('fa-value').textContent = focusArea || '—';
}

function updateRunningScore() {
  if (state.runningScores.length === 0) return;
  const avg = state.runningScores.reduce((a, b) => a + b, 0) / state.runningScores.length;
  document.getElementById('running-score').textContent = avg.toFixed(1);
}

function updateEvalPanel(score, evaluation) {
  document.getElementById('ep-score').textContent = score.toFixed(1);

  // Ring animation: circumference = 2*PI*32 ≈ 201
  const circ = 201;
  const filled = (score / 10) * circ;
  document.getElementById('ring-fill').style.strokeDasharray = `${filled} ${circ}`;

  // Strengths & improvements
  const strengths = document.getElementById('ep-strengths');
  const improvements = document.getElementById('ep-improvements');

  if (evaluation) {
    const s = evaluation.strengths || [];
    const i = evaluation.improvements || [];
    strengths.innerHTML = s.length ? s.map(x => `<li>${x}</li>`).join('') : '<li class="ep-empty">—</li>';
    improvements.innerHTML = i.length ? i.map(x => `<li>${x}</li>`).join('') : '<li class="ep-empty">—</li>';
  }
}

function endInterviewEarly() {
  if (confirm('End the interview and get your report now?')) {
    fetchAndShowReport();
  }
}

function startOver() {
  state.sessionId = null;
  state.mode = 'voice';
  state.runningScores = [];
  state.currentQuestion = 0;
  document.getElementById('chat-messages').innerHTML = '';
  document.getElementById('qa-chat').innerHTML = `
    <div class="qa-msg ai">
      <div class="qa-avatar">AI</div>
      <div class="qa-bubble">Hi! I've analyzed your resume thoroughly. Ask me anything!</div>
    </div>
  `;
  clearFile();
  showScreen('upload');
}

function goBack() {
  showScreen('ready');
}

// ══════════════════════════════════════════════════════
// UTILITY
// ══════════════════════════════════════════════════════
function showToast(msg, type = '') {
  const toast = document.getElementById('toast');
  toast.textContent = msg;
  toast.className = 'toast show' + (type ? ` ${type}` : '');
  setTimeout(() => { toast.className = 'toast'; }, 3500);
}

function formatBytes(bytes) {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

function formatKey(key) {
  return key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.appendChild(document.createTextNode(text));
  return div.innerHTML;
}

// ══════════════════════════════════════════════════════
// INIT
// ══════════════════════════════════════════════════════
document.addEventListener('DOMContentLoaded', () => {
  showScreen('upload');

  // Handle keyboard shortcut for text answer
  document.addEventListener('keydown', e => {
    if (e.ctrlKey && e.key === 'Enter' && state.mode === 'text') {
      sendTextAnswer();
    }
  });
});
