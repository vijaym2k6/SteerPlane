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
                    <img
                        src="/SteerPlane_Logo.jpg"
                        alt="SteerPlane"
                        className="navbar-logo-img"
                    />
                    <span className="navbar-logo-text">STEER PLANE</span>
                </Link>
                <span className="navbar-tagline">Runtime Control Plane for AI Agents</span>
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
