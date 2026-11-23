const PIECES={K:"♔",Q:"♕",R:"♖",B:"♗",N:"♘",P:"♙",k:"♚",q:"♛",r:"♜",b:"♝",n:"♞",p:"♟"},FILES="abcdefgh";
let sessionId=null,state=null,selected=null,targets=[],lastMove=null,history=[],hintLevel=1,mode="guided",busy=false;
const $=id=>document.getElementById(id);
async function api(path,options={}){const r=await fetch(path,{headers:{"Content-Type":"application/json"},...options});const b=await r.json().catch(()=>({}));if(!r.ok)throw new Error(b.detail||"Request failed");return b;}
function parseFen(fen){const rows=fen.split(" ")[0].split("/"),out=[];rows.forEach((row,r)=>{let f=0;for(const c of row){if(/[1-8]/.test(c)){for(let n=0;n<+c;n++)out.push({sq:FILES[f++]+(8-r),p:null});}else out.push({sq:FILES[f++]+(8-r),p:c});}});return out;}
function parseUci(u){return {from:u.slice(0,2),to:u.slice(2,4),promotion:u[4]||null};}
function legalFrom(sq){return (state.board.legal_moves_uci||[]).filter(u=>u.slice(0,2)===sq).map(parseUci);}
function arrow(){if(mode==="mastery")return null;const h=state.coach.active_hint;if(h&&h.arrow_from&&h.arrow_to)return {from:h.arrow_from,to:h.arrow_to};const a=state.coach.expected_move&&state.coach.expected_move.arrow;return mode==="guided"&&a&&a.from&&a.to?a:null;}
function render(){if(!state)return;const root=$("board");root.innerHTML="";const cells=parseFen(state.board.fen),a=arrow();for(let rank=8;rank>=1;rank--)for(let file=0;file<8;file++){const sq=FILES[file]+rank,entry=cells.find(x=>x.sq===sq),b=document.createElement("button");b.type="button";b.className="square "+(((file+rank)%2===0)?"light":"dark");if(sq===selected)b.classList.add("selected");if(lastMove&&lastMove.includes(sq))b.classList.add("last-move");const target=targets.find(x=>x.to===sq);if(target)b.classList.add(entry&&entry.p?"capture":"legal");if(entry&&entry.p){const span=document.createElement("span");span.className="piece "+(entry.p===entry.p.toUpperCase()?"white":"black");span.textContent=PIECES[entry.p];b.append(span);}b.setAttribute("aria-label",sq+(entry&&entry.p?" "+entry.p:" empty"));b.addEventListener("click",()=>clickSquare(sq,entry&&entry.p));root.append(b);}
if(a){const pos=s=>({x:(FILES.indexOf(s[0])+.5)*12.5,y:(8-Number(s[1])+.5)*12.5}),p=pos(a.from),q=pos(a.to),svg=document.createElementNS("http://www.w3.org/2000/svg","svg");svg.setAttribute("viewBox","0 0 100 100");svg.setAttribute("class","board-arrow");svg.innerHTML='<defs><marker id="arrowhead" markerWidth="5" markerHeight="5" refX="3.8" refY="2.5" orient="auto"><path d="M0 0 L5 2.5 L0 5Z" fill="#d7f18a"/></marker></defs>';const line=document.createElementNS("http://www.w3.org/2000/svg","line");line.setAttribute("x1",p.x);line.setAttribute("y1",p.y);line.setAttribute("x2",q.x);line.setAttribute("y2",q.y);svg.append(line);root.append(svg);}}
function clickSquare(sq,piece){if(busy)return;if(selected){const move=targets.find(x=>x.to===sq);if(move){sendMove(selected+sq+(move.promotion||""));return;}if(selected===sq){selected=null;targets=[];render();return;}}if(piece){selected=sq;targets=legalFrom(sq);render();}else{selected=null;targets=[];render();}}
async function sendMove(uci){setBusy(true);try{const result=await api("/api/sessions/"+sessionId+"/moves",{method:"POST",body:JSON.stringify({uci})});if(result.move.applied){lastMove=[uci.slice(0,2),uci.slice(2,4)];history.push(result.move.actual_san||uci);feedback(result.move.message||"Move accepted.",result.move.correct!==false);}else feedback(result.move.message||"Try again.",false);selected=null;targets=[];apply(result.state);}catch(e){feedback(e.message,false);}finally{setBusy(false);}}
function apply(s){state=s;mode=s.mode||mode;hintLevel=s.coach.active_hint?s.coach.active_hint.level:0;render();$("turn-label").textContent=s.board.turn.toUpperCase()+" TO MOVE";$("coach-text").textContent=s.coach.text||"Lesson line complete.";$("coach-explanation").textContent=s.coach.explanation||"";$("hint-level").textContent=s.coach.active_hint?"LEVEL "+hintLevel+" / 4":(mode==="mastery"?"HINTS HIDDEN":"HINT NOT REVEALED");$("hint-text").textContent=s.coach.active_hint?s.coach.active_hint.text:"Choose a mode or request a hint."; $("hint-btn").disabled=mode==="mastery"||!s.coach.hints_available||hintLevel>=4;$("hint-btn").textContent=mode==="mastery"?"Hints disabled":hintLevel>=4?"All hints revealed":(hintLevel===0?"Reveal first hint":"Reveal next hint");$("engine-status").textContent=s.engine.analysis_error?"Stockfish unavailable — legal lesson play remains active.":s.engine.recommendation?"Position analysed by the configured engine.":"No Stockfish configured — engine recommendations are off.";$("move-count").textContent=history.length+" half-moves";$("moves").className=history.length?"move-list":"moves-empty";$("moves").textContent=history.length?history.map((m,i)=>Math.floor(i/2)+1+(i%2?". ":"... ")+m).join("   "):"Your moves will appear here.";if(s.coach.kind==="complete"||s.coach.kind==="free_play")$("lesson-title").textContent="Lesson line complete";if($("voice-toggle").checked)speak(s.coach.voice_script||s.coach.text);}
function feedback(msg,good){const e=$("feedback");e.textContent=msg;e.className="feedback"+(good?"":" bad");}
function setBusy(v){busy=v;document.querySelectorAll(".square").forEach(b=>b.disabled=v);}
function speak(t){if(!window.speechSynthesis||!t)return;window.speechSynthesis.cancel();const u=new SpeechSynthesisUtterance(t);u.rate=.92;window.speechSynthesis.speak(u);}
async function createSession(){try{$("connection-label").textContent="Connecting";mode=$("mode-select").value;const r=await api("/api/sessions",{method:"POST",body:JSON.stringify({mode})});sessionId=r.session_id;history=[];lastMove=null;selected=null;targets=[];$("connection-label").textContent="SESSION ACTIVE";$("lesson-title").textContent="Open Game · First Five Moves";$("feedback").className="feedback hidden";apply(r.state);const h=await api("/api/health");if(!h.stockfish_available)$("engine-status").textContent="Stockfish not configured — board and guided lesson are playable.";}catch(e){$("connection-label").textContent="SERVER OFFLINE";$("coach-text").textContent=e.message;}}
$("hint-btn").addEventListener("click",async()=>{try{const r=await api("/api/sessions/"+sessionId+"/hints",{method:"POST",body:JSON.stringify({level:Math.min(4,hintLevel+1)})});apply(r.state);}catch(e){feedback(e.message,false);}});
$("undo-btn").addEventListener("click",async()=>{try{const r=await api("/api/sessions/"+sessionId+"/undo",{method:"POST"});history.pop();lastMove=null;apply(r.state);$("feedback").className="feedback hidden";}catch(e){feedback(e.message,false);}});
$("restart-btn").addEventListener("click",async()=>{try{const r=await api("/api/sessions/"+sessionId+"/restart",{method:"POST"});history=[];lastMove=null;apply(r.state);$("feedback").className="feedback hidden";}catch(e){feedback(e.message,false);}});
$("mode-select").addEventListener("change",createSession);$("speak-btn").addEventListener("click",()=>state&&speak(state.coach.voice_script||state.coach.text));$("voice-toggle").addEventListener("change",e=>{if(!e.target.checked&&window.speechSynthesis)window.speechSynthesis.cancel();else if(state)speak(state.coach.voice_script||state.coach.text);});createSession();

