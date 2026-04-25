"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useState } from "react";

import {
    ADMIN_TOKEN_EVENT,
    clearAdminToken,
    getAdminToken,
    setAdminToken,
} from "@/services/admin-auth";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const navLinks = [
    { href: "/", label: "Home" },
    { href: "/dashboard", label: "Dashboard" },
    { href: "/approvals", label: "Approvals" },
    { href: "/policies", label: "Policies" },
    { href: "/api-keys", label: "API Keys" },
];

type ApiStatus = "checking" | "connected" | "offline";

export default function Navbar() {
    const pathname = usePathname();
    const [apiStatus, setApiStatus] = useState<ApiStatus>("checking");
    const [hasAdminToken, setHasAdminToken] = useState(false);
    const [showTokenModal, setShowTokenModal] = useState(false);
    const [draftToken, setDraftToken] = useState("");

    const getIsActive = (href: string) => {
        if (href === "/") return pathname === "/";
        return pathname.startsWith(href);
    };

    useEffect(() => {
        const syncAdminToken = () => {
            const token = getAdminToken();
            setHasAdminToken(Boolean(token));
            setDraftToken(token);
        };

        const checkHealth = async () => {
            try {
                const res = await fetch(`${API_BASE}/health`, { cache: "no-store" });
                setApiStatus(res.ok ? "connected" : "offline");
            } catch {
                setApiStatus("offline");
            }
        };

        syncAdminToken();
        checkHealth();

        const interval = setInterval(checkHealth, 15000);
        window.addEventListener(ADMIN_TOKEN_EVENT, syncAdminToken);
        window.addEventListener("storage", syncAdminToken);

        return () => {
            clearInterval(interval);
            window.removeEventListener(ADMIN_TOKEN_EVENT, syncAdminToken);
            window.removeEventListener("storage", syncAdminToken);
        };
    }, []);

    const saveToken = () => {
        setAdminToken(draftToken);
        setShowTokenModal(false);
    };

    const clearToken = () => {
        clearAdminToken();
        setDraftToken("");
    };

    const apiLabel = {
        checking: "Checking API",
        connected: "API Connected",
        offline: "API Offline",
    }[apiStatus];

    return (
        <>
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

                <div className="navbar-right">
                    <button
                        type="button"
                        className={`btn btn-sm navbar-admin-button ${hasAdminToken ? "btn-success" : "btn-secondary"}`}
                        onClick={() => setShowTokenModal(true)}
                    >
                        {hasAdminToken ? "Admin Ready" : "Admin Token"}
                    </button>

                    <div className={`navbar-status ${apiStatus === "offline" ? "offline" : ""}`}>
                        <div className={`status-dot ${apiStatus === "offline" ? "status-dot-offline" : ""}`}></div>
                        <span>{apiLabel}</span>
                    </div>
                </div>
            </nav>

            <AnimatePresence>
                {showTokenModal && (
                    <div className="modal-overlay" onClick={() => setShowTokenModal(false)}>
                        <motion.div
                            className="modal-content"
                            initial={{ opacity: 0, scale: 0.95 }}
                            animate={{ opacity: 1, scale: 1 }}
                            exit={{ opacity: 0, scale: 0.95 }}
                            onClick={(e) => e.stopPropagation()}
                        >
                            <h2 className="modal-title">Admin Access Token</h2>
                            <div className="modal-form">
                                <div className="form-group">
                                    <label>Admin Token</label>
                                    <input
                                        type="password"
                                        value={draftToken}
                                        onChange={(e) => setDraftToken(e.target.value)}
                                        className="form-input"
                                        placeholder="Paste X-SteerPlane-Admin-Token value"
                                        autoFocus
                                    />
                                </div>
                                <p className="modal-helper-text">
                                    Use the token printed by the API on startup, or the value from
                                    the <code>STEERPLANE_ADMIN_TOKEN</code> environment variable.
                                </p>
                                <div className="modal-actions">
                                    <button type="button" onClick={clearToken} className="btn btn-secondary">
                                        Clear
                                    </button>
                                    <button type="button" onClick={() => setShowTokenModal(false)} className="btn btn-secondary">
                                        Cancel
                                    </button>
                                    <button type="button" onClick={saveToken} className="btn btn-primary">
                                        Save Token
                                    </button>
                                </div>
                            </div>
                        </motion.div>
                    </div>
                )}
            </AnimatePresence>
        </>
    );
}
