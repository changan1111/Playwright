<!DOCTYPE html>
<html>
<head>
    <title>Playwright Smoke Test</title>
    <style>
        #results-container {
            border: 1px solid #ccc;
            padding: 10px;
            margin-top: 10px;
            white-space: pre-wrap;
            font-family: monospace;
            height: 300px;
            overflow-y: auto;
        }
        .progress-bar {
            width: 100%;
            background-color: #f3f3f3;
            border-radius: 5px;
            margin-bottom: 5px;
        }
        .progress {
            background-color: #4CAF50;
            color: white;
            padding: 8px 0;
            text-align: center;
            border-radius: 5px;
            width: 0%;
            transition: width 0.3s ease;
        }
        .progress.failed {
            background-color: #f44336;
        }
        .progress-details {
            display: flex;
            justify-content: space-between;
            margin-bottom: 5px;
        }
        #status-message {
            margin-top: 10px;
            font-weight: bold;
        }
    </style>
</head>
<body>
    <h1>Playwright Smoke Test</h1>
    <button id="runButton" {% if is_running %}disabled{% endif %}>Run Smoke Test</button>
    <button id="stopButton" {% if not is_running %}disabled{% endif %}>Stop Smoke Test</button>

    <h2>Test Progress</h2>
    <div class="progress-details">
        <span>Total: <span id="total-tests">{{ progress.total }}</span></span>
        <span>Passed: <span id="passed-tests">{{ progress.passed }}</span></span>
        <span>Failed: <span id="failed-tests">{{ progress.failed }}</span></span>
        <span>Skipped: <span id="skipped-tests">{{ progress.skipped }}</span></span>
    </div>
    <div class="progress-bar">
        <div id="overall-progress" class="progress" style="width: 0%;">0%</div>
    </div>
    <div id="status-message"></div>

    <h2>Results</h2>
    <div id="results-container">{{ results }}</div>

    <script>
        const runButton = document.getElementById('runButton');
        const stopButton = document.getElementById('stopButton');
        const resultsContainer = document.getElementById('results-container');
        const totalTests = document.getElementById('total-tests');
        const passedTests = document.getElementById('passed-tests');
        const failedTests = document.getElementById('failed-tests');
        const skippedTests = document.getElementById('skipped-tests');
        const overallProgress = document.getElementById('overall-progress');
        const statusMessage = document.getElementById('status-message');

        let intervalId = null;

        runButton.addEventListener('click', () => {
            fetch('/run_smoke', { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    if (data.running) {
                        runButton.disabled = true;
                        stopButton.disabled = false;
                        resultsContainer.innerHTML = '';
                        statusMessage.textContent = '⏳ Running tests...';
                        startPolling();
                    } else {
                        alert(data.message);
                    }
                });
        });

        stopButton.addEventListener('click', () => {
            fetch('/stop_smoke', { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    if (data.stopped) {
                        runButton.disabled = false;
                        stopButton.disabled = true;
                        stopPolling();
                        statusMessage.textContent = '⛔ Test manually stopped.';
                    } else {
                        alert(data.message);
                    }
                });
        });

        function updateResults() {
            fetch('/results')
                .then(response => response.json())
                .then(data => {
                    resultsContainer.innerHTML = data.results.replace(/\n/g, '<br>');
                    resultsContainer.scrollTop = resultsContainer.scrollHeight;

                    const progress = data.progress;
                    totalTests.textContent = progress.total;
                    passedTests.textContent = progress.passed;
                    failedTests.textContent = progress.failed;
                    skippedTests.textContent = progress.skipped;

                    const total = progress.total;
                    const done = progress.passed + progress.failed + progress.skipped;
                    const percent = total > 0 ? Math.round((done / total) * 100) : 0;

                    overallProgress.style.width = `${percent}%`;
                    overallProgress.textContent = `${percent}%`;
                    overallProgress.className = 'progress';
                    if (progress.failed > 0) {
                        overallProgress.classList.add('failed');
                    }

                    if (data.finished) {
                        stopPolling();
                        runButton.disabled = false;
                        stopButton.disabled = true;
                        statusMessage.textContent = '✅ All tests finished!';
                    }
                })
                .catch(error => {
                    console.error("Error fetching results:", error);
                    stopPolling();
                    runButton.disabled = false;
                    stopButton.disabled = true;
                    statusMessage.textContent = '⚠️ Error fetching results.';
                });
        }

        function startPolling() {
            updateResults(); // Immediate first update
            intervalId = setInterval(updateResults, 1000); // 1s interval for live updates
        }

        function stopPolling() {
            if (intervalId) {
                clearInterval(intervalId);
                intervalId = null;
            }
        }

        document.addEventListener('DOMContentLoaded', () => {
            const isRunning = {{ is_running|lower }};
            runButton.disabled = isRunning;
            stopButton.disabled = !isRunning;
            if (isRunning) {
                startPolling();
            }
        });
    </script>
</body>
</html>























import os
import subprocess
import threading
from flask import Flask, render_template, jsonify

app = Flask(__name__)

# Global variables to track state
test_process = None
test_running = False
test_output = []
progress_data = {
    "total": 0,
    "passed": 0,
    "failed": 0,
    "skipped": 0
}
test_finished = False
lock = threading.Lock()

def run_test():
    global test_process, test_running, test_output, progress_data, test_finished

    with lock:
        test_running = True
        test_finished = False
        test_output = []
        progress_data = {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0
        }

    # Change to the target directory where your Playwright project is
    os.chdir("C:/MBP_Playwright")

    # Example: Use 'pytest' or 'npx playwright test' or any custom command
    # Replace this with your actual test command
    test_process = subprocess.Popen(
        ["npx", "playwright", "test"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )

    for line in test_process.stdout:
        with lock:
            test_output.append(line)
            update_progress_from_line(line)

            # Check if we encountered "All tests finished." to stop the test
            if "all tests finished." in line.lower():
                test_finished = True
                break

    test_process.wait()
    with lock:
        test_running = False

def update_progress_from_line(line):
    line = line.strip().lower()
    # Adjust parsing for your actual output format
    if "passed" in line:
        progress_data["passed"] += 1
    elif "failed" in line:
        progress_data["failed"] += 1
    elif "skipped" in line:
        progress_data["skipped"] += 1

    # Optional: Infer total
    progress_data["total"] = (
        progress_data["passed"] +
        progress_data["failed"] +
        progress_data["skipped"]
    )

@app.route('/')
def index():
    return render_template("index.html", is_running=test_running, progress=progress_data, results="\n".join(test_output))

@app.route('/run_smoke', methods=['POST'])
def run_smoke():
    global test_running
    if test_running:
        return jsonify({"running": False, "message": "Test is already running"})
    thread = threading.Thread(target=run_test)
    thread.start()
    return jsonify({"running": True})

@app.route('/stop_smoke', methods=['POST'])
def stop_smoke():
    global test_process, test_running
    with lock:
        if test_running and test_process:
            test_process.terminate()
            test_running = False
            return jsonify({"stopped": True})
        else:
            return jsonify({"stopped": False, "message": "No test is currently running"})

@app.route('/results')
def get_results():
    with lock:
        return jsonify({
            "results": "".join(test_output),
            "progress": progress_data,
            "finished": test_finished
        })

if __name__ == '__main__':
    app.run(debug=True)
