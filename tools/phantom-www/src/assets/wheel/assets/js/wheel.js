// SPDX-License-Identifier: AGPL-3.0-or-later
/**
 * ██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
 * ██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
 * ██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
 * ██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
 * ██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
 * ╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝
 *
 * Phantom-WG — Spin & Deploy (Provider Wheel)
 *
 * Copyright (C) 2025 Riza Emre ARAS <r.emrearas@proton.me>
 *
 * This file is part of Phantom-WG.
 *
 * Phantom-WG is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program. If not, see <https://www.gnu.org/licenses/>.
 */

// ==== Language (loaded by i18n.js from languages.json) ====
/**
 * @typedef {Object} WheelLang
 * @property {string} skipLink
 * @property {string} start
 * @property {string} spin
 * @property {string} spinning
 * @property {string} reset
 * @property {string} backHome
 * @property {string} privacyNotice
 * @property {string} privacyHref
 * @property {string} stepLabel1
 * @property {string} stepLabel2
 * @property {string} stepServer
 * @property {string} stepExit
 * @property {string} finalTitle
 * @property {string} serverRole
 * @property {string} exitNode
 */
const LANG = /** @type {WheelLang} */ (window.WHEEL_LANG);

// ==== State ====
let PROVIDERS = [];
let canvas, ctx, W, H, CX, CY, R, segAngle;
let currentAngle = 0;
let isSpinning = false;
let flowState = 'idle';
let serverChoice = null;
let exitChoice = null;

// ==== Audio ====
const AudioCtxClass = window.AudioContext || window['webkitAudioContext'];
let audioCtx = null;

function initAudio() {
  if (!audioCtx && AudioCtxClass) {
    audioCtx = new AudioCtxClass();
  }
}

function playTick(volume = 0.08) {
  if (!audioCtx) return;
  const oscillator = audioCtx.createOscillator();
  const gain = audioCtx.createGain();
  oscillator.connect(gain);
  gain.connect(audioCtx.destination);
  oscillator.type = 'sine';
  oscillator.frequency.value = 2800 + Math.random() * 400;
  gain.gain.setValueAtTime(volume, audioCtx.currentTime);
  gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.06);
  oscillator.start();
  oscillator.stop(audioCtx.currentTime + 0.06);
}

function playWin() {
  if (!audioCtx) return;
  const notes = [523, 659, 784, 1047];
  notes.forEach((freq, i) => {
    const oscillator = audioCtx.createOscillator();
    const gain = audioCtx.createGain();
    oscillator.connect(gain);
    gain.connect(audioCtx.destination);
    oscillator.type = 'sine';
    oscillator.frequency.value = freq;
    const startTime = audioCtx.currentTime + i * 0.12;
    gain.gain.setValueAtTime(0.12, startTime);
    gain.gain.exponentialRampToValueAtTime(0.001, startTime + 0.3);
    oscillator.start(startTime);
    oscillator.stop(startTime + 0.3);
  });
}

// ==== Wheel Drawing ====
function drawWheel(angle) {
  ctx.clearRect(0, 0, W, H);

  // Outer ring
  ctx.beginPath();
  ctx.arc(CX, CY, R + 6, 0, Math.PI * 2);
  ctx.strokeStyle = 'rgba(74,222,128,0.12)';
  ctx.lineWidth = 3;
  ctx.stroke();

  // Segments
  PROVIDERS.forEach((provider, i) => {
    const startAngle = angle + i * segAngle;
    const endAngle = startAngle + segAngle;
    const midAngle = startAngle + segAngle / 2;

    // Segment fill
    ctx.beginPath();
    ctx.moveTo(CX, CY);
    ctx.arc(CX, CY, R, startAngle, endAngle);
    ctx.closePath();
    const hue = 150 + (i * (70 / PROVIDERS.length));
    const gradient = ctx.createRadialGradient(CX, CY, R * 0.15, CX, CY, R);
    gradient.addColorStop(0, i % 2 === 0 ? '#080e1b' : '#0a1322');
    gradient.addColorStop(0.5, `hsla(${hue}, 60%, 22%, 0.15)`);
    gradient.addColorStop(0.85, `hsla(${hue}, 60%, 28%, 0.25)`);
    gradient.addColorStop(1, `hsla(${hue}, 65%, 32%, 0.35)`);
    ctx.fillStyle = gradient;
    ctx.fill();

    // Segment border
    ctx.beginPath();
    ctx.moveTo(CX, CY);
    ctx.arc(CX, CY, R, startAngle, endAngle);
    ctx.closePath();
    ctx.strokeStyle = 'rgba(74,222,128,0.15)';
    ctx.lineWidth = 1.5;
    ctx.stroke();

    // Text
    ctx.save();
    ctx.translate(CX, CY);
    ctx.rotate(midAngle);
    ctx.textAlign = 'right';
    ctx.textBaseline = 'middle';
    ctx.font = '600 22px Orbitron,monospace';
    ctx.fillStyle = '#86EFAC';
    ctx.shadowColor = 'rgba(74,222,128,0.5)';
    ctx.shadowBlur = 8;
    ctx.fillText(provider.name, R - 28, 0);
    ctx.shadowBlur = 0;
    ctx.font = '400 11px Inter,sans-serif';
    ctx.fillStyle = 'rgba(156,163,175,0.6)';
    ctx.fillText(provider.crypto, R - 28, 18);
    ctx.restore();
  });

  // Center fade
  const innerGradient = ctx.createRadialGradient(CX, CY, 0, CX, CY, R * 0.18);
  innerGradient.addColorStop(0, '#0a1628');
  innerGradient.addColorStop(1, 'transparent');
  ctx.beginPath();
  ctx.arc(CX, CY, R * 0.18, 0, Math.PI * 2);
  ctx.fillStyle = innerGradient;
  ctx.fill();

  // Tick marks
  PROVIDERS.forEach((_, i) => {
    const tickAngle = angle + i * segAngle;
    ctx.beginPath();
    ctx.moveTo(CX + Math.cos(tickAngle) * (R - 4), CY + Math.sin(tickAngle) * (R - 4));
    ctx.lineTo(CX + Math.cos(tickAngle) * (R + 2), CY + Math.sin(tickAngle) * (R + 2));
    ctx.strokeStyle = 'rgba(74,222,128,0.4)';
    ctx.lineWidth = 2.5;
    ctx.stroke();
  });
}

