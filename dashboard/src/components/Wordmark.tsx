"use client";

import { useEffect, useRef } from "react";

/**
 * Big STEERPLANE wordmark for the bottom of the page, drawn as a grid of small
 * squares on a canvas.
 *
 * - As the footer scrolls into view, the squares drift down from above and
 *   settle into the letters. Scrolling back up lifts them off again.
 * - Near the pointer (mouse or finger) the squares are pushed aside and light up.
 * - Only animates while on screen. With reduced motion turned on, it is drawn
 *   once, already settled, and ignores the pointer.
 *
 * Same file in steerplane-web, the public dashboard and the partner dashboard.
 */

const TEXT = "STEERPLANE";
const FONT = "Orbitron";
// Letters are drawn taller than the font's own shape, for a big poster-style word.
const STRETCH = 1.2;
// Top to bottom: light sky blue to deep brand blue.
const STOPS: [number, [number, number, number]][] = [
    [0, [191, 219, 254]],
    [0.45, [96, 165, 250]],
    [1, [37, 99, 235]],
];

type Dot = {
    hx: number; hy: number; // home position
    fx: number; fy: number; // where it floats from
    delay: number;
    ox: number; oy: number; // current push from the pointer
    glow: number;
    color: string;
};

function mix(t: number): [number, number, number] {
    for (let i = 1; i < STOPS.length; i++) {
        const [p1, c1] = STOPS[i];
        const [p0, c0] = STOPS[i - 1];
        if (t <= p1) {
            const k = (t - p0) / (p1 - p0);
            return [0, 1, 2].map((j) => Math.round(c0[j] + (c1[j] - c0[j]) * k)) as [number, number, number];
        }
    }
    return STOPS[STOPS.length - 1][1];
}

const clamp = (v: number, a = 0, b = 1) => Math.min(b, Math.max(a, v));
const easeOut = (t: number) => 1 - Math.pow(1 - t, 3);

