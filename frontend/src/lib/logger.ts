const SENSITIVE = /password|passwd|secret|token|authorization|cookie|credential|body|content/i;

type Context = Record<string, unknown>;

function redact(context: Context): Context {
  return Object.fromEntries(
    Object.entries(context).map(([key, value]) => [key, SENSITIVE.test(key) ? "[redacted]" : value]),
  );
}

function emit(level: "warn" | "error", message: string, context: Context) {
  const line = JSON.stringify({ level, message, timestamp: new Date().toISOString(), ...redact(context) });
  if (level === "error") console.error(line);
  else console.warn(line);
}

/** Console logging for diagnostics. Callers pass identifiers and statuses, never form values or note text. */
export const logger = {
  warn: (message: string, context: Context = {}) => emit("warn", message, context),
  error: (message: string, context: Context = {}) => emit("error", message, context),
};
