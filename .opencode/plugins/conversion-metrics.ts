import { mkdir, open, readFile, readdir, rename, rm, stat, utimes } from "node:fs/promises"
import { join } from "node:path"
import { tool, type Plugin, type PluginInput } from "@opencode-ai/plugin"

const SCHEMA_VERSION = 1
const STATE_DIR = ".opencode/conversion-metrics"
const DAG_FILE = "mimic-iv/concept_dag/concept_dag.json"
const METRICS_DIR = "mimic-iv/concepts_fhir/metrics"
const CONCEPT_RE = /^[A-Za-z0-9][A-Za-z0-9_-]*$/
const SESSION_RE = /^[A-Za-z0-9_-]{1,256}$/
const LOCK_STALE_MS = 15 * 60_000
const LOCK_RETRY_MS = 100
const LOCK_TIMEOUT_MS = 120_000

type Binding = {
  schema_version: 1
  tracker_version: string
  concept: string
  run: number
  root_session_ids: string[]
  sessions: Record<string, { attached_at: string }>
  started_at: string
  finalized: boolean
  finalized_at?: string
  output_path?: string
  finalized_before_terminal_response?: true
}

type BindingFile = { path: string; binding: Binding }
type FinalizeResult = { title: string; output: string }

function codeIs(error: unknown, code: string): boolean {
  return typeof error === "object" && error !== null && "code" in error &&
    (error as { code?: unknown }).code === code
}

function stateDir(root: string): string {
  return join(root, STATE_DIR)
}

function conceptDir(root: string, concept: string): string {
  return join(stateDir(root), concept)
}

function metricsDir(root: string, concept: string): string {
  return join(root, METRICS_DIR, concept)
}

function bindingPath(root: string, concept: string, run: number): string {
  return join(conceptDir(root, concept), `run-${String(run).padStart(4, "0")}.json`)
}

function expectedOutputPath(root: string, concept: string, run: number): string {
  return join(metricsDir(root, concept), `run_${String(run).padStart(4, "0")}.json`)
}

function validateSession(sessionID: string): void {
  if (!SESSION_RE.test(sessionID)) throw new Error("Unsupported OpenCode session ID")
}

async function validateConcept(root: string, argument: string): Promise<string> {
  if (typeof argument !== "string") throw new Error("Usage: /goal <concept>")
  const concept = argument.trim()
  if (!concept || !CONCEPT_RE.test(concept)) throw new Error("Usage: /goal <concept>")

  const dag = JSON.parse(await readFile(join(root, DAG_FILE), "utf8")) as {
    nodes?: Record<string, { stem?: unknown }>
  }
  const node = dag.nodes?.[concept]
  if (!node || node.stem !== concept) throw new Error(`Unknown DAG concept: ${concept}`)
  return concept
}

function isGoalControl(argument: unknown): boolean {
  if (typeof argument !== "string") return true
  const args = argument.trim()
  if (!args) return true
  if (["status", "history", "resume", "list"].includes(args)) return true
  const lower = args.toLowerCase()
  return (
    args === "edit" || lower.startsWith("edit ") ||
    args === "focus" || lower.startsWith("focus ") ||
    args === "add" || lower.startsWith("add ")
  )
}

function sleep(milliseconds: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, milliseconds))
}

async function acquireLock(root: string): Promise<() => Promise<void>> {
  const directory = stateDir(root)
  await mkdir(directory, { recursive: true })
  const lock = join(directory, ".lock")
  const started = Date.now()

  while (Date.now() - started < LOCK_TIMEOUT_MS) {
    try {
      await mkdir(lock)
      let released = false
      const heartbeat = setInterval(() => {
        void utimes(lock, new Date(), new Date()).catch(() => undefined)
      }, 5_000)
      return async () => {
        if (released) return
        released = true
        clearInterval(heartbeat)
        await rm(lock, { recursive: true, force: true })
      }
    } catch (error) {
      if (!codeIs(error, "EEXIST")) throw error
      try {
        if (Date.now() - (await stat(lock)).mtimeMs > LOCK_STALE_MS) {
          await rm(lock, { recursive: true, force: true })
        }
      } catch (statError) {
        if (!codeIs(statError, "ENOENT")) throw statError
      }
      await sleep(LOCK_RETRY_MS)
    }
  }
  throw new Error("Timed out waiting for conversion metric state lock")
}

