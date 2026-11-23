extends RefCounted

const HOLD_MS := 300
const MAX_GAP_MS := 250

var poses: Dictionary = {}


func update(hands: Array, now: int) -> Array[String]:
	var confirmed: Array[String] = []
	var observed: Dictionary = {}
	for hand in hands:
		var side: String = hand.side
		if observed.has(side):
			continue
		observed[side] = true
		var gesture := _classify(hand.landmarks)
		var pose: Dictionary = poses.get(side, {})
		if pose.get("gesture") != gesture:
			pose = {"gesture": gesture, "since": now, "confirmed": false, "last_seen": now}
		elif now - int(pose.last_seen) > MAX_GAP_MS or pose.since < 0:
			pose.since = now
		pose.last_seen = now
		if not gesture.is_empty() and not pose.confirmed and now - int(pose.since) >= HOLD_MS:
			pose.confirmed = true
			confirmed.append(gesture)
		poses[side] = pose

	for side in poses:
		if not observed.has(side):
			poses[side].since = -1
	return confirmed


func block_held() -> void:
	for pose in poses.values():
		pose.confirmed = not pose.gesture.is_empty()


func _classify(points: Array) -> String:
	var extended := 0
	var curled := 0
	# 親指を除く4本の指について、付け根から指先までの伸びを測る。
	for base in [5, 9, 13, 17]:
		var root := _point(points[base])
		var joint := _point(points[base + 1])
		var distal := _point(points[base + 2])
		var tip := _point(points[base + 3])
		var length := root.distance_to(joint) + joint.distance_to(distal) + distal.distance_to(tip)
		if length < 0.00001:
			return ""
		var reach := root.distance_to(tip) / length
		var alignment := (joint - root).normalized().dot((distal - joint).normalized())
		if reach >= 0.85 and alignment >= 0.75:
			extended += 1
		elif reach <= 0.72 and alignment <= 0.6:
			curled += 1
	if extended == 4:
		return "OPEN_PALM"
	if curled == 4:
		return "FIST"
	return ""


func _point(coordinates: Array) -> Vector3:
	return Vector3(coordinates[0], coordinates[1], coordinates[2])
