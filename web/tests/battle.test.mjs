import assert from 'node:assert/strict';
import { test } from 'node:test';
import { Battle, GestureInput, classify } from '../battle.mjs';

function hand(side, extended) {
  const points = [{ x: 0.5, y: 0.7, z: 0 }];
  for (let i = 0; i < 5; i++) {
    const x = 0.30 + i * 0.10;
    points.push({ x, y: 0.5, z: 0 }, { x, y: 0.4, z: 0 });
    if (extended.includes(i)) {
      points.push({ x, y: 0.3, z: 0 }, { x, y: 0.2, z: 0 });
    } else {
      points.push({ x, y: 0.4, z: -0.1 }, { x, y: 0.45, z: -0.1 });
    }
  }
  return { side, points };
}

test('US-05：握りこぶしと開いた手を区別する', () => {
  assert.equal(classify(hand('Right', []).points), 'FIST');
  assert.equal(classify(hand('Right', [1, 2, 3, 4]).points), 'OPEN_PALM');
  assert.equal(classify(hand('Right', [1]).points), '');
  assert.equal(classify([]), '');
});

test('US-05：両手の保持・再発動・追跡切れを別々に管理する', () => {
  const input = new GestureInput();
  const fist = hand('Right', []);
  const palm = hand('Left', [1, 2, 3, 4]);
  assert.deepEqual(input.update([fist, palm], 0), []);
  assert.deepEqual(input.update([fist, palm], 150), []);
  assert.deepEqual(input.update([fist, palm], 300), ['FIST', 'OPEN_PALM']);
  input.update([palm], 350);
  assert.deepEqual(input.update([fist, palm], 500), []);
  input.blockHeld();
  assert.deepEqual(input.update([fist, palm], 600), []);
  input.update([hand('Right', [1])], 650);
  input.update([fist], 700);
  assert.deepEqual(input.update([fist], 1000), []);
  input.update([fist], 1150);
  assert.deepEqual(input.update([fist], 1300), ['FIST']);
});

test('US-04・US-05：攻撃、回避、時間切れ、勝敗と再開', () => {
  const battle = new Battle();
  battle.start(0, 'normal');
  assert.equal(battle.accept('OPEN_PALM', 100), false);
  assert.equal(battle.accept('FIST', 400), true);
  assert.equal(battle.enemyHP, 80);
  assert.equal(battle.accept('FIST', 500), false);
  assert.equal(battle.accept('OPEN_PALM', 800), true);
  assert.equal(battle.playerHP, 100);
  battle.advance(5800);
  assert.equal(battle.accept('OPEN_PALM', 8800), false);
  battle.advance(8800);
  assert.equal(battle.playerHP, 75);
  for (let i = 0; i < 4; i++) {
    battle.accept('FIST', 9000 + i * 100);
    battle.accept('OPEN_PALM', 9001 + i * 100);
  }
  assert.equal(battle.phase, 'victory');
  battle.start(10000, 'easy');
  for (let i = 0; i < 7; i++) {
    battle.advance(battle.deadline);
    battle.advance(battle.deadline);
  }
  assert.equal(battle.phase, 'defeat');
});
