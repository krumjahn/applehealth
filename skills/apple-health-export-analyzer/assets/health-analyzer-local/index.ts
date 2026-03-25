const BASE_URL = "http://127.0.0.1:8765";
const TIMEOUT_MS = 15_000;

type ToolParams = {
  command?: string;
  commandName?: string;
  skillName?: string;
};

type DailyBriefEnvelope = {
  ok?: boolean;
  success?: boolean;
  summary?: string;
  data?: {
    date?: string;
    context_summary?: string;
    steps?: {
      value?: number | null;
      baseline_7d?: number | null;
      delta_vs_baseline?: number | null;
    };
    sleep?: {
      hours?: number | null;
      baseline_7d?: number | null;
      bedtime?: string | null;
      wake_time?: string | null;
    };
    workouts?: {
      count?: number;
      total_minutes?: number;
      types?: string[];
    };
    heart_rate?: {
      average?: number | null;
      resting?: number | null;
      resting_baseline_7d?: number | null;
    };
    hrv?: {
      value?: number | null;
      baseline_7d?: number | null;
      recovery_score?: number | null;
      recovery_status?: string | null;
    };
    signals?: string[];
  };
};

type SeriesEnvelope = {
  ok?: boolean;
  success?: boolean;
  data?: {
    days?: Array<Record<string, unknown>>;
  };
};

function normalizeDate(value?: string): string | null {
  if (!value) return null;
  const match = value.match(/\b\d{4}-\d{2}-\d{2}\b/);
  return match?.[0] ?? null;
}

function todayDateString(): string {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function daysAgoDateString(daysAgo: number): string {
  const date = new Date();
  date.setDate(date.getDate() - daysAgo);
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

async function fetchJson(path: string, signal?: AbortSignal): Promise<any> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), TIMEOUT_MS);
  if (signal) {
    signal.addEventListener("abort", () => controller.abort(), { once: true });
  }

  try {
    const response = await fetch(`${BASE_URL}${path}`, { signal: controller.signal });
    if (!response.ok) {
      const body = await response.text().catch(() => "");
      throw new Error(`Local API failed (${response.status}): ${body}`);
    }
    return await response.json();
  } catch (error) {
    if ((error as Error).name === "AbortError") {
      throw new Error(`Local API timed out after ${TIMEOUT_MS}ms`);
    }
    throw error;
  } finally {
    clearTimeout(timeout);
  }
}

function formatNumber(value?: number | null, digits = 0): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "insufficient data";
  return digits > 0 ? value.toFixed(digits) : Math.round(value).toString();
}

function buildDailyBriefText(payload: DailyBriefEnvelope): string {
  const brief = payload.data ?? {};
  const steps = brief.steps ?? {};
  const sleep = brief.sleep ?? {};
  const workouts = brief.workouts ?? {};
  const heartRate = brief.heart_rate ?? {};
  const hrv = brief.hrv ?? {};
  const missing: string[] = [];

  if (sleep.hours == null) missing.push("Sleep: insufficient data");
  if (heartRate.resting == null) missing.push("Resting heart rate: insufficient data");
  if (heartRate.average == null) missing.push("Average heart rate: insufficient data");
  if (hrv.value == null) missing.push("HRV: insufficient data");

  const lines = [
    "Status",
    `- ${(brief.date ?? "Unknown date")} looks like a ${workouts.count ? "training" : "low-activity"} day relative to your recent baseline. ${brief.context_summary ?? ""}`.trim(),
    "",
    "What changed",
    `- Steps: ${formatNumber(steps.value)} vs 7-day baseline ${formatNumber(steps.baseline_7d, 1)}`,
    `- Workouts: ${workouts.total_minutes ?? 0} minutes, ${workouts.count ?? 0} workouts`,
    `- Signals: ${(brief.signals ?? []).length ? (brief.signals ?? []).join(", ") : "none"}`,
    "",
    "Suggestions",
    "1. Use this as a baseline-aware planning day rather than trying to overcorrect with a hard workout.",
    "2. Add one low-friction movement block, like a walk, if your activity is below baseline.",
    "3. If recovery metrics are missing, keep intensity moderate and use routine-based movement instead.",
    "",
    "Missing data",
    ...(missing.length ? missing.map((item) => `- ${item.replace(/^- /, "")}`) : ["- None"])
  ];

  return lines.join("\n");
}

function buildTrendComparisonText(stepsPayload: SeriesEnvelope, sleepPayload: SeriesEnvelope, command: string): string {
  const stepDays = (stepsPayload.data?.days ?? []) as Array<{ date?: string; value?: number }>;
  const sleepDays = (sleepPayload.data?.days ?? []) as Array<{ date?: string; hours?: number }>;

  const lines = [
    "Comparison for the last 7 days",
    "",
    "Steps",
    ...stepDays.map((day) => `- ${day.date ?? "Unknown"}: ${day.value ?? "insufficient data"} steps`),
    "",
    "Sleep",
    ...sleepDays.map((day) => `- ${day.date ?? "Unknown"}: ${day.hours == null ? "insufficient data" : `${Number(day.hours).toFixed(1)} h`}`),
    "",
    "Summary",
    `- Generated from the Health Data AI Analyzer local API for: ${command}`
  ];

  return lines.join("\n");
}

async function executeHealthAnalyzerTool(_toolCallId: string, params: ToolParams, signal?: AbortSignal) {
  const command = params.command?.trim() ?? "";
  const lower = command.toLowerCase();

  if (lower.includes("compare") && lower.includes("sleep") && lower.includes("step")) {
    const end = todayDateString();
    const start = daysAgoDateString(6);
    const [stepsPayload, sleepPayload] = await Promise.all([
      fetchJson(`/steps/daily?start=${start}&end=${end}`, signal),
      fetchJson(`/sleep/summary?start=${start}&end=${end}`, signal)
    ]);

    return { content: [{ type: "text" as const, text: buildTrendComparisonText(stepsPayload, sleepPayload, command) }] };
  }

  const date = normalizeDate(command) ?? todayDateString();
  const payload = (await fetchJson(`/openclaw/daily-brief?date=${date}`, signal)) as DailyBriefEnvelope;
  return { content: [{ type: "text" as const, text: buildDailyBriefText(payload) }] };
}

const healthAnalyzerLocalPlugin = {
  id: "health-analyzer-local",
  name: "Health Data AI Analyzer Local",
  description: "Deterministic local tool for daily health briefs and simple trends",
  register(api: any) {
    api.registerTool({
      name: "health_analyzer_local",
      label: "Health Data AI Analyzer Local",
      description: "Read daily briefs and recent step/sleep trends from the local Health Data AI Analyzer app.",
      parameters: {
        type: "object",
        properties: {
          command: { type: "string", description: "The raw slash-command or skill input." },
          commandName: { type: "string" },
          skillName: { type: "string" }
        },
        required: ["command"]
      },
      execute: executeHealthAnalyzerTool
    } as any);
  }
};

export default healthAnalyzerLocalPlugin;
