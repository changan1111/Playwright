from flask import Flask, render_template, Response
import subprocess
import threading
import time
import re

app = Flask(__name__)
result_lines = []
stream_active = True
total_tests = 0  # Extracted from "Running X tests..."

def run_playwright():
    global result_lines, stream_active, total_tests
    process = subprocess.Popen(
        ['npx', 'playwright', 'test', '--headed'],
        cwd='C:\\mbp_playwright',
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    for line in process.stdout:
        print(line.strip())

        if match := re.search(r'Running (\d+) tests? using \d+ workers?', line):
            total_tests = int(match.group(1))

        if "RESULT#" in line:
            result_lines.append(line.strip())

        elif "All tests finished." in line:
            stream_active = False
            result_lines.append("FINISHED")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/stream')
def stream():
    def event_stream():
        current_index = 0
        while stream_active or current_index < len(result_lines):
            if current_index < len(result_lines):
                new_line = result_lines[current_index]
                if new_line == "FINISHED":
                    yield f"event: done\ndata: All tests finished\n\n"
                else:
                    match = re.search(r'RESULT# Passed: (\d+), Failed: (\d+), Skipped: (\d+)', new_line)
                    if match:
                        passed, failed, skipped = match.groups()
                        yield (
                            f"data: {{"
                            f"\"passed\": {passed}, "
                            f"\"failed\": {failed}, "
                            f"\"skipped\": {skipped}, "
                            f"\"total\": {total_tests}"
                            f"}}\n\n"
                        )
                current_index += 1
            time.sleep(1)
    return Response(event_stream(), mimetype='text/event-stream')

if __name__ == '__main__':
    threading.Thread(target=run_playwright, daemon=True).start()
    app.run(debug=True)









<!DOCTYPE html>
<html>
<head>
    <title>Playwright Test Progress</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            padding: 20px;
        }
        .stat {
            margin: 10px 0;
        }
        #done {
            color: green;
            font-weight: bold;
            display: none;
        }
    </style>
</head>
<body>
    <h1>Playwright Test Progress</h1>

    <div class="stat">✅ Passed: <span id="passed">0</span> / <span id="total">?</span></div>
    <div class="stat">❌ Failed: <span id="failed">0</span></div>
    <div class="stat">⚠️ Skipped: <span id="skipped">0</span></div>

    <div id="done">✅ All tests finished.</div>

    <script>
        const evtSource = new EventSource("/stream");

        evtSource.onmessage = function(event) {
            const data = JSON.parse(event.data);
            document.getElementById("passed").textContent = data.passed;
            document.getElementById("failed").textContent = data.failed;
            document.getElementById("skipped").textContent = data.skipped;
            document.getElementById("total").textContent = data.total ?? '?';
        };

        evtSource.addEventListener("done", function(event) {
            document.getElementById("done").style.display = "block";
            evtSource.close();
        });
    </script>
</body>
</html>
