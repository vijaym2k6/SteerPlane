"use client";

import Link from "next/link";
import Image from "next/image";
import { usePathname } from "next/navigation";
import { motion } from "framer-motion";

const navLinks = [
    { href: "/", label: "Home" },
    { href: "/dashboard", label: "Dashboard" },
    { href: "/policies", label: "Policies" },
    { href: "/api-keys", label: "API Keys" },
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
                    <Image
                        src="/SteerPlane_Logo.jpg"
                        alt="SteerPlane"
                        className="navbar-logo-img"
                        width={40}
                        height={40}
                    />
                    <span className="navbar-logo-text">STEERPLANE</span>
                </Link>
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
            </div>

            <div className="navbar-status">
                <div className="status-dot"></div>
                <span>API Connected</span>
            </div>
        </nav>
    );
}
