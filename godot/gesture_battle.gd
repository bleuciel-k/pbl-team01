extends Node3D

const BattleRules = preload("res://battle_rules.gd")
const GestureInput = preload("res://battle_gestures.gd")

@onready var status: Label = $BattleHud/Panel/Status
@onready var controls: Label = $BattleHud/Panel/Controls
@onready var difficulty: OptionButton = $BattleHud/Panel/Difficulty
@onready var start_button: Button = $BattleHud/Panel/Start
@onready var enemy: MeshInstance3D = $Enemy
@onready var fireball: MeshInstance3D = $Fireball

var battle := BattleRules.new()
var gesture_input := GestureInput.new()
var cast_animation: Tween


func _ready() -> void:
	$DualHandPreview.tracking_frame.connect(_on_tracking_frame)
	start_button.pressed.connect(_start_battle)
	difficulty.add_item("Easy")
	difficulty.add_item("Normal")
	difficulty.select(1)
	_refresh(Time.get_ticks_msec())


func _process(_delta: float) -> void:
	var now := Time.get_ticks_msec()
	if battle.advance(now):
		gesture_input.block_held()
	_refresh(now)


func _start_battle() -> void:
	battle.enemy_damage = 15 if difficulty.selected == 0 else 25
	battle.start(Time.get_ticks_msec())
	gesture_input.block_held()
	if cast_animation:
		cast_animation.kill()
	fireball.hide()
	enemy.show()


func _on_tracking_frame(hands: Array) -> void:
	var now := Time.get_ticks_msec()
	for gesture in gesture_input.update(hands, now):
		if not battle.accept_gesture(gesture, now):
			continue
		if gesture == "FIST":
			_play_fireball()
		gesture_input.block_held()
		break


func _play_fireball() -> void:
	if cast_animation:
		cast_animation.kill()
	fireball.position = Vector3(0.0, -0.5, 1.3)
	fireball.show()
	cast_animation = create_tween()
	cast_animation.tween_property(fireball, "position", enemy.position, 0.25)
	cast_animation.tween_callback(_finish_fireball)


func _finish_fireball() -> void:
	fireball.hide()
	enemy.visible = battle.enemy_hp > 0


func _refresh(now: int) -> void:
	var active := battle.phase in [BattleRules.Phase.ATTACK, BattleRules.Phase.DEFEND]
	difficulty.visible = not active
	start_button.visible = not active
	start_button.text = "Start battle" if battle.phase == BattleRules.Phase.TITLE else "Play again"
	var time_left := maxf(0.0, (battle.deadline_ms - now) / 1000.0)
	match battle.phase:
		BattleRules.Phase.TITLE:
			status.text = "Gesture Magic Battle"
			controls.text = "Fist: fireball | Open palm: dodge | Hold for 0.3 s"
		BattleRules.Phase.ATTACK:
			controls.text = "Attack (%.1f s): make a fist" % time_left
		BattleRules.Phase.DEFEND:
			controls.text = "Enemy attacking (%.1f s): open your palm to dodge" % time_left
		_:
			controls.text = "Choose a difficulty to play again"
	if battle.phase != BattleRules.Phase.TITLE:
		status.text = "You %s HP | Enemy %s HP | %s" % [battle.player_hp, battle.enemy_hp, battle.event]
	enemy.material_override.albedo_color = Color(0.98, 0.22, 0.15) if battle.phase == BattleRules.Phase.DEFEND else Color(0.55, 0.37, 0.84)
