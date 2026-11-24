import { Battle, GestureInput, classify } from './battle.mjs';

const VISION = 'https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.21';
const MODEL = 'https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task';
const byId = (id) => document.getElementById(id);
const arena = document.querySelector('.arena');
const spell = document.querySelector('.spell');
const video = byId('video');
const canvas = byId('landmarks');
const context = canvas.getContext('2d');
const camera = byId('camera');
const cameraState = byId('camera-state');
const cameraError = byId('camera-error');
const placeholder = byId('camera-placeholder');
const handCount = byId('hand-count');
const start = byId('start');
const difficulty = byId('difficulty');
const phase = byId('phase');
const instruction = byId('instruction');
const timer = byId('timer');
const event = byId('event');
const exampleIcon = byId('example-icon');
const exampleLabel = byId('example-label');
const recognizedIcon = byId('recognized-icon');
const recognizedLabel = byId('recognized-label');
const playerStatus = byId('player-status');
const gestureIcons = { FIST: './assets/gesture-fist.png', OPEN_PALM: './assets/gesture-palm.png' };
const gestureLabels = { FIST: '握りこぶし', OPEN_PALM: '開いた手' };
const statusLabels = {
  title: '待機中', attack: '攻撃可能', defend: '防御中', victory: '勝利', defeat: '敗北',
};
const copy = {
  title: ['対戦準備', 'カメラを有効にしてバトルを始めます。'],
  attack: ['あなたのターン', '握りこぶしを作って火球を放ちます。'],
  defend: ['相手の攻撃', '手を開いて相手の攻撃を回避します。'],
  victory: ['勝利', '難易度を選んで、もう一度対戦できます。'],
  defeat: ['敗北', '難易度を選んで、もう一度対戦できます。'],
};

let battle = new Battle();
let input = new GestureInput();
let stream;
let detector;
let lastVideoTime = -1;
let animation;
let renderedPhase;

function showGestureIcons(target, kinds) {
  const key = kinds.join(' ');
  if (target.dataset.gestures === key) return;
  target.dataset.gestures = key;
  if (kinds.length === 0) {
    target.textContent = '—';
    return;
  }
  target.replaceChildren(...kinds.map((kind) => {
    const icon = new Image(72, 72);
    icon.src = gestureIcons[kind];
    icon.alt = '';
    return icon;
  }));
}

function render(now) {
  const active = battle.phase === 'attack' || battle.phase === 'defend';
  arena.dataset.phase = battle.phase;
  if (renderedPhase !== battle.phase) {
    const example = battle.phase === 'attack' ? 'FIST' : battle.phase === 'defend' ? 'OPEN_PALM' : null;
    showGestureIcons(exampleIcon, example ? [example] : ['FIST', 'OPEN_PALM']);
    exampleLabel.textContent = example ? gestureLabels[example] : '攻撃：握る ／ 回避：開く';
    playerStatus.textContent = statusLabels[battle.phase];
    renderedPhase = battle.phase;
  }
  const [label, help] = copy[battle.phase];
  phase.textContent = label;
  instruction.textContent = battle.phase === 'title' && detector ? '難易度を選んで対戦を開始します。' : help;
  byId('player-hp').value = battle.playerHP;
  byId('enemy-hp').value = battle.enemyHP;
  byId('player-value').textContent = `${battle.playerHP} HP`;
  byId('enemy-value').textContent = `${battle.enemyHP} HP`;
  timer.hidden = !active;
  if (active) timer.value = `${(Math.max(0, battle.deadline - now) / 1000).toFixed(1)} 秒`;
  if (event.textContent !== battle.event) event.textContent = battle.event;
  start.textContent = battle.phase === 'title' ? 'バトル開始' : '再戦';
  start.disabled = !detector || active;
  difficulty.disabled = active;
}

function drawHands(hands) {
  context.clearRect(0, 0, canvas.width, canvas.height);
  context.fillStyle = '#aaffd2';
  for (const { points } of hands) {
    for (const { x, y } of points) {
      context.beginPath();
      context.arc(x * canvas.width, y * canvas.height, 3, 0, 2 * Math.PI);
      context.fill();
    }
  }
  handCount.textContent = `${hands.length} 手を検出`;
  const kinds = [...new Set(hands.map(({ points }) => classify(points)).filter(Boolean))];
  showGestureIcons(recognizedIcon, kinds);
  recognizedLabel.textContent = kinds.map((kind) => gestureLabels[kind]).join(' ／ ') ||
    (hands.length ? '該当するポーズなし' : '未検出');
}