// Opening study explorer -----------------------------------------------------
let openingItems=[], activeOpening=null, selectedStudyPath=[], trainingId=null, trainingState=null, trainingSelected=null, trainingTargets=[];
const studyPieceGlyph=PIECES;
function studyNodeAtPath(nodes,path){
  let current=nodes,node=null;
  for(const uci of path){node=current.find(item=>item.uci===uci);if(!node)return null;current=node.children;}
  return node;
}
function allStudyNodes(nodes,result=[]){
  for(const node of nodes){result.push(node);allStudyNodes(node.children,result);}
  return result;
}
function studySanLine(path){
  let siblings=activeOpening.roots;const sans=[];
  for(const uci of path){const node=siblings.find(item=>item.uci===uci);if(!node)break;sans.push(node.san);siblings=node.children;}
  return sans;
}
function renderStudyBoard(fen){
  if(trainingState){renderTrainingBoard();return;}
  const root=$("study-board");root.innerHTML="";
  const cells=parseFen(fen);
  for(let rank=8;rank>=1;rank--)for(let file=0;file<8;file++){
    const sq=FILES[file]+rank,entry=cells.find(x=>x.sq===sq),cell=document.createElement("div");
    cell.className="study-square "+(((file+rank)%2===0)?"light":"dark");
    if(entry&&entry.p){const piece=document.createElement("span");piece.className="piece "+(entry.p===entry.p.toUpperCase()?"white":"black");piece.textContent=studyPieceGlyph[entry.p];cell.append(piece);}
    root.append(cell);
  }
}
function renderStudyPosition(){
  if(!activeOpening)return;
  const node=studyNodeAtPath(activeOpening.roots,selectedStudyPath);
  const fen=node?node.fen_after:activeOpening.starting_fen;
  renderStudyBoard(fen);
  const sans=studySanLine(selectedStudyPath);
  $("study-line").textContent=sans.length?sans.map((san,i)=>Math.floor(i/2)+1+(i%2?". ":"... ")+san).join("  "):"Starting position";
  $("study-ply").textContent=selectedStudyPath.length+" ply";
  $("study-prev").disabled=selectedStudyPath.length===0;
  const canNext=!!(node&&node.children.length);
  $("study-next").disabled=!canNext;
  const notes=node?[node.explanation,node.white_plan?"White plan: "+node.white_plan:"",node.black_plan?"Black plan: "+node.black_plan:""].filter(Boolean).join(" "):"Starting position. Select a move to inspect its resulting position and plans.";
  $("study-notes").textContent=notes||"No editorial notes have been added for this position yet.";
  $("study-variation").textContent=node&&node.label?node.label:"Main line / unnamed continuation";
  $("study-name").textContent=activeOpening.name;
  $("study-family").textContent=activeOpening.family_name+" · "+activeOpening.side+" to move";
  $("study-branches").textContent=activeOpening.branch_count+" move nodes";
  $("study-provenance").textContent="Content status: "+activeOpening.review_status+". Source: "+activeOpening.source_name+". "+activeOpening.license_name+".";
  document.querySelectorAll(".variation-move").forEach(button=>button.classList.toggle("active",button.dataset.path===JSON.stringify(selectedStudyPath)));
}
function buildVariationTree(nodes,container){
  for(const node of nodes){
    const branch=document.createElement("div");branch.className="variation-branch";
    const button=document.createElement("button");button.type="button";button.className="variation-move";
    button.dataset.path=JSON.stringify(node.path_uci);
    button.textContent=node.san+(node.label?" · "+node.label:"");
    button.addEventListener("click",()=>{selectedStudyPath=[...node.path_uci];renderStudyPosition();});
    branch.append(button);
    if(node.children.length){const children=document.createElement("div");children.className="variation-children";buildVariationTree(node.children,children);branch.append(children);}
    container.append(branch);
  }
}
async function loadOpeningList(){
  const query=$("opening-search").value.trim(),side=$("opening-side").value;
  const params=new URLSearchParams();if(query)params.set("query",query);if(side)params.set("side",side);
  try{
    const result=await api("/api/openings?"+params.toString());openingItems=result.items;
    const root=$("opening-list");root.innerHTML="";
    if(!openingItems.length){root.textContent="No matching study trees yet.";return;}
    openingItems.forEach(item=>{
      const button=document.createElement("button");button.type="button";button.className="opening-card";
      if(activeOpening&&activeOpening.opening_id===item.opening_id)button.classList.add("active");
      const name=document.createElement("strong");name.textContent=item.name;
      const meta=document.createElement("span");meta.textContent=item.family_name+" · "+item.branch_count+" moves";
      const status=document.createElement("small");status.textContent="IN REVIEW";
      button.append(name,meta,status);button.addEventListener("click",()=>loadOpening(item.opening_id));root.append(button);
    });
  }catch(error){$("opening-list").textContent="Opening library unavailable: "+error.message;}
}
async function loadOpening(openingId){
  try{
    trainingId=null;trainingState=null;trainingSelected=null;trainingTargets=[];
    activeOpening=await api("/api/openings/"+encodeURIComponent(openingId));selectedStudyPath=[];
    $("variation-tree").innerHTML="";buildVariationTree(activeOpening.roots,$("variation-tree"));
    renderStudyPosition();await loadOpeningList();
  }catch(error){$("study-name").textContent="Could not load opening";$("study-notes").textContent=error.message;}
}
$("opening-search").addEventListener("input",loadOpeningList);
$("opening-side").addEventListener("change",loadOpeningList);
$("study-prev").addEventListener("click",()=>{if(selectedStudyPath.length){selectedStudyPath.pop();renderStudyPosition();}});
$("study-next").addEventListener("click",()=>{if(!activeOpening)return;const node=studyNodeAtPath(activeOpening.roots,selectedStudyPath);if(node&&node.children.length){selectedStudyPath.push(node.children[0].uci);renderStudyPosition();}});
loadOpeningList();


