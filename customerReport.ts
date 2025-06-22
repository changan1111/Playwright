import {
    FullConfig,
    Reporter,
    Suite,
    TestCase,
    TestResult,
    TestStep,
} from '@playwright/test/reporter';
import fs from 'fs';
import path from 'path';
import { DateTime } from 'luxon';
import test from '@playwright/test';

interface StepInfo {
    name: string;
    status: 'pending' | 'passed' | 'failed' | 'skipped' | 'timedOut' | 'interrupted';
    children: StepInfo[];
    parent?: StepInfo | null;
    duration?: number;
    startTime?: number;
}

interface TestCaseInfo {
    name: string;
    steps: StepInfo[];
    status: 'pending' | 'passed' | 'failed' | 'skipped' | 'timedOut' | 'interrupted';
    attachments: { title: string; url: string }[];
    duration?: number;
    startTime?: string;
    stdout?: string[];
    error?: string; // Add an error property
}

interface TestResultData {
    testCaseInfo?: TestCaseInfo;
    currentStep?: StepInfo | null;
    stepStack?: StepInfo[]; // To maintain the stack of current steps
}

const testResultData = new WeakMap<TestResult, TestResultData>();
let reformattedMessage: string;

class CustomReporter implements Reporter {
    onBegin(config: FullConfig, suite: Suite): void {
        console.log(`Starting tests in ${config.rootDir}`);
        fs.mkdirSync(process.cwd() + '\\resultDocumentDirectory\\', { recursive: true });
    }

    onTestBegin(test: TestCase, result: TestResult): void {
        const now = DateTime.fromJSDate(result.startTime).setZone('Asia/Kolkata');
        const testInfo: TestCaseInfo = {
            name: test.titlePath().slice(2).join(' > '),
            steps: [],
            status: 'pending',
            attachments: [],
            startTime: now.toLocaleString(DateTime.DATETIME_SHORT_WITH_SECONDS),
            stdout: [],
            error: undefined, // Initialize error as undefined
        };
        testResultData.set(result, { testCaseInfo: testInfo, currentStep: null, stepStack: [] });
        reformattedMessage = "No Errors"; // Initialize for each test

        result.stdout.forEach(output => {
            if (typeof output === 'string') {
                testInfo.stdout?.push(output);
            } else if (output instanceof Buffer) {
                testInfo.stdout?.push(output.toString());
            }
        });
    }
    async onStepBegin(test: TestCase, result: TestResult, step: TestStep): Promise<void> {
        const data = testResultData.get(result);
        if (!data || !data.testCaseInfo) return;

        const newStep: StepInfo = {
            name: step.title,
            status: 'pending',
            children: [],
            parent: data.currentStep, // Set parent to the current step
            startTime: Date.now(),
        };

        if (data.currentStep) {
            data.currentStep.children.push(newStep);
        } else {
            data.testCaseInfo.steps.push(newStep);
        }
        data.currentStep = newStep;
    }

    async onStepEnd(test: TestCase, result: TestResult, step: TestStep): Promise<void> {
        const data = testResultData.get(result);
        if (!data || !data.currentStep) return;

        if (data.currentStep.name === step.title) {
            const endTime = Date.now();
            data.currentStep.duration = endTime - (data.currentStep.startTime || endTime);
            data.currentStep.status = result.status;

            data.currentStep = data.currentStep.parent || null; // Move back to the parent
        }
    }

