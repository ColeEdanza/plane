/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * CSFD fork addition: reactions on issue-activity rows. Each row instance
 * fetches and mutates its own reactions independently — a global mobx store
 * mirrors IssueReaction/CommentReaction but isn't needed at this scale
 * (activity feed is small and reactions are low-churn).
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import { stringToEmoji } from "@plane/propel/emoji-icon-picker";
import { EmojiReactionGroup, EmojiReactionPicker } from "@plane/propel/emoji-reaction";
import type { EmojiReactionType } from "@plane/propel/emoji-reaction";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import {
  IssueActivityReactionService,
  type TIssueActivityReaction,
} from "@/services/issue/issue_activity_reaction.service";

type Props = {
  workspaceSlug: string;
  projectId: string;
  issueId: string;
  activityId: string;
  currentUserId: string;
  disabled?: boolean;
};

const reactionService = new IssueActivityReactionService();

export function IssueActivityRowReactions(props: Props) {
  const { workspaceSlug, projectId, issueId, activityId, currentUserId, disabled = false } = props;

  const [reactionsList, setReactionsList] = useState<TIssueActivityReaction[]>([]);
  const [isPickerOpen, setIsPickerOpen] = useState(false);
  const [isLoaded, setIsLoaded] = useState(false);

  useEffect(() => {
    let cancelled = false;
    if (!workspaceSlug || !projectId || !issueId || !activityId) return;
    (async () => {
      try {
        const rows = await reactionService.list(workspaceSlug, projectId, issueId, activityId);
        if (cancelled) return;
        setReactionsList(rows || []);
      } catch {
        // swallow — empty list is the right fallback for a UI affordance
      } finally {
        if (!cancelled) setIsLoaded(true);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [workspaceSlug, projectId, issueId, activityId]);

  const userReactions = useMemo(
    () => reactionsList.filter((r) => r.actor === currentUserId).map((r) => r.reaction),
    [reactionsList, currentUserId]
  );

  const grouped = useMemo<EmojiReactionType[]>(() => {
    const byCode = new Map<string, TIssueActivityReaction[]>();
    reactionsList.forEach((r) => {
      const bucket = byCode.get(r.reaction) ?? [];
      bucket.push(r);
      byCode.set(r.reaction, bucket);
    });
    return Array.from(byCode.entries()).map(([code, rows]) => ({
      emoji: stringToEmoji(code),
      count: rows.length,
      reacted: userReactions.includes(code),
      users: rows.map((r) => r.actor_detail?.display_name || r.display_name).filter(Boolean),
    }));
  }, [reactionsList, userReactions]);

  const react = useCallback(
    async (reactionCode: string) => {
      if (disabled) return;
      const alreadyReacted = userReactions.includes(reactionCode);
      try {
        if (alreadyReacted) {
          await reactionService.remove(workspaceSlug, projectId, issueId, activityId, reactionCode);
          setReactionsList((prev) => prev.filter((r) => !(r.reaction === reactionCode && r.actor === currentUserId)));
        } else {
          const created = await reactionService.create(workspaceSlug, projectId, issueId, activityId, reactionCode);
          setReactionsList((prev) => [...prev, created]);
        }
      } catch {
        setToast({
          title: "Error",
          type: TOAST_TYPE.ERROR,
          message: alreadyReacted ? "Could not remove reaction" : "Could not add reaction",
        });
      }
    },
    [disabled, userReactions, workspaceSlug, projectId, issueId, activityId, currentUserId]
  );

  const handleGroupClick = (emoji: string) => {
    const code = Array.from(emoji)
      .map((c) => c.codePointAt(0))
      .join("-");
    react(code);
  };

  if (!isLoaded || (grouped.length === 0 && disabled)) return null;

  return (
    <span className="inline-flex items-center align-middle">
      <EmojiReactionPicker
        isOpen={isPickerOpen}
        handleToggle={setIsPickerOpen}
        onChange={react}
        disabled={disabled}
        label={
          <EmojiReactionGroup
            reactions={grouped}
            onReactionClick={handleGroupClick}
            showAddButton={!disabled}
            onAddReaction={() => setIsPickerOpen(true)}
          />
        }
        placement="bottom-start"
      />
    </span>
  );
}
