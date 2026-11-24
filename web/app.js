const FILES = "abcdefgh";
const $ = (id) => document.getElementById(id);
const SVG_PIECES = window.KF_PIECES_SVG || {};
const AUDIO = window.KF_AUDIO || {
  isMuted: () => true, toggleMute: () => true,
  playMove() {}, playCapture() {}, playCastle() {},
  playCheck() {}, playVictory() {}, playError() {},
};

let authToken = localStorage.getItem("kf_token") || "";
let authUsername = localStorage.getItem("kf_user") || "guest";

async function api(path, options = {}) {
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (authToken) headers.Authorization = "Bearer " + authToken;
  const res = await fetch(path, { ...options, headers });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(body.detail || "Request failed");
  return body;
}

function parseFen(fen) {
  const rows = fen.split(" ")[0].split("/");
  const out = {};
  rows.forEach((row, r) => {
    let f = 0;
    for (const c of row) {
      if (/[1-8]/.test(c)) {
        for (let n = 0; n < +c; n++) out[FILES[f++] + (8 - r)] = null;
      } else {
        out[FILES[f++] + (8 - r)] = c;
      }
    }
  });
  return out;
}

function parseUci(u) {
  return { from: u.slice(0, 2), to: u.slice(2, 4), promotion: u[4] || null };
}

function formatMoves(sanMoves) {
  if (!sanMoves.length) return "Your moves will appear here.";
  const parts = [];
  for (let i = 0; i < sanMoves.length; i += 2) {
    const num = Math.floor(i / 2) + 1;
    parts.push(`${num}. ${sanMoves[i]}${sanMoves[i + 1] ? " " + sanMoves[i + 1] : ""}`);
  }
  return parts.join("   ");
}

function formatClock(seconds) {
  const s = Math.max(0, Math.floor(seconds));
  const m = Math.floor(s / 60);
  const rem = s % 60;
  return `${String(m).padStart(2, "0")}:${String(rem).padStart(2, "0")}`;
}

function showFeedback(id, msg, good = true) {
  const el = $(id);
  el.textContent = msg;
  el.className = "feedback" + (good ? "" : " bad");
}

function playSoundForSan(san, isCheckmate = false) {
  if (isCheckmate) return AUDIO.playVictory();
  if (!san) return AUDIO.playMove();
  if (san.includes("#")) return AUDIO.playVictory();
  if (san.includes("+")) return AUDIO.playCheck();
  if (san.startsWith("O-O")) return AUDIO.playCastle();
  if (san.includes("x")) return AUDIO.playCapture();
  AUDIO.playMove();
}

function renderCoords(ids, flipped) {
  const f = flipped ? [...FILES].reverse() : [...FILES];
  const r = flipped ? [1, 2, 3, 4, 5, 6, 7, 8] : [8, 7, 6, 5, 4, 3, 2, 1];
  const fh = f.map((x) => `<span>${x}</span>`).join("");
  const rh = r.map((x) => `<span>${x}</span>`).join("");
  $(ids[0]).innerHTML = fh;
  $(ids[1]).innerHTML = fh;
  $(ids[2]).innerHTML = rh;
  $(ids[3]).innerHTML = rh;
}

// =========================================================================
// UNIFIED POINTER-EVENT DRAG-AND-DROP (ANDROID TOUCH + DESKTOP MOUSE) + TAP
// =========================================================================
let activeDrag = null;

function squareFromPoint(boardEl, clientX, clientY, flipped) {
  const rect = boardEl.getBoundingClientRect();
  if (
    clientX < rect.left || clientX > rect.right ||
    clientY < rect.top || clientY > rect.bottom
  ) return null;
  const col = Math.min(7, Math.max(0, Math.floor(((clientX - rect.left) / rect.width) * 8)));
  const row = Math.min(7, Math.max(0, Math.floor(((clientY - rect.top) / rect.height) * 8)));
  const fileIdx = flipped ? 7 - col : col;
  const rankNum = flipped ? row + 1 : 8 - row;
  return FILES[fileIdx] + rankNum;
}

function clearDragHover(boardEl) {
  boardEl.querySelectorAll(".square.drag-over").forEach((el) => el.classList.remove("drag-over"));
}

window.addEventListener("pointermove", (ev) => {
  if (!activeDrag || ev.pointerId !== activeDrag.pointerId) return;
  const dx = ev.clientX - activeDrag.startX;
  const dy = ev.clientY - activeDrag.startY;
  const ghost = $("drag-ghost");
  if (!activeDrag.dragging && Math.hypot(dx, dy) > 7) {
    activeDrag.dragging = true;
    if (activeDrag.sourceWrap) activeDrag.sourceWrap.classList.add("dragging-source");
    ghost.innerHTML = SVG_PIECES[activeDrag.piece] || "";
    ghost.classList.remove("hidden");
  }
  if (activeDrag.dragging) {
    const liftY = ev.pointerType === "touch" ? -28 : 0;
    ghost.style.left = ev.clientX + "px";
    ghost.style.top = (ev.clientY + liftY) + "px";
    clearDragHover(activeDrag.boardEl);
    const overSq = squareFromPoint(activeDrag.boardEl, ev.clientX, ev.clientY, activeDrag.flipped);
    if (overSq) {
      const targetBtn = activeDrag.boardEl.querySelector(`.square[data-sq="${overSq}"]`);
      if (targetBtn) targetBtn.classList.add("drag-over");
    }
  }
});

function finishPointerDrag(ev) {
  if (!activeDrag || ev.pointerId !== activeDrag.pointerId) return;
  const drag = activeDrag;
  activeDrag = null;
  $("drag-ghost").classList.add("hidden");
  clearDragHover(drag.boardEl);
  if (drag.sourceWrap) drag.sourceWrap.classList.remove("dragging-source");

  if (drag.dragging) {
    const destSq = squareFromPoint(drag.boardEl, ev.clientX, ev.clientY, drag.flipped);
    if (destSq && destSq !== drag.fromSq && drag.onDropMove) {
      drag.onDropMove(drag.fromSq, destSq);
      return;
    }
  }
  // Short tap (not a drag) -> normal click-to-select / click-to-move
  if (drag.onSquareClick) drag.onSquareClick(drag.fromSq, drag.piece);
}
window.addEventListener("pointerup", finishPointerDrag);
window.addEventListener("pointercancel", finishPointerDrag);

