import { NextResponse } from "next/server";
import { runPythonScript } from "@/lib/python";

export async function POST() {
  try {
    const result = await runPythonScript(["evals/run_evals.py", "--json-output"]);

    const trimmed = result.stdout.trim();
    const jsonStart = trimmed.indexOf("{");
    const jsonEnd = trimmed.lastIndexOf("}");

    if (jsonStart === -1 || jsonEnd === -1) {
      return NextResponse.json(
        {
          error: "Failed to parse evals runner JSON output",
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
    });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : String(err);
    return NextResponse.json(
      { error: "Server exception during evals", details: message },
      { status: 500 }
    );
  }
}
