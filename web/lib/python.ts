import path from "path";
import fs from "fs";
import { spawn } from "child_process";

export function getProjectRoot(): string {
  // Check if cwd is inside web or at project root
  const cwd = process.cwd();
  if (fs.existsSync(path.join(cwd, ".venv"))) {
    return cwd;
  }
  const parent = path.resolve(cwd, "..");
  if (fs.existsSync(path.join(parent, ".venv"))) {
    return parent;
  }
  return "E:\\Agentic Ai Projects\\Github_issue_triage";
}

export function getPythonExecutable(projectRoot: string): string {
  // Windows venv path
  const winPython = path.join(projectRoot, ".venv", "Scripts", "python.exe");
  if (fs.existsSync(winPython)) {
    return winPython;
  }
  // Unix/Mac venv path
  const unixPython = path.join(projectRoot, ".venv", "bin", "python");
  if (fs.existsSync(unixPython)) {
    return unixPython;
  }
  return "python";
}

export interface PythonExecutionResult {
  stdout: string;
  stderr: string;
  code: number | null;
}

export function runPythonScript(
  args: string[],
  stdinInput?: string
): Promise<PythonExecutionResult> {
  return new Promise((resolve, reject) => {
    const projectRoot = getProjectRoot();
    const pythonExe = getPythonExecutable(projectRoot);

    const proc = spawn(pythonExe, args, {
      cwd: projectRoot,
      env: {
        ...process.env,
        PYTHONUNBUFFERED: "1",
      },
    });

    let stdout = "";
    let stderr = "";

    proc.stdout.on("data", (chunk) => {
      stdout += chunk.toString();
    });

    proc.stderr.on("data", (chunk) => {
      stderr += chunk.toString();
    });

    proc.on("error", (err) => {
      reject(err);
    });

    proc.on("close", (code) => {
      resolve({ stdout, stderr, code });
    });

    if (stdinInput !== undefined) {
      proc.stdin.write(stdinInput);
      proc.stdin.end();
    }
  });
}
