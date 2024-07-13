class HtmlGenerator {

    static getHtmlHeader(): string {
        return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: Arial, sans-serif; margin: 2em; line-height: 1.6; }
        pre { background-color: #FAFAFA; padding: 1em; border-radius: 5px; white-space: pre-wrap; word-break: break-all; }
        .expandable { cursor: pointer; background-color: #f0f0f0; border: 1px solid #ddd; padding: 0.5em; border-radius: 5px; }
        .expandable-content { display: none; margin-top: 1em; }
        .attachment { margin: 1em 0; }
        .attachment img { max-width: 100%; height: auto; }
    </style>
    <script>
        function toggleContent(event) {
            const content = event.target.nextElementSibling;
            if (content.style.display === 'none' || content.style.display === '') {
                content.style.display = 'block';
                event.target.innerHTML = 'v All Steps'; // Change to collapse icon
            } else {
                content.style.display = 'none';
                event.target.innerHTML = '> All Steps'; // Change to expand icon
            }
        }
    </script>
</head>
<body>`;
    }

    static getHtmlFooter(): string {
        return '</body></html>';
    }

    static createTextAndAttachmentsHtml(title: string, textSteps: string[], attachments: { title: string; url: string }[]) {
        const ATTACHMENT_SEPARATOR = '<hr/>';

        let htmlLines: string[] = ['<pre>', '<code>'];

        // Create expandable section for all steps
        htmlLines.push('<div class="expandable" onclick="toggleContent(event)">> All Steps</div>');
        htmlLines.push('<div class="expandable-content">');

        for (let i = 0; i < textSteps.length; ++i) {
            const stepDesc = textSteps[i];
            htmlLines.push(`<div>Step ${i + 1}: ${stepDesc}</div>`);
        }

        htmlLines.push('</div>'); // End of expandable-content

        // Insert attachments
        if (attachments.length > 0) {
            htmlLines.push('\n' + ATTACHMENT_SEPARATOR + '\n');
            for (const attachment of attachments) {
                const stepImg = `<div class="attachment"><img src='${attachment.url}' height='550' width='950'><div>${attachment.title}</div></div>`;
                htmlLines.push(stepImg);
            }
        }

        htmlLines.push('</code></pre>');

        return HtmlGenerator.getHtmlHeader() + htmlLines.join('') + HtmlGenerator.getHtmlFooter();
    }
}

export default HtmlGenerator;
