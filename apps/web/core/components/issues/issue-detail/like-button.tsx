/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Like button reacting with 👍 to the work item's "created" IssueActivity row.
 * Reuses the existing activity-reaction backend — no new model, no new API.
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import { observer } from "mobx-react";
import { ThumbsUp } from "lucide-react";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import { Tooltip } from "@plane/propel/tooltip";
import { cn } from "@plane/utils";
import { useIssueDetail } from "@/hooks/store/use-issue-detail";
import {
  IssueActivityReactionService,
  type TIssueActivityReaction,
} from "@/services/issue/issue_activity_reaction.service";

const LIKE_REACTION_CODE = "128077"; // 👍 codePointAt(0).toString()
const reactionService = new IssueActivityReactionService();

type Props = {
  workspaceSlug: string;
  projectId: string;
  issueId: string;
  currentUserId: string | undefined;
  disabled?: boolean;
};

export const IssueLikeButton = observer(function IssueLikeButton(props: Props) {
  const { workspaceSlug, projectId, issueId, currentUserId, disabled = false } = props;
  const {
    activity: { getActivitiesByIssueId, getActivityById },
    fetchActivities,
  } = useIssueDetail();

  const [reactions, setReactions] = useState<TIssueActivityReaction[]>([]);
  const [isReactionsLoaded, setIsReactionsLoaded] = useState(false);

  // Find the "created" activity for this issue. May not be present until the
  // activity store is populated — fetch on mount if missing.
  const activityIds = getActivitiesByIssueId(issueId);
  const createdActivityId = useMemo(() => {
    if (!activityIds?.length) return undefined;
    for (const aid of activityIds) {
      const a = getActivityById(aid);
      if (a && a.verb === "created" && !a.field) return aid;
    }
    return undefined;
  }, [activityIds, getActivityById]);

  // Trigger an activity fetch if the store is empty for this issue. The
  // activity feed below will also trigger one — this is idempotent at the
  // store level (it overwrites the per-issue list).
  useEffect(() => {
    if (!activityIds && workspaceSlug && projectId && issueId) {
      fetchActivities(workspaceSlug, projectId, issueId).catch(() => {});
    }
  }, [activityIds, workspaceSlug, projectId, issueId, fetchActivities]);

  // Fetch this activity's reactions once we know the activity id.
  useEffect(() => {
    let cancelled = false;
    if (!createdActivityId) return;
    (async () => {
      try {
        const rows = await reactionService.list(workspaceSlug, projectId, issueId, createdActivityId);
        if (!cancelled) setReactions(rows || []);
      } catch {
        // empty list is fine; button still works for first reactor
      } finally {
        if (!cancelled) setIsReactionsLoaded(true);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [createdActivityId, workspaceSlug, projectId, issueId]);

  const likeRows = useMemo(() => reactions.filter((r) => r.reaction === LIKE_REACTION_CODE), [reactions]);
  const userLiked = useMemo(
    () => !!currentUserId && likeRows.some((r) => r.actor === currentUserId),
    [likeRows, currentUserId]
  );
  const likeCount = likeRows.length;

  const toggle = useCallback(async () => {
    if (disabled || !createdActivityId || !currentUserId) return;
    try {
      if (userLiked) {
        await reactionService.remove(workspaceSlug, projectId, issueId, createdActivityId, LIKE_REACTION_CODE);
        setReactions((prev) => prev.filter((r) => !(r.reaction === LIKE_REACTION_CODE && r.actor === currentUserId)));
      } else {
        const created = await reactionService.create(
          workspaceSlug,
          projectId,
          issueId,
          createdActivityId,
          LIKE_REACTION_CODE
        );
        setReactions((prev) => [...prev, created]);
      }
    } catch {
      setToast({
        title: "Error",
        type: TOAST_TYPE.ERROR,
        message: userLiked ? "Could not remove like" : "Could not like work item",
      });
    }
  }, [disabled, createdActivityId, currentUserId, userLiked, workspaceSlug, projectId, issueId]);

  // Don't render until we know the target activity exists; avoids a button
  // that errors if the activity hasn't loaded yet.
  if (!createdActivityId) return null;

  const tooltip = userLiked ? "Unlike" : likeCount > 0 ? `Like (${likeCount})` : "Like";

  return (
    <Tooltip tooltipContent={tooltip} position="bottom">
      <button
        type="button"
        onClick={toggle}
        disabled={disabled || !isReactionsLoaded || !currentUserId}
        className={cn(
          "inline-flex h-7 items-center gap-1 rounded-md border border-strong bg-layer-2 px-2 text-body-sm-medium shadow-raised-100 transition-colors",
          "hover:bg-layer-2-hover focus:bg-layer-2-active disabled:pointer-events-none disabled:opacity-60",
          userLiked ? "text-accent-primary" : "text-secondary"
        )}
        aria-pressed={userLiked}
      >
        <ThumbsUp className={cn("h-4 w-4", { "fill-current": userLiked })} aria-hidden />
        {likeCount > 0 && <span className="leading-none">{likeCount}</span>}
      </button>
    </Tooltip>
  );
});
