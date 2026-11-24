extends Node3D

const LandmarkReceiver = preload("res://landmark_receiver.gd")

@onready var rig = $HandRig
@onready var status: Label = $Hud/Status

var receiver := LandmarkReceiver.new()
var landmarks: Array = []


func _ready() -> void:
	$Camera3D.look_at(Vector3(0.0, 0.82, 0.0))
	var error := receiver.bind()
	if error != OK:
		status.text = "Could not open UDP 5005. Stop the other preview and try again."
		set_process(false)


func _process(delta: float) -> void:
	if receiver.update():
		landmarks = []
		for hand in receiver.hands:
			if hand.side == "Right":
				landmarks = hand.landmarks
				break

	if landmarks.is_empty():
		rig.hide()
		status.text = "Waiting for Python on UDP 5005" if receiver.last_received_ms < 0 else "Show your right hand"
		return

	var blend := 1.0 - exp(-20.0 * delta) if rig.visible else 1.0
	var tracked: bool = rig.apply_landmarks(landmarks, blend)
	rig.visible = tracked
	status.text = "Right hand | 3D tracking" if tracked else "Adjust your right hand"
