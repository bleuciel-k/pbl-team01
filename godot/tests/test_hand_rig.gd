extends SceneTree

const HandRig = preload("res://hand_rig.gd")

var failures := 0


func _initialize() -> void:
	_run.call_deferred()


func _run() -> void:
	# US-05の技術検証として、合成ランドマークで指と手首の回転を確認する。
	var rig := HandRig.new()
	root.add_child(rig)
	_check(rig.get_bone_count() == 16, "wrist and fifteen finger bones")
	_check(rig.apply_landmarks(_pose([])), "open hand")
	_check(_direction(rig, "index_2").dot(Vector3.UP) > 0.95, "open index extends upward")
	_check(_direction(rig, "middle_2").dot(Vector3.UP) > 0.95, "open middle finger extends upward")
	_check(rig.apply_landmarks(_pose([0, 1, 2, 3, 4])), "fist")
	_check(_direction(rig, "index_2").dot(Vector3.DOWN) > 0.9, "fist index curls inward")
	_check(rig.apply_landmarks(_pose([0, 2, 3, 4])), "pointing hand")
	_check(_direction(rig, "index_2").dot(Vector3.UP) > 0.95, "pointing index remains extended")
	_check(_direction(rig, "middle_2").dot(Vector3.DOWN) > 0.9, "pointing middle finger remains curled")
	_check(rig.apply_landmarks(_pose([], PI / 2.0)), "rotated wrist")
	_check(_direction(rig, "wrist").dot(Vector3.LEFT) > 0.95, "wrist follows a quarter turn")
	var collapsed: Array = []
	collapsed.resize(21)
	collapsed.fill([0.5, 0.5, 0.0])
	_check(not rig.apply_landmarks(collapsed), "degenerate tracking result is rejected")
	rig.free()
	if failures == 0:
		print("PASS: open hand, fist, pointing, wrist rotation and degenerate data")
	quit(0 if failures == 0 else 1)


func _pose(curled: Array, roll := 0.0) -> Array:
	var points: Array = [[0.5, 0.7, 0.0]]
	for finger in range(5):
		var joint := Vector3(0.5 - finger * 0.24, 0.7, 0.0)
		for segment in range(4):
			var rotated := joint.rotated(Vector3.BACK, roll)
			points.append([0.5 - rotated.x * 0.15, 0.7 - rotated.y * 0.2, -rotated.z * 0.15])
			var direction := Vector3.UP
			if finger in curled:
				direction = [Vector3.BACK, Vector3.DOWN, Vector3.DOWN][mini(segment, 2)]
			joint += direction * 0.24
	return points


func _direction(rig: Skeleton3D, bone: String) -> Vector3:
	return rig.get_bone_global_pose(rig.find_bone(bone)).basis.y.normalized()


func _check(condition: bool, description: String) -> void:
	if not condition:
		failures += 1
		push_error(description)
