"use client";

import { useQuery } from "@tanstack/react-query";
import { getCandidates } from "@/services/candidateService";

export function useCandidates() {
  return useQuery({
    queryKey: ["candidates"],
    queryFn: getCandidates,
  });
}