function infer(now) {
  if (!detector || video.readyState < 2 || video.currentTime === lastVideoTime) return;
  lastVideoTime = video.currentTime;
  const result = detector.detectForVideo(video, now);
  const hands = result.landmarks.flatMap((points, i) => {
    const side = result.handedness[i]?.[0]?.categoryName;
    return side ? [{ side, points }] : [];
  });
  drawHands(hands);
  for (const gesture of input.update(hands, now)) {
    if (!battle.accept(gesture, now)) continue;
    if (gesture === 'FIST') {
      animation?.cancel();
      animation = spell.animate([
        { left: '31%', top: '55%', opacity: 1, transform: 'scale(1)' },
        { left: '69%', top: '48%', opacity: 0, transform: 'scale(.35)' },
      ], { duration: 360, easing: 'ease-in' });
    }
    input.blockHeld();
    break;
  }
}

function tick(now) {
  if (battle.advance(now)) input.blockHeld();
  try {
    infer(now);
  } catch (error) {
    console.error(error);
    showError('手の追跡が停止しました。カメラを起動し直してください。');
  }
  render(now);
  requestAnimationFrame(tick);
}

function stopCamera() {
  const stopped = stream;
  stream = undefined;
  stopped?.getTracks().forEach((track) => track.stop());
  detector?.close();
  detector = undefined;
  video.srcObject = null;
  lastVideoTime = -1;
  battle = new Battle();
  input = new GestureInput();
  animation?.cancel();
  drawHands([]);
  placeholder.hidden = false;
  handCount.hidden = true;
  cameraState.textContent = 'カメラ停止中';
  camera.textContent = 'カメラを起動';
}

function showError(message) {
  stopCamera();
  cameraError.textContent = message;
  cameraError.hidden = false;
}

async function startCamera() {
  if (!navigator.mediaDevices?.getUserMedia) {
    showError('カメラを使うにはHTTPSまたはlocalhostで開いてください。');
    return;
  }
  cameraState.textContent = 'カメラの許可を待っています';
  try {
    stream = await navigator.mediaDevices.getUserMedia({ video: { width: { ideal: 640 }, height: { ideal: 480 } }, audio: false });
  } catch (error) {
    showError(error.name === 'NotAllowedError' ? 'ブラウザでカメラの使用を許可してください。' : 'カメラを開けませんでした。接続を確認してください。');
    return;
  }

  cameraState.textContent = '手の追跡モデルを読み込み中';
  try {
    video.srcObject = stream;
    await video.play();
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const { FilesetResolver, HandLandmarker } = await import(`${VISION}/vision_bundle.mjs`);
    const vision = await FilesetResolver.forVisionTasks(`${VISION}/wasm`);
    detector = await HandLandmarker.createFromOptions(vision, {
      baseOptions: { modelAssetPath: MODEL }, runningMode: 'VIDEO', numHands: 2,
    });
    const current = stream;
    for (const track of current.getVideoTracks()) {
      track.addEventListener('ended', () => {
        if (stream === current) showError('カメラの接続が切れました。');
      });
      if (track.readyState === 'ended') throw new Error('Camera disconnected');
    }
    placeholder.hidden = true;
    handCount.hidden = false;
    cameraState.textContent = 'カメラ動作中';
    camera.textContent = 'カメラを停止';
  } catch (error) {
    console.error(error);
    showError('手の追跡を開始できませんでした。カメラやネットワークを確認して再試行してください。');
  }
}

camera.addEventListener('click', async () => {
  cameraError.hidden = true;
  camera.disabled = true;
  try {
    if (stream) stopCamera();
    else await startCamera();
  } finally {
    camera.disabled = false;
  }
});

start.addEventListener('click', () => {
  battle.start(performance.now(), difficulty.value);
  input.blockHeld();
});

requestAnimationFrame(tick);
