"use client";

// Reusable "Duplicate" dialog (Cycle 5, Phase 15).
// Collects a new name and, optionally, a target customer (admin cross-tenant clone).

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { SearchableSelect } from "@/components/ui/searchable-select";
import { useToast } from "@/components/ui/toast";
import { api } from "@/lib/api/client";
import type { Customer } from "@/lib/api/types";

const inputCls =
  "h-9 w-full rounded-md border border-input bg-background px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring";

export interface CloneDialogProps {
  open: boolean;
  onClose: () => void;
  entityLabel: string;
  currentName: string;
  /** Perform the clone with the collected options; return on success. */
  onClone: (opts: { new_name?: string; target_tenant_id?: string }) => Promise<void>;
  /** When true, show a target-customer picker (admin cross-tenant clone). */
  allowTargetCustomer?: boolean;
  /** Extra note shown under the form (e.g. "Credentials are not copied"). */
  note?: string;
}

export function CloneDialog({
  open,
  onClose,
  entityLabel,
  currentName,
  onClone,
  allowTargetCustomer = false,
  note,
}: CloneDialogProps) {
  const { success, error } = useToast();
  const [name, setName] = useState("");
  const [target, setTarget] = useState("");
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!open) return;
    setName(`${currentName} (copy)`);
    setTarget("");
    if (allowTargetCustomer) {
      api
        .listCustomers()
        .then(setCustomers)
        .catch(() => setCustomers([]));
    }
  }, [open, currentName, allowTargetCustomer]);

  async function submit() {
    setBusy(true);
    try {
      await onClone({
        new_name: name.trim() || undefined,
        target_tenant_id: target || undefined,
      });
      success(`Duplicated ${entityLabel}.`);
      onClose();
    } catch (e) {
      error(e instanceof Error ? e.message : "Could not duplicate.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Dialog open={open} onClose={onClose} title={`Duplicate ${entityLabel}`}>
      <div className="space-y-4">
        <div className="space-y-1.5">
          <label className="text-xs font-medium text-muted-foreground">New name</label>
          <input
            className={inputCls}
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder={`${currentName} (copy)`}
          />
        </div>
        {allowTargetCustomer && (
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted-foreground">
              Target customer (optional)
            </label>
            <SearchableSelect
              value={target}
              onChange={setTarget}
              placeholder="Same customer"
              options={customers.map((c) => ({ value: c.id, label: c.name, hint: c.slug }))}
            />
          </div>
        )}
        {note && <p className="text-xs text-muted-foreground">{note}</p>}
        <div className="flex justify-end gap-2 pt-1">
          <Button variant="outline" size="sm" onClick={onClose} disabled={busy}>
            Cancel
          </Button>
          <Button size="sm" onClick={submit} disabled={busy}>
            {busy ? "Duplicating…" : "Duplicate"}
          </Button>
        </div>
      </div>
    </Dialog>
  );
}
