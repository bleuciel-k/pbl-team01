extends Skeleton3D

const FINGERS := ["thumb", "index", "middle", "ring", "pinky"]
# モデルの指の付け根と長さは固定し、ランドマークは回転の推定に使う。
const ROOTS := [
	Vector3(0.38, 0.36, 0.04), Vector3(0.29, 0.84, 0.0), Vector3(0.07, 0.94, 0.0),
	Vector3(-0.16, 0.87, 0.0), Vector3(-0.35, 0.74, 0.02),
]
const LENGTHS := [
	Vector3(0.28, 0.24, 0.21), Vector3(0.38, 0.26, 0.21), Vector3(0.42, 0.30, 0.23),
	Vector3(0.38, 0.26, 0.21), Vector3(0.29, 0.21, 0.17),
]
const RADII := [0.12, 0.095, 0.10, 0.094, 0.079]
const MIN_DIRECTION_SQUARED := 0.00000001


func _ready() -> void:
	var material := StandardMaterial3D.new()
	material.albedo_color = Color(0.29, 0.73, 0.88)
	material.roughness = 0.62
	var wrist := _add_joint("wrist", -1, Vector3.ZERO)
	var palm := SphereMesh.new()
	_attach(wrist, palm, material, Vector3(0.0, 0.46, 0.0), Vector3(0.96, 1.10, 0.33))

	for finger in range(FINGERS.size()):
		var parent := wrist
		var offset: Vector3 = ROOTS[finger]
		for segment in range(3):
			var length: float = LENGTHS[finger][segment]
			var bone := _add_joint("%s_%s" % [FINGERS[finger], segment], parent, offset)
			var mesh := CapsuleMesh.new()
			mesh.radius = RADII[finger] * (1.0 - 0.13 * segment)
			mesh.height = length + 2.0 * mesh.radius
			_attach(bone, mesh, material, Vector3.UP * length * 0.5)
			parent = bone
			offset = Vector3.UP * length


func apply_landmarks(landmarks: Array, blend := 1.0) -> bool:
	if landmarks.size() != 21:
		return false
	var points := PackedVector3Array()
	for point in landmarks:
		# xは鏡像表示、yは上向き、zはカメラに近い方向を正とする。
		points.append(Vector3(-float(point[0]), -float(point[1]), -float(point[2])))

	# 人差し指と小指の付け根、手首から中指への方向で手のひらの座標系を作る。
	var across := points[5] - points[17]
	var along := points[9] - points[0]
	if across.length_squared() < MIN_DIRECTION_SQUARED or along.length_squared() < MIN_DIRECTION_SQUARED:
		return false
	var normal := across.normalized().cross(along.normalized())
	if normal.length_squared() < MIN_DIRECTION_SQUARED:
		return false
	var x := across.normalized()
	var z := normal.normalized()
	var palm := Basis(x, z.cross(x), z)
	var rotations: Array[Quaternion] = [palm.get_rotation_quaternion()]

	for finger in range(FINGERS.size()):
		var parent_basis := palm
		for segment in range(3):
			var first := 1 + finger * 4 + segment
			var direction := points[first + 1] - points[first]
			if direction.length_squared() < MIN_DIRECTION_SQUARED:
				return false
			var target := _segment_basis(direction.normalized(), palm)
			# 各指ボーンの回転を親ボーンの座標系に変換する。
			rotations.append((parent_basis.transposed() * target).get_rotation_quaternion())
			parent_basis = target

	for bone in range(rotations.size()):
		var current := get_bone_pose_rotation(bone)
		set_bone_pose_rotation(bone, current.slerp(rotations[bone], blend))
	return true


func _segment_basis(direction: Vector3, palm: Basis) -> Basis:
	var reference := palm.x if absf(direction.dot(palm.x)) < 0.9 else palm.z
	var x := (reference - direction * reference.dot(direction)).normalized()
	return Basis(x, direction, x.cross(direction))


func _add_joint(bone_name: String, parent: int, offset: Vector3) -> int:
	var bone := add_bone(bone_name)
	set_bone_parent(bone, parent)
	set_bone_rest(bone, Transform3D(Basis.IDENTITY, offset))
	reset_bone_pose(bone)
	return bone


func _attach(bone: int, mesh: PrimitiveMesh, material: Material, offset: Vector3, mesh_scale := Vector3.ONE) -> void:
	var attachment := BoneAttachment3D.new()
	attachment.bone_idx = bone
	add_child(attachment)
	var part := MeshInstance3D.new()
	part.mesh = mesh
	part.material_override = material
	part.position = offset
	part.scale = mesh_scale
	attachment.add_child(part)
