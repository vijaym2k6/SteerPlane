import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

/**
 * On the hosted demo (app.steerplane.com, NEXT_PUBLIC_STEERPLANE_DEMO=true) the
 * app should open straight into the console — steerplane.com is the marketing
 * site, so the app subdomain shouldn't show a second marketing landing.
 *
 * Self-hosted installs (demo off) keep the landing page at "/".
 */
export function middleware(request: NextRequest) {
    if (process.env.NEXT_PUBLIC_STEERPLANE_DEMO === "true") {
        return NextResponse.redirect(new URL("/dashboard", request.url));
    }
    return NextResponse.next();
}

export const config = {
    matcher: "/", // only the root path
};