// ==== Selection Logic ====
function getSelectedIndex(angle) {
  const normalized = ((-Math.PI / 2 - angle) % (2 * Math.PI) + 2 * Math.PI) % (2 * Math.PI);
  return Math.floor(normalized / segAngle) % PROVIDERS.length;
}

// ==== Flow Control ====
function startFlow() {
  initAudio();
  flowState = 'server';
  serverChoice = null;
  exitChoice = null;
  document.getElementById('startScreen').classList.add('hidden');
  document.getElementById('stepIndicator').classList.add('visible');
  updateStepIndicator();
  document.getElementById('wheelWrapper').classList.add('visible');
  document.getElementById('spinArea').classList.add('visible');
  setStepTitle(LANG.stepServer);
}

function updateStepIndicator() {
  const dot1 = document.getElementById('stepDot1');
  const dot2 = document.getElementById('stepDot2');
  const line = document.getElementById('stepLine1');
  const label1 = document.getElementById('stepLabel1');
  const label2 = document.getElementById('stepLabel2');

  dot1.className = 'step-dot';
  dot2.className = 'step-dot';
  line.className = 'step-line';
  label1.className = 'step-label';
  label2.className = 'step-label';

  if (flowState === 'server') {
    dot1.classList.add('active');
    label1.classList.add('active');
  } else if (flowState === 'exit') {
    dot1.classList.add('done');
    line.classList.add('done');
    label1.classList.add('done');
    dot2.classList.add('active');
    label2.classList.add('active');
  } else if (flowState === 'final') {
    dot1.classList.add('done');
    line.classList.add('done');
    label1.classList.add('done');
    dot2.classList.add('done');
    label2.classList.add('done');
  }
}

function setStepTitle(text) {
  const el = document.getElementById('currentStepTitle');
  el.classList.remove('visible');
  setTimeout(() => {
    el.textContent = text;
    el.classList.add('visible');
  }, 200);
}

// ==== Spin Mechanics ====
function spinWheel() {
  if (isSpinning) return;
  initAudio();
  isSpinning = true;

  const spinBtn = document.getElementById('spinBtn');
  const wrapper = document.getElementById('wheelWrapper');
  spinBtn.disabled = true;
  spinBtn.textContent = LANG.spinning;
  wrapper.classList.add('spinning');
  wrapper.classList.remove('celebrate');
  document.getElementById('stepResultName').classList.remove('visible');
  document.getElementById('stepResultMeta').classList.remove('visible');

  const totalRotation = Math.PI * 2 * (6 + Math.random() * 6);
  const targetAngle = currentAngle + totalRotation;
  const duration = 5000 + Math.random() * 2000;
  const startTime = performance.now();
  const startAngle = currentAngle;
  let lastSegment = -1;
  const tickFlash = document.getElementById('tickFlash');

  function easeOut(t) {
    return 1 - Math.pow(1 - t, 4);
  }

  function animate(now) {
    const progress = Math.min((now - startTime) / duration, 1);
    currentAngle = startAngle + (targetAngle - startAngle) * easeOut(progress);
    drawWheel(currentAngle);

    const currentSegment = getSelectedIndex(currentAngle);
    if (currentSegment !== lastSegment) {
      playTick(0.03 + (1 - progress) * 0.08);
      tickFlash.classList.add('active');
      setTimeout(() => tickFlash.classList.remove('active'), 50);
      lastSegment = currentSegment;
    }

    if (progress < 1) {
      requestAnimationFrame(animate);
    } else {
      isSpinning = false;
      wrapper.classList.remove('spinning');
      wrapper.classList.add('celebrate');
      playWin();
      onSpinComplete(PROVIDERS[getSelectedIndex(currentAngle)]);
    }
  }

  requestAnimationFrame(animate);
}

