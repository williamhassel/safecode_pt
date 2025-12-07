extends RichTextLabel

func _ready():
	# Simple code snippet for now
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