// Opening training ----------------------------------------------------------
function trainingFeedback(message,good){
  const el=$("training-feedback");el.textContent=message;el.className="feedback"+(good?"":" bad");
}
function renderTrainingBoard(){
  if(!trainingState)return;
  const root=$("study-board");root.innerHTML="";
  const cells=parseFen(trainingState.fen),legal=trainingState.legal_moves_uci||[];
  for(let rank=8;rank>=1;rank--)for(let file=0;file<8;file++){
    const sq=FILES[file]+rank,entry=cells.find(x=>x.sq===sq),button=document.createElement("button");
    button.type="button";button.className="study-square "+(((file+rank)%2===0)?"light":"dark");
    if(sq===trainingSelected)button.classList.add("selected");
    if(trainingTargets.some(move=>move.slice(2,4)===sq))button.classList.add("legal");
    if(entry&&entry.p){const piece=document.createElement("span");piece.className="piece "+(entry.p===entry.p.toUpperCase()?"white":"black");piece.textContent=studyPieceGlyph[entry.p];button.append(piece);}
    button.disabled=trainingState.complete;
    button.addEventListener("click",()=>trainingClick(sq,entry&&entry.p));
    root.append(button);
  }
}
function applyTrainingState(s){
  trainingState=s;trainingSelected=null;trainingTargets=[];
  renderTrainingBoard();
  $("study-line").textContent=s.mode==="guided"&&s.expected_san?s.prompt+" Play "+s.expected_san+".":s.prompt;
  $("study-ply").textContent=s.progress.plies_played+" plies";
  $("study-family").textContent=s.learner_color.toUpperCase()+" · "+s.mode.toUpperCase();
  $("study-branches").textContent=s.complete?"COMPLETE":s.turn.toUpperCase()+" TO MOVE";
  $("training-progress").textContent=s.progress.correct_moves+" correct · "+s.progress.attempts+" attempts · "+s.progress.accuracy_percent+"% accuracy";
  $("training-hint").disabled=!s.hints_available||s.hint&&s.hint.level>=3||s.complete;
  $("training-undo").disabled=false;
  $("training-restart").disabled=false;
  if(s.hint)trainingFeedback(s.hint.text,true);
  if(s.complete)trainingFeedback("Opening line complete. Restart to practise again.",true);
}
function trainingClick(square,piece){
  if(!trainingState||trainingState.complete)return;
  if(trainingSelected){
    const candidate=trainingTargets.find(move=>move.slice(2,4)===square);
    if(candidate){submitTrainingMove(candidate);return;}
    if(trainingSelected===square){trainingSelected=null;trainingTargets=[];renderTrainingBoard();return;}
  }
  const own=trainingState.learner_color==="white"?/[A-Z]/.test(piece||""):/[a-z]/.test(piece||"");
  if(piece&&own){trainingSelected=square;trainingTargets=(trainingState.legal_moves_uci||[]).filter(move=>move.slice(0,2)===square);renderTrainingBoard();}
}
async function submitTrainingMove(uci){
  try{
    const result=await api("/api/training/"+trainingId+"/moves",{method:"POST",body:JSON.stringify({uci})});
    applyTrainingState(result.state);
    trainingFeedback(result.message,result.applied);
  }catch(error){trainingFeedback(error.message,false);}
}
$("training-start").addEventListener("click",async()=>{
  if(!activeOpening){trainingFeedback("Choose an opening first.",false);return;}
  try{
    const result=await api("/api/training",{method:"POST",body:JSON.stringify({
      opening_id:activeOpening.opening_id,mode:$("training-mode").value
    })});
    trainingId=result.training_id;applyTrainingState(result.state);
    trainingFeedback("Training started. Play the moves for your repertoire side.",true);
  }catch(error){trainingFeedback(error.message,false);}
});
$("training-hint").addEventListener("click",async()=>{
  if(!trainingId||!trainingState)return;
  try{const level=(trainingState.hint?trainingState.hint.level:0)+1;
    const result=await api("/api/training/"+trainingId+"/hints",{method:"POST",body:JSON.stringify({level})});
    applyTrainingState(result.state);
  }catch(error){trainingFeedback(error.message,false);}
});
$("training-undo").addEventListener("click",async()=>{
  if(!trainingId)return;
  try{const result=await api("/api/training/"+trainingId+"/undo",{method:"POST"});applyTrainingState(result.state);}
  catch(error){trainingFeedback(error.message,false);}
});
$("training-restart").addEventListener("click",async()=>{
  if(!trainingId)return;
  try{const result=await api("/api/training/"+trainingId+"/restart",{method:"POST"});applyTrainingState(result.state);trainingFeedback("Training restarted.",true);}
  catch(error){trainingFeedback(error.message,false);}
});