function renderBoard({
  boardId, coordIds, fen, flipped, selected, targets, lastMove,
  checkedSquare, arrowData, interactive = true, onSquareClick, onDropMove,
}) {
  renderCoords(coordIds, flipped);
  const root = $(boardId);
  root.innerHTML = "";
  const cells = parseFen(fen);
  const ranks = flipped ? [1, 2, 3, 4, 5, 6, 7, 8] : [8, 7, 6, 5, 4, 3, 2, 1];
  const files = flipped ? [7, 6, 5, 4, 3, 2, 1, 0] : [0, 1, 2, 3, 4, 5, 6, 7];

  for (const rank of ranks) {
    for (const file of files) {
      const sq = FILES[file] + rank;
      const piece = cells[sq];
      const b = document.createElement("button");
      b.type = "button";
      b.dataset.sq = sq;
      b.className = "square " + ((file + rank) % 2 === 0 ? "dark" : "light");
      if (sq === selected) b.classList.add("selected");
      if (sq === checkedSquare) b.classList.add("in-check");
      if (lastMove && lastMove.includes(sq)) b.classList.add("last-move");
      if (targets.some((t) => t.to === sq)) {
        b.classList.add(piece ? "capture" : "legal");
      }
      let wrap = null;
      if (piece) {
        wrap = document.createElement("span");
        wrap.className = "piece-wrap";
        wrap.innerHTML = SVG_PIECES[piece] || piece;
        b.append(wrap);
      }
      b.setAttribute("aria-label", sq + (piece ? " " + piece : " empty"));
      if (interactive) {
        b.addEventListener("pointerdown", (ev) => {
          if (ev.button !== 0 && ev.pointerType === "mouse") return;
          if (piece && onDropMove) {
            activeDrag = {
              pointerId: ev.pointerId,
              boardEl: root,
              flipped,
              fromSq: sq,
              piece,
              sourceWrap: wrap,
              startX: ev.clientX,
              startY: ev.clientY,
              dragging: false,
              onSquareClick,
              onDropMove,
            };
          } else if (onSquareClick) {
            onSquareClick(sq, piece);
          }
        });
      }
      root.append(b);
    }
  }

  if (arrowData && arrowData.from && arrowData.to) {
    const pos = (s) => {
      const fIdx = FILES.indexOf(s[0]);
      const rNum = Number(s[1]);
      return {
        x: ((flipped ? 7 - fIdx : fIdx) + 0.5) * 12.5,
        y: ((flipped ? rNum - 1 : 8 - rNum) + 0.5) * 12.5,
      };
    };
    const p = pos(arrowData.from);
    const q = pos(arrowData.to);
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("viewBox", "0 0 100 100");
    svg.setAttribute("class", "board-arrow");
    svg.innerHTML =
      '<defs><marker id="arrowhead" markerWidth="5" markerHeight="5" refX="3.8" refY="2.5" orient="auto">' +
      '<path d="M0 0 L5 2.5 L0 5Z" fill="#d7f18a"/></marker></defs>';
    const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
    line.setAttribute("x1", p.x);
    line.setAttribute("y1", p.y);
    line.setAttribute("x2", q.x);
    line.setAttribute("y2", q.y);
    svg.append(line);
    root.append(svg);
  }
}

let promoResolver = null;
function askPromotion() {
  return new Promise((resolve) => {
    promoResolver = resolve;
    $("promo-modal").classList.remove("hidden");
  });
}
document.querySelectorAll(".promo-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    $("promo-modal").classList.add("hidden");
    if (promoResolver) {
      promoResolver(btn.dataset.promo);
      promoResolver = null;
    }
  });
});

function speak(t) {
  if (!window.speechSynthesis || !t) return;
  window.speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(t);
  u.rate = 0.94;
  window.speechSynthesis.speak(u);
}

// =========================================================================
// THEME, SOUND & NAVIGATION (DESKTOP TOP TABS + MOBILE BOTTOM BAR)
// =========================================================================
$("sound-toggle").textContent = AUDIO.isMuted() ? "🔇" : "🔊";
$("sound-toggle").addEventListener("click", () => {
  const m = AUDIO.toggleMute();
  $("sound-toggle").textContent = m ? "🔇" : "🔊";
  if (!m) AUDIO.playMove();
});
$("theme-toggle").addEventListener("click", () => {
  const root = document.documentElement;
  root.dataset.theme = root.dataset.theme === "dark" ? "light" : "dark";
});
$("board-theme-select").addEventListener("change", (e) => {
  document.documentElement.dataset.boardTheme = e.target.value;
});
$("piece-style-select").addEventListener("change", (e) => {
  document.documentElement.dataset.pieceStyle = e.target.value;
});

function switchTab(tabName) {
  document.querySelectorAll(".tab-btn, .mobile-tab-btn").forEach((b) => {
    b.classList.toggle("active", b.dataset.tab === tabName);
  });
  document.querySelectorAll(".tab-panel").forEach((p) => {
    p.classList.toggle("active", p.id === "tab-" + tabName);
  });
  if (tabName === "academy" && !academySessionId) loadLessonsAndStart();
  if (tabName === "openings" && !openingsLoaded) loadOpenings();
  if (tabName === "tactics" && !puzzleListCache.length) loadPuzzles();
  if (tabName === "profile") loadProfile();
}
document.querySelectorAll(".tab-btn, .mobile-tab-btn").forEach((btn) => {
  btn.addEventListener("click", () => switchTab(btn.dataset.tab));
});

// =========================================================================
// TAB 1: PLAY CHESS (HvAI / Local PvP / Online WS + Eval Bar + Replay HUD)
// =========================================================================
let playGameId = null;
let playToken = null;
let playState = null;
let playSelected = null;
let playTargets = [];
let playLastMove = null;
let playFlipped = false;
let playViewPly = null; // null means live position
let playWs = null;
let playClockTimer = null;

function connectPlayWs(gameId) {
  if (playWs) { playWs.close(); playWs = null; }
  const proto = location.protocol === "https:" ? "wss:" : "ws:";
  try {
    playWs = new WebSocket(`${proto}//${location.host}/ws/games/${gameId}`);
    playWs.onmessage = (ev) => {
      const msg = JSON.parse(ev.data);
      if (msg.state) {
        playState = msg.state;
        playViewPly = null;
        if (msg.event === "opponent_joined") {
          showFeedback("play-status", "Opponent joined! Game is live.", true);
          AUDIO.playCastle();
        } else if (msg.event === "move") {
          const lastSan = playState.moves_san[playState.moves_san.length - 1];
          playSoundForSan(lastSan, playState.termination === "checkmate");
        }
        renderPlay();
      }
    };
  } catch (_) {}
}

function startClockTicker() {
  if (playClockTimer) clearInterval(playClockTimer);
  playClockTimer = setInterval(() => {
    if (!playState || playState.is_over || !playState.clock.enabled || playState.clock.paused) return;
    if (playState.clock.active_side === "white") {
      playState.clock.white_remaining = Math.max(0, playState.clock.white_remaining - 1);
    } else if (playState.clock.active_side === "black") {
      playState.clock.black_remaining = Math.max(0, playState.clock.black_remaining - 1);
    }
    updateClockDisplay();
  }, 1000);
}

function updateClockDisplay() {
  if (!playState) return;
  const c = playState.clock;
  const topColor = playFlipped ? "white" : "black";
  const bottomColor = playFlipped ? "black" : "white";
  const wTime = c.enabled ? formatClock(c.white_remaining) : "∞";
  const bTime = c.enabled ? formatClock(c.black_remaining) : "∞";
  $("clock-top-time").textContent = topColor === "white" ? wTime : bTime;
  $("clock-bottom-time").textContent = bottomColor === "white" ? wTime : bTime;
  $("clock-top").classList.toggle("active-clock", c.enabled && c.active_side === topColor && !c.paused);
  $("clock-bottom").classList.toggle("active-clock", c.enabled && c.active_side === bottomColor && !c.paused);
}

function updateEvalBar() {
  if (!playState) return;
  let pct = 50;
  let label = "0.0";
  if (playState.mate_in !== null && playState.mate_in !== undefined) {
    pct = playState.mate_in > 0 ? 97 : 3;
    label = `M${Math.abs(playState.mate_in)}`;
    $("eval-pill").textContent = `Mate in ${Math.abs(playState.mate_in)}`;
  } else if (playState.eval_cp_white !== null && playState.eval_cp_white !== undefined) {
    const pawns = playState.eval_cp_white / 100;
    const clamped = Math.max(-8, Math.min(8, pawns));
    pct = Math.round(50 + (clamped / 8) * 46);
    label = (pawns >= 0 ? "+" : "") + pawns.toFixed(1);
    $("eval-pill").textContent = `Eval: ${label}`;
  } else {
    $("eval-pill").textContent = "Eval: 0.0";
  }
  $("eval-bar-fill").style.height = (playFlipped ? 100 - pct : pct) + "%";
  $("eval-bar-label").textContent = label;
}

