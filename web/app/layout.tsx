import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Noveland",
  description: "Persistent virtual-world operating system for AI agents.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
