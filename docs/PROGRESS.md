# Gesture Magic Battle 開発状況と引き継ぎ

バージョン v0.1 · 2026-11-24

## 現在地

実装済みの動作を試すには、`T-003-gesture-battle` のコミット `46273eb` を基準にします。このブランチにはフェーズ1から3までの実装が含まれています。2026-11-24時点で `main` は仕様の初期草案 `5be0df0` です。計画は [PROJECT_PLAN.md](../PROJECT_PLAN.md)、要求と受け入れ基準は [要求仕様書](specs/requirements.md) を参照してください。

| 段階 | 実装状況 | 確認状況 |
| --- | --- | --- |
| 1. Webカメラによる手の追跡 | 左右の手と各21点を検出。Webカメラのプレビューは鏡像表示。 | Macの実機で動作を確認済み。 |
| 2. Godotとの連動 | ローカルUDPで座標を送り、片手・両手の3Dモデルに反映。 | Macで2D表示と右手の3D表示を確認済み。両手の独立したポーズと追跡復帰もテスト用UDPデータで確認済み。 |
| 3. 最小構成のバトル | 握りこぶしで火球、相手の攻撃中に手を開くと回避。難易度、HP、時間制限、勝敗、再開を実装。 | Macでバトルの動作を確認済み。テストでは回避、時間切れのダメージ、勝敗を確認済み。 |
| 4. 機能拡張 | 次の候補は `POINT`（氷の槍）。`PEACE`（雷）、`THUMBS_UP`（回復）、キャラクターの腕との連動は未実装。 | 認識精度と遅延の定量評価は未実施。 |

## 修正箇所の探し方

| 変更したいこと | 確認するファイルと関数 |
| --- | --- |
| カメラ入力、プレビューの向き、FPS表示 | [`app/hand_tracking.py`](../app/hand_tracking.py) の `track_capture()` と `annotate_frame()` |
| UDPの項目、宛先、欠落時の扱い | [`app/landmark_stream.py`](../app/landmark_stream.py) の `send_landmarks()` と [`godot/landmark_receiver.gd`](../godot/landmark_receiver.gd) の `_read_frame()`、`update()`。送受信の形式は [UDP仕様](godot_landmark_preview.md#udpの形式) を参照。 |
| 指の形状、手首の向き、左右別の表示 | [`godot/hand_rig.gd`](../godot/hand_rig.gd) の `ROOTS`、`LENGTHS`、`apply_landmarks()` と [`godot/dual_hand_preview.gd`](../godot/dual_hand_preview.gd) の `_process()`、`_reflect()` |
| ジェスチャーの条件、保持時間、再発動 | [`godot/battle_gestures.gd`](../godot/battle_gestures.gd) の `_classify()`、`update()`、`block_held()` |
| 発動できるターン、ダメージ、勝敗 | [`godot/battle_rules.gd`](../godot/battle_rules.gd) の `accept_gesture()`、`advance()`。難易度別の敵ダメージは [`godot/gesture_battle.gd`](../godot/gesture_battle.gd) の `_start_battle()`。 |
| 魔法の表示、操作案内、HUD | [`godot/gesture_battle.gd`](../godot/gesture_battle.gd) の `_on_tracking_frame()`、`_play_fireball()`、`_refresh()` と [`godot/gesture_battle.tscn`](../godot/gesture_battle.tscn) |

ジェスチャーを追加する場合は、姿勢の判定、発動条件やダメージ、演出や操作案内の順に確認します。例えば `POINT` は、判定を追加したうえでバトル側の発動条件と氷の槍の演出を実装します。既存の握りこぶし・開いた手との区別や、同じ姿勢を保持したまま再発動しないことも確認します。

## 動作確認

Webカメラは既存のPython環境から `app.landmark_stream` で起動し、Godotで `gesture_battle.tscn` を開いて現在のシーンを実行します。2D表示や片手・両手の確認シーンを先に起動している場合は停止します。手順と操作は [バトルの実行ガイド](godot_gesture_battle.md) を参照してください。

```bash
.venv/bin/python -m unittest discover -s tests -v
godot --headless --path godot --script res://tests/test_hand_rig.gd
godot --headless --path godot --script res://tests/test_gesture_battle.gd
```

自動テストではWebカメラを使いません。判定条件や座標変換を変えた場合は、実機でも左右それぞれの手を動かし、検出の消失・復帰と、攻撃・防御の各ターンを確認します。

## 変更履歴

| バージョン | 日付 | 内容 |
| --- | --- | --- |
| v0.1 | 2026-11-24 | フェーズごとの進捗、実装の参照先、テスト手順を記載 |