async function writeAtomic(path: string, value: Binding): Promise<void> {
  const temporary = `${path}.tmp-${Date.now()}-${Math.random().toString(36).slice(2)}`
  let handle: Awaited<ReturnType<typeof open>> | undefined
  try {
    handle = await open(temporary, "wx")
    await handle.writeFile(`${JSON.stringify(value, null, 2)}\n`, "utf8")
    await handle.sync()
    await handle.close()
    handle = undefined
    await rename(temporary, path)
  } catch (error) {
    if (handle) await handle.close().catch(() => undefined)
    await rm(temporary, { force: true }).catch(() => undefined)
    throw error
  }
}

function parseBinding(value: unknown, path: string): Binding {
  if (typeof value !== "object" || value === null) throw new Error(`Invalid binding: ${path}`)
  const binding = value as Partial<Binding>
  if (
    binding.schema_version !== SCHEMA_VERSION ||
    typeof binding.tracker_version !== "string" ||
    typeof binding.concept !== "string" ||
    !CONCEPT_RE.test(binding.concept) ||
    typeof binding.run !== "number" ||
    !Number.isSafeInteger(binding.run) ||
    binding.run < 1 ||
    !Array.isArray(binding.root_session_ids) ||
    binding.root_session_ids.length === 0 ||
    typeof binding.sessions !== "object" ||
    binding.sessions === null ||
    typeof binding.started_at !== "string" ||
    typeof binding.finalized !== "boolean" ||
    new Set(binding.root_session_ids).size !== binding.root_session_ids.length
  ) {
    throw new Error(`Invalid binding: ${path}`)
  }

  const sessions = binding.sessions as Record<string, { attached_at?: unknown }>
  for (const sessionID of binding.root_session_ids) {
    if (typeof sessionID !== "string" || !SESSION_RE.test(sessionID)) {
      throw new Error(`Invalid session in binding: ${path}`)
    }
    if (typeof sessions[sessionID]?.attached_at !== "string") {
      throw new Error(`Missing session attachment: ${path}`)
    }
  }
  return binding as Binding
}

async function readBinding(path: string): Promise<BindingFile> {
  return { path, binding: parseBinding(JSON.parse(await readFile(path, "utf8")), path) }
}

async function bindingsFor(root: string, concept: string): Promise<BindingFile[]> {
  const directory = conceptDir(root, concept)
  let entries
  try {
    entries = await readdir(directory, { withFileTypes: true })
  } catch (error) {
    if (codeIs(error, "ENOENT")) return []
    throw error
  }
  const result: BindingFile[] = []
  for (const entry of entries) {
    if (!entry.isFile() || !/^run-0*[1-9][0-9]*\.json$/.test(entry.name)) continue
    result.push(await readBinding(join(directory, entry.name)))
  }
  return result
}

async function allBindings(root: string): Promise<BindingFile[]> {
  const directory = stateDir(root)
  let entries
  try {
    entries = await readdir(directory, { withFileTypes: true })
  } catch (error) {
    if (codeIs(error, "ENOENT")) return []
    throw error
  }
  const result: BindingFile[] = []
  for (const entry of entries) {
    if (!entry.isDirectory() || !CONCEPT_RE.test(entry.name)) continue
    result.push(...(await bindingsFor(root, entry.name)))
  }
  return result
}

async function committedRuns(root: string, concept: string): Promise<Map<number, string>> {
  const directory = metricsDir(root, concept)
  let entries
  try {
    entries = await readdir(directory, { withFileTypes: true })
  } catch (error) {
    if (codeIs(error, "ENOENT")) return new Map()
    throw error
  }
  const result = new Map<number, string>()
  for (const entry of entries) {
    const match = entry.isFile() && entry.name.match(/^run_([0-9]+)\.json$/)
    if (!match) continue
    const run = Number(match[1])
    if (Number.isSafeInteger(run)) result.set(run, join(directory, entry.name))
  }
  return result
}

