import { WorldClientError } from "@/lib/worlds/client";

export function formString(form: FormData, key: string): string {
  const value = form.get(key);
  return typeof value === "string" ? value.trim() : "";
}

export function optionalFormString(form: FormData, key: string): string | null {
  const value = formString(form, key);
  return value === "" ? null : value;
}

export function numberFormValue(form: FormData, key: string, fallback: number): number {
  const value = formString(form, key);
  if (value === "") {
    return fallback;
  }
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) {
    throw new Error(`${key} must be a number.`);
  }
  return parsed;
}

export function optionalNumberFormValue(form: FormData, key: string): number | null {
  const value = formString(form, key);
  if (value === "") {
    return null;
  }
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) {
    throw new Error(`${key} must be a number.`);
  }
  return parsed;
}

export function jsonObject(rawValue: string): Record<string, unknown> {
  if (rawValue.trim() === "") {
    return {};
  }
  const parsed = JSON.parse(rawValue) as unknown;
  if (parsed === null || typeof parsed !== "object" || Array.isArray(parsed)) {
    throw new Error("Value must be a JSON object.");
  }
  return parsed as Record<string, unknown>;
}

export function jsonNumberArray(rawValue: string): number[] {
  const parsed = JSON.parse(rawValue) as unknown;
  if (!Array.isArray(parsed) || parsed.some((item) => typeof item !== "number")) {
    throw new Error("Embedding must be a JSON array of numbers.");
  }
  const values = parsed as number[];
  if (values.length === 1536) {
    return values;
  }
  if (values.length > 1536) {
    throw new Error("Embedding cannot exceed 1536 dimensions.");
  }
  return [...values, ...Array.from({ length: 1536 - values.length }, () => 0)];
}

export function messageForError(error: unknown): string {
  if (error instanceof WorldClientError) {
    if (error.status === 403) {
      return "Forbidden";
    }
    if (error.status === 422) {
      return "Check the fields and try again.";
    }
    return error.message;
  }
  if (error instanceof SyntaxError || error instanceof Error) {
    return error.message;
  }
  return "Request failed.";
}
