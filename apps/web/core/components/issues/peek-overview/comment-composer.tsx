/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * CSFD fork addition: composer pinned at the bottom of the peek panel
 * (Asana style). Lives as a sibling of the scrollable content so it stays
 * visible regardless of scroll position. The activity feed renders its
 * own composer inline only when this one isn't mounted.
 */

import { observer } from "mobx-react";
import { CommentCreate } from "@/components/comments/comment-create";
import { useWorkItemCommentOperations } from "@/components/issues/issue-detail/issue-activity/helper";

type Props = {
  workspaceSlug: string;
  projectId: string;
  issueId: string;
  disabled?: boolean;
};

export const PeekCommentComposer = observer(function PeekCommentComposer(props: Props) {
  const { workspaceSlug, projectId, issueId, disabled = false } = props;
  const activityOperations = useWorkItemCommentOperations(workspaceSlug, projectId, issueId);

  if (disabled) return null;

  return (
    <div className="flex-shrink-0 border-t border-subtle bg-surface-1 px-8 pt-3 pb-4">
      <CommentCreate
        workspaceSlug={workspaceSlug}
        entityId={issueId}
        activityOperations={activityOperations}
        showToolbarInitially={false}
        projectId={projectId}
      />
    </div>
  );
});