function updateMaterialBars() {
  if (!playState || !playState.material) return;
  const mat = playState.material;
  const topIsWhite = playFlipped;
  $("top-side-label").textContent = topIsWhite ? "WHITE" : "BLACK";
  $("top-side-label").className = "side-dot " + (topIsWhite ? "white-dot" : "black-dot");
  $("bottom-side-label").textContent = topIsWhite ? "BLACK" : "WHITE";
  $("bottom-side-label").className = "side-dot " + (topIsWhite ? "black-dot" : "white-dot");

  const topCap = topIsWhite ? mat.captured_by_white : mat.captured_by_black;
  const botCap = topIsWhite ? mat.captured_by_black : mat.captured_by_white;
  $("captured-top").innerHTML = topCap.map((p) => SVG_PIECES[p] || "").join("");
  $("captured-bottom").innerHTML = botCap.map((p) => SVG_PIECES[p] || "").join("");

  const adv = mat.white_advantage || 0;
  const topAdv = topIsWhite ? adv : -adv;
  const botAdv = topIsWhite ? -adv : adv;
  $("material-top").textContent = topAdv > 0 ? `+${topAdv}` : "";
  $("material-top").classList.toggle("hidden", topAdv <= 0);
  $("material-bottom").textContent = botAdv > 0 ? `+${botAdv}` : "";
  $("material-bottom").classList.toggle("hidden", botAdv <= 0);
}

async function startPlayGame(startingFen = null) {
  const mode = $("play-mode").value;
  const player_color = $("play-color").value;
  const difficulty = $("play-difficulty").value;
  const time_control = $("play-clock").value;
  const body = { mode, player_color, difficulty, time_control };
  if (startingFen) body.starting_fen = startingFen;
  const res = await api("/api/games", { method: "POST", body: JSON.stringify(body) });
  playGameId = res.game_id;
  playToken = res.player_token;
  playState = res.state;
  playSelected = null;
  playTargets = [];
  playLastMove = null;
  playViewPly = null;
  playFlipped = res.assigned_color === "black";
  $("play-status").className = "feedback hidden";
  if (res.invite_code) {
    $("invite-box").classList.remove("hidden");
    $("invite-code-display").textContent = res.invite_code;
    connectPlayWs(playGameId);
  } else {
    $("invite-box").classList.add("hidden");
  }
  $("play-title").textContent =
    mode === "human_vs_ai"
      ? `Human vs. AI (${difficulty})`
      : mode === "local_pvp"
      ? "Local Two-Player Match"
      : "Online Private Match";
  startClockTicker();
  renderPlay();
}

function renderPlayMoveChips() {
  const container = $("play-moves");
  const sans = playState.moves_san || [];
  if (!sans.length) {
    container.className = "moves-empty";
    container.textContent = "Drag or tap any piece to start playing.";
    return;
  }
  const activePly = playViewPly === null ? sans.length : playViewPly;
  container.className = "move-list";
  container.innerHTML = "";
  sans.forEach((san, idx) => {
    const ply = idx + 1;
    const prefix = idx % 2 === 0 ? `${Math.floor(idx / 2) + 1}. ` : "";
    const chip = document.createElement("button");
    chip.type = "button";
    chip.className = "move-chip" + (ply === activePly ? " active-ply" : "");
    chip.textContent = prefix + san;
    chip.addEventListener("click", () => {
      playViewPly = ply === sans.length ? null : ply;
      renderPlay();
    });
    container.append(chip);
  });
}

function renderPlay() {
  if (!playState) return;
  updateClockDisplay();
  updateEvalBar();
  updateMaterialBars();

  const hist = playState.fen_history || [playState.fen];
  const maxPly = hist.length - 1;
  const viewingLive = playViewPly === null || playViewPly >= maxPly;
  const shownFen = viewingLive ? playState.fen : hist[playViewPly];
  $("replay-indicator").textContent = viewingLive ? "Live" : `Move ${playViewPly}/${maxPly}`;

  $("play-turn").textContent = playState.is_over
    ? `GAME OVER · ${(playState.termination || "").toUpperCase()}`
    : playState.waiting_for_opponent
    ? "WAITING FOR OPPONENT"
    : playState.turn.toUpperCase() + " TO MOVE";
  $("play-opening").textContent =
    "Opening: " + (playState.opening && playState.opening.name ? playState.opening.name : "—");
  renderPlayMoveChips();

  if (playState.is_over) {
    const msg = playState.winner
      ? `${playState.winner.toUpperCase()} wins by ${playState.termination}!`
      : `Game drawn by ${playState.termination}.`;
    showFeedback("play-status", msg, true);
  } else if (playState.draw_offer_by) {
    showFeedback("play-status", `${playState.draw_offer_by.toUpperCase()} offered a draw — tap ½ Draw to accept.`, true);
  }

  renderBoard({
    boardId: "play-board",
    coordIds: ["play-files-top", "play-files-bottom", "play-ranks-left", "play-ranks-right"],
    fen: shownFen,
    flipped: playFlipped,
    selected: viewingLive ? playSelected : null,
    targets: viewingLive ? playTargets : [],
    lastMove: viewingLive ? playLastMove : null,
    checkedSquare: viewingLive ? playState.checked_king_square : null,
    arrowData: null,
    interactive: viewingLive && !playState.is_over,
    onSquareClick: clickPlaySquare,
    onDropMove: dropPlayMove,
  });
}

async function submitPlayMove(fromSq, toSq) {
  const matching = (playState.legal_moves_uci || [])
    .filter((u) => u.slice(0, 2) === fromSq && u.slice(2, 4) === toSq)
    .map(parseUci);
  if (!matching.length) {
    AUDIO.playError();
    return;
  }
  let promo = "";
  if (matching.some((m) => m.promotion)) promo = await askPromotion();
  try {
    const res = await api(`/api/games/${playGameId}/moves`, {
      method: "POST",
      body: JSON.stringify({ uci: fromSq + toSq + promo, player_token: playToken }),
    });
    playSoundForSan(res.played_san, res.state.termination === "checkmate");
    if (res.ai_reply) {
      setTimeout(
        () => playSoundForSan(res.ai_reply.san, res.state.termination === "checkmate"),
        180
      );
    }
    playLastMove = res.ai_reply
      ? [res.ai_reply.uci.slice(0, 2), res.ai_reply.uci.slice(2, 4)]
      : [fromSq, toSq];
    playSelected = null;
    playTargets = [];
    playViewPly = null;
    playState = res.state;
    renderPlay();
  } catch (e) {
    AUDIO.playError();
    showFeedback("play-status", e.message, false);
  }
}

async function dropPlayMove(fromSq, toSq) {
  if (!playState || playState.is_over) return;
  await submitPlayMove(fromSq, toSq);
}

async function clickPlaySquare(sq, piece) {
  if (!playState || playState.is_over) return;
  if (playSelected && playTargets.some((t) => t.to === sq)) {
    await submitPlayMove(playSelected, sq);
    return;
  }
  if (piece) {
    playSelected = sq;
    playTargets = (playState.legal_moves_uci || [])
      .filter((u) => u.slice(0, 2) === sq)
      .map(parseUci);
  } else {
    playSelected = null;
    playTargets = [];
  }
  renderPlay();
}

// Replay scrub buttons
$("replay-start").addEventListener("click", () => { if (playState) { playViewPly = 0; renderPlay(); } });
$("replay-prev").addEventListener("click", () => {
  if (!playState) return;
  const maxPly = (playState.fen_history || []).length - 1;
  const cur = playViewPly === null ? maxPly : playViewPly;
  playViewPly = Math.max(0, cur - 1);
  renderPlay();
});
$("replay-next").addEventListener("click", () => {
  if (!playState) return;
  const maxPly = (playState.fen_history || []).length - 1;
  const cur = playViewPly === null ? maxPly : playViewPly;
  playViewPly = cur + 1 >= maxPly ? null : cur + 1;
  renderPlay();
});
$("replay-live").addEventListener("click", () => { if (playState) { playViewPly = null; renderPlay(); } });

