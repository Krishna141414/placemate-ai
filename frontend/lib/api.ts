// Client for the PlaceMate API. The session is an httpOnly cookie set by the
// backend, so every request is sent with credentials and no token is ever
// handled in JavaScript.

export const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");

export class ApiError extends Error {
  status: number;
  code: string;
  details?: { field: string; message: string }[];
  retryAfter?: number;

  constructor(status: number, code: string, message: string, details?: { field: string; message: string }[], retryAfter?: number) {
    super(message);
    this.status = status;
    this.code = code;
    this.details = details;
    this.retryAfter = retryAfter;
  }
}

type Options = {
  method?: "GET" | "POST" | "PATCH" | "PUT" | "DELETE";
  body?: unknown;
  form?: FormData;
  signal?: AbortSignal;
};

async function toApiError(response: Response): Promise<ApiError> {
  let code = "error";
  let message = "Something went wrong. Please try again.";
  let details: { field: string; message: string }[] | undefined;
  try {
    const data = await response.json();
    if (data?.error) {
      code = data.error.code ?? code;
      message = data.error.message ?? message;
      details = data.error.details;
    }
  } catch {
    // not JSON: keep the generic message
  }
  const retry = response.headers.get("Retry-After");
  return new ApiError(response.status, code, message, details, retry ? Number(retry) : undefined);
}

export async function api<T>(path: string, { method = "GET", body, form, signal }: Options = {}): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      method,
      credentials: "include",
      headers: form ? { Accept: "application/json" } : { "Content-Type": "application/json", Accept: "application/json" },
      body: form ?? (body !== undefined ? JSON.stringify(body) : undefined),
      signal,
    });
  } catch (error) {
    if ((error as Error).name === "AbortError") throw error;
    throw new ApiError(0, "network_error", "Cannot reach the PlaceMate server. Is the backend running on port 8000?");
  }
  if (!response.ok) throw await toApiError(response);
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export type SseHandler = (event: string, data: unknown) => void;

/** POST a JSON body and read the response as server-sent events. */
export async function streamSSE(path: string, body: unknown, onEvent: SseHandler, signal?: AbortSignal): Promise<void> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
      body: JSON.stringify(body),
      signal,
    });
  } catch (error) {
    if ((error as Error).name === "AbortError") throw error;
    throw new ApiError(0, "network_error", "Cannot reach the PlaceMate server. Is the backend running on port 8000?");
  }
  if (!response.ok) throw await toApiError(response);
  if (!response.body) throw new ApiError(0, "no_stream", "The server did not send a stream.");

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let boundary = buffer.indexOf("\n\n");
    while (boundary !== -1) {
      const block = buffer.slice(0, boundary);
      buffer = buffer.slice(boundary + 2);
      let event = "message";
      const dataLines: string[] = [];
      for (const line of block.split("\n")) {
        if (line.startsWith("event:")) event = line.slice(6).trim();
        else if (line.startsWith("data:")) dataLines.push(line.slice(5).trimStart());
      }
      if (dataLines.length) {
        try {
          onEvent(event, JSON.parse(dataLines.join("\n")));
        } catch {
          onEvent(event, dataLines.join("\n"));
        }
      }
      boundary = buffer.indexOf("\n\n");
    }
  }
}

/** One readable sentence for an error, for toasts and inline messages. */
export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 422 && error.details?.length) {
      return error.details.map((d) => `${d.field}: ${d.message}`).join("; ");
    }
    return error.message;
  }
  return "Something went wrong. Please try again.";
}
