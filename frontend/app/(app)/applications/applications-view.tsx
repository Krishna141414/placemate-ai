"use client";

import { Loader2, Pencil, Plus, Trash2 } from "lucide-react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { ToneBadge } from "@/components/shared/badges";
import { CompanySelect } from "@/components/shared/company-select";
import { EmptyState, ErrorState, LoadingRows, PageHeader } from "@/components/shared/page";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { api, errorMessage } from "@/lib/api";
import { daysUntil, dueLabel, formatDate, STATUS_LABELS } from "@/lib/format";
import type { Application, ApplicationStatus } from "@/lib/types";
import { useApi } from "@/lib/use-api";

const STATUSES = Object.keys(STATUS_LABELS) as ApplicationStatus[];
const STATUS_TONE: Record<ApplicationStatus, "success" | "warning" | "error" | "neutral" | "info"> = {
  planned: "neutral",
  applied: "info",
  online_test: "info",
  interview: "warning",
  offer: "success",
  rejected: "error",
};

type Draft = { id?: number; company_id?: string; status: ApplicationStatus; deadline: string; notes: string };

export function ApplicationsView() {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const filter = params.get("status") ?? "all";
  const list = useApi<Application[]>("/api/applications");

  const [draft, setDraft] = useState<Draft | null>(null);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [toDelete, setToDelete] = useState<Application | null>(null);
  const [updating, setUpdating] = useState<number | null>(null);

  const rows = (list.data ?? []).filter((row) => filter === "all" || row.status === filter);
  const counts = (list.data ?? []).reduce<Record<string, number>>((acc, row) => ({ ...acc, [row.status]: (acc[row.status] ?? 0) + 1 }), {});

  async function changeStatus(row: Application, status: ApplicationStatus) {
    setUpdating(row.id);
    try {
      const updated = await api<Application>(`/api/applications/${row.id}`, { method: "PATCH", body: { status } });
      list.setData((list.data ?? []).map((item) => (item.id === row.id ? updated : item)));
      toast.success(`${row.company_name}: ${STATUS_LABELS[status]}`);
    } catch (error) {
      toast.error(errorMessage(error));
    } finally {
      setUpdating(null);
    }
  }

  async function saveDraft() {
    if (!draft) return;
    if (!draft.id && !draft.company_id) {
      setFormError("Choose a company.");
      return;
    }
    setSaving(true);
    setFormError(null);
    try {
      if (draft.id) {
        await api(`/api/applications/${draft.id}`, {
          method: "PATCH",
          body: { status: draft.status, deadline: draft.deadline || null, notes: draft.notes },
        });
      } else {
        await api("/api/applications", {
          method: "POST",
          body: { company_id: draft.company_id, status: draft.status, deadline: draft.deadline || null, notes: draft.notes },
        });
      }
      toast.success(draft.id ? "Application updated." : "Application saved.");
      setDraft(null);
      list.reload();
    } catch (error) {
      setFormError(errorMessage(error));
    } finally {
      setSaving(false);
    }
  }

  async function confirmDelete() {
    if (!toDelete) return;
    try {
      await api(`/api/applications/${toDelete.id}`, { method: "DELETE" });
      list.setData((list.data ?? []).filter((item) => item.id !== toDelete.id));
      toast.success(`${toDelete.company_name} removed from your tracker.`);
    } catch (error) {
      toast.error(errorMessage(error));
    } finally {
      setToDelete(null);
    }
  }

  return (
    <div>
      <PageHeader
        title="Applications"
        description="Where you have applied, what stage you are at, and what is due. Adding a company you already track updates it instead of duplicating it."
        actions={
          <Button type="button" onClick={() => setDraft({ status: "planned", deadline: "", notes: "" })} data-tour="applications-add">
            <Plus aria-hidden="true" />
            Add application
          </Button>
        }
      />

      <Tabs value={filter} onValueChange={(value) => router.replace(value === "all" ? pathname : `${pathname}?status=${value}`, { scroll: false })} className="mb-4">
        <TabsList className="h-auto flex-wrap justify-start">
          <TabsTrigger value="all">
            All <span className="ml-1 text-muted-foreground num">{list.data?.length ?? 0}</span>
          </TabsTrigger>
          {STATUSES.map((status) => (
            <TabsTrigger key={status} value={status}>
              {STATUS_LABELS[status]}
              {counts[status] ? <span className="ml-1 text-muted-foreground num">{counts[status]}</span> : null}
            </TabsTrigger>
          ))}
        </TabsList>
      </Tabs>

      {list.loading ? (
        <LoadingRows rows={5} />
      ) : list.error ? (
        <ErrorState message={list.error} onRetry={list.reload} />
      ) : !rows.length ? (
        <EmptyState
          title={filter === "all" ? "Nothing tracked yet" : `No applications at "${STATUS_LABELS[filter as ApplicationStatus] ?? filter}"`}
          message={filter === "all" ? "Add the companies you are applying to. Approving a prep plan also adds one here." : "Try another stage, or show all."}
          action={
            filter === "all" ? (
              <Button type="button" size="sm" onClick={() => setDraft({ status: "planned", deadline: "", notes: "" })}>
                Add application
              </Button>
            ) : (
              <Button type="button" size="sm" variant="outline" onClick={() => router.replace(pathname)}>
                Show all
              </Button>
            )
          }
        />
      ) : (
        <div className="overflow-x-auto" data-tour="applications-table">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Company</TableHead>
                <TableHead>Stage</TableHead>
                <TableHead>Deadline</TableHead>
                <TableHead className="hidden lg:table-cell">Notes</TableHead>
                <TableHead className="text-right">
                  <span className="sr-only">Actions</span>
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.map((row) => {
                const days = daysUntil(row.deadline);
                return (
                  <TableRow key={row.id}>
                    <TableCell className="min-w-44">
                      <p className="font-medium">{row.company_name}</p>
                      <p className="text-xs text-muted-foreground">{row.role_title}</p>
                    </TableCell>
                    <TableCell>
                      <Select value={row.status} onValueChange={(value) => void changeStatus(row, value as ApplicationStatus)} disabled={updating === row.id}>
                        <SelectTrigger className="h-8 w-36" aria-label={`Stage for ${row.company_name}`}>
                          <SelectValue>
                            <ToneBadge tone={STATUS_TONE[row.status]}>{STATUS_LABELS[row.status]}</ToneBadge>
                          </SelectValue>
                        </SelectTrigger>
                        <SelectContent>
                          {STATUSES.map((status) => (
                            <SelectItem key={status} value={status}>
                              {STATUS_LABELS[status]}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </TableCell>
                    <TableCell className="whitespace-nowrap">
                      <p className="num">{formatDate(row.deadline)}</p>
                      {row.deadline && (
                        <p className={days !== null && days >= 0 && days <= 7 ? "text-xs text-warning" : "text-xs text-muted-foreground"}>{dueLabel(row.deadline)}</p>
                      )}
                    </TableCell>
                    <TableCell className="hidden max-w-xs lg:table-cell">
                      <p className="line-clamp-2 text-sm text-muted-foreground">{row.notes || "No notes"}</p>
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-1">
                        <Button
                          type="button"
                          size="icon"
                          variant="ghost"
                          aria-label={`Edit ${row.company_name}`}
                          onClick={() => setDraft({ id: row.id, company_id: row.company_id, status: row.status, deadline: row.deadline ?? "", notes: row.notes })}
                        >
                          <Pencil aria-hidden="true" />
                        </Button>
                        <Button type="button" size="icon" variant="ghost" aria-label={`Remove ${row.company_name}`} onClick={() => setToDelete(row)}>
                          <Trash2 aria-hidden="true" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </div>
      )}

      <Dialog open={draft !== null} onOpenChange={(open) => !open && setDraft(null)}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>{draft?.id ? "Edit application" : "Add application"}</DialogTitle>
            <DialogDescription>Leave the deadline empty to use the company&apos;s application deadline.</DialogDescription>
          </DialogHeader>
          {draft && (
            <form
              className="grid gap-4"
              onSubmit={(event) => {
                event.preventDefault();
                void saveDraft();
              }}
            >
              {!draft.id && (
                <div className="grid gap-1.5">
                  <Label htmlFor="app-company">Company</Label>
                  <CompanySelect id="app-company" value={draft.company_id} onChange={(id) => setDraft({ ...draft, company_id: id })} className="w-full" />
                </div>
              )}
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="grid gap-1.5">
                  <Label htmlFor="app-status">Stage</Label>
                  <Select value={draft.status} onValueChange={(value) => setDraft({ ...draft, status: value as ApplicationStatus })}>
                    <SelectTrigger id="app-status" className="w-full">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {STATUSES.map((status) => (
                        <SelectItem key={status} value={status}>
                          {STATUS_LABELS[status]}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="grid gap-1.5">
                  <Label htmlFor="app-deadline">Deadline</Label>
                  <Input id="app-deadline" name="deadline" type="date" value={draft.deadline} onChange={(event) => setDraft({ ...draft, deadline: event.target.value })} />
                </div>
              </div>
              <div className="grid gap-1.5">
                <Label htmlFor="app-notes">Notes</Label>
                <Textarea id="app-notes" name="notes" maxLength={1000} value={draft.notes} onChange={(event) => setDraft({ ...draft, notes: event.target.value })} placeholder="Test date, contact, what to revise" />
              </div>
              <p role="alert" aria-live="polite" className="min-h-5 text-sm text-error">
                {formError}
              </p>
              <DialogFooter>
                <Button type="button" variant="outline" onClick={() => setDraft(null)}>
                  Cancel
                </Button>
                <Button type="submit" disabled={saving}>
                  {saving && <Loader2 className="animate-spin" aria-hidden="true" />}
                  Save
                </Button>
              </DialogFooter>
            </form>
          )}
        </DialogContent>
      </Dialog>

      <AlertDialog open={toDelete !== null} onOpenChange={(open) => !open && setToDelete(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Remove {toDelete?.company_name}?</AlertDialogTitle>
            <AlertDialogDescription>This removes it from your tracker. Your prep plans are not affected.</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Keep it</AlertDialogCancel>
            <AlertDialogAction onClick={() => void confirmDelete()}>Remove</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
