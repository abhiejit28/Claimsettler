import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { ThemeProvider } from "next-themes";
import { Toaster } from "@/components/ui/sonner";
import { TenantProvider } from "@/lib/theme/tenant-context";
import { getTenantConfig } from "@/lib/theme/tenant-config";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export async function generateMetadata(): Promise<Metadata> {
  const tenant = await getTenantConfig();
  return {
    title: tenant.name,
    description: `${tenant.name} claims portal`,
    icons: { icon: tenant.faviconUrl },
  };
}

export default async function RootLayout({ children }: LayoutProps<"/">) {
  const tenant = await getTenantConfig();

  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
      style={
        {
          "--primary": tenant.colors.primary,
          "--primary-foreground": tenant.colors.primaryForeground,
          ...(tenant.colors.accent ? { "--accent": tenant.colors.accent } : {}),
        } as React.CSSProperties
      }
    >
      <body className="min-h-full flex flex-col">
        <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
          <TenantProvider tenant={tenant}>{children}</TenantProvider>
          <Toaster />
        </ThemeProvider>
      </body>
    </html>
  );
}