export default function Wordmark({ className = "" }: { className?: string }) {
    const wrapRef = useRef<HTMLDivElement>(null);
    const canvasRef = useRef<HTMLCanvasElement>(null);

    useEffect(() => {
        const wrap = wrapRef.current;
        const canvas = canvasRef.current;
        if (!wrap || !canvas) return;
        const ctx = canvas.getContext("2d");
        if (!ctx) return;

        const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
        let dots: Dot[] = [];
        let cell = 6;
        let size = 5;
        let W = 0;
        let dpr = 1;
        let H = 0;
        let visible = false;
        let frame = 0;
        let alive = true;
        const pointer = { x: -9999, y: -9999, active: false };
        // Shown progress eases toward the scroll position, so the squares
        // drift in over about two and a half seconds instead of snapping with the scroll.
        let shown = reduce ? 1 : 0;

        // Seeded random, so the float-in pattern is the same on every visit.
        let seed = 7;
        const rand = () => {
            seed = (seed * 16807) % 2147483647;
            return seed / 2147483647;
        };

        const build = () => {
            W = Math.max(1, wrap.clientWidth);
            cell = Math.max(3, Math.round(W / 140));
            size = Math.max(2, Math.round(cell * 0.8));

            // Lay the word out on a hidden canvas at full width, then sample it.
            const probe = document.createElement("canvas");
            const pctx = probe.getContext("2d");
            if (!pctx) return;
            const base = 200;
            pctx.font = `900 ${base}px ${FONT}, sans-serif`;
            const gap = base * 0.06;
            const widths = [...TEXT].map((ch) => pctx.measureText(ch).width);
            const total = widths.reduce((a, b) => a + b, 0) + gap * (TEXT.length - 1);
            const scale = W / total;
            const fontPx = base * scale;
            H = Math.ceil(fontPx * STRETCH);

            probe.width = W;
            probe.height = H;
            pctx.font = `900 ${fontPx}px ${FONT}, sans-serif`;
            pctx.textBaseline = "alphabetic";
            pctx.setTransform(1, 0, 0, STRETCH, 0, 0);
            pctx.fillStyle = "#fff";
            let x = 0;
            [...TEXT].forEach((ch, i) => {
                pctx.fillText(ch, x, fontPx * 0.8);
                x += (widths[i] + gap) * scale;
            });

            pctx.setTransform(1, 0, 0, 1, 0, 0);
            const data = pctx.getImageData(0, 0, W, H).data;

            // Crop to the rows that hold letters, so there is no empty band.
            let top = H;
            let bottom = 0;
            for (let y = 0; y < H; y++) {
                for (let x = 0; x < W; x += 2) {
                    if (data[(y * W + x) * 4 + 3] >= 128) {
                        if (y < top) top = y;
                        bottom = y;
                        break;
                    }
                }
            }
            if (bottom < top) return;
            const rows = Math.ceil((bottom - top + 1) / cell);
            const fullH = H;
            H = rows * cell;

            seed = 7;
            dots = [];
            for (let r = 0; r < rows; r++) {
                const y = r * cell;
                const rgb = mix(y / H);
                const color = `rgb(${rgb[0]},${rgb[1]},${rgb[2]})`;
                for (let cx = 0; cx < W; cx += cell) {
                    const sx = Math.min(W - 1, cx + (cell >> 1));
                    const sy = Math.min(fullH - 1, top + y + (cell >> 1));
                    if (data[(sy * W + sx) * 4 + 3] < 128) continue;
                    dots.push({
                        hx: cx, hy: y,
                        fx: cx + (rand() - 0.5) * W * 0.12,
                        fy: y - H * (0.5 + rand() * 1.1),
                        // Left letters land first, with some scatter.
                        delay: (cx / W) * 0.3 + rand() * 0.2,
                        ox: 0, oy: 0, glow: 0,
                        color,
                    });
                }
            }

            dpr = Math.min(2, window.devicePixelRatio || 1);
            canvas.width = Math.round(W * dpr);
            canvas.height = Math.round(H * dpr);
            canvas.style.height = `${canvas.height / dpr}px`;
            ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        };

        // 0 = scattered above, 1 = settled. Driven by scroll position.
        const progress = () => {
            if (reduce) return 1;
            // Fully formed only at the very bottom of the page. While part of the
            // word is still below the screen edge it is partly scattered, so the
            // outro starts as soon as you scroll back up.
            const r = canvas.getBoundingClientRect();
            const vh = window.innerHeight;
            const gap = Math.max(0, document.documentElement.scrollHeight - (r.bottom + window.scrollY));
            return clamp((vh - r.top - r.height * 0.35) / (r.height * 0.65 + gap));
        };

        const draw = () => {
            // Intro (settling) is slow; outro (lifting off when you scroll back
            // up) is quicker, so it plays while the word is still on screen.
            const target = progress();
            shown += (target - shown) * (target > shown ? 0.024 : 0.07);
            if (Math.abs(target - shown) < 0.001) shown = target;
            const p = shown;
            const R = cell * 10;
            // Clear every device pixel. With screen scaling (125%, 150%) the canvas
            // is a fraction of a pixel taller than H, and a partial clear leaves
            // a strip at the bottom where pushed squares pile up into a line.
            ctx.setTransform(1, 0, 0, 1, 0, 0);
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
            for (const d of dots) {
                const local = easeOut(clamp((p - d.delay * 0.6) / 0.55));
                if (local <= 0.001) continue;

                // Pointer push and glow, eased so it springs back.
                let tx = 0;
                let ty = 0;
                let tg = 0;
                if (pointer.active && !reduce) {
                    const dx = d.hx - pointer.x;
                    const dy = d.hy - pointer.y;
                    const dist = Math.hypot(dx, dy);
                    if (dist < R && dist > 0.01) {
                        const f = Math.pow(1 - dist / R, 2);
                        tx = (dx / dist) * f * R * 0.55;
                        ty = (dy / dist) * f * R * 0.55;
                        tg = f;
                    }
                }
                d.ox += (tx - d.ox) * 0.16;
                d.oy += (ty - d.oy) * 0.16;
                d.glow += (tg - d.glow) * 0.12;
                // Clear tiny leftovers, or a square sits a fraction of a pixel off
                // after the pointer leaves and leaves a faint line under the word.
                if (Math.abs(d.ox) < 0.05) d.ox = 0;
                if (Math.abs(d.oy) < 0.05) d.oy = 0;
                if (d.glow < 0.01) d.glow = 0;

                // Snapped to whole device pixels so every square stays crisp.
                const x = Math.round((d.fx + (d.hx - d.fx) * local + d.ox) * dpr) / dpr;
                const y = Math.round((d.fy + (d.hy - d.fy) * local + d.oy) * dpr) / dpr;
                ctx.globalAlpha = local;
                ctx.fillStyle = d.color;
                ctx.fillRect(x, y, size, size);
                if (d.glow > 0.02) {
                    ctx.globalAlpha = local * d.glow * 0.85;
                    ctx.fillStyle = "#ffffff";
                    ctx.fillRect(x, y, size, size);
                }
            }
            ctx.globalAlpha = 1;
        };

        const loop = () => {
            frame = 0;
            if (!alive || !visible) return;
            draw();
            frame = requestAnimationFrame(loop);
        };
        const start = () => {
            if (!frame && visible && !reduce) frame = requestAnimationFrame(loop);
        };

        const io = new IntersectionObserver(
            ([e]) => {
                visible = e.isIntersecting;
                // Fully off screen: start from scattered, so the intro plays again next time.
                if (!visible && !reduce) shown = 0;
                if (reduce) draw();
                else start();
            },
            { rootMargin: "200px 0px" },
        );

        let lastW = 0;
        const ro = new ResizeObserver(() => {
            if (wrap.clientWidth === lastW) return;
            lastW = wrap.clientWidth;
            build();
            draw();
        });

        const onMove = (e: PointerEvent) => {
            const r = canvas.getBoundingClientRect();
            pointer.x = e.clientX - r.left;
            pointer.y = e.clientY - r.top;
            pointer.active = true;
        };
        const onLeave = () => {
            pointer.active = false;
        };

        // Wait for the display font, or the word is sampled in a fallback font.
        const fontReady = document.fonts
            ? Promise.race([
                  document.fonts.load(`900 100px ${FONT}`),
                  new Promise((r) => setTimeout(r, 2500)),
              ])
            : Promise.resolve();

        fontReady.then(() => {
            if (!alive) return;
            lastW = wrap.clientWidth;
            build();
            draw();
            ro.observe(wrap);
            io.observe(wrap);
            canvas.addEventListener("pointermove", onMove, { passive: true });
            canvas.addEventListener("pointerleave", onLeave);
            canvas.addEventListener("pointercancel", onLeave);
        });

        return () => {
            alive = false;
            cancelAnimationFrame(frame);
            io.disconnect();
            ro.disconnect();
            canvas.removeEventListener("pointermove", onMove);
            canvas.removeEventListener("pointerleave", onLeave);
            canvas.removeEventListener("pointercancel", onLeave);
        };
    }, []);

    return (
        <div ref={wrapRef} className={`sp-wordmark ${className}`} aria-hidden="true">
            <canvas ref={canvasRef} style={{ display: "block", width: "100%", touchAction: "pan-y" }} />
        </div>
    );
}
