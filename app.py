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























from flask import Flask, render_template, request, jsonify
import subprocess
import threading
import time
import os
import shutil
import re
import json

app = Flask(__name__)

class SmokeTest:
    def __init__(self):
        self.playwright_dir = "C:/MBP_Playwright"  # Update this to the correct path
        self.npx_path = None
        self.smoke_test_process = None
        self.smoke_test_output = ""
        self.is_running = False
        self.test_progress = {"passed": 0, "failed": 0, "pending": 0, "running": 0, "total": 0, "yet_to_run": 0}

    def find_npx_path(self):
        """Find the path to the npx command"""
        npx = shutil.which('npx')
        if not npx:
            print("npx not found in the system path.")
        return npx

    def parse_playwright_output(self, output: str) -> dict:
        """Parse the Playwright output to extract test progress"""
        progress = {"passed": 0, "failed": 0, "pending": 0, "running": 0, "total": 0, "yet_to_run": 0}
        lines = output.splitlines()

        # Process RESULT# for live updates
        for line in lines:
            match_result = re.search(r"RESULT#\s+Passed:\s+(\d+),\s*Failed:\s+(\d+),\s*Skipped:\s+(\d+)", line, re.IGNORECASE)
            if match_result:
                passed = int(match_result.group(1))
                failed = int(match_result.group(2))
                skipped = int(match_result.group(3))
                progress["passed"] += passed
                progress["failed"] += failed
                progress["pending"] += skipped
                print(f"LIVE RESULT# - Passed: {passed}, Failed: {failed}, Skipped: {skipped} - Current Progress: {progress}")
                return progress  # Return immediately after a live update

        # Process total and running counts (these might appear before or during)
        for line in lines:
            match_total = re.search(r"Total:\s+(\d+)", line, re.IGNORECASE)
            if match_total and progress["total"] == 0:  # Update total only once or if it changes
                progress["total"] = int(match_total.group(1))
                print(f"PARSED Total: {progress['total']}")

            match_in_progress = re.search(r"In Progress:\s+(\d+)", line, re.IGNORECASE)
            if match_in_progress:
                progress["running"] = int(match_in_progress.group(1))
                print(f"PARSED In Progress: {progress['running']}")

            match_yet_to_run = re.search(r"Yet to Run:\s+(\d+)", line, re.IGNORECASE)
            if match_yet_to_run and progress["total"] > 0:
                progress["yet_to_run"] = int(match_yet_to_run.group(1))
                print(f"PARSED Yet to Run: {progress['yet_to_run']}")

            match_pending = re.search(r"Pending:\s+(\d+)", line, re.IGNORECASE)
            if match_pending:
                progress["pending"] = int(match_pending.group(1))
                print(f"PARSED Pending: {progress['pending']}")

        # Process final counts (these appear at the end)
        final_passed = 0
        final_failed = 0
        final_skipped = 0
        final_total = progress["total"] # Use existing total if found

        for line in lines:
            match_passed_count = re.search(r"Passed Count:\s+(\d+)", line, re.IGNORECASE)
            if match_passed_count:
                final_passed = int(match_passed_count.group(1))

            match_failed_count = re.search(r"Failed Count:\s+(\d+)", line, re.IGNORECASE)
            if match_failed_count:
                final_failed = int(match_failed_count.group(1))

            match_skipped_count = re.search(r"Skipped Count:\s+(\d+)", line, re.IGNORECASE)
            if match_skipped_count:
                final_skipped = int(match_skipped_count.group(1))

            match_final_summary = re.search(r"All\s+(\d+)\s+Passed\s+(\d+)\s+Failed\s+(\d+)\s+Flaky\s+(\d+)\s+Skipped\s+(\d+)", line, re.IGNORECASE)
            if match_final_summary:
                final_total = int(match_final_summary.group(1))
                final_passed = int(match_final_summary.group(2))
                final_failed = int(match_final_summary.group(3))
                final_skipped = int(match_final_summary.group(5))

        if final_passed > 0 or final_failed > 0 or final_skipped > 0:
            progress["passed"] = final_passed
            progress["failed"] = final_failed
            progress["pending"] = final_skipped
            if final_total > 0:
                progress["total"] = final_total
            progress["running"] = 0
            progress["yet_to_run"] = max(0, progress["total"] - progress["passed"] - progress["failed"] - progress["pending"])
            print(f"FINAL COUNTS - Passed: {progress['passed']}, Failed: {progress['failed']}, Skipped: {progress['pending']}, Total: {progress['total']}")
            return progress

        if progress["total"] > 0:
            progress["yet_to_run"] = max(0, progress["total"] - progress["passed"] - progress["failed"] - progress["pending"] - progress["running"])

        return progress

    def run_smoke_test_command(self):
        """Run the smoke test command"""
        self.smoke_test_output = ""
        self.is_running = True
        self.test_progress = {"passed": 0, "failed": 0, "pending": 0, "running": 0, "total": 0, "yet_to_run": 0}
        original_cwd = os.getcwd()
        try:
            os.chdir(self.playwright_dir)
            self.npx_path = self.find_npx_path()

            if not self.npx_path:
                self.smoke_test_output = "Error: npx not found."
                return

            command = [self.npx_path, 'playwright', 'test', '--headed']
            print(f"Executing command: {command}")

            self.smoke_test_process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',  # Explicitly set encoding to UTF-8
                errors='replace'   # Replace undecodable characters
            )
            while True:
                if self.smoke_test_process.poll() is not None:
                    break
                line = self.smoke_test_process.stdout.readline()
                if line:
                    self.smoke_test_output += line
                    self.test_progress = self.parse_playwright_output(self.smoke_test_output)
                    print(f"Stdout: {line.strip()} - Progress: {self.test_progress}")
                time.sleep(0.1)

            stdout, stderr = self.smoke_test_process.communicate()
            self.smoke_test_output += stdout
            self.test_progress = self.parse_playwright_output(self.smoke_test_output)
            if stderr:
                self.smoke_test_output += f"\nError:\n{stderr}"
                print(f"Stderr: {stderr}")

        except FileNotFoundError as e:
            self.smoke_test_output = f"Error: {e}"
        except Exception as e:
            self.smoke_test_output = f"An unexpected error occurred: {str(e)}"
        finally:
            os.chdir(original_cwd)
            self.is_running = False
            self.smoke_test_process = None

