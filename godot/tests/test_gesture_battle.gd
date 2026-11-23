extends SceneTree

const Battle = preload("res://battle_rules.gd")
const GestureInput = preload("res://battle_gestures.gd")

var failures := 0


func _initialize() -> void:
	_run.call_deferred()


func _run() -> void:
	_test_us05_stabilizes_each_hand()
	_test_us04_us05_resolves_turns()
	if failures == 0:
		print("PASS: gesture stabilization, independent hands, dodge, damage, victory and defeat")
	quit(0 if failures == 0 else 1)


func _test_us05_stabilizes_each_hand() -> void:
	var input := GestureInput.new()
	var fist := {"side": "Right", "landmarks": _hand(true)}
	var palm := {"side": "Left", "landmarks": _hand(false)}
	_check(input.update([fist, palm], 0).is_empty(), "first frame cannot cast")
	_check(input.update([fist, palm], 150).is_empty(), "gestures must be stable")
	_check(input.update([fist, palm], 300) == ["FIST", "OPEN_PALM"], "both hands classify independently")
	_check(input.update([fist, palm], 450).is_empty(), "holding cannot cast again")
	input.update([palm], 500)
	_check(input.update([fist, palm], 800).is_empty(), "tracking loss does not rearm a held fist")
	input.update([{"side": "Right", "landmarks": _hand(false)}], 900)
	input.update([fist], 1000)
	input.update([fist], 1150)
	_check(input.update([fist], 1300) == ["FIST"], "release rearms a subsequent fist")
	input.update([{"side": "Right", "landmarks": _hand(false)}], 1400)
	input.block_held()
	input.update([{"side": "Right", "landmarks": _hand(false)}], 1550)
	_check(input.update([{"side": "Right", "landmarks": _hand(false)}], 1700).is_empty(), "old phase pose cannot fire in new phase")


func _test_us04_us05_resolves_turns() -> void:
	var battle := Battle.new()
	battle.start(0)
	_check(not battle.accept_gesture("OPEN_PALM", 100), "palm is ignored during attack")
	_check(battle.accept_gesture("FIST", 400) and battle.enemy_hp == 80, "fist deals 20 damage")
	_check(not battle.accept_gesture("FIST", 500), "fist is ignored during defense")
	_check(battle.accept_gesture("OPEN_PALM", 800) and battle.player_hp == 100, "palm dodges all damage")
	battle.advance(5800)
	_check(battle.phase == Battle.Phase.DEFEND, "attacking turn times out")
	_check(not battle.accept_gesture("OPEN_PALM", 8800), "palm at deadline is too late")
	battle.advance(8800)
	_check(battle.player_hp == 75, "missed defense deals damage")
	var now := 9000
	for i in range(4):
		battle.accept_gesture("FIST", now)
		battle.accept_gesture("OPEN_PALM", now + 1)
		now += 100
	_check(battle.phase == Battle.Phase.VICTORY and battle.enemy_hp == 0, "winning ends the battle")
	battle.start(now)
	for i in range(4):
		battle.advance(battle.deadline_ms)
		battle.advance(battle.deadline_ms)
	_check(battle.phase == Battle.Phase.DEFEAT and battle.player_hp == 0, "losing ends the battle")


func _hand(closed: bool) -> Array:
	var points: Array = [[0.5, 0.7, 0.0]]
	for finger in range(5):
		var x := 0.3 + 0.1 * finger
		points.append_array([[x, 0.5, 0.0], [x, 0.4, 0.0]])
		if closed:
			points.append_array([[x, 0.4, -0.1], [x, 0.45, -0.1]])
		else:
			points.append_array([[x, 0.3, 0.0], [x, 0.2, 0.0]])
	return points


func _check(condition: bool, description: String) -> void:
	if not condition:
		failures += 1
		push_error(description)
