export const HOLD_MS = 300;
const MAX_GAP_MS = 250;
const MAX_HP = 100;
const ATTACK_MS = 5000;
const DEFEND_MS = 3000;
const FIREBALL_DAMAGE = 20;
const ENEMY_DAMAGE = { easy: 15, normal: 25 };

function difference(a, b) {
  return [a.x - b.x, a.y - b.y, a.z - b.z];
}

export function classify(points) {
  if (points.length !== 21) return '';
  let extended = 0;
  let curled = 0;
  // 親指以外の4本を、指の長さに対する伸びと最初の関節の角度で判定する。
  for (const base of [5, 9, 13, 17]) {
    const a = difference(points[base + 1], points[base]);
    const b = difference(points[base + 2], points[base + 1]);
    const c = difference(points[base + 3], points[base + 2]);
    const first = Math.hypot(...a);
    const second = Math.hypot(...b);
    if (first < 0.00001 || second < 0.00001) return '';
    const reach = Math.hypot(...difference(points[base + 3], points[base])) /
      (first + second + Math.hypot(...c));
    const alignment = a.reduce((sum, coordinate, i) => sum + coordinate * b[i], 0) / (first * second);
    if (reach >= 0.85 && alignment >= 0.75) extended++;
    else if (reach <= 0.72 && alignment <= 0.6) curled++;
  }
  if (extended === 4) return 'OPEN_PALM';
  if (curled === 4) return 'FIST';
  return '';
}

export class GestureInput {
  poses = new Map();

  update(hands, now) {
    const confirmed = [];
    const observed = new Set();
    for (const { side, points } of hands) {
      if (observed.has(side)) continue;
      observed.add(side);
      const gesture = classify(points);
      let pose = this.poses.get(side);
      if (pose?.gesture !== gesture) {
        pose = { gesture, since: now, lastSeen: now, confirmed: false };
        this.poses.set(side, pose);
      }
      if (pose.since === null || now - pose.lastSeen > MAX_GAP_MS) pose.since = now;
      pose.lastSeen = now;
      if (gesture && !pose.confirmed && now - pose.since >= HOLD_MS) {
        pose.confirmed = true;
        confirmed.push(gesture);
      }
    }
    // 追跡が途切れても、直前に発動した姿勢は姿勢が変わるまで再発動させない。
    for (const [side, pose] of this.poses) {
      if (!observed.has(side)) pose.since = null;
    }
    return confirmed;
  }

  blockHeld() {
    for (const pose of this.poses.values()) pose.confirmed = Boolean(pose.gesture);
  }
}

export class Battle {
  phase = 'title';
  playerHP = MAX_HP;
  enemyHP = MAX_HP;
  deadline = 0;
  event = '';

  start(now, difficulty) {
    this.playerHP = MAX_HP;
    this.enemyHP = MAX_HP;
    this.enemyDamage = ENEMY_DAMAGE[difficulty] ?? ENEMY_DAMAGE.normal;
    this.attackTurn(now, 'バトル開始');
  }

  advance(now) {
    if (now < this.deadline) return false;
    if (this.phase === 'attack') {
      this.defenseTurn(now, '攻撃ターンの時間切れ');
    } else if (this.phase === 'defend') {
      this.playerHP = Math.max(0, this.playerHP - this.enemyDamage);
      if (this.playerHP === 0) {
        this.phase = 'defeat';
        this.event = '敗北';
      } else {
        this.attackTurn(now, `${this.enemyDamage} ダメージを受けました`);
      }
    } else {
      return false;
    }
    return true;
  }

  accept(gesture, now) {
    if (now >= this.deadline) return false;
    if (this.phase === 'attack' && gesture === 'FIST') {
      this.enemyHP = Math.max(0, this.enemyHP - FIREBALL_DAMAGE);
      if (this.enemyHP === 0) {
        this.phase = 'victory';
        this.event = '勝利';
      } else {
        this.defenseTurn(now, `火球が命中 · ${FIREBALL_DAMAGE} ダメージ`);
      }
      return true;
    }
    if (this.phase === 'defend' && gesture === 'OPEN_PALM') {
      this.attackTurn(now, '攻撃を回避しました');
      return true;
    }
    return false;
  }

  attackTurn(now, event) {
    this.phase = 'attack';
    this.deadline = now + ATTACK_MS;
    this.event = event;
  }

  defenseTurn(now, event) {
    this.phase = 'defend';
    this.deadline = now + DEFEND_MS;
    this.event = event;
  }
}
