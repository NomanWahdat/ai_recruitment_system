"use client";

import { useQuery } from "@tanstack/react-query";
import { getJobs } from "@/services/jobService";

export function useJobs() {
  return useQuery({
    queryKey: ["jobs"],
    queryFn: getJobs,
  });
}
