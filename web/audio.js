/* Synthesized Web Audio API chess sound effects (zero external asset deps). */
window.KF_AUDIO = (function () {
  let ctx = null;
  let muted = localStorage.getItem("kf_muted") === "1";

  function ensureCtx() {
    if (muted) return null;
    const AudioCtx = window.AudioContext || window.webkitAudioContext;
    if (!AudioCtx) return null;
    if (!ctx) ctx = new AudioCtx();
    if (ctx.state === "suspended") ctx.resume().catch(() => {});
    return ctx;
  }

  function tone(freq, duration, type = "triangle", gainPeak = 0.14, delay = 0) {
    const c = ensureCtx();
    if (!c) return;
    const now = c.currentTime + delay;
    const osc = c.createOscillator();
    const gain = c.createGain();
    osc.type = type;
    osc.frequency.setValueAtTime(freq, now);
    osc.frequency.exponentialRampToValueAtTime(Math.max(40, freq * 0.55), now + duration);
    gain.gain.setValueAtTime(0.001, now);
    gain.gain.linearRampToValueAtTime(gainPeak, now + 0.008);
    gain.gain.exponentialRampToValueAtTime(0.001, now + duration);
    osc.connect(gain);
    gain.connect(c.destination);
    osc.start(now);
    osc.stop(now + duration + 0.02);
  }

  return {
    isMuted() { return muted; },
    toggleMute() {
      muted = !muted;
      localStorage.setItem("kf_muted", muted ? "1" : "0");
      return muted;
    },
    playMove() { tone(310, 0.075, "triangle", 0.15); },
    playCapture() {
      tone(190, 0.11, "sawtooth", 0.14);
      tone(110, 0.13, "triangle", 0.16, 0.015);
    },
    playCastle() {
      tone(300, 0.065, "triangle", 0.13, 0);
      tone(360, 0.075, "triangle", 0.13, 0.08);
    },
    playCheck() {
      tone(580, 0.09, "sine", 0.14, 0);
      tone(740, 0.12, "sine", 0.14, 0.08);
    },
    playVictory() {
      tone(523.25, 0.14, "triangle", 0.12, 0);
      tone(659.25, 0.14, "triangle", 0.12, 0.10);
      tone(783.99, 0.24, "triangle", 0.14, 0.20);
    },
    playError() {
      tone(180, 0.12, "square", 0.06, 0);
    },
  };
})();
