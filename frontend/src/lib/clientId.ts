/**
 * An anonymous, random id for this browser. The API keys the application tracker by it, so
 * every visitor of a public deployment gets a private tracker without signing up.
 */
const STORAGE_KEY = "gradguide.client-id";

let fallback: string | undefined; // used when storage is blocked (private mode)

function newId(): string {
  return crypto.randomUUID();
}

export function getClientId(): string {
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (stored && /^[A-Za-z0-9-]{16,64}$/.test(stored)) return stored;
    const id = newId();
    window.localStorage.setItem(STORAGE_KEY, id);
    return id;
  } catch {
    fallback ??= newId();
    return fallback;
  }
}
