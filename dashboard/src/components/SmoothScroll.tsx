"use client";

import { useEffect, useRef } from "react";
import { usePathname } from "next/navigation";
import Lenis from "lenis";

/**
 * Smooth scrolling (Lenis), the same feel as steerplane.com.
 * A new page always starts at the top; back and forward keep the browser's position.
 * Off when the visitor has reduced motion turned on.
 */
export default function SmoothScroll() {
    const pathname = usePathname();
    const lenisRef = useRef<Lenis | null>(null);
    const firstRender = useRef(true);
    const lastPopState = useRef(0);

    useEffect(() => {
        const onPopState = () => {
            lastPopState.current = Date.now();
        };
        window.addEventListener("popstate", onPopState);
        return () => window.removeEventListener("popstate", onPopState);
    }, []);

    useEffect(() => {
        if (firstRender.current) {
            firstRender.current = false;
            return;
        }
        if (Date.now() - lastPopState.current < 1000) return;
        if (window.location.hash) return;
        lenisRef.current?.scrollTo(0, { immediate: true, force: true });
        window.scrollTo(0, 0);
    }, [pathname]);

    useEffect(() => {
        if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
        const lenis = new Lenis({
            lerp: 0.055,
            wheelMultiplier: 0.8,
            touchMultiplier: 1.4,
            smoothWheel: true,
            // Let scrollable boxes (tables, modals, step lists) scroll on their own.
            prevent: (node: HTMLElement) =>
                node.closest?.("[data-lenis-prevent], .modal, [role=dialog]") != null,
        });
        lenisRef.current = lenis;
        let frame = requestAnimationFrame(function raf(time: number) {
            lenis.raf(time);
            frame = requestAnimationFrame(raf);
        });
        return () => {
            cancelAnimationFrame(frame);
            lenisRef.current = null;
            lenis.destroy();
        };
    }, []);

    return null;
}