$("quick-match-btn").addEventListener("click", async () => {
  try {
    const res = await api("/api/matchmaking/enqueue", {
      method: "POST",
      body: JSON.stringify({ time_control: $("play-clock").value }),
    });
    playGameId = res.game_id;
    playToken = res.player_token;
    playState = res.state;
    playViewPly = null;
    playFlipped = res.assigned_color === "black";
    connectPlayWs(playGameId);
    showFeedback(
      "play-status",
      res.matched
        ? `Matched! Playing as ${res.assigned_color.toUpperCase()}.`
        : `Queued as WHITE. Waiting for opponent (or share code ${res.invite_code}).`,
      true
    );
    renderPlay();
  } catch (e) { showFeedback("play-status", e.message, false); }
});
$("play-new-btn").addEventListener("click", () => startPlayGame());
$("play-flip-btn").addEventListener("click", () => { playFlipped = !playFlipped; renderPlay(); });
$("play-undo-btn").addEventListener("click", async () => {
  try {
    const r = await api(`/api/games/${playGameId}/undo`, { method: "POST" });
    playState = r.state; playViewPly = null; playSelected = null; playTargets = []; renderPlay();
  } catch (e) { showFeedback("play-status", e.message, false); }
});
$("play-restart-btn").addEventListener("click", async () => {
  try {
    const r = await api(`/api/games/${playGameId}/restart`, { method: "POST" });
    playState = r.state; playViewPly = null; playLastMove = null;
    $("play-status").className = "feedback hidden"; renderPlay();
  } catch (e) { showFeedback("play-status", e.message, false); }
});
$("play-pause-btn").addEventListener("click", async () => {
  try {
    const r = await api(`/api/games/${playGameId}/pause`, { method: "POST" });
    playState = r.state;
    $("play-pause-btn").textContent = r.paused ? "▶ Resume" : "⏸ Pause";
    renderPlay();
  } catch (e) { showFeedback("play-status", e.message, false); }
});
$("play-resign-btn").addEventListener("click", async () => {
  const r = await api(`/api/games/${playGameId}/resign`, { method: "POST" });
  playState = r.state; playViewPly = null; renderPlay();
});
$("play-draw-btn").addEventListener("click", async () => {
  if (!playState) return;
  const action = playState.can_claim_draw ? "claim" : (playState.draw_offer_by ? "accept" : "offer");
  try {
    const r = await api(`/api/games/${playGameId}/draw`, {
      method: "POST",
      body: JSON.stringify({ action }),
    });
    playState = r.state;
    showFeedback("play-status", r.message, true);
    renderPlay();
  } catch (e) { showFeedback("play-status", e.message, false); }
});
$("play-copy-pgn").addEventListener("click", async () => {
  const r = await api(`/api/games/${playGameId}/pgn`);
  if (navigator.clipboard) await navigator.clipboard.writeText(r.pgn).catch(() => {});
  showFeedback("play-status", "PGN copied to clipboard.", true);
});
$("play-analyze-btn").addEventListener("click", async () => {
  const r = await api(`/api/games/${playGameId}/pgn`);
  $("analysis-pgn-input").value = r.pgn;
  $("coach-fen-input").value = playState.fen;
  switchTab("analysis");
  runGameAnalysis();
});
$("join-game-btn").addEventListener("click", async () => {
  const code = $("join-code-input").value.trim();
  if (!code) return;
  try {
    const res = await api(`/api/games/join/${code}`, { method: "POST" });
    playGameId = res.game_id;
    playToken = res.player_token;
    playState = res.state;
    playViewPly = null;
    playFlipped = res.assigned_color === "black";
    connectPlayWs(playGameId);
    showFeedback("play-status", `Joined online match as ${res.assigned_color.toUpperCase()}!`, true);
    renderPlay();
  } catch (e) { showFeedback("play-status", e.message, false); }
});
$("import-pgn-btn").addEventListener("click", async () => {
  const pgn = $("import-pgn-input").value.trim();
  if (!pgn) return;
  try {
    const res = await api("/api/games/import-pgn", {
      method: "POST",
      body: JSON.stringify({ pgn, mode: "local_pvp" }),
    });
    playGameId = res.game_id;
    playState = res.state;
    playViewPly = null;
    playFlipped = false;
    showFeedback("play-status", "PGN imported! Continue playing or scrub moves above.", true);
    renderPlay();
  } catch (e) { showFeedback("play-status", e.message, false); }
});

// =========================================================================
// TAB 2: ACADEMY LESSONS
// =========================================================================
let academySessionId = null;
let academyState = null;
let acSelected = null;
let acTargets = [];
let acLastMove = null;
let acHistory = [];
let acHintLevel = 1;
let acMode = "guided";
let acFlipped = false;

function academyArrow() {
  if (!academyState || acMode === "mastery") return null;
  const h = academyState.coach.active_hint;
  if (h && h.arrow_from && h.arrow_to) return { from: h.arrow_from, to: h.arrow_to };
  const a = academyState.coach.expected_move && academyState.coach.expected_move.arrow;
  return acMode === "guided" && a && a.from && a.to ? a : null;
}

function renderAcademy() {
  if (!academyState) return;
  renderBoard({
    boardId: "board",
    coordIds: ["files-top", "files-bottom", "ranks-left", "ranks-right"],
    fen: academyState.board.fen,
    flipped: acFlipped,
    selected: acSelected,
    targets: acTargets,
    lastMove: acLastMove,
    checkedSquare: null,
    arrowData: academyArrow(),
    onSquareClick: clickAcademySquare,
    onDropMove: dropAcademyMove,
  });
}

async function submitAcademyMove(fromSq, toSq) {
  const matching = (academyState.board.legal_moves_uci || [])
    .filter((u) => u.slice(0, 2) === fromSq && u.slice(2, 4) === toSq)
    .map(parseUci);
  if (!matching.length) { AUDIO.playError(); return; }
  let promo = "";
  if (matching.some((m) => m.promotion)) promo = await askPromotion();
  try {
    const res = await api(`/api/sessions/${academySessionId}/moves`, {
      method: "POST",
      body: JSON.stringify({ uci: fromSq + toSq + promo }),
    });
    if (res.move.applied) {
      playSoundForSan(res.move.actual_san, res.state.coach.kind === "complete");
      acLastMove = [fromSq, toSq];
      acHistory.push(res.move.actual_san || (fromSq + toSq + promo));
      if (res.auto_reply_san) acHistory.push(res.auto_reply_san);
      showFeedback("feedback", res.move.message || "Move accepted.", res.move.correct !== false);
    } else {
      AUDIO.playError();
      showFeedback("feedback", res.move.message || "Try again.", false);
    }
    acSelected = null;
    acTargets = [];
    applyAcademyState(res.state);
  } catch (e) { AUDIO.playError(); showFeedback("feedback", e.message, false); }
}

async function dropAcademyMove(fromSq, toSq) {
  if (academyState) await submitAcademyMove(fromSq, toSq);
}

async function clickAcademySquare(sq, piece) {
  if (!academyState) return;
  if (acSelected && acTargets.some((t) => t.to === sq)) {
    await submitAcademyMove(acSelected, sq);
    return;
  }
  if (piece) {
    acSelected = sq;
    acTargets = (academyState.board.legal_moves_uci || [])
      .filter((u) => u.slice(0, 2) === sq)
      .map(parseUci);
  } else {
    acSelected = null;
    acTargets = [];
  }
  renderAcademy();
}

