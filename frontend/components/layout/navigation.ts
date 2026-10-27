import { BriefcaseBusiness, Home, Users, Settings2 } from "lucide-react";
export const mainNavigation = [
  {label: "Home", href: "/", icon: Home},
  {label: "Jobs", href: "/jobs", icon: BriefcaseBusiness},
  {label: "Candidates", href: "/candidates", icon: Users},
];
export const settingsNavigation = {label: "Settings & tools", href: "/settings", icon: Settings2};
export const advancedPaths = ["/settings", "/rankings", "/ai-tools", "/automation", "/evaluation"];
export function navigationActive(pathname: string, href: string) {
  return href === "/settings" ? advancedPaths.some(path => pathname === path || pathname.startsWith(path + "/")) : pathname === href || (href !== "/" && pathname.startsWith(href + "/"));
}
