"use client";

import { LogOut, Moon, Sun } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useTheme } from "next-themes";
import { useEffect, type ReactNode } from "react";

import { StatusView } from "@/components/shared/status-view";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarInset,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarProvider,
  SidebarTrigger,
  useSidebar,
} from "@/components/ui/sidebar";
import { Skeleton } from "@/components/ui/skeleton";
import { homeFor, useAuth } from "@/lib/auth";
import { findNav, navFor, type NavItem } from "@/lib/nav";

const GROUP_LABELS: Record<NavItem["group"], string> = {
  student: "Workspace",
  coordinator: "Placement cell",
  about: "About the system",
};

function Logo() {
  return (
    <Link href="/" aria-label="PlaceMate home" className="flex items-center gap-2.5 rounded-md px-2 py-1.5">
      <svg width="26" height="26" viewBox="0 0 26 26" aria-hidden="true">
        <rect width="26" height="26" rx="7" fill="currentColor" opacity="0.12" />
        <path d="M8 18V8h5.2a3.6 3.6 0 0 1 0 7.2H8" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
        <circle cx="18.5" cy="18" r="1.6" fill="currentColor" />
      </svg>
      <span className="text-[15px] font-semibold tracking-tight">PlaceMate</span>
    </Link>
  );
}

function CloseOnNavigate() {
  const pathname = usePathname();
  const { setOpenMobile } = useSidebar();
  useEffect(() => setOpenMobile(false), [pathname, setOpenMobile]);
  return null;
}

function AppSidebar() {
  const pathname = usePathname();
  const { user } = useAuth();
  if (!user) return null;
  const items = navFor(user.role);
  const groups = (["student", "coordinator", "about"] as const)
    .map((group) => ({ group, items: items.filter((item) => item.group === group) }))
    .filter((entry) => entry.items.length);

  return (
    <Sidebar collapsible="offcanvas">
      <SidebarHeader className="px-3 pt-4 text-sidebar-primary">
        <Logo />
      </SidebarHeader>
      <SidebarContent>
        {groups.map(({ group, items: groupItems }) => (
          <SidebarGroup key={group}>
            <SidebarGroupLabel className="text-sidebar-foreground/60 text-xs font-medium">{GROUP_LABELS[group]}</SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>
                {groupItems.map((item) => {
                  const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
                  return (
                    <SidebarMenuItem key={item.href}>
                      <SidebarMenuButton asChild isActive={active} className="h-9" data-tour={`nav-${item.href.slice(1)}`}>
                        <Link href={item.href} aria-current={active ? "page" : undefined}>
                          <item.icon aria-hidden="true" />
                          <span>{item.label}</span>
                        </Link>
                      </SidebarMenuButton>
                    </SidebarMenuItem>
                  );
                })}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        ))}
      </SidebarContent>
      <SidebarFooter className="px-4 pb-4">
        <p className="text-xs leading-relaxed text-sidebar-foreground/60">
          Sample data for a fictional college. Every company and student is invented.
        </p>
      </SidebarFooter>
    </Sidebar>
  );
}

function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme();
  const dark = resolvedTheme === "dark";
  return (
    <Button
      type="button"
      variant="ghost"
      size="icon"
      aria-label={dark ? "Switch to light mode" : "Switch to dark mode"}
      onClick={() => setTheme(dark ? "light" : "dark")}
    >
      {dark ? <Sun aria-hidden="true" /> : <Moon aria-hidden="true" />}
    </Button>
  );
}

function UserMenu() {
  const { user, logout } = useAuth();
  const router = useRouter();
  if (!user) return null;
  const initials = user.name
    .split(" ")
    .map((part) => part[0])
    .slice(0, 2)
    .join("");
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button type="button" variant="ghost" className="h-9 gap-2 px-2" data-tour="user-menu">
          <span className="grid size-7 place-items-center rounded-full bg-secondary text-xs font-semibold" aria-hidden="true">
            {initials}
          </span>
          <span className="hidden text-sm font-medium sm:inline">{user.name}</span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-60">
        <DropdownMenuLabel className="font-normal">
          <span className="block text-sm font-medium">{user.name}</span>
          <span className="block text-xs text-muted-foreground">{user.email}</span>
          <span className="mt-1 block text-xs text-muted-foreground">Signed in as {user.role}</span>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem
          onSelect={async () => {
            await logout();
            router.push("/login");
          }}
        >
          <LogOut aria-hidden="true" />
          Log out
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

function TopBar() {
  const pathname = usePathname();
  const item = findNav(pathname);
  return (
    <header className="sticky top-0 z-30 flex h-14 items-center gap-3 border-b bg-background/95 px-4 backdrop-blur supports-[backdrop-filter]:bg-background/80 md:px-6">
      <SidebarTrigger aria-label="Open navigation" className="md:hidden" />
      <p className="truncate text-sm font-medium text-muted-foreground">{item?.label ?? "PlaceMate"}</p>
      <div className="ml-auto flex items-center gap-1">
        <ThemeToggle />
        <UserMenu />
      </div>
    </header>
  );
}

function ShellSkeleton() {
  return (
    <div className="grid min-h-dvh md:grid-cols-[16rem_1fr]" aria-busy="true" aria-label="Loading">
      <div className="hidden bg-sidebar md:block" />
      <div className="space-y-6 p-8">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-4 w-96 max-w-full" />
        <div className="grid gap-4 md:grid-cols-3">
          <Skeleton className="h-32" />
          <Skeleton className="h-32" />
          <Skeleton className="h-32" />
        </div>
      </div>
    </div>
  );
}

export function AppShell({ children }: { children: ReactNode }) {
  const { user, loading, offline } = useAuth();
  const pathname = usePathname();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user && !offline) router.replace(`/login?next=${encodeURIComponent(pathname)}`);
  }, [loading, user, offline, pathname, router]);

  if (loading) return <ShellSkeleton />;
  if (offline) {
    return (
      <StatusView
        code="Offline"
        title="PlaceMate's server is not reachable"
        message="The backend did not answer. Start it with scripts\dev.ps1 (or uvicorn on port 8000) and reload."
        action={{ label: "Try again", onClick: () => window.location.reload() }}
      />
    );
  }
  if (!user) return <ShellSkeleton />;

  const item = findNav(pathname);
  const allowed = !item || item.roles.includes(user.role);

  return (
    <SidebarProvider>
      <CloseOnNavigate />
      <AppSidebar />
      <SidebarInset className="min-w-0">
        <TopBar />
        <main id="main" className="min-w-0 flex-1 px-4 py-6 md:px-8 md:py-8">
          {allowed ? (
            children
          ) : (
            <StatusView
              embedded
              code="403"
              title="This page is not part of your role"
              message={`${item?.label} is for ${item?.roles.join(" and ")}s. You are signed in as a ${user.role}.`}
              action={{ label: "Go to my home page", href: homeFor(user) }}
            />
          )}
        </main>
      </SidebarInset>
    </SidebarProvider>
  );
}
