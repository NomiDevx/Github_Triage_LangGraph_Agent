import { NextResponse } from "next/server";
import { runPythonScript } from "@/lib/python";

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { title, body: issueBody, codeDir } = body;

    if (!title || typeof title !== "string") {
      return NextResponse.json(
        { error: "Issue title is required" },
        { status: 400 }
      );
    }

    const payload = JSON.stringify({
      title,
      body: issueBody || "",
      code_dir: codeDir || null,
    });

    const result = await runPythonScript(["main.py", "--stdin-json"], payload);

    if (result.code !== 0 && !result.stdout.trim()) {
      return NextResponse.json(
        {
          error: "Triage agent execution failed",
          details: result.stderr || "Unknown python error",
        },
        { status: 500 }
      );
    }

    // Extract JSON payload from stdout
    const trimmed = result.stdout.trim();
    // In case there is log output before or after the JSON:
    const jsonStart = trimmed.indexOf("{");
    const jsonEnd = trimmed.lastIndexOf("}");

    if (jsonStart === -1 || jsonEnd === -1) {
      return NextResponse.json(
        {
          error: "Could not parse JSON response from triage agent",
          raw_stdout: trimmed,
          stderr: result.stderr,
        },
        { status: 500 }
      );
    }

    const jsonStr = trimmed.slice(jsonStart, jsonEnd + 1);
    const data = JSON.parse(jsonStr);

    return NextResponse.json({
      success: true,
      data,
      trace_log: result.stderr,
    });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : String(err);
    return NextResponse.json(
      { error: "Server exception during triage", details: message },
      { status: 500 }
    );
  }
}