function applyAcademyState(s) {
  academyState = s;
  acMode = s.mode || acMode;
  acHintLevel = s.coach.active_hint ? s.coach.active_hint.level : 0;
  renderAcademy();
  $("lesson-title").textContent = s.lesson_title || "KnightForge Lesson";
  $("turn-label").textContent = s.board.turn.toUpperCase() + " TO MOVE";
  $("opening-badge").textContent = "Opening: " + (s.opening && s.opening.name ? s.opening.name : "—");
  $("coach-text").textContent = s.coach.text || "Lesson line complete.";
  $("coach-explanation").textContent = s.coach.explanation || "";
  $("hint-level").textContent = s.coach.active_hint
    ? `LEVEL ${acHintLevel} / 4`
    : acMode === "mastery" ? "HINTS HIDDEN" : "HINT NOT REVEALED";
  $("hint-text").textContent = s.coach.active_hint ? s.coach.active_hint.text : "Request a hint if needed.";
  $("hint-btn").disabled = acMode === "mastery" || !s.coach.hints_available || acHintLevel >= 4;
  $("move-count").textContent = `${acHistory.length} half-moves`;
  $("moves").className = acHistory.length ? "move-list" : "moves-empty";
  $("moves").textContent = formatMoves(acHistory);
  if ($("voice-toggle").checked) speak(s.coach.voice_script || s.coach.text);
}

async function loadLessonsAndStart() {
  const cat = $("academy-category").value;
  const data = await api("/api/lessons" + (cat ? `?category=${cat}` : ""));
  const sel = $("lesson-select");
  sel.innerHTML = "";
  data.lessons.forEach((l) => {
    const opt = document.createElement("option");
    opt.value = l.lesson_id;
    opt.textContent = `${l.completed ? "✓ " : ""}L${l.level} [${l.category}] ${l.title}`;
    sel.append(opt);
  });
  await createAcademySession();
}

async function createAcademySession() {
  acMode = $("mode-select").value;
  const lessonId = $("lesson-select").value || "open-game-first-five";
  const r = await api("/api/sessions", {
    method: "POST",
    body: JSON.stringify({ mode: acMode, lesson_id: lessonId }),
  });
  academySessionId = r.session_id;
  acHistory = [];
  acLastMove = null;
  acSelected = null;
  acTargets = [];
  acFlipped = r.state.learner_color === "black";
  $("feedback").className = "feedback hidden";
  applyAcademyState(r.state);
}

$("academy-category").addEventListener("change", loadLessonsAndStart);
$("lesson-select").addEventListener("change", createAcademySession);
$("mode-select").addEventListener("change", createAcademySession);
$("hint-btn").addEventListener("click", async () => {
  const r = await api(`/api/sessions/${academySessionId}/hints`, {
    method: "POST",
    body: JSON.stringify({ level: Math.min(4, acHintLevel + 1) }),
  });
  applyAcademyState(r.state);
});
$("undo-btn").addEventListener("click", async () => {
  try {
    const r = await api(`/api/sessions/${academySessionId}/undo`, { method: "POST" });
    acHistory.pop(); acLastMove = null; applyAcademyState(r.state);
  } catch (e) { showFeedback("feedback", e.message, false); }
});
$("restart-btn").addEventListener("click", async () => {
  const r = await api(`/api/sessions/${academySessionId}/restart`, { method: "POST" });
  acHistory = []; acLastMove = null; $("feedback").className = "feedback hidden"; applyAcademyState(r.state);
});
$("flip-btn").addEventListener("click", () => { acFlipped = !acFlipped; renderAcademy(); });
$("continue-free-btn").addEventListener("click", async () => {
  if (!academyState) return;
  switchTab("play");
  await startPlayGame(academyState.board.fen);
  showFeedback("play-status", "Continuing your lesson position as a full unrestricted game!", true);
});
$("speak-btn").addEventListener("click", () => academyState && speak(academyState.coach.voice_script || academyState.coach.text));

// =========================================================================
// TAB 3: INTERACTIVE OPENING & GAMBIT TREE EXPLORER
// =========================================================================
let openingsLoaded = false;
let activeOpeningTree = null;
let opPath = []; // array of enriched node objects stepped through
let opFlipped = false;

async function loadOpenings(query = "") {
  openingsLoaded = true;
  const [tax, repo] = await Promise.all([
    api("/api/openings/taxonomy"),
    api("/api/openings/repository" + (query ? `?q=${encodeURIComponent(query)}` : "")),
  ]);
  if (tax.coverage) {
    $("coverage-summary").innerHTML = `
      <span class="tag">${tax.coverage.stored_tree_count} Trees</span>
      <span class="tag">${tax.coverage.total_move_nodes} Legal Nodes</span>
      <span class="tag">${tax.coverage.matched_system_ids.length}/${tax.coverage.taxonomy_system_count} Systems</span>
    `;
  }
  const box = $("repo-openings-list");
  box.innerHTML = "";
  repo.openings.forEach((o) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "list-card" + (activeOpeningTree && activeOpeningTree.opening_id === o.opening_id ? " active-card" : "");
    btn.innerHTML = `<div><strong>${o.name} (${o.eco || "—"})</strong><small>${o.mainline_san.join(" ")}</small></div><span class="tag">${o.branch_count} nodes</span>`;
    btn.addEventListener("click", () => openInteractiveTree(o.opening_id));
    box.append(btn);
  });
  if (!activeOpeningTree && repo.openings.length) {
    openInteractiveTree(repo.openings[0].opening_id);
  }
}

async function openInteractiveTree(openingId) {
  const [treeData, varData] = await Promise.all([
    api(`/api/openings/${openingId}/tree`),
    api(`/api/openings/${openingId}/variations`),
  ]);
  activeOpeningTree = treeData;
  opPath = [];
  opFlipped = activeOpeningTree.side === "black";
  $("op-explorer-title").textContent = activeOpeningTree.name;
  $("op-explorer-eco").textContent = `ECO ${activeOpeningTree.eco || "—"}`;
  const sel = $("op-variation-select");
  sel.innerHTML = `<option value="">Full Repertoire Tree (All Branches)</option>`;
  (varData.variations || []).forEach((v) => {
    const opt = document.createElement("option");
    opt.value = v.variation_id;
    opt.textContent = `${v.label} (${v.moves_san.slice(0, 6).join(" ")})`;
    sel.append(opt);
  });
  renderOpeningExplorer();
}

function renderOpeningExplorer() {
  if (!activeOpeningTree) return;
  const current = opPath.length ? opPath[opPath.length - 1] : null;
  const fen = current ? current.fen : activeOpeningTree.starting_fen;
  const children = current ? current.children : activeOpeningTree.roots;
  const lastMv = current ? [current.move_uci.slice(0, 2), current.move_uci.slice(2, 4)] : null;
  const nextArrow = children && children.length
    ? { from: children[0].move_uci.slice(0, 2), to: children[0].move_uci.slice(2, 4) }
    : null;

  renderBoard({
    boardId: "opening-board",
    coordIds: ["op-files-top", "op-files-bottom", "op-ranks-left", "op-ranks-right"],
    fen,
    flipped: opFlipped,
    selected: null,
    targets: [],
    lastMove: lastMv,
    checkedSquare: null,
    arrowData: nextArrow,
    interactive: false,
  });

  const branchBox = $("op-branches");
  branchBox.innerHTML = "";
  if (children && children.length) {
    children.forEach((child) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "branch-btn";
      btn.textContent = child.san + (child.label ? ` · ${child.label}` : "");
      btn.addEventListener("click", () => {
        opPath.push(child);
        playSoundForSan(child.san);
        renderOpeningExplorer();
      });
      branchBox.append(btn);
    });
  } else {
    branchBox.innerHTML = `<span class="tag">End of curated branch — click "Play From Here" to continue vs AI!</span>`;
  }

  const lineText = opPath.length ? formatMoves(opPath.map((n) => n.san)) : "Starting position";
  $("op-node-explanation").textContent =
    (current && current.explanation) || `${lineText} — click a branch above to step through this opening.`;
  const plans = [];
  if (current && current.white_plan) plans.push("White plan: " + current.white_plan);
  if (current && current.black_plan) plans.push("Black plan: " + current.black_plan);
  $("op-node-plans").textContent = plans.join("  |  ");
}