// Tactical puzzle trainer ---------------------------------------------------
let tacticsId=null,tacticsState=null,tacticsSelected=null,tacticsTargets=[];
function tacticsMessage(message,good=true){
  const el=$("tactics-feedback");el.textContent=message;el.className="feedback"+(good?"":" bad");
}
function renderTacticsBoard(){
  if(!tacticsState)return;
  const root=$("tactics-board");root.innerHTML="";
  const cells=parseFen(tacticsState.fen),legal=tacticsState.legal_moves_uci||[];
  for(let rank=8;rank>=1;rank--)for(let file=0;file<8;file++){
    const square=FILES[file]+rank,entry=cells.find(x=>x.sq===square),button=document.createElement("button");
    button.type="button";button.className="tactics-square "+(((file+rank)%2===0)?"light":"dark");
    if(square===tacticsSelected)button.classList.add("selected");
    if(tacticsTargets.some(move=>move.slice(2,4)===square))button.classList.add("legal");
    if(entry&&entry.p){const piece=document.createElement("span");piece.className="piece "+(entry.p===entry.p.toUpperCase()?"white":"black");piece.textContent=PIECES[entry.p];button.append(piece);}
    button.disabled=tacticsState.solved;
    button.addEventListener("click",()=>tacticsSquareClick(square,entry&&entry.p));
    root.append(button);
  }
}
function applyTacticsState(s){
  tacticsState=s;tacticsSelected=null;tacticsTargets=[];renderTacticsBoard();
  $("tactics-theme").textContent=s.theme.toUpperCase()+" · "+s.difficulty.toUpperCase();
  $("tactics-name").textContent=s.title;$("tactics-prompt").textContent=s.prompt;
  $("tactics-progress").textContent=s.progress.solved+" solved · "+s.progress.attempts+" attempts · "+s.progress.accuracy_percent+"% accuracy";
  $("tactics-hint").disabled=!s.hints_available;
  $("tactics-restart").disabled=false;
  $("tactics-hint").textContent=s.hint_level>=3?"All hints revealed":"Reveal hint "+(s.hint_level+1);
  $("tactics-hint-text").textContent=s.hint||"Hints will appear here.";
  $("tactics-explanation").textContent=s.explanation||"";
  if(s.solved)tacticsMessage("Excellent calculation — puzzle solved!",true);
}
function tacticsSquareClick(square,piece){
  if(!tacticsState||tacticsState.solved)return;
  if(tacticsSelected){
    const move=tacticsTargets.find(uci=>uci.slice(2,4)===square);
    if(move){submitTacticsMove(move);return;}
    if(tacticsSelected===square){tacticsSelected=null;tacticsTargets=[];renderTacticsBoard();return;}
  }
  if(piece&&((tacticsState.turn==="white"&&piece===piece.toUpperCase())||(tacticsState.turn==="black"&&piece===piece.toLowerCase()))){
    tacticsSelected=square;tacticsTargets=(tacticsState.legal_moves_uci||[]).filter(uci=>uci.slice(0,2)===square);renderTacticsBoard();
  }
}
async function submitTacticsMove(uci){
  try{
    const result=await api("/api/tactics/"+tacticsId+"/moves",{method:"POST",body:JSON.stringify({uci})});
    applyTacticsState(result.state);tacticsMessage(result.message,result.correct);
  }catch(error){tacticsMessage(error.message,false);}
}
async function loadTacticsCatalog(){
  try{
    const result=await api("/api/tactics");$("tactics-puzzle").innerHTML="";
    result.items.forEach(puzzle=>{const option=document.createElement("option");option.value=puzzle.puzzle_id;option.textContent=puzzle.title+" · "+puzzle.difficulty; $("tactics-puzzle").append(option);});
  }catch(error){tacticsMessage("Could not load puzzles: "+error.message,false);}
}
$("tactics-start").addEventListener("click",async()=>{
  try{
    const result=await api("/api/tactics",{method:"POST",body:JSON.stringify({puzzle_id:$("tactics-puzzle").value,mode:$("tactics-mode").value})});
    tacticsId=result.tactics_id;applyTacticsState(result.state);tacticsMessage("Puzzle started. Find the forcing move.",true);
  }catch(error){tacticsMessage(error.message,false);}
});
$("tactics-hint").addEventListener("click",async()=>{
  if(!tacticsId||!tacticsState)return;
  try{const result=await api("/api/tactics/"+tacticsId+"/hints",{method:"POST",body:JSON.stringify({level:tacticsState.hint_level+1})});applyTacticsState(result.state);}
  catch(error){tacticsMessage(error.message,false);}
});
$("tactics-restart").addEventListener("click",async()=>{
  if(!tacticsId)return;
  try{const result=await api("/api/tactics/"+tacticsId+"/restart",{method:"POST"});applyTacticsState(result.state);tacticsMessage("Puzzle restarted.",true);}
  catch(error){tacticsMessage(error.message,false);}
});
loadTacticsCatalog();


