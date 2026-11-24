import { NextResponse } from "next/server";

export async function GET() {
  const samples = [
    {
      id: "bug_sample",
      label: "Complete Bug (Empty List Crash)",
      category: "bug",
      codeDir: "sample_repo",
      title: "App crashes with AttributeError when processing an empty list",
      body: `**Environment:**
- Python 3.11.4
- myapp v2.3.1
- OS: Ubuntu 22.04

**Steps to reproduce:**
1. Create an empty Python list: \`items = []\`
2. Pass it to the processor: \`result = process_items(items)\`
3. Observe the crash

**Error message:**
\`\`\`
Traceback (most recent call last):
  File "myapp/cli.py", line 18, in run
    result = process_items(items)
  File "myapp/processor.py", line 42, in process_items
    result = item.strip()
AttributeError: 'NoneType' object has no attribute 'strip'
\`\`\`

**Expected behavior:**
\`process_items([])\` should return an empty list, not crash.`,
    },
    {
      id: "incomplete_bug",
      label: "Incomplete Bug (CLI Crash - Missing Info)",
      category: "bug",
      codeDir: "sample_repo",
      title: "CLI crashes on startup with invalid config file",
      body: "Whenever I launch the CLI with --config custom.yaml it crashes immediately with a JSONDecodeError.",
    },
    {
      id: "question_sample",
      label: "Question (Retry Timeout)",
      category: "question",
      codeDir: "",
      title: "How do I configure the retry timeout?",
      body: "I've been reading the docs but I can't find where to set the HTTP retry timeout. Is it an environment variable or a config file setting? I'm on v1.4.0.",
    },
    {
      id: "feature_sample",
      label: "Feature Request (CSV Export)",
      category: "feature_request",
      codeDir: "",
      title: "Add support for CSV export",
      body: "It would be very useful to be able to export the results to a CSV file, not just JSON. This would make it easier to open the output in Excel for further analysis.",
    },
    {
      id: "docs_sample",
      label: "Documentation (Broken Tutorial Link)",
      category: "docs",
      codeDir: "",
      title: "Fix broken hyperlink in Getting Started guide",
      body: "The link to the 'Authentication Tutorial' in docs/getting-started.md line 24 points to a 404 URL (https://docs.example.com/auth-v1 instead of /auth-v2).",
    },
  ];

  return NextResponse.json({ samples });
}