smoke_test = SmokeTest()

@app.route('/')
def index():
    return render_template('index.html', is_running=smoke_test.is_running, results=smoke_test.smoke_test_output, progress=smoke_test.test_progress)

@app.route('/run_smoke', methods=['POST'])
def run_smoke():
    if not smoke_test.is_running:
        smoke_test.smoke_test_output = ""
        smoke_test.test_progress = {"passed": 0, "failed": 0, "pending": 0, "running": 0, "total": 0, "yet_to_run": 0}
        threading.Thread(target=smoke_test.run_smoke_test_command).start()
        return jsonify({'running': True})
    return jsonify({'running': smoke_test.is_running, 'message': 'Smoke test is already running.'})

@app.route('/stop_smoke', methods=['POST'])
def stop_smoke():
    if smoke_test.smoke_test_process and smoke_test.is_running:
        smoke_test.smoke_test_process.terminate()
        smoke_test.is_running = False
        return jsonify({'stopped': True})
    return jsonify({'stopped': False, 'message': 'No smoke test is currently running.'})

@app.route('/results')
def results():
    current_progress = smoke_test.parse_playwright_output(smoke_test.smoke_test_output)
    return jsonify({'results': smoke_test.smoke_test_output, 'is_running': smoke_test.is_running, 'progress': current_progress})

if __name__ == '__main__':
    app.run(debug=True, port=8000)
