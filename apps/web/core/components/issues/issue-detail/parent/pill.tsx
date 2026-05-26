/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { useRouter } from "next/navigation";
import { CornerDownRight, MinusCircle } from "lucide-react";
import { useTranslation } from "@plane/i18n";
import type { TIssue } from "@plane/types";
import { ControlLink, CustomMenu } from "@plane/ui";
import { generateWorkItemLink } from "@plane/utils";
import { useIssues } from "@/hooks/store/use-issues";
import { useProject } from "@/hooks/store/use-project";
import { useProjectState } from "@/hooks/store/use-project-state";
import useIssuePeekOverviewRedirection from "@/hooks/use-issue-peek-overview-redirection";
import { usePlatformOS } from "@/hooks/use-platform-os";
import { IssueIdentifier } from "@/plane-web/components/issues/issue-details/issue-identifier";
import type { TIssueOperations } from "../root";
import { IssueParentSiblings } from "./siblings";

export type TIssueParentPill = {
  workspaceSlug: string;
  projectId: string;
  issueId: string;
  issue: TIssue;
  issueOperations: TIssueOperations;
};

export const IssueParentPill = observer(function IssueParentPill(props: TIssueParentPill) {
  const { workspaceSlug, projectId, issueId, issue, issueOperations } = props;
  const router = useRouter();
  const { t } = useTranslation();
  const { issueMap } = useIssues();
  const { getProjectStates } = useProjectState();
  const { handleRedirection } = useIssuePeekOverviewRedirection();
  const { isMobile } = usePlatformOS();
  const { getProjectIdentifierById } = useProject();

  const parentIssue = issueMap?.[issue.parent_id || ""] || undefined;
  if (!parentIssue) return null;

  const isParentEpic = parentIssue.is_epic;
  const projectIdentifier = getProjectIdentifierById(parentIssue.project_id);
  const parentState = getProjectStates(parentIssue.project_id)?.find((s) => s?.id === parentIssue.state_id);
  const stateColor = parentState?.color || undefined;

  const workItemLink = generateWorkItemLink({
    workspaceSlug,
    projectId: parentIssue.project_id,
    issueId: parentIssue.id,
    projectIdentifier,
    sequenceId: parentIssue.sequence_id,
    isEpic: isParentEpic,
  });

  const handleParentIssueClick = () => {
    if (isParentEpic) router.push(workItemLink);
    else handleRedirection(workspaceSlug, parentIssue, isMobile);
  };

  return (
    <div className="flex w-fit max-w-[260px] items-center gap-1.5 rounded-md border border-subtle bg-layer-1 px-1.5 py-0.5 text-10 whitespace-nowrap">
      <CornerDownRight className="h-3 w-3 flex-shrink-0 text-tertiary" />
      <ControlLink href={workItemLink} onClick={handleParentIssueClick}>
        <div className="flex items-center gap-1.5">
          {stateColor && (
            <span className="block h-1.5 w-1.5 flex-shrink-0 rounded-full" style={{ backgroundColor: stateColor }} />
          )}
          {parentIssue.project_id && (
            <IssueIdentifier
              projectId={parentIssue.project_id}
              issueId={parentIssue.id}
              size="xs"
              variant="secondary"
            />
          )}
          <span className="max-w-[140px] truncate text-primary">{parentIssue.name}</span>
        </div>
      </ControlLink>

      <CustomMenu ellipsis optionsClassName="p-1.5">
        <div className="border-b border-strong text-11 font-medium text-secondary">{t("issue.sibling.label")}</div>
        <IssueParentSiblings workspaceSlug={workspaceSlug} currentIssue={issue} parentIssue={parentIssue} />
        <CustomMenu.MenuItem
          onClick={() => issueOperations.update(workspaceSlug, projectId, issueId, { parent_id: null })}
          className="flex items-center gap-2 py-2 text-danger-primary"
        >
          <MinusCircle className="h-4 w-4" />
          <span>{t("issue.remove.parent.label")}</span>
        </CustomMenu.MenuItem>
      </CustomMenu>
    </div>
  );
});
