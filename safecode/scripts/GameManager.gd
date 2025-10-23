extends Node

var jwt_token = "your-jwt-token"

func submit_score(score: int, challenge_id: int):
	var http := HTTPRequest.new()
	add_child(http)

	var headers := [
		"Content-Type: application/json",
		"Authorization: Bearer " + jwt_token
	]

	var body := {
		"score": score,
		"challenge": challenge_id
	}
	var body_str := JSON.stringify(body)

	# Correct for Godot 4.x:
	var err := http.request(
		"http://127.0.0.1:8000/api/results/",
		headers,
		HTTPClient.METHOD_POST,
		body_str
	)

	if err != OK:
		push_error("HTTP request failed with error code %s" % err)

func fetch_challenges():
	var http := HTTPRequest.new()
	add_child(http)
	http.request_completed.connect(_on_challenges_received)

	var headers := [
		"Content-Type: application/json",
		"Authorization: Bearer " + jwt_token
	]

	# Godot 4 request() method signature:
	# request(url: String, headers: PackedStringArray, method: HTTPClient.Method, body: String = "")
	var err := http.request(
		"http://127.0.0.1:8000/api/challenges/",
		headers,
		HTTPClient.METHOD_GET
	)

	if err != OK:
		push_error("HTTP request failed with error code %s" % err)


func _on_challenges_received(result, response_code, headers, body):
	print("Response code: ", response_code)

	if response_code == 200:
		var text: String = body.get_string_from_utf8()
		var data: Variant = JSON.parse_string(text)

		if data == null:
			push_error("Failed to parse response JSON: " + text)
			return

		for challenge in data:
			print("- %s (%s)" % [challenge["title"], challenge["difficulty"]])
	else:
		push_error("Server responded with code: %s" % response_code)

func _ready():
	print("Fetching challenges from API...")
	fetch_challenges()
