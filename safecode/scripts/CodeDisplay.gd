extends RichTextLabel

func _ready():
	# Enable JavaScript communication
	if OS.has_feature("web"):
		# Set up JavaScript interface to listen for messages
		var js_code = """
		window.addEventListener('message', function(event) {
			console.log('Godot iframe received message:', event.data);
			if (event.data && event.data.type === 'SET_CODE') {
				console.log('Setting code in Godot:', event.data.code.substring(0, 50) + '...');
				// Store the code in a global variable that Godot can read
				window.pendingCode = event.data.code;
			}
		});

		// Notify parent that Godot is ready
		window.parent.postMessage({ type: 'GODOT_READY' }, '*');
		console.log('Godot ready, listening for messages');
		"""
		JavaScriptBridge.eval(js_code)

		# Start polling for code updates
		var timer = Timer.new()
		timer.wait_time = 0.1  # Check every 100ms
		timer.timeout.connect(_check_for_code_update)
		add_child(timer)
		timer.start()

	# Default code snippet (will be replaced when message is received)
	var code_text = """
 1  # views.py (insecure example)
 2  import json
 3  from django.http import JsonResponse
 4  from django.views.decorators.csrf import csrf_exempt
 5  from django.db import connection
 6
 7  @csrf_exempt
 8  def get_user_vulnerable(request):
 9      if request.method != "POST":
10          return JsonResponse({"error": "POST only"}, status=405)
11
12      data = json.loads(request.body)
13      user_id = data.get("user_id")
14
15      # Dangerous: building SQL by inserting raw user input
16      query = f"SELECT id, username, email FROM auth_user WHERE id = {user_id}"
17
18      with connection.cursor() as cursor:
19          cursor.execute(query)
20          rows = cursor.fetchall()
21
22      return JsonResponse({"rows": rows})
"""
	# Format and style
	self.bbcode_enabled = true
	self.text = code_text
	self.scroll_active = true
	self.scroll_following = false

# Check for code updates from JavaScript
func _check_for_code_update():
	if OS.has_feature("web"):
		var js_code = "window.pendingCode || null"
		var pending_code = JavaScriptBridge.eval(js_code)

		if pending_code != null and pending_code != "":
			# Clear the pending code
			JavaScriptBridge.eval("window.pendingCode = null")

			# Update the display
			update_code_display(pending_code)

# Update the code display with line numbers
func update_code_display(new_code: String):
	# Add line numbers to the code
	var lines = new_code.split("\n")
	var numbered_code = ""
	for i in range(lines.size()):
		var line_num = str(i + 1).pad_zeros(2)
		numbered_code += " " + line_num + "  " + lines[i]
		if i < lines.size() - 1:
			numbered_code += "\n"

	self.text = numbered_code
