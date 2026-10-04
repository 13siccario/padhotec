import type { Metadata } from "next";
import { Funnel_Display, Funnel_Sans, Instrument_Serif } from "next/font/google";
import { AuthProvider } from "@/lib/auth";
import "./globals.css";

const sans = Funnel_Sans({ variable: "--font-sans", subsets: ["latin"] });
const display = Funnel_Display({ variable: "--font-display", subsets: ["latin"] });
const serif = Instrument_Serif({ variable: "--font-serif", subsets: ["latin"], weight: "400" });

export const metadata: Metadata = {
  title: "Padhotec",
  description: "Study smarter with honest numbers: what you know, what to do next, and how sure we are.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${sans.variable} ${display.variable} ${serif.variable} h-full antialiased`}>
      <body className="min-h-full">
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
