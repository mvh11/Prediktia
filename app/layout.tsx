import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link"; 
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Prediktia",
  description: "Predicciones deportivas con IA",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="es"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col bg-gray-950 text-white">

        {/* NAVBAR (Aqui se modfica el cambio entre pantallas)*/}
        <nav className="bg-gray-900 border-b border-gray-800 px-10 py-4">
          <div className="flex justify-between items-center">

            <h1 className="text-xl font-bold text-cyan-400">PREDIKTIA</h1>

            <div className="flex gap-6 text-gray-300 text-sm">

              <Link href="/" className="hover:text-cyan-400 transition">
                Home
              </Link>

              <Link href="/value" className="hover:text-cyan-400 transition">
                Value
              </Link>

              <Link href="/acca" className="hover:text-cyan-400 transition">
                ACCA
              </Link>

              <Link href="/planes" className="hover:text-cyan-400 transition">
                Planes
              </Link>

            </div>

          </div>
        </nav>

        {/* CONTENIDO */}
        <main className="flex-1">
          {children}
        </main>

      </body>
    </html>
  );
}
