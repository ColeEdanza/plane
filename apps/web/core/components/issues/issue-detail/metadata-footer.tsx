/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { Tooltip } from "@plane/propel/tooltip";
import { renderFormattedDate, renderFormattedTime } from "@plane/utils";
import { ButtonAvatars } from "@/components/dropdowns/member/avatar";
import { useIssueDetail } from "@/hooks/store/use-issue-detail";
import { useMember } from "@/hooks/store/use-member";

type Props = {
  issueId: string;
};

const formatFull = (date: string | null | undefined) => {
  if (!date) return "";
  return `${renderFormattedDate(date)} at ${renderFormattedTime(date, "12-hour")}`;
};

const Separator = () => <span aria-hidden className="mx-2 h-3 flex-shrink-0 self-center border-l border-strong" />;

export const IssueMetadataFooter = observer(function IssueMetadataFooter(props: Props) {
  const { issueId } = props;
  const {
    issue: { getIssueById },
  } = useIssueDetail();
  const { getUserDetails } = useMember();

  const issue = getIssueById(issueId);
  if (!issue) return null;

  const createdBy = issue.created_by ? getUserDetails(issue.created_by) : null;

  return (
    <div className="mt-6 flex flex-wrap items-center gap-y-1 pt-3 text-body-xs-regular text-tertiary">
      {createdBy && (
        <>
          <span className="flex items-center gap-1.5">
            <span className="text-placeholder">Created by</span>
            <span className="flex items-center gap-1">
              <ButtonAvatars showTooltip userIds={createdBy.id} />
              <span className="text-secondary">{createdBy.display_name}</span>
            </span>
          </span>
          <Separator />
        </>
      )}

      <Tooltip tooltipContent={formatFull(issue.created_at)} position="top">
        <span className="flex items-center gap-1.5">
          <span className="text-placeholder">Created</span>
          <span className="text-secondary">{renderFormattedDate(issue.created_at)}</span>
        </span>
      </Tooltip>

      <Separator />

      <Tooltip tooltipContent={formatFull(issue.updated_at)} position="top">
        <span className="flex items-center gap-1.5">
          <span className="text-placeholder">Updated</span>
          <span className="text-secondary">{renderFormattedDate(issue.updated_at)}</span>
        </span>
      </Tooltip>

      {issue.completed_at && (
        <>
          <Separator />
          <Tooltip tooltipContent={formatFull(issue.completed_at)} position="top">
            <span className="flex items-center gap-1.5">
              <span className="text-placeholder">Completed</span>
              <span className="text-secondary">{renderFormattedDate(issue.completed_at)}</span>
            </span>
          </Tooltip>
        </>
      )}
    </div>
  );
});
