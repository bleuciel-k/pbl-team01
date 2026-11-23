extends RefCounted

const PORT := 5005
const TIMEOUT_MS := 500
const MAX_PACKET_BYTES := 4096

var socket := PacketPeerUDP.new()
var last_sequence := -1
var last_received_ms := -1
var hands: Array = []


func bind() -> Error:
	return socket.bind(PORT, "127.0.0.1")


func update() -> bool:
	var now := Time.get_ticks_msec()
	var changed := false
	if last_received_ms >= 0 and now - last_received_ms >= TIMEOUT_MS:
		last_received_ms = -1
		last_sequence = -1
		hands = []
		changed = true

	for i in range(mini(socket.get_available_packet_count(), 64)):
		var data := socket.get_packet()
		if data.size() > MAX_PACKET_BYTES:
			continue
		if _read_frame(data):
			last_received_ms = now
			changed = true
	return changed


func _read_frame(data: PackedByteArray) -> bool:
	var parser := JSON.new()
	if parser.parse(data.get_string_from_utf8()) != OK or not parser.data is Dictionary:
		return false
	var frame: Dictionary = parser.data
	if frame.get("version") != 1 or not frame.get("hands") is Array:
		return false
	var sequence: Variant = frame.get("sequence")
	if not _number(sequence) or sequence < 0 or sequence != floor(sequence) or sequence <= last_sequence:
		return false
	if not _number(frame.get("timestamp_ms")) or frame.timestamp_ms < 0 or frame.hands.size() > 2:
		return false
	for hand in frame.hands:
		if not _valid_hand(hand):
			return false

	last_sequence = int(sequence)
	hands = frame.hands
	return true


func _valid_hand(hand: Variant) -> bool:
	if not hand is Dictionary or hand.get("side") not in ["Left", "Right"]:
		return false
	if not hand.get("landmarks") is Array or hand.landmarks.size() != 21:
		return false
	for point in hand.landmarks:
		if not point is Array or point.size() != 3:
			return false
		for coordinate in point:
			if not _number(coordinate):
				return false
	return true


func _number(value: Variant) -> bool:
	return (value is float or value is int) and is_finite(value)
