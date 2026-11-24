extends RefCounted

enum Phase { TITLE, ATTACK, DEFEND, VICTORY, DEFEAT }

const MAX_HP := 100
const FIREBALL_DAMAGE := 20
const ATTACK_MS := 5000
const DEFEND_MS := 3000

var phase := Phase.TITLE
var player_hp := MAX_HP
var enemy_hp := MAX_HP
var enemy_damage := 25
var deadline_ms := 0
var event := ""


func start(now: int) -> void:
	player_hp = MAX_HP
	enemy_hp = MAX_HP
	_attack_turn(now, "Battle started")


# 時間切れを処理する。攻撃の時間切れは敵のターンへ進み、防御の時間切れは被弾する。
func advance(now: int) -> bool:
	if now < deadline_ms:
		return false
	match phase:
		Phase.ATTACK:
			_defense_turn(now, "Your turn expired")
		Phase.DEFEND:
			player_hp = maxi(0, player_hp - enemy_damage)
			if player_hp == 0:
				phase = Phase.DEFEAT
				event = "Defeat"
			else:
				_attack_turn(now, "You took %s damage" % enemy_damage)
		_:
			return false
	return true


# 発動条件とダメージはここで管理する。新しい攻撃ジェスチャーを追加するときもここを確認する。
func accept_gesture(gesture: String, now: int) -> bool:
	if now >= deadline_ms:
		return false
	if phase == Phase.ATTACK and gesture == "FIST":
		enemy_hp = maxi(0, enemy_hp - FIREBALL_DAMAGE)
		if enemy_hp == 0:
			phase = Phase.VICTORY
			event = "Victory"
		else:
			_defense_turn(now, "Fireball hit for %s damage" % FIREBALL_DAMAGE)
		return true
	if phase == Phase.DEFEND and gesture == "OPEN_PALM":
		_attack_turn(now, "Attack dodged")
		return true
	return false


func _attack_turn(now: int, message: String) -> void:
	phase = Phase.ATTACK
	deadline_ms = now + ATTACK_MS
	event = message


func _defense_turn(now: int, message: String) -> void:
	phase = Phase.DEFEND
	deadline_ms = now + DEFEND_MS
	event = message
