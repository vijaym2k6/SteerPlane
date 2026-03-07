import type { Metadata } from 'next';
import './globals.css';
import Navbar from '@/components/Navbar';

export const metadata: Metadata = {
  title: 'SteerPlane — Agent Control Plane',
  description: 'Runtime guardrails, monitoring, and loop detection for autonomous AI agents.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>
        {/* Premium neural network / abstract tech background video */}
        <div className="bg-video-container">
          <video autoPlay loop muted playsInline className="bg-video">
            <source src="/bg-video-2.mp4" type="video/mp4" />
          </video>
          <div className="bg-video-overlay" />
        </div>

        <div className="bg-orb-1" />
        <div className="bg-orb-2" />
        <div className="bg-orb-3" />

        <div className="app-container">
          <Navbar />

          <main className="main-content">
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