async function reconcile(
  bindings: BindingFile[],
  outputs: Map<number, string>,
): Promise<void> {
  for (const file of bindings) {
    const output = outputs.get(file.binding.run)
    if (!output || file.binding.finalized) continue
    file.binding = {
      ...file.binding,
      finalized: true,
      finalized_at: new Date().toISOString(),
      output_path: output,
      finalized_before_terminal_response: true,
    }
    await writeAtomic(file.path, file.binding)
  }
}

function newest(files: BindingFile[]): BindingFile | undefined {
  return [...files].sort((a, b) => b.binding.run - a.binding.run)[0]
}

function freshSessionError(sessionID: string, concept: string): Error {
  return new Error(
    `Root session ${sessionID} already belongs to a ${concept} metric run; start a fresh OpenCode session.`,
  )
}

async function bindGoal(root: string, concept: string, sessionID: string): Promise<void> {
  validateSession(sessionID)
  const release = await acquireLock(root)
  try {
    const bindings = await allBindings(root)
    const conceptFiles = await bindingsFor(root, concept)
    const outputs = await committedRuns(root, concept)
    await reconcile(conceptFiles, outputs)

    const owned = bindings
      .filter((file) => file.binding.root_session_ids.includes(sessionID))
      .sort((a, b) => b.binding.run - a.binding.run)
    const foreign = owned.find((file) => file.binding.concept !== concept)
    if (foreign) throw new Error(`Root session ${sessionID} is already bound to another concept`)

    const sameConcept = owned.filter((file) => file.binding.concept === concept)
    const latest = newest(conceptFiles)
    if (sameConcept.length > 0) {
      if (
        sameConcept.length === 1 &&
        latest &&
        sameConcept[0].path === latest.path &&
        !latest.binding.finalized
      ) return
      throw freshSessionError(sessionID, concept)
    }

    if (latest && !latest.binding.finalized) {
      const attachedAt = new Date().toISOString()
      const resumed: Binding = {
        ...latest.binding,
        root_session_ids: [...latest.binding.root_session_ids, sessionID],
        sessions: { ...latest.binding.sessions, [sessionID]: { attached_at: attachedAt } },
      }
      await writeAtomic(latest.path, resumed)
      return
    }

    const maxBinding = conceptFiles.reduce((max, file) => Math.max(max, file.binding.run), 0)
    const maxCommitted = [...outputs.keys()].reduce((max, run) => Math.max(max, run), 0)
    const run = Math.max(maxBinding, maxCommitted) + 1
    const startedAt = new Date().toISOString()
    await mkdir(conceptDir(root, concept), { recursive: true })
    await writeAtomic(bindingPath(root, concept, run), {
      schema_version: SCHEMA_VERSION,
      tracker_version: "1",
      concept,
      run,
      root_session_ids: [sessionID],
      sessions: { [sessionID]: { attached_at: startedAt } },
      started_at: startedAt,
      finalized: false,
    })
  } finally {
    await release()
  }
}

function outputPath(text: string): string | undefined {
  try {
    const parsed = JSON.parse(text) as Record<string, unknown>
    for (const key of ["output_path", "outputPath", "artifact_path", "path"]) {
      if (typeof parsed[key] === "string" && parsed[key]) return parsed[key] as string
    }
  } catch {
    // The Python CLI currently prints a labelled human-readable path.
  }
  const match = text.match(/(?:output[_ ]path|artifact[_ ]path)\s*[:=]\s*(\S+)|Wrote conversion metrics:\s*(\S+)/i)
  return match?.[1] ?? match?.[2]
}

function shortOutput(stdout: string, stderr: string): string {
  const text = [stdout.trim(), stderr.trim()].filter(Boolean).join("\n") || "metrics-finalize completed"
  return text.length > 2_000 ? `${text.slice(0, 1_997)}...` : text
}

function reportPath(text: string): string | undefined {
  return text.match(/Wrote metrics report:\s*(\S+)/)?.[1]
}

/**
 * Regenerate the HTML rollup after a successful finalize.  Cosmetic only: every
 * failure mode -- non-zero exit, spawn failure, a thrown shell helper -- is
 * swallowed, because a broken report must never fail a finalize that already
 * wrote its artifact and its binding.
 */
