"use client";

import { MessageSquare, Send, User } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { useToast } from "@/components/ui/toast";
import { api, ApiError } from "@/lib/api/client";
import type { Comment, UserRead } from "@/lib/api/types";
import { formatDateTime } from "@/lib/format";

/** Comment thread + @mention on an object (file/sheet/flag) — the activity feed. */
export function CommentsPanel({
  targetType,
  targetId,
}: {
  targetType: "file" | "sheet" | "flag";
  targetId: string;
}) {
  const toast = useToast();
  const [comments, setComments] = useState<Comment[] | null>(null);
  const [users, setUsers] = useState<UserRead[]>([]);
  const [body, setBody] = useState("");
  const [mentions, setMentions] = useState<string[]>([]);
  const [posting, setPosting] = useState(false);

  const load = useCallback(async () => {
    try {
      setComments(await api.listComments(targetType, targetId));
    } catch {
      setComments([]);
    }
  }, [targetType, targetId]);

  useEffect(() => {
    void load();
    api
      .listUsers()
      .then(setUsers)
      .catch(() => setUsers([]));
  }, [load]);

  async function post() {
    if (!body.trim()) return;
    setPosting(true);
    try {
      await api.createComment({
        target_type: targetType,
        target_id: targetId,
        body: body.trim(),
        mentions: mentions.length ? mentions : undefined,
      });
      setBody("");
      setMentions([]);
      await load();
      toast.success("Comment posted.");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not post comment.");
    } finally {
      setPosting(false);
    }
  }

  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <div className="mb-3 flex items-center gap-2 text-sm font-semibold">
        <MessageSquare className="h-4 w-4 text-muted-foreground" /> Comments
        {comments ? <span className="text-xs text-muted-foreground">({comments.length})</span> : null}
      </div>

      <div className="space-y-3">
        {comments === null ? (
          <p className="text-xs text-muted-foreground">Loading…</p>
        ) : comments.length === 0 ? (
          <p className="text-xs text-muted-foreground">
            No comments yet — start the conversation for your team.
          </p>
        ) : (
          comments.map((c) => (
            <div key={c.id} className="rounded-md border border-border p-2.5 text-sm">
              <div className="mb-1 flex items-center gap-2 text-xs text-muted-foreground">
                <User className="h-3 w-3" />
                {c.author_email ?? "someone"}
                <span className="ml-auto">{formatDateTime(c.created_at)}</span>
              </div>
              <p className="whitespace-pre-wrap break-words">{c.body}</p>
            </div>
          ))
        )}
      </div>

      <div className="mt-3 space-y-2">
        <textarea
          className="min-h-[64px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          placeholder="Leave a note for your team…"
          value={body}
          onChange={(e) => setBody(e.target.value)}
        />
        <div className="flex flex-wrap items-center gap-2">
          {users.length > 0 ? (
            <label className="flex items-center gap-1.5 text-xs text-muted-foreground">
              mention
              <select
                multiple={false}
                className="h-8 rounded-md border border-input bg-background px-2 text-xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                value=""
                onChange={(e) => {
                  const id = e.target.value;
                  if (id && !mentions.includes(id)) setMentions((m) => [...m, id]);
                }}
              >
                <option value="">+ teammate</option>
                {users.map((u) => (
                  <option key={u.id} value={u.id}>
                    {u.email}
                  </option>
                ))}
              </select>
            </label>
          ) : null}
          {mentions.map((id) => {
            const u = users.find((x) => x.id === id);
            return (
              <span
                key={id}
                className="inline-flex items-center gap-1 rounded-full border border-primary/40 px-2 py-0.5 text-xs text-primary"
              >
                @{u?.email ?? id}
                <button
                  type="button"
                  onClick={() => setMentions((m) => m.filter((x) => x !== id))}
                  className="opacity-70 hover:opacity-100"
                >
                  ×
                </button>
              </span>
            );
          })}
          <Button size="sm" className="ml-auto" onClick={post} disabled={posting || !body.trim()}>
            <Send className="h-3.5 w-3.5" />
            {posting ? "Posting…" : "Comment"}
          </Button>
        </div>
      </div>
    </div>
  );
}