$("op-back-btn").addEventListener("click", () => { if (opPath.length) { opPath.pop(); renderOpeningExplorer(); } });
$("op-reset-btn").addEventListener("click", () => { opPath = []; renderOpeningExplorer(); });
$("op-flip-btn").addEventListener("click", () => { opFlipped = !opFlipped; renderOpeningExplorer(); });
$("op-play-here-btn").addEventListener("click", async () => {
  if (!activeOpeningTree) return;
  const fen = opPath.length ? opPath[opPath.length - 1].fen : activeOpeningTree.starting_fen;
  switchTab("play");
  await startPlayGame(fen);
  showFeedback("play-status", `Practicing ${activeOpeningTree.name} from your selected branch!`, true);
});
$("opening-search-input").addEventListener("input", (e) => loadOpenings(e.target.value));

async function runRecognize() {
  const raw = $("recognize-input").value.trim();
  if (!raw) return;
  const isFen = raw.split(" ").length >= 4 && raw.includes("/");
  try {
    const res = await api("/api/openings/recognize", {
      method: "POST",
      body: JSON.stringify(isFen ? { fen: raw } : { moves: raw }),
    });
    if (res.variation_matches.length) {
      const m = res.variation_matches[0];
      $("recognize-output").innerHTML =
        `<strong>${m.name} (${m.eco || "—"})</strong><br>` +
        `Variations: ${m.variation_labels.join(" → ") || "Mainline"}<br>` +
        `Line: ${m.matched_line_san.join(" ")} (ply ${m.matched_ply})`;
    } else if (res.anchor_matches.length) {
      const m = res.anchor_matches[0];
      $("recognize-output").innerHTML = `<strong>${m.name} (${m.eco || "—"})</strong> — Anchor at ply ${m.matched_ply}.`;
    } else {
      $("recognize-output").textContent = "Valid position, no reviewed opening tree matched.";
    }
  } catch (e) { $("recognize-output").textContent = "Error: " + e.message; }
}
$("recognize-btn").addEventListener("click", runRecognize);

// =========================================================================
// TAB 4: TACTICS TRAINER
// =========================================================================
let puzzleListCache = [];
let dailyPuzzleId = null;
let puzzleIdx = 0;
let puzzleSessionId = null;
let puzzleState = null;
let puzSelected = null;
let puzTargets = [];
let puzArrow = null;
let puzHintLvl = 0;
let puzSeconds = 0;
let puzTimer = null;

let loadPuzzles = async function() {
  const diff = $("puzzle-diff-filter").value;
  const data = await api("/api/puzzles" + (diff ? `?difficulty=${diff}` : ""));
  puzzleListCache = data.puzzles;
  dailyPuzzleId = data.daily_puzzle_id;
  renderPuzzleList();
  if (puzzleListCache.length) startPuzzle(0);
}

function renderPuzzleList() {
  const box = $("puzzle-list");
  box.innerHTML = "";
  puzzleListCache.forEach((p, idx) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "list-card" + (idx === puzzleIdx ? " active-card" : "");
    btn.innerHTML = `<div><strong>${p.solved ? "✓ " : ""}${p.title}</strong><small>${p.themes.join(" · ")}</small></div><span class="tag">${p.rating}</span>`;
    btn.addEventListener("click", () => startPuzzle(idx));
    box.append(btn);
  });
}

async function startPuzzle(idx) {
  puzzleIdx = idx;
  const p = puzzleListCache[idx];
  const res = await api(`/api/puzzles/${p.puzzle_id}/sessions`, { method: "POST" });
  puzzleSessionId = res.session_id;
  puzzleState = res.state;
  puzSelected = null;
  puzTargets = [];
  puzArrow = null;
  puzHintLvl = 0;
  puzSeconds = 0;
  if (puzTimer) clearInterval(puzTimer);
  puzTimer = setInterval(() => {
    if (puzzleState && !puzzleState.solved) {
      puzSeconds++;
      $("puzzle-timer").textContent = formatClock(puzSeconds);
    }
  }, 1000);
  $("puzzle-timer").textContent = "00:00";
  $("puzzle-feedback").className = "feedback hidden";
  renderPuzzleList();
  renderPuzzleView();
}

function renderPuzzleView() {
  if (!puzzleState) return;
  $("puzzle-title").textContent = `${puzzleState.title} (${puzzleState.rating})`;
  $("puzzle-turn").textContent = puzzleState.turn.toUpperCase() + " TO MOVE";
  $("puzzle-themes").textContent = `Themes: ${puzzleState.themes.join(", ")} · Difficulty: ${puzzleState.difficulty}`;
  $("puzzle-meta").textContent = `Mistakes: ${puzzleState.mistakes} · Hints: ${puzzleState.hints_used}`;
  $("puzzle-prompt").textContent = puzzleState.solved
    ? puzzleState.explanation
    : `Find the winning tactic for ${puzzleState.solver_color}.`;

  renderBoard({
    boardId: "puzzle-board",
    coordIds: ["puz-files-top", "puz-files-bottom", "puz-ranks-left", "puz-ranks-right"],
    fen: puzzleState.fen,
    flipped: puzzleState.solver_color === "black",
    selected: puzSelected,
    targets: puzTargets,
    lastMove: null,
    checkedSquare: null,
    arrowData: puzArrow,
    interactive: !puzzleState.solved,
    onSquareClick: clickPuzzleSquare,
    onDropMove: dropPuzzleMove,
  });
}

async function submitPuzzleMove(fromSq, toSq) {
  const matching = (puzzleState.legal_moves_uci || [])
    .filter((u) => u.slice(0, 2) === fromSq && u.slice(2, 4) === toSq)
    .map(parseUci);
  if (!matching.length) { AUDIO.playError(); return; }
  let promo = "";
  if (matching.some((m) => m.promotion)) promo = await askPromotion();
  const res = await api(`/api/puzzles/sessions/${puzzleSessionId}/moves`, {
    method: "POST",
    body: JSON.stringify({ uci: fromSq + toSq + promo }),
  });
  puzSelected = null;
  puzTargets = [];
  puzArrow = null;
  puzzleState = res.state;
  if (res.outcome.solved) AUDIO.playVictory();
  else if (res.outcome.correct) playSoundForSan(res.outcome.played_san);
  else AUDIO.playError();

  const ratingNote = res.puzzle_rating ? ` (Puzzle Elo: ${res.puzzle_rating})` : "";
  showFeedback("puzzle-feedback", res.outcome.message + ratingNote, res.outcome.correct);
  if (res.outcome.solved) {
    puzzleListCache[puzzleIdx].solved = true;
    renderPuzzleList();
  }
  renderPuzzleView();
}

async function dropPuzzleMove(fromSq, toSq) {
  if (puzzleState && !puzzleState.solved) await submitPuzzleMove(fromSq, toSq);
}

let clickPuzzleSquare = async function(sq, piece) {
  if (!puzzleState || puzzleState.solved) return;
  if (puzSelected && puzTargets.some((t) => t.to === sq)) {
    await submitPuzzleMove(puzSelected, sq);
    return;
  }
  if (piece) {
    puzSelected = sq;
    puzTargets = (puzzleState.legal_moves_uci || [])
      .filter((u) => u.slice(0, 2) === sq)
      .map(parseUci);
  } else {
    puzSelected = null;
    puzTargets = [];
  }
  renderPuzzleView();
}