    onTestEnd(test: TestCase, result: TestResult): void {
        const data = testResultData.get(result);
        if (!data || !data.testCaseInfo) return;

        data.testCaseInfo.status = result.status;
        data.testCaseInfo.duration = result.duration;

        if (result.status === 'failed' && result.error) {
            const ansiPattern = /\u001b\[[0-9;]*[a-zA-Z]/g;
            const errorMessage = JSON.stringify(result.error);
            try {
                const errorMessageObj = JSON.parse(errorMessage);
                if (errorMessageObj && typeof errorMessageObj.message === 'string') {
                    const decodedMessage = errorMessageObj.message.replace(ansiPattern, '');
                    const decodedMessageArr = decodedMessage.split('\n');
                    data.testCaseInfo.error = decodedMessageArr.join('\r\n');
                        reformattedMessage = data.testCaseInfo.error?.toString()?? "No Errors";
                    console.log("Decoded:", decodedMessage);
                    console.log("Encoded:", JSON.stringify(reformattedMessage));
                } else if (typeof result.error.message === 'string') {
                    const decodedMessage = result.error.message.replace(ansiPattern, '');
                    const decodedMessageArr = decodedMessage.split('\n');
                    data.testCaseInfo.error = decodedMessageArr.join('\r\n');
                    reformattedMessage = data.testCaseInfo.error; // Update reformattedMessage
                    console.log("Decoded:", decodedMessage);
                    console.log("Encoded:", JSON.stringify(reformattedMessage));
                } else {
                    data.testCaseInfo.error = errorMessage; // Fallback to the raw error string
                    reformattedMessage = data.testCaseInfo.error; // Update reformattedMessage
                }
            } catch (e) {
                console.error("Error processing error message:", e);
                data.testCaseInfo.error = errorMessage; // Fallback if JSON parsing fails
                reformattedMessage = data.testCaseInfo.error; // Update reformattedMessage
            }
        } else {
            data.testCaseInfo.error = undefined;
            reformattedMessage = "No Errors";
        }

        result.stdout.forEach(output => {
            if (typeof output === 'string') {
                data.testCaseInfo?.stdout?.push(output);
            } else if (output instanceof Buffer) {
                data.testCaseInfo?.stdout?.push(output.toString());
            }
        });

        const attach = result.attachments;
        const fileDir = process.cwd() + '\\resultDocumentDirectory\\';
        const now = DateTime.now().setZone('Asia/Kolkata');
        const formattedDate = now.toFormat('MMddyyyyHHmmss');
        const baseFilename = test.title.replace(/[^a-zA-Z0-9]/g, '_');
        const reportFilename = `${fileDir}${baseFilename}_${result.status}_${formattedDate}.html`;

        const imageObjects: { title: string; url: string }[] = [];
        for (const image of attach) {
            if (image.body) {
                const base64ImageString = `data:${image.contentType};base64,${image.body.toString("base64")}`;
                imageObjects.push({ title: image.name, url: base64ImageString });
            } else if (image.path) {
                try {
                    const screenshotContent = fs.readFileSync(image.path, 'base64');
                    imageObjects.push({ title: image.name, url: `data:image/png;base64,${screenshotContent}` });
                } catch (error) {
                    console.error(`Error reading screenshot file: ${image.path}`, error);
                }
            }
        }
        data.testCaseInfo.attachments = imageObjects;
        this.generateHTMLReport([data.testCaseInfo], reportFilename);
    }

    async onEnd(): Promise<void> {
        console.log(`All tests finished.`);
    }

    private generateHTMLReport(testCaseResults: TestCaseInfo[], reportFilename: string): void {
        const now = DateTime.now().setZone('Asia/Kolkata');
        const formattedDateTime = now.toLocaleString(DateTime.DATETIME_FULL);

        const formatDuration = (milliseconds: number | undefined): string => {
            if (milliseconds === undefined) {
                return 'N/A';
            }
            const totalSeconds = Math.floor(milliseconds / 1000);
            const minutes = Math.floor(totalSeconds / 60);
            const seconds = totalSeconds % 60;
            const ms = milliseconds % 1000;
            return `${minutes} min <span class="math-inline">\{seconds\}\.</span>{ms.toString().padStart(3, '0')} sec`;
        };

        let html = `
        <!DOCTYPE html>
        <html>
        <head>
            <title>Test Report - ${testCaseResults[0]?.name} - ${formattedDateTime}</title>
            <style>
                body { font-family: sans-serif; }
                .test-case { margin-bottom: 20px; border: 1px solid #ccc; padding: 10px; }
                .test-case h2 { margin-top: 0; }
                .test-info-container {
                    background-color: #f9f9f9;
                    border: 1px solid #eee;
                    padding: 10px;
                    margin-bottom: 10px;
                    font-size: 0.9em;
                }
                .test-info-item { margin-bottom: 5px; }
                .error-container {
                    background-color: #ffe0e0;
                    border: 1px solid #ffb3b3;
                    padding: 10px;
                    margin-bottom: 10px;
                    font-size: 0.9em;
                    white-space: pre-wrap;
                    color: darkred;
                    font-weight: bold;
                }
                .step { margin-left: 20px; color: #777; }
                .parent { font-weight: bold; cursor: pointer; color: #777; }
                .children { display: none; }
                .expanded > .children { display: block; }
                .screenshot-container { margin-top: 10px; border-top: 1px solid #eee; padding-top: 10px; }
                .attachment-title { font-size: 1.1em; color: #333; margin-bottom: 5px; font-weight: bold; }
                .screenshot { max-width: 600px; height: auto; display: block; margin-bottom: 15px; border: 1px solid #ddd; }
                .status-passed { color: green; }
                .status-failed { color: red; }
                .status-skipped { color: orange; }
                .status-timedOut { color: darkred; }
                .status-interrupted { color: gray; }
                .duration { font-size: 0.8em; color: #999; float: right; }
                .total-duration { font-size: 0.9em; color: #555; font-style: italic; margin-top: 5px; }
                .stdout-container { margin-top: 10px; border-top: 1px solid #eee; padding-top: 10px; font-size: 0.85em; white-space: pre-wrap; }
                .stdout-title { font-weight: bold; margin-bottom: 5px; }
            </style>
        </head>
        <body>
            <h1>Test Report</h1>
            <h2>Test Case: ${testCaseResults[0]?.name}</h2>
            <p>Timestamp: <span class="math-inline">\{formattedDateTime\} \(</span>{now.zoneName})</p>
        `;

        for (const testCase of testCaseResults) {
            const statusClass = `status-${testCase.status.toLowerCase()}`;
            html += `<div class="test-case ${statusClass}">`;
            html += `<div class="test-info-container">`;
            html += `<div class="test-info-item"><b>Client:</b> ${process.env.CLIENT || 'N/A'}</div>`;
            html += `<div class="test-info-item"><b>Title:</b> ${testCase.name}</div>`;
            html += `<div class="test-info-item"><b>Status:</b> ${testCase.status.toUpperCase()}</div>`;
            html += `<div class="test-info-item"><b>Duration:</b> ${this.formatDuration(testCase.duration)}</div>`;
            html += `<div class="test-info-item"><b>Environment:</b> ${process.env.TESTENVIRONMENT || 'N/A'}</div>`;
            html += `<div class="test-info-item"><b>Build Number:</b> ${process.env.BuildNumber || 'N/A'}</div>`;
            if (testCase.startTime) {
                html += `<div class="test-info-item"><b>Start Time:</b> ${testCase.startTime}</div>`;
            }
            html += `</div>`;

            // Add error container if the test failed and has an error message
            if (testCase.status === 'failed' && testCase.error) {
                html += `<div class="error-container"><b>Error:</b><pre>${this.escapeHtml(testCase.error)}</pre>`;
                const locationMatch = testCase.error.match(/at (?:.*?)\((.*?):(\d+):(\d+)\)/);
                if (locationMatch) {
                    const filePath = locationMatch[1];
                    const lineNumber = locationMatch[2];
                    html += `<div style="font-size: 0.8em; color: #555; margin-top: 5px;">at <span class="math-inline">\{this\.escapeHtml\(filePath\)\}\:</span>{lineNumber}</div>`;
                } else {
                    const simpleLocationMatch = testCase.error.match(/at (.*?):(\d+)/);
                    if (simpleLocationMatch) {
                        const filePath = simpleLocationMatch[1];
                        const lineNumber = simpleLocationMatch[2];
                        html += `<div style="font-size: 0.8em; color: #555; margin-top: 5px;">at <span class="math-inline">\{this\.escapeHtml\(filePath\)\}\:</span>{lineNumber}</div>`;
                    }
                }
                html += `</div>`;
            }

            html += this.generateStepHTML(testCase.steps, testCase.attachments, testCase.status === 'failed');
            html += `<div class="screenshot-container">`;
            html += `<h4>Attachments</h4>`;
            for (const attachment of testCase.attachments) {
                html += `<div class="attachment-title">${attachment.title}</div>`;
                html += `<img src="${attachment.url}" class="screenshot">`;
            }
            html += `</div>`;
            if (testCase.stdout && testCase.stdout.length > 0) {
                html += `<div class="stdout-container">`;
                html += `<div class="stdout-title">Console Output (stdout)</div>`;
                html += `<pre>${this.escapeHtml(testCase.stdout.join(''))}</pre>`;
                html += `</div>`;
            }
            html += `</div>`;
        }

        html += `
            <script>
                document.addEventListener('click', function (event) {
                    if (event.target.classList.contains('parent')) {
                        event.target.parentElement.classList.toggle('expanded');
                    }
                });
            </script>
        </body>
        </html>
    `;
        fs.writeFileSync(reportFilename, html, 'utf-8');
        console.log(`HTML report generated: ${reportFilename}`);
    }

    private generateStepHTML(steps: StepInfo[], attachments: { title: string; url: string }[], testCaseFailed: boolean, level: number = 0): string {
        let html = '<ul class="steps">';
        for (const step of steps) {
            const statusClass = `status-${step.status.toLowerCase()}`;
            const isParent = step.children.length > 0;
            const parentClass = isParent ? 'parent' : '';
            const expandButton = isParent ? '[+] ' : '';
            const marginLeft = level * 20;
            html += `<li style="margin-left: ${marginLeft}px;"><span class="${parentClass} ${statusClass}" style="color: #777;">${expandButton}${this.escapeHtml(step.name)}</span>`;
            if (step.duration !== undefined) {
                html += ` <span style="font-size: 0.8em; color: #999; float: right;">(${step.duration}ms)</span>`;
            }
            if (step.children) {
                html += `<ul class="children">${this.generateStepHTML(step.children, attachments, testCaseFailed, level + 1)}</ul>`;
            }
            html += '</li>';
        }
        html += '</ul>';
        return html;
    }

    private formatDuration(milliseconds: number | undefined): string {
        if (milliseconds === undefined) {
            return 'N/A';
        }
        const totalSeconds = Math.floor(milliseconds / 1000);
        const minutes = Math.floor(totalSeconds / 60);
        const seconds = totalSeconds % 60;
        const ms = milliseconds % 1000;
        return `${minutes} min ${seconds}.${ms.toString().padStart(3, '0')} sec`;
    }

    private escapeHtml(unsafe: string): string {
        return unsafe
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }
}

export default CustomReporter;