// ==== Results ====
function onSpinComplete(provider) {
  const spinBtn = document.getElementById('spinBtn');
  const resultName = document.getElementById('stepResultName');
  const resultMeta = document.getElementById('stepResultMeta');

  resultName.textContent = provider.name;
  resultMeta.innerHTML = `${provider.crypto} &middot; <a href="${provider.url}" target="_blank">${provider.url.replace('https://', '')}</a>`;
  setTimeout(() => resultName.classList.add('visible'), 100);
  setTimeout(() => resultMeta.classList.add('visible'), 300);

  if (flowState === 'server') {
    serverChoice = provider;
    setTimeout(() => {
      flowState = 'exit';
      updateStepIndicator();
      setStepTitle(LANG.stepExit);
      spinBtn.disabled = false;
      spinBtn.textContent = LANG.spin;
      resultName.classList.remove('visible');
      resultMeta.classList.remove('visible');
    }, 2200);
  } else if (flowState === 'exit') {
    exitChoice = provider;
    setTimeout(() => {
      flowState = 'final';
      updateStepIndicator();
      showFinal();
    }, 2200);
  }
}

function showFinal() {
  document.getElementById('wheelWrapper').classList.remove('visible');
  document.getElementById('spinArea').classList.remove('visible');
  document.getElementById('currentStepTitle').classList.remove('visible');

  document.getElementById('finalServerName').textContent = serverChoice.name;
  document.getElementById('finalServerCrypto').textContent = serverChoice.crypto;
  document.getElementById('finalServerUrl').innerHTML = `<a href="${serverChoice.url}" target="_blank">${serverChoice.url.replace('https://', '')}</a>`;

  document.getElementById('finalExitName').textContent = exitChoice.name;
  document.getElementById('finalExitCrypto').textContent = exitChoice.crypto;
  document.getElementById('finalExitUrl').innerHTML = `<a href="${exitChoice.url}" target="_blank">${exitChoice.url.replace('https://', '')}</a>`;

  document.getElementById('finalPanel').classList.add('visible');
  setTimeout(() => document.getElementById('finalCardServer').classList.add('visible'), 200);
  setTimeout(() => document.getElementById('routeArrow').classList.add('visible'), 500);
  setTimeout(() => document.getElementById('finalCardExit').classList.add('visible'), 700);
}

function resetFlow() {
  flowState = 'idle';
  serverChoice = null;
  exitChoice = null;
  currentAngle = 0;

  document.getElementById('finalPanel').classList.remove('visible');
  document.getElementById('finalCardServer').classList.remove('visible');
  document.getElementById('finalCardExit').classList.remove('visible');
  document.getElementById('routeArrow').classList.remove('visible');
  document.getElementById('stepIndicator').classList.remove('visible');
  document.getElementById('wheelWrapper').classList.remove('visible', 'celebrate');
  document.getElementById('spinArea').classList.remove('visible');
  document.getElementById('stepResultName').classList.remove('visible');
  document.getElementById('stepResultMeta').classList.remove('visible');
  document.getElementById('spinBtn').disabled = false;
  document.getElementById('spinBtn').textContent = LANG.spin;

  drawWheel(currentAngle);
  setTimeout(() => document.getElementById('startScreen').classList.remove('hidden'), 300);
}

// ==== Particles ====
(function initParticles() {
  for (let i = 0; i < 20; i++) {
    const particle = document.createElement('div');
    particle.className = 'particle';
    particle.style.left = Math.random() * 100 + 'vw';
    particle.style.top = Math.random() * 100 + 'vh';
    particle.style.animation = `pf ${6 + Math.random() * 8}s ease-in-out ${Math.random() * 4}s infinite`;
    document.body.appendChild(particle);
  }
  const style = document.createElement('style');
  style.textContent = '@keyframes pf{0%,100%{opacity:0;transform:translateY(0) scale(1)}20%{opacity:.4}50%{opacity:.6;transform:translateY(-40px) scale(1.5)}80%{opacity:.3}}';
  document.head.appendChild(style);
})();

// ==== Init ====
fetch('data/providers.json')
  .then(res => res.json())
  .then(data => {
    PROVIDERS = data;

    canvas = document.getElementById('wheel');
    ctx = canvas.getContext('2d');
    W = canvas.width;
    H = canvas.height;
    CX = W / 2;
    CY = H / 2;
    R = W / 2 - 12;
    segAngle = (2 * Math.PI) / PROVIDERS.length;

    drawWheel(currentAngle);
  });
