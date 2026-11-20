"use client";

import { motion } from "motion/react";

import { useSpeed } from "@/lib/speed";

// Re-mounts on every navigation inside the app, giving each page a short fade.
export default function AppTemplate({ children }: { children: React.ReactNode }) {
  const { reduced } = useSpeed();
  return (
    <motion.div
      className="app-container"
      initial={reduced ? false : { opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.28, ease: [0.16, 1, 0.3, 1] }}
    >
      {children}
    </motion.div>
  );
}
