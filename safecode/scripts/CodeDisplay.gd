extends RichTextLabel

func _ready():
	# Simple code snippet for now
	var code_text = """
1  // Server receives JSON from client
2  function handleRequest(req) {
3      const data = JSON.parse(req.body);
4
5      // take user-provided id and use it in query
6      const userId = data.userId;
7      const query = "SELECT * FROM users WHERE id = " + userId;
8
9      // run the query
10     db.query(query, (err, rows) => {
11         if (err) {
12             console.error(err);
13             return sendError();
14         }
15         sendRows(rows);
16     });
17  }
"""
	# Format and style
	self.bbcode_enabled = true
	self.text = code_text
	self.scroll_active = true
	self.scroll_following = false
