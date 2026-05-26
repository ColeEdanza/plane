/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { useTranslation } from "@plane/i18n";
import { cn, getDate, renderFormattedPayloadDate, shouldHighlightIssueDueDate } from "@plane/utils";
import { DateDropdown } from "@/components/dropdowns/date";
import { MemberDropdown } from "@/components/dropdowns/member/dropdown";
import { PriorityDropdown } from "@/components/dropdowns/priority";
import { useIssueDetail } from "@/hooks/store/use-issue-detail";
import { useProjectState } from "@/hooks/store/use-project-state";
import { DateAlert } from "@/plane-web/components/issues/issue-details/sidebar/date-alert";
import type { TIssueOperations } from "./root";

type Props = {
  workspaceSlug: string;
  projectId: string;
  issueId: string;
  issueOperations: TIssueOperations;
  isEditable: boolean;
  isArchived: boolean;
};

const Divider = () => (
  <span aria-hidden className="mx-2 inline-block h-5 flex-shrink-0 self-center border-l border-strong" />
);

const pillTextClass = "text-body-sm-regular";

export const IssueInlineProperties = observer(function IssueInlineProperties(props: Props) {
  const { workspaceSlug, projectId, issueId, issueOperations, isEditable, isArchived } = props;
  const { t } = useTranslation();
  const {
    issue: { getIssueById },
  } = useIssueDetail();
  const { getStateById } = useProjectState();

  const issue = getIssueById(issueId);
  if (!issue || !issue.project_id) return null;

  const disabled = !isEditable || isArchived;
  const stateDetails = getStateById(issue.state_id);

  const minDate = issue.start_date ? getDate(issue.start_date) : null;
  minDate?.setDate(minDate.getDate());
  const maxDate = issue.target_date ? getDate(issue.target_date) : null;
  maxDate?.setDate(maxDate.getDate());

  return (
    <div className={cn("flex flex-wrap items-center gap-x-5 gap-y-2 py-1", { "opacity-60": disabled })}>
      <MemberDropdown
        value={issue?.assignee_ids ?? undefined}
        onChange={(val) => issueOperations.update(workspaceSlug, projectId, issueId, { assignee_ids: val })}
        disabled={disabled}
        projectId={issue.project_id}
        placeholder={t("issue.add.assignee")}
        multiple
        buttonVariant={issue?.assignee_ids?.length > 1 ? "transparent-without-text" : "transparent-with-text"}
        buttonClassName={cn(pillTextClass, "px-1.5 py-1", {
          "text-placeholder": !issue?.assignee_ids?.length,
        })}
        showTooltip
      />
      <Divider />
      <PriorityDropdown
        value={issue?.priority}
        onChange={(val) => issueOperations.update(workspaceSlug, projectId, issueId, { priority: val })}
        disabled={disabled}
        buttonVariant="transparent-with-text"
        buttonClassName={cn(pillTextClass, "px-1.5 py-1")}
        showTooltip
      />
      <Divider />
      <DateDropdown
        placeholder={t("issue.add.start_date")}
        value={issue.start_date}
        onChange={(val) =>
          issueOperations.update(workspaceSlug, projectId, issueId, {
            start_date: val ? renderFormattedPayloadDate(val) : null,
          })
        }
        maxDate={maxDate ?? undefined}
        disabled={disabled}
        buttonVariant="transparent-with-text"
        buttonClassName={cn(pillTextClass, "px-1.5 py-1", {
          "text-placeholder": !issue?.start_date,
        })}
        showTooltip
      />
      <Divider />
      <div className="flex items-center gap-1.5">
        <DateDropdown
          placeholder={t("issue.add.due_date")}
          value={issue.target_date}
          onChange={(val) =>
            issueOperations.update(workspaceSlug, projectId, issueId, {
              target_date: val ? renderFormattedPayloadDate(val) : null,
            })
          }
          minDate={minDate ?? undefined}
          disabled={disabled}
          buttonVariant="transparent-with-text"
          buttonClassName={cn(pillTextClass, "px-1.5 py-1", {
            "text-placeholder": !issue.target_date,
            "text-danger-primary": shouldHighlightIssueDueDate(issue.target_date, stateDetails?.group),
          })}
          showTooltip
        />
        {issue.target_date && <DateAlert date={issue.target_date} workItem={issue} projectId={projectId} />}
      </div>
    </div>
  );
});