$("puzzle-diff-filter").addEventListener("change", loadPuzzles);
$("puzzle-hint-btn").addEventListener("click", async () => {
  if (!puzzleSessionId || !puzzleState || puzzleState.solved) return;
  puzHintLvl = Math.min(3, puzHintLvl + 1);
  const res = await api(`/api/puzzles/sessions/${puzzleSessionId}/hint`, {
    method: "POST",
    body: JSON.stringify({ level: puzHintLvl }),
  });
  puzzleState = res.state;
  puzArrow = res.hint.arrow_from && res.hint.arrow_to ? { from: res.hint.arrow_from, to: res.hint.arrow_to } : null;
  showFeedback("puzzle-feedback", res.hint.text, true);
  renderPuzzleView();
});
$("puzzle-daily-btn").addEventListener("click", () => {
  const idx = puzzleListCache.findIndex((p) => p.puzzle_id === dailyPuzzleId);
  if (idx >= 0) startPuzzle(idx);
});
$("puzzle-random-btn").addEventListener("click", () => {
  if (puzzleListCache.length) startPuzzle(Math.floor(Math.random() * puzzleListCache.length));
});
$("puzzle-next-btn").addEventListener("click", () => {
  if (puzzleListCache.length) startPuzzle((puzzleIdx + 1) % puzzleListCache.length);
});

// =========================================================================
// TAB 5: GAME ANALYSIS & GROUNDED AI COACH
// =========================================================================
async function runGameAnalysis() {
  const pgn = $("analysis-pgn-input").value.trim();
  if (!pgn) return;
  $("analysis-disclaimer").textContent = "Analyzing moves…";
  try {
    const res = await api("/api/analysis/game", {
      method: "POST",
      body: JSON.stringify({ pgn }),
    });
    const c = res.classification_counts;
    $("analysis-summary").innerHTML = `
      <div class="stat-card"><span class="eyebrow">WHITE ACCURACY</span><strong>${res.white_accuracy}%</strong></div>
      <div class="stat-card"><span class="eyebrow">BLACK ACCURACY</span><strong>${res.black_accuracy}%</strong></div>
      <div class="stat-card"><span class="eyebrow">BEST / GOOD</span><strong>${c.best + c.excellent + c.good}</strong></div>
      <div class="stat-card"><span class="eyebrow">MISTAKES / BLUNDERS</span><strong>${c.mistake + c.blunder + c.missed_opportunity}</strong></div>
    `;
    $("analysis-disclaimer").textContent = res.disclaimer + (res.opening ? ` · Opening: ${res.opening.name}` : "");
    const pts = res.eval_graph;
    if (pts.length > 1) {
      $("eval-graph-wrap").classList.remove("hidden");
      const poly = pts.map((pt, i) => {
        const x = (i / (pts.length - 1)) * 600;
        const clamped = Math.max(-800, Math.min(800, pt.eval_cp_white));
        const y = 70 - (clamped / 800) * 60;
        return `${x.toFixed(1)},${y.toFixed(1)}`;
      }).join(" ");
      $("eval-graph-svg").innerHTML =
        `<line x1="0" y1="70" x2="600" y2="70" stroke="#5a6c60" stroke-dasharray="4 4"/>` +
        `<polyline fill="none" stroke="#b7e36a" stroke-width="2.5" points="${poly}"/>`;
    }
    $("analysis-moves-list").innerHTML = res.moves.map((m) => {
      const isBad = ["inaccuracy", "mistake", "blunder", "missed_opportunity"].includes(m.classification);
      return `<div class="list-card"><div><strong>${m.move_number}. ${m.side === "black" ? "... " : ""}${m.played_san}</strong><small>${m.comment}</small></div><span class="tag ${isBad ? "bad" : ""}">${m.classification}</span></div>`;
    }).join("");
  } catch (e) { $("analysis-disclaimer").textContent = "Error: " + e.message; }
}
$("run-analysis-btn").addEventListener("click", runGameAnalysis);

$("ask-coach-btn").addEventListener("click", async () => {
  try {
    const res = await api("/api/coach/ask", {
      method: "POST",
      body: JSON.stringify({
        fen: $("coach-fen-input").value.trim(),
        question: $("coach-question-input").value.trim(),
        player_level: $("coach-level").value,
      }),
    });
    const candText = res.candidates.map((c) => `${c.san} (${((c.score_cp_white || 0) / 100).toFixed(2)})`).join(" · ");
    $("coach-answer-box").innerHTML =
      `<strong>Coach (${res.engine_source}):</strong><br>${res.answer}<br><br>` +
      `<small>Candidates: ${candText || "none"}</small><br>` +
      res.insights.map((line) => `<div>• ${line}</div>`).join("");
  } catch (e) { $("coach-answer-box").textContent = "Error: " + e.message; }
});

// =========================================================================
// TAB 6: USER PROFILE, ACCOUNTS & PROGRESS
// =========================================================================
async function loadProfile() {
  const p = await api("/api/progress");
  const prof = p.profile;
  $("profile-heading").textContent = `${prof.username} · Streak: ${prof.daily_streak}d`;
  $("header-user").textContent = `${prof.username} · Chess ${prof.chess_rating} · Puzzles ${prof.puzzle_rating}`;
  $("profile-notes").value = prof.notes || "";
  $("progress-stats").innerHTML = `
    <div class="stat-card"><span class="eyebrow">CHESS ELO</span><strong>${prof.chess_rating}</strong></div>
    <div class="stat-card"><span class="eyebrow">PUZZLE ELO</span><strong>${prof.puzzle_rating}</strong></div>
    <div class="stat-card"><span class="eyebrow">LESSONS</span><strong>${p.lessons_completed}/${p.lessons_total}</strong></div>
    <div class="stat-card"><span class="eyebrow">PUZZLES</span><strong>${p.puzzles_solved}/${p.puzzles_total}</strong></div>
  `;
  $("achievements-box").innerHTML = p.achievements.length
    ? p.achievements.map((a) => `<span class="tag">★ ${a}</span>`).join("")
    : `<span class="tag">Complete a lesson or puzzle to earn achievements</span>`;
  const rec = p.recommended_next;
  $("progress-next").innerHTML = `<span class="eyebrow">RECOMMENDED NEXT STEP</span><p>${rec.reason}</p><p class="explanation">Target: ${rec.kind.toUpperCase()} · ${rec.target_id}</p>`;
  $("progress-games").innerHTML = p.recent_games.length
    ? p.recent_games.map((g) =>
        `<button type="button" class="list-card" data-pgn="${g.pgn.replace(/"/g, "&quot;")}">
          <div><strong>${g.result.toUpperCase()} · ${g.mode} (${g.difficulty})</strong><small>${g.termination} · ${g.plies} plies · Tap to Analyze</small></div>
          <span class="tag">${g.created_at.slice(0, 10)}</span>
        </button>`
      ).join("")
    : `<div class="moves-empty">No completed games saved yet.</div>`;
  document.querySelectorAll("#progress-games .list-card").forEach((card) => {
    card.addEventListener("click", () => {
      $("analysis-pgn-input").value = card.dataset.pgn;
      switchTab("analysis");
      runGameAnalysis();
    });
  });
}

