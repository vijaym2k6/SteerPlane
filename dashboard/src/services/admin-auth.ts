export const ADMIN_TOKEN_STORAGE_KEY = "steerplane_admin_token";
export const ADMIN_TOKEN_EVENT = "steerplane-admin-token-change";

export function getAdminToken(): string {
    if (typeof window === "undefined") return "";
    return window.localStorage.getItem(ADMIN_TOKEN_STORAGE_KEY)?.trim() || "";
}

export function setAdminToken(token: string): void {
    if (typeof window === "undefined") return;
    const trimmed = token.trim();
    if (trimmed) {
        window.localStorage.setItem(ADMIN_TOKEN_STORAGE_KEY, trimmed);
    } else {
        window.localStorage.removeItem(ADMIN_TOKEN_STORAGE_KEY);
    }
    window.dispatchEvent(new Event(ADMIN_TOKEN_EVENT));
}

export function clearAdminToken(): void {
    setAdminToken("");
}
