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
        self.playwright_dir = "C:/MBP_Playwright"
        self.npx_path = None
        self.smoke_test_process = None
        self.smoke_test_output = ""
        self.is_running = False
        self.test_progress = {"passed": 0, "failed": 0, "pending": 0, "running": 0, "total": 0, "yet_to_run": 0}

    def find_npx_path(self):
        """Find the path to the npx command"""
        return shutil.which('npx')

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

        # Process final summary counts (Final pass/fail count)
        final_passed = 0
        final_failed = 0
        final_skipped = 0
        final_total = progress["total"]  # Use existing total if found

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

        # Update final counts
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
            command = ['playwright', 'test', '--headed']
            if self.npx_path:
                command.insert(0, self.npx_path)

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
    return jsonify({'running': smoke_test.is_running,'message': 'Smoke test is already running.'})

@app.route('/stop_smoke', methods=['POST'])
def stop_smoke():
    if smoke_test.smoke_test_process and smoke_test.is_running:
        smoke_test.smoke_test_process.terminate()
        smoke_test.is_running = False
        return jsonify({'stopped': True})
    return jsonify({'stopped': False,'message': 'No smoke test is currently running.'})

@app.route('/results')
def results():
    current_progress = smoke_test.parse_playwright_output(smoke_test.smoke_test_output)
    return jsonify({'results': smoke_test.smoke_test_output, 'is_running': smoke_test.is_running, 'progress': current_progress})

if __name__ == '__main__':
    app.run(debug=True, port=8000)







<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Smoke Test</title>
</head>
<body>
    <h1>Smoke Test</h1>
    
    <div id="test-status">
        <p>Status: <span id="status-text">{{ 'Running' if is_running else 'Not Running' }}</span></p>
        <button id="run-btn" onclick="runTest()" {{ 'disabled' if is_running else '' }}>Run Test</button>
        <button id="stop-btn" onclick="stopTest()" {{ 'disabled' if not is_running else '' }}>Stop Test</button>
    </div>

    <h2>Test Progress</h2>
    <div id="progress">
        <p>Passed: <span id="passed">{{ progress['passed'] }}</span></p>
        <p>Failed: <span id="failed">{{ progress['failed'] }}</span></p>
        <p>Pending: <span id="pending">{{ progress['pending'] }}</span></p>
        <p>Total: <span id="total">{{ progress['total'] }}</span></p>
        <p>Running: <span id="running">{{ progress['running'] }}</span></p>
        <p>Yet to Run: <span id="yet_to_run">{{ progress['yet_to_run'] }}</span></p>
    </div>

    <h2>Results</h2>
    <pre id="results">{{ results }}</pre>

    <script>
        function runTest() {
            fetch('/run_smoke', { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    if (data.running) {
                        document.getElementById('status-text').innerText = 'Running';
                        document.getElementById('run-btn').disabled = true;
                        document.getElementById('stop-btn').disabled = false;
                    }
                });
        }

        function stopTest() {
            fetch('/stop_smoke', { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    if (data.stopped) {
                        document.getElementById('status-text').innerText = 'Not Running';
                        document.getElementById('run-btn').disabled = false;
                        document.getElementById('stop-btn').disabled = true;
                    }
                });
        }

        function fetchResults() {
            fetch('/results')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('results').textContent = data.results;
                    document.getElementById('passed').innerText = data.progress.passed;
                    document.getElementById('failed').innerText = data.progress.failed;
                    document.getElementById('pending').innerText = data.progress.pending;
                    document.getElementById('total').innerText = data.progress.total;
                    document.getElementById('running').innerText = data.progress.running;
                    document.getElementById('yet_to_run').innerText = data.progress.yet_to_run;
                });
        }

        setInterval(fetchResults, 1000);
    </script>
</body>
</html>