async function handleAuth(endpoint) {
  try {
    const res = await api(endpoint, {
      method: "POST",
      body: JSON.stringify({
        username: $("auth-username").value.trim(),
        password: $("auth-password").value,
      }),
    });
    authToken = res.token;
    authUsername = res.username;
    localStorage.setItem("kf_token", authToken);
    localStorage.setItem("kf_user", authUsername);
    showFeedback("auth-status", `Signed in as ${authUsername}!`, true);
    loadProfile();
  } catch (e) { showFeedback("auth-status", e.message, false); }
}
$("auth-login-btn").addEventListener("click", () => handleAuth("/api/auth/login"));
$("auth-register-btn").addEventListener("click", () => handleAuth("/api/auth/register"));
$("auth-logout-btn").addEventListener("click", () => {
  authToken = ""; authUsername = "guest";
  localStorage.removeItem("kf_token"); localStorage.removeItem("kf_user");
  showFeedback("auth-status", "Logged out (switched to Guest profile).", true);
  loadProfile();
});
$("save-notes-btn").addEventListener("click", async () => {
  await api("/api/auth/notes", {
    method: "POST",
    body: JSON.stringify({ notes: $("profile-notes").value }),
  });
  showFeedback("auth-status", "Personal study notes saved to database.", true);
});
$("refresh-progress-btn").addEventListener("click", loadProfile);

// =========================================================================
// BOOTSTRAP
// =========================================================================
async function boot() {
  try {
    const h = await api("/api/health");
    $("connection-label").textContent = h.stockfish_available ? "STOCKFISH READY" : "ENGINE ACTIVE";
    await Promise.all([startPlayGame(), loadProfile()]);
  } catch (e) {
    $("connection-label").textContent = "SERVER OFFLINE";
  }
}
boot();


// =========================================================================
// V4.0 ULTIMATE ADDONS: VARIATION TRAINER, 1,079+ PUZZLES, VISION & DRILLS
// =========================================================================
$("op-train-btn").addEventListener("click", async () => {
  if (!activeOpeningTree) return;
  const variationId = $("op-variation-select").value || null;
  const learnerColor = activeOpeningTree.side === "black" ? "black" : "white";
  try {
    const r = await api(`/api/openings/${activeOpeningTree.opening_id}/train`, {
      method: "POST",
      body: JSON.stringify({
        variation_id: variationId,
        mode: "guided",
        learner_color: learnerColor,
        auto_reply: true,
      }),
    });
    academySessionId = r.session_id;
    acHistory = [];
    acLastMove = null;
    acSelected = null;
    acTargets = [];
    acFlipped = learnerColor === "black";
    $("feedback").className = "feedback hidden";
    switchTab("academy");
    applyAcademyState(r.state);
    showFeedback(
      "feedback",
      `Training ${r.state.lesson_title}! Follow the green arrow — opponent replies automatically.`,
      true
    );
  } catch (e) {
    showFeedback("feedback", e.message, false);
  }
});

// Endgame Drill Lab Loader
async function loadEndgameDrills() {
  try {
    const data = await api("/api/endgames/drills");
    const sel = $("endgame-drill-select");
    sel.innerHTML = "";
    data.drills.forEach((d) => {
      const opt = document.createElement("option");
      opt.value = d.fen;
      opt.dataset.goal = d.goal;
      opt.textContent = `${d.title} (${d.difficulty})`;
      sel.append(opt);
    });
  } catch (_) {}
}
$("start-drill-btn").addEventListener("click", async () => {
  const sel = $("endgame-drill-select");
  if (!sel.value) return;
  const goal = sel.options[sel.selectedIndex].dataset.goal || "";
  await startPlayGame(sel.value);
  showFeedback("play-status", "Endgame Drill: " + goal, true);
});

// Upgraded 1,079+ Puzzle Bank Pagination & Filters
let puzzleOffset = 0;
let puzzleTotalMatching = 0;
let puzzleMistakesOnly = false;

async function loadPuzzlesPage(append = false) {
  if (!append) puzzleOffset = 0;
  const diff = $("puzzle-diff-filter").value;
  const theme = $("puzzle-theme-filter").value;
  const params = new URLSearchParams({ limit: "30", offset: String(puzzleOffset) });
  if (diff) params.set("difficulty", diff);
  if (theme) params.set("theme", theme);
  if (puzzleMistakesOnly) params.set("mistakes_only", "true");
  const data = await api("/api/puzzles?" + params.toString());
  dailyPuzzleId = data.daily_puzzle_id;
  puzzleTotalMatching = data.total_matching || data.puzzles.length;
  $("puzzle-bank-count").textContent =
    `${data.total_catalog || puzzleTotalMatching} VERIFIED PUZZLES · SHOWING ${puzzleTotalMatching} MATCHING`;
  puzzleListCache = append ? [...puzzleListCache, ...data.puzzles] : data.puzzles;
  puzzleOffset = puzzleListCache.length;
  $("puzzle-more-btn").classList.toggle("hidden", puzzleOffset >= puzzleTotalMatching);
  renderPuzzleList();
  if (!append && puzzleListCache.length) startPuzzle(0);
}

$("puzzle-theme-filter").addEventListener("change", () => loadPuzzlesPage(false));
$("puzzle-more-btn").addEventListener("click", () => loadPuzzlesPage(true));
$("puzzle-mistakes-btn").addEventListener("click", () => {
  puzzleMistakesOnly = !puzzleMistakesOnly;
  $("puzzle-mistakes-btn").classList.toggle("hint-button", puzzleMistakesOnly);
  loadPuzzlesPage(false);
});

// Override random button to draw across ALL 1,079+ puzzles on the server!
$("puzzle-random-btn").addEventListener("click", async () => {
  const diff = $("puzzle-diff-filter").value;
  const theme = $("puzzle-theme-filter").value;
  const params = new URLSearchParams();
  if (diff) params.set("difficulty", diff);
  if (theme) params.set("theme", theme);
  const res = await api("/api/puzzles/random/session?" + params.toString(), { method: "POST" });
  puzzleSessionId = res.session_id;
  puzzleState = res.state;
  puzSelected = null; puzTargets = []; puzArrow = null; puzHintLvl = 0; puzSeconds = 0;
  $("puzzle-feedback").className = "feedback hidden";
  renderPuzzleView();
});

// Board Vision 30-Second Coordinate Speed Drill
let visionActive = false;
let visionTarget = "";
let visionScore = 0;
let visionLeft = 30;
let visionTimer = null;

function pickVisionSquare() {
  visionTarget = FILES[Math.floor(Math.random() * 8)] + (1 + Math.floor(Math.random() * 8));
  $("vision-prompt").textContent = `Tap square: ${visionTarget.toUpperCase()}`;
}

function updateVisionHud() {
  const best = Number(localStorage.getItem("kf_vision_best") || "0");
  $("vision-score").textContent = `Score: ${visionScore} · Best: ${best} · Time: ${visionLeft}s`;
}

$("vision-drill-btn").addEventListener("click", () => {
  visionActive = !visionActive;
  $("vision-box").classList.toggle("hidden", !visionActive);
  if (visionTimer) clearInterval(visionTimer);
  if (!visionActive) return;
  visionScore = 0;
  visionLeft = 30;
  pickVisionSquare();
  updateVisionHud();
  visionTimer = setInterval(() => {
    visionLeft--;
    if (visionLeft <= 0) {
      clearInterval(visionTimer);
      visionActive = false;
      const best = Math.max(visionScore, Number(localStorage.getItem("kf_vision_best") || "0"));
      localStorage.setItem("kf_vision_best", String(best));
      $("vision-prompt").textContent = `Time's up! Final score: ${visionScore} (Best: ${best})`;
      AUDIO.playVictory();
    }
    updateVisionHud();
  }, 1000);
});

const _origClickPuzzleSquare = clickPuzzleSquare;
clickPuzzleSquare = async function (sq, piece) {
  if (visionActive) {
    if (sq === visionTarget) {
      visionScore++;
      AUDIO.playMove();
      pickVisionSquare();
    } else {
      AUDIO.playError();
    }
    updateVisionHud();
    return;
  }
  return _origClickPuzzleSquare(sq, piece);
};

// Hook loadPuzzles to use paginated loader
loadPuzzles = () => loadPuzzlesPage(false);

// Register PWA Service Worker for Android "Install App" support
if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("/sw.js").catch(() => {});
}
loadEndgameDrills();
