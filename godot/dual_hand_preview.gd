extends Node3D

signal tracking_frame(hands: Array)

const LandmarkReceiver = preload("res://landmark_receiver.gd")
const HandRig = preload("res://hand_rig.gd")

@onready var right_rig = $HandRig
@onready var left_rig = $LeftHand/HandRig
@onready var status: Label = $Hud/Status

var receiver := LandmarkReceiver.new()
var hands: Dictionary = {}


func _ready() -> void:
	$Camera3D.look_at(Vector3(0.0, 0.65, 0.0))
	if receiver.bind() != OK:
		status.text = "Could not open UDP 5005. Stop the other preview and try again."
		set_process(false)


func _process(delta: float) -> void:
	if receiver.update():
		hands.clear()
		for hand in receiver.hands:
			hands[hand.side] = hand.landmarks
		tracking_frame.emit(receiver.hands)

	_update_rig(right_rig, hands.get("Right", []), delta)
	_update_rig(left_rig, _reflect(hands.get("Left", [])), delta)
	if receiver.last_received_ms < 0:
		status.text = "Waiting for Python on UDP 5005"
	else:
		status.text = "Left: %s     Right: %s" % [_tracking_text(left_rig), _tracking_text(right_rig)]


func _update_rig(rig, points: Array, delta: float) -> void:
	var blend := 1.0 - exp(-20.0 * delta) if rig.visible else 1.0
	rig.visible = not points.is_empty() and rig.apply_landmarks(points, blend)


func _reflect(points: Array) -> Array:
	# 左手の入力を右手モデルに合わせ、親ノードの鏡映で左手に戻す。
	var reflected: Array = []
	for point in points:
		reflected.append([1.0 - point[0], point[1], point[2]])
	return reflected


func _tracking_text(rig: Skeleton3D) -> String:
	return "tracking" if rig.visible else "not detected"
