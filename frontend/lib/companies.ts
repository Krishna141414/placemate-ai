"use client";

import { useEffect, useState } from "react";

import { api, errorMessage } from "@/lib/api";
import type { Company } from "@/lib/types";

let cache: Promise<Company[]> | null = null;

export function loadCompanies(): Promise<Company[]> {
  if (!cache) {
    cache = api<Company[]>("/api/meta/companies").catch((error) => {
      cache = null;
      throw error;
    });
  }
  return cache;
}

export function useCompanies() {
  const [companies, setCompanies] = useState<Company[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    let alive = true;
    loadCompanies()
      .then((rows) => alive && setCompanies(rows))
      .catch((err) => alive && setError(errorMessage(err)));
    return () => {
      alive = false;
    };
  }, []);
  return { companies, error };
}