async function refreshReport(root: string, $: PluginInput["$"]): Promise<string> {
  try {
    const result = await $.cwd(root).nothrow()`${["uv", "run", "mimic_utils", "metrics-report"]}`
    const stdout = result.stdout.toString("utf8")
    const stderr = result.stderr.toString("utf8")
    if (result.exitCode !== 0) {
      const reason = [stderr.trim(), stdout.trim()].filter(Boolean).join(" ").split("\n")[0] ?? ""
      return `Report skipped: metrics-report exited ${result.exitCode}${reason ? ` (${reason.slice(0, 200)})` : ""}`
    }
    const path = reportPath(stdout) ?? reportPath(stderr)
    return path ? `Report refreshed: ${path}` : "Report refreshed: metrics report regenerated"
  } catch (error) {
    // Even describing the failure must not throw (a Symbol or a throwing
    // toString() would otherwise escape and take the finalize down with it).
    try {
      const reason = error instanceof Error ? error.message : String(error)
      return `Report skipped: ${reason.slice(0, 200)}`
    } catch {
      return "Report skipped: metrics-report could not be run"
    }
  }
}

async function finalize(
  root: string,
  $: PluginInput["$"],
  conceptArgument: string,
  sessionID: string,
): Promise<FinalizeResult> {
  const concept = await validateConcept(root, conceptArgument)
  validateSession(sessionID)
  const release = await acquireLock(root)
  try {
    const files = await bindingsFor(root, concept)
    const outputs = await committedRuns(root, concept)
    await reconcile(files, outputs)
    const owned = files
      .filter((file) => file.binding.root_session_ids.includes(sessionID))
      .sort((a, b) => b.binding.run - a.binding.run)
    const active = owned.find((file) => !file.binding.finalized)
    if (!active) {
      const done = owned.find((file) => file.binding.finalized)
      if (!done) throw new Error(`No ${concept} metric binding for root session ${sessionID}`)
      const path = done.binding.output_path ?? outputs.get(done.binding.run) ??
        expectedOutputPath(root, concept, done.binding.run)
      return {
        title: `Conversion metrics already finalized: ${concept} run ${done.binding.run}`,
        output: `Conversion metrics already finalized: ${path}`,
      }
    }

    const args = ["uv", "run", "mimic_utils", "metrics-finalize", concept, "--run", String(active.binding.run)]
    for (const rootSession of active.binding.root_session_ids) {
      validateSession(rootSession)
      args.push("--session-id", rootSession)
    }
    const result = await $.cwd(root).nothrow()`${args}`
    const stdout = result.stdout.toString("utf8")
    const stderr = result.stderr.toString("utf8")
    if (result.exitCode !== 0) {
      throw new Error(`metrics-finalize failed for ${concept} run ${active.binding.run}: ${shortOutput(stdout, stderr)}`)
    }

    const finalized: Binding = {
      ...active.binding,
      finalized: true,
      finalized_at: new Date().toISOString(),
      finalized_before_terminal_response: true,
    }
    const path = outputPath(stdout) ?? outputPath(stderr)
    if (path) finalized.output_path = path
    await writeAtomic(active.path, finalized)
    return {
      title: `Conversion metrics finalized: ${concept} run ${active.binding.run}`,
      output: `${shortOutput(stdout, stderr)}\n${await refreshReport(root, $)}`,
    }
  } finally {
    await release()
  }
}

export default (async ({ $, worktree }) => {
  const finalizeTool = tool({
    description: "Finalize metrics for the active conversion run.",
    args: { concept: tool.schema.string().describe("Exact DAG concept stem") },
    execute: async ({ concept }, context) => finalize(worktree, $, concept, context.sessionID),
  })

  return {
    "command.execute.before": async (input: {
      command: string
      sessionID: string
      arguments: string
    }) => {
      if (input.command !== "goal" || isGoalControl(input.arguments)) return
      await bindGoal(worktree, await validateConcept(worktree, input.arguments), input.sessionID)
    },
    tool: { conversion_metrics_finalize: finalizeTool },
  }
}) satisfies Plugin
