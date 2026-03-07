"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion } from "framer-motion";

const navLinks = [
    { href: "/", label: "Home" },
    { href: "/dashboard", label: "Dashboard" },
];

export default function Navbar() {
    const pathname = usePathname();

    // Determine which link is active
    const getIsActive = (href: string) => {
        if (href === "/") return pathname === "/";
        return pathname.startsWith(href);
    };

    return (
        <nav className="navbar">
            <div className="navbar-brand">
                <Link href="/" className="navbar-logo">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                        <polygon points="12 2 2 7 12 12 22 7 12 2" />
                        <polyline points="2 17 12 22 22 17" />
                        <polyline points="2 12 12 17 22 12" />
                    </svg>
                    SteerPlane
                </Link>
                <span className="navbar-tagline">Advanced Agent Control Plane</span>
            </div>

            <div className="navbar-nav">
                {navLinks.map((link) => {
                    const isActive = getIsActive(link.href);
                    return (
                        <Link
                            key={link.href}
                            href={link.href}
                            className={`navbar-link ${isActive ? "active" : ""}`}
                        >
                            {isActive && (
                                <motion.span
                                    className="navbar-active-bg"
                                    layoutId="navbar-active-pill"
                                    transition={{ type: "spring", stiffness: 380, damping: 30 }}
                                />
                            )}
                            <span style={{ position: "relative", zIndex: 1 }}>{link.label}</span>
                        </Link>
                    );
                })}
                <a
                    href="http://localhost:8000/docs"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="navbar-link"
                >
                    <span style={{ position: "relative", zIndex: 1 }}>API Docs</span>
                </a>
            </div>

            <div className="navbar-status">
                <div className="status-dot"></div>
                <span>API Connected</span>
            </div>
        </nav>
    );
}
