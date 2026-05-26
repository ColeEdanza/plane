/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { API_BASE_URL } from "@plane/constants";
import { APIService } from "@/services/api.service";

export type TIssueActivityReaction = {
  id: string;
  actor: string;
  activity: string;
  reaction: string;
  display_name: string;
  actor_detail?: {
    id: string;
    first_name: string;
    last_name: string;
    display_name: string;
    avatar_url?: string | null;
  };
};

export class IssueActivityReactionService extends APIService {
  constructor() {
    super(API_BASE_URL);
  }

  async list(
    workspaceSlug: string,
    projectId: string,
    issueId: string,
    activityId: string
  ): Promise<TIssueActivityReaction[]> {
    return this.get(
      `/api/workspaces/${workspaceSlug}/projects/${projectId}/issues/${issueId}/activities/${activityId}/reactions/`
    )
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async create(
    workspaceSlug: string,
    projectId: string,
    issueId: string,
    activityId: string,
    reaction: string
  ): Promise<TIssueActivityReaction> {
    return this.post(
      `/api/workspaces/${workspaceSlug}/projects/${projectId}/issues/${issueId}/activities/${activityId}/reactions/`,
      { reaction }
    )
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async remove(
    workspaceSlug: string,
    projectId: string,
    issueId: string,
    activityId: string,
    reaction: string
  ): Promise<void> {
    return this.delete(
      `/api/workspaces/${workspaceSlug}/projects/${projectId}/issues/${issueId}/activities/${activityId}/reactions/${reaction}/`
    )
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }
}