// Strategy lessons and positional decision exercises -----------------------
let strategyId=null,strategyState=null,strategySelected=null,strategyTargets=[];
function strategyMessage(message,good=true){
  const el=$("strategy-feedback");el.textContent=message;el.className="feedback"+(good?"":" bad");
}
async function loadStrategyLessons(){
  try{
    const result=await api("/api/strategy/lessons");
    const filter=$("strategy-theme");
    result.themes.forEach(theme=>{const option=document.createElement("option");option.value=theme;option.textContent=theme.replaceAll("_"," ");filter.append(option);});
    renderStrategyLessonList(result.items);
    if(result.items.length)loadStrategyLesson(result.items[0].lesson_id);
  }catch(error){$("strategy-lesson-list").textContent="Strategy lessons unavailable: "+error.message;}
}
function renderStrategyLessonList(items){
  const root=$("strategy-lesson-list");root.innerHTML="";
  items.forEach(item=>{
    const button=document.createElement("button");button.type="button";button.className="strategy-lesson-button";
    button.textContent=item.title+" · "+item.level;
    button.addEventListener("click",()=>loadStrategyLesson(item.lesson_id));
    root.append(button);
  });
}
async function loadStrategyLesson(id){
  try{
    const lesson=await api("/api/strategy/lessons/"+encodeURIComponent(id));
    $("strategy-level").textContent=lesson.theme.replaceAll("_"," ").toUpperCase()+" · "+lesson.level.toUpperCase();
    $("strategy-lesson-title").textContent=lesson.title;
    $("strategy-principle").textContent=lesson.principle;
    $("strategy-why").textContent=lesson.why_it_matters;
    $("strategy-checklist").innerHTML="";
    lesson.checklist.forEach(item=>{const li=document.createElement("li");li.textContent=item;$("strategy-checklist").append(li);});
    $("strategy-example").textContent="Example plan: "+lesson.example_plan;
  }catch(error){strategyMessage(error.message,false);}
}
async function loadStrategyExercises(){
  try{
    const result=await api("/api/strategy/exercises");$("strategy-exercise").innerHTML="";
    result.items.forEach(item=>{const option=document.createElement("option");option.value=item.exercise_id;option.textContent=(item.position_phase==="middlegame"?"Middlegame · ":"Opening · ")+item.title+" · "+item.theme.replaceAll("_"," ");$("strategy-exercise").append(option);});
  }catch(error){strategyMessage("Could not load positional exercises: "+error.message,false);}
}
function renderStrategyBoard(){
  if(!strategyState)return;
  const root=$("strategy-board");root.innerHTML="";
  const cells=parseFen(strategyState.fen),legal=strategyState.legal_moves_uci||[];
  for(let rank=8;rank>=1;rank--)for(let file=0;file<8;file++){
    const square=FILES[file]+rank,entry=cells.find(x=>x.sq===square),button=document.createElement("button");
    button.type="button";button.className="tactics-square "+(((file+rank)%2===0)?"light":"dark");
    if(square===strategySelected)button.classList.add("selected");
    if(strategyTargets.some(move=>move.slice(2,4)===square))button.classList.add("legal");
    if(entry&&entry.p){const piece=document.createElement("span");piece.className="piece "+(entry.p===entry.p.toUpperCase()?"white":"black");piece.textContent=PIECES[entry.p];button.append(piece);}
    button.disabled=strategyState.solved;
    button.addEventListener("click",()=>strategySquareClick(square,entry&&entry.p));
    root.append(button);
  }
}
function applyStrategyState(s){
  strategyState=s;strategySelected=null;strategyTargets=[];renderStrategyBoard();
  $("strategy-turn").textContent=s.solved?"DECISION COMPLETE":s.turn.toUpperCase()+" TO MOVE";
  $("strategy-exercise-title").textContent=s.title;$("strategy-prompt").textContent=s.prompt;
  $("strategy-progress").textContent=s.progress.solved+" completed · "+s.progress.attempts+" attempts · "+s.progress.accuracy_percent+"% accuracy";
  $("strategy-hint").disabled=!s.hints_available;
  $("strategy-hint").textContent=s.hint_level>=3?"All hints revealed":"Reveal hint "+(s.hint_level+1);
  $("strategy-restart").disabled=false;
  $("strategy-hint-text").textContent=s.hint||"Hints help you identify the strategic idea.";
  $("strategy-explanation").textContent=s.explanation||"";
  const review=s.strategic_review;
  $("strategy-review").hidden=!review;
  if(review){
    $("strategy-plan").textContent=review.plan;
    $("strategy-gains").innerHTML="";review.positional_gains.forEach(item=>{const li=document.createElement("li");li.textContent=item;$("strategy-gains").append(li);});
    $("strategy-concessions").innerHTML="";review.concessions.forEach(item=>{const li=document.createElement("li");li.textContent=item;$("strategy-concessions").append(li);});
    $("strategy-opponent-plan").textContent=review.opponent_plan;
    $("strategy-candidate-comparison").textContent=review.candidate_comparison;
    $("strategy-evaluation-basis").textContent=review.evaluation_basis;
  }
  if(s.solved)strategyMessage("Decision recorded. Read the explanation and identify the positional gains.",true);
}
function strategySquareClick(square,piece){
  if(!strategyState||strategyState.solved)return;
  if(strategySelected){
    const move=strategyTargets.find(uci=>uci.slice(2,4)===square);
    if(move){submitStrategyMove(move);return;}
    if(strategySelected===square){strategySelected=null;strategyTargets=[];renderStrategyBoard();return;}
  }
  if(piece&&((strategyState.turn==="white"&&piece===piece.toUpperCase())||(strategyState.turn==="black"&&piece===piece.toLowerCase()))){
    strategySelected=square;strategyTargets=(strategyState.legal_moves_uci||[]).filter(uci=>uci.slice(0,2)===square);renderStrategyBoard();
  }
}
async function submitStrategyMove(uci){
  try{const result=await api("/api/strategy/"+strategyId+"/moves",{method:"POST",body:JSON.stringify({uci})});
    applyStrategyState(result.state);strategyMessage(result.message,result.correct);
  }catch(error){strategyMessage(error.message,false);}
}
$("strategy-theme").addEventListener("change",async()=>{
  try{const result=await api("/api/strategy/lessons"+($("strategy-theme").value?"?theme="+encodeURIComponent($("strategy-theme").value):""));renderStrategyLessonList(result.items);}
  catch(error){strategyMessage(error.message,false);}
});
$("strategy-start").addEventListener("click",async()=>{
  try{const result=await api("/api/strategy",{method:"POST",body:JSON.stringify({exercise_id:$("strategy-exercise").value,mode:$("strategy-mode").value})});
    strategyId=result.strategy_id;applyStrategyState(result.state);strategyMessage("Exercise started. Choose a move and explain the plan to yourself.",true);
  }catch(error){strategyMessage(error.message,false);}
});
$("strategy-hint").addEventListener("click",async()=>{
  if(!strategyId||!strategyState)return;
  try{const result=await api("/api/strategy/"+strategyId+"/hints",{method:"POST",body:JSON.stringify({level:strategyState.hint_level+1})});applyStrategyState(result.state);}
  catch(error){strategyMessage(error.message,false);}
});
$("strategy-restart").addEventListener("click",async()=>{
  if(!strategyId)return;
  try{const result=await api("/api/strategy/"+strategyId+"/restart",{method:"POST"});applyStrategyState(result.state);strategyMessage("Exercise restarted.",true);}
  catch(error){strategyMessage(error.message,false);}
});
loadStrategyLessons();loadStrategyExercises();
