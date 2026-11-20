"use client";

import { ThemeProvider } from "next-themes";
import type { ReactNode } from "react";

import { TourProvider } from "@/components/tour/tour-provider";
import { Toaster } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { AuthProvider } from "@/lib/auth";
import { SpeedProvider } from "@/lib/speed";

export function Providers({ children }: { children: ReactNode }) {
  return (
    <ThemeProvider attribute="class" defaultTheme="light" enableSystem disableTransitionOnChange>
      <SpeedProvider>
        <AuthProvider>
          <TooltipProvider delayDuration={300}>
            <TourProvider>{children}</TourProvider>
            <Toaster position="top-right" richColors closeButton />
          </TooltipProvider>
        </AuthProvider>
      </SpeedProvider>
    </ThemeProvider>
  );
}
