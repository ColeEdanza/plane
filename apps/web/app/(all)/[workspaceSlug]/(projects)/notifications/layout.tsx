/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { Outlet } from "react-router";
// components
import { NotificationsSidebarRoot } from "@/components/workspace-notifications/sidebar";

export default function ProjectInboxIssuesLayout() {
  return (
    <div className="relative flex h-full w-full items-center overflow-hidden">
      <NotificationsSidebarRoot />
      {/* CSFD fork: drop the outer overflow-y-auto so the embedded peek
          panel's internal scroll handles work-item content. With the
          outer scrolling, the peek panel never gets bounded height and
          its pinned composer floats with the content instead of pinning. */}
      <div className="h-full w-full overflow-hidden">
        <Outlet />
      </div>
    </div>
  );
}
