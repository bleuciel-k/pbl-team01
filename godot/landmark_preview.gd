extends Node2D

const LandmarkReceiver = preload("res://landmark_receiver.gd")
const EDGES := [
	Vector2i(0, 1), Vector2i(1, 2), Vector2i(2, 3), Vector2i(3, 4),
	Vector2i(0, 5), Vector2i(5, 6), Vector2i(6, 7), Vector2i(7, 8),
	Vector2i(5, 9), Vector2i(9, 10), Vector2i(10, 11), Vector2i(11, 12),
	Vector2i(9, 13), Vector2i(13, 14), Vector2i(14, 15), Vector2i(15, 16),
	Vector2i(13, 17), Vector2i(17, 18), Vector2i(18, 19), Vector2i(19, 20),
	Vector2i(0, 17),
]

var receiver := LandmarkReceiver.new()
var bind_error := OK


func _ready() -> void:
	bind_error = receiver.bind()
	if bind_error != OK:
		push_error("UDP port 5005 could not be opened: %s" % error_string(bind_error))
		set_process(false)
	get_viewport().size_changed.connect(queue_redraw)


func _process(_delta: float) -> void:
	if receiver.update():
		queue_redraw()


func _draw() -> void:
	if bind_error != OK:
		_draw_status("Could not open UDP port 5005")
		return
	if receiver.last_received_ms < 0:
		_draw_status("Waiting for Python on UDP 5005")
		return
	if receiver.hands.is_empty():
		_draw_status("No hand detected")
		return

	var hand: Dictionary = receiver.hands[0]
	for candidate in receiver.hands:
		if candidate.side == "Right":
			hand = candidate
			break

	var area := get_viewport_rect().grow(-40.0)
	var points := PackedVector2Array()
	for point in hand.landmarks:
		# Python側のWebカメラ表示と同じ向きにそろえる。
		points.append(area.position + Vector2(1.0 - point[0], point[1]) * area.size)
	for edge in EDGES:
		draw_line(points[edge.x], points[edge.y], Color.SKY_BLUE, 2.0, true)
	for point in points:
		draw_circle(point, 4.0, Color.WHITE)
	_draw_status("%s | 21 landmarks | frame %s" % [hand.side, receiver.last_sequence])


func _draw_status(message: String) -> void:
	draw_string(ThemeDB.fallback_font, Vector2(16, 26), message, HORIZONTAL_ALIGNMENT_LEFT, -1, 16)
