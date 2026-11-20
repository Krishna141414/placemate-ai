import {
  BarChart3,
  Bot,
  ClipboardList,
  FileStack,
  FileText,
  FlaskConical,
  LayoutDashboard,
  MessageSquareText,
  ShieldCheck,
  UserCheck,
  type LucideIcon,
} from "lucide-react";

import type { Role } from "@/lib/types";

export interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
  roles: Role[];
  group: "student" | "coordinator" | "about";
  description: string;
}

export const NAV: NavItem[] = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard, roles: ["student"], group: "student", description: "Your eligibility, deadlines and plan at a glance." },
  { href: "/ask", label: "Ask PlaceMate", icon: MessageSquareText, roles: ["student", "coordinator"], group: "student", description: "Answers from the placement documents, with sources." },
  { href: "/eligibility", label: "Eligibility", icon: UserCheck, roles: ["student"], group: "student", description: "Check your profile against each company's criteria." },
  { href: "/resume", label: "Resume match", icon: FileText, roles: ["student"], group: "student", description: "Compare your resume with a job description." },
  { href: "/agent", label: "Prep agent", icon: Bot, roles: ["student"], group: "student", description: "A week-by-week plan for one company, saved only when you approve." },
  { href: "/applications", label: "Applications", icon: ClipboardList, roles: ["student"], group: "student", description: "Track where you applied and what is due." },
  { href: "/documents", label: "Documents", icon: FileStack, roles: ["coordinator"], group: "coordinator", description: "Upload and manage the documents PlaceMate answers from." },
  { href: "/analytics", label: "Analytics", icon: BarChart3, roles: ["coordinator"], group: "coordinator", description: "What students ask, what goes unanswered, who is eligible." },
  { href: "/evaluation", label: "Evaluation", icon: FlaskConical, roles: ["student", "coordinator"], group: "about", description: "How well the system performs, measured." },
  { href: "/security", label: "Security", icon: ShieldCheck, roles: ["student", "coordinator"], group: "about", description: "Each protection, with a live check." },
];

export function navFor(role: Role): NavItem[] {
  return NAV.filter((item) => item.roles.includes(role));
}

export function findNav(pathname: string): NavItem | undefined {
  return NAV.find((item) => pathname === item.href || pathname.startsWith(`${item.href}/`));
}
