from flask import Flask, request, jsonify, render_template
import traceback
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# ---------------- MODEL ----------------
class Execution(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    task = db.Column(db.Text)
    generated_code = db.Column(db.Text)
    final_code = db.Column(db.Text)
    input_value = db.Column(db.Text)
    output_value = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime)

# ---------------- GLOBALS ----------------
generated_code_global = ""
final_code_global = ""
last_test_input = None
last_execution_id = None

# ---------------- CODE GENERATION ----------------
def generate_code(task):
    task = task.lower()

    if "add" in task:
        return """def add_numbers(nums):
    return sum(nums)
"""
    elif "subtract" in task:
        return """def subtract_numbers(nums):
    result = nums[0]
    for n in nums[1:]:
        result -= n
    return result
"""
    elif "multiply" in task:
        return """def multiply_numbers(nums):
    result = 1
    for n in nums:
        result *= n
    return result
"""
    elif "divide" in task:
        return """def divide_numbers(nums):
    result = nums[0]
    for n in nums[1:]:
        if n == 0:
            raise ZeroDivisionError("Division by zero")
        result /= n
    return result
"""
    elif "sort" in task:
        return """def sort_numbers(nums):
    return sorted(nums)
"""
    elif "factorial" in task:
        return """def factorial(n):
    if n < 0:
        raise ValueError("Negative number")
    result = 1
    for i in range(1, n+1):
        result *= i
    return result
"""
    elif "palindrome" in task:
        return """def is_palindrome(s):
    s = str(s)
    return s == s[::-1]
"""
    else:
        return """def dummy():
    return "Task not recognized"
"""

# ---------------- HELPERS ----------------
def detect_function(task):
    task = task.lower()
    if "add" in task: return "add_numbers"
    if "subtract" in task: return "subtract_numbers"
    if "multiply" in task: return "multiply_numbers"
    if "divide" in task: return "divide_numbers"
    if "sort" in task: return "sort_numbers"
    if "factorial" in task: return "factorial"
    if "palindrome" in task: return "is_palindrome"
    return "dummy"

def normalize_input(func, value):
    if func in ["add_numbers","subtract_numbers","multiply_numbers","divide_numbers","sort_numbers"]:
        if isinstance(value, list):
            return [float(x) for x in value]
        return [float(x) for x in str(value).split(",")]
    if func == "factorial":
        return int(value)
    return str(value)

def execute_code(code, func_name, test_input):
    try:
        local_ns = {}
        exec(code, {}, local_ns)
        return local_ns[func_name](test_input), None
    except Exception:
        return None, traceback.format_exc()

def apply_feedback(code, feedback):
    lines = code.split("\n")
    lines.insert(1, f"# Feedback: {feedback}")
    return "\n".join(lines)

# ---------------- ROUTES ----------------
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/generate", methods=["POST"])
def generate():
    global generated_code_global, final_code_global, last_test_input, last_execution_id

    data = request.json
    task = data.get("task", "")
    raw_input = data.get("testInput")

    func = detect_function(task)
    test_input = normalize_input(func, raw_input)

    code = generate_code(task)
    generated_code_global = code
    final_code_global = code
    last_test_input = test_input

    output, error = execute_code(code, func, test_input)
    if error:
        output = error

    record = Execution(
        task=task,
        generated_code=code,
        final_code=code,
        input_value=str(test_input),
        output_value=str(output)
    )
    db.session.add(record)
    db.session.commit()
    last_execution_id = record.id

    return jsonify({
        "generated_code": code,
        "output": output,
        "answer": output
    })

@app.route("/feedback", methods=["POST"])
def feedback():
    global final_code_global, last_execution_id

    data = request.json
    feedback = data.get("feedback", "")

    final_code_global = apply_feedback(final_code_global, feedback)

    func = detect_function(final_code_global)
    output, error = execute_code(final_code_global, func, last_test_input)
    if error:
        output = error

    rec = Execution.query.get(last_execution_id)
    rec.final_code = final_code_global
    rec.output_value = str(output)
    rec.updated_at = datetime.utcnow()
    db.session.commit()

    return jsonify({
        "final_code": final_code_global,
        "output": output,
        "answer": output
    })

# ---------------- RUN ----------------
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
