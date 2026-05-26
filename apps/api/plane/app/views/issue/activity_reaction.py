# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Third Party imports
from rest_framework.response import Response
from rest_framework import status

# Module imports
from .. import BaseViewSet
from plane.app.serializers import IssueActivityReactionSerializer
from plane.app.permissions import allow_permission, ROLE
from plane.db.models import IssueActivity, IssueActivityReaction


class IssueActivityReactionViewSet(BaseViewSet):
    serializer_class = IssueActivityReactionSerializer
    model = IssueActivityReaction

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(workspace__slug=self.kwargs.get("slug"))
            .filter(project_id=self.kwargs.get("project_id"))
            .filter(activity_id=self.kwargs.get("activity_id"))
            .filter(
                project__project_projectmember__member=self.request.user,
                project__project_projectmember__is_active=True,
                project__archived_at__isnull=True,
            )
            .order_by("-created_at")
            .distinct()
        )

    @allow_permission([ROLE.ADMIN, ROLE.MEMBER, ROLE.GUEST])
    def create(self, request, slug, project_id, issue_id, activity_id):
        # Bind the reaction to an activity that actually belongs to this issue.
        # Guards against a member crafting a payload referencing an activity
        # on an issue they cannot see.
        if not IssueActivity.objects.filter(
            pk=activity_id,
            issue_id=issue_id,
            project_id=project_id,
            workspace__slug=slug,
        ).exists():
            return Response({"error": "Activity not found"}, status=status.HTTP_404_NOT_FOUND)

        serializer = IssueActivityReactionSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(
                activity_id=activity_id,
                project_id=project_id,
                actor=request.user,
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @allow_permission([ROLE.ADMIN, ROLE.MEMBER, ROLE.GUEST])
    def destroy(self, request, slug, project_id, issue_id, activity_id, reaction_code):
        issue_activity_reaction = IssueActivityReaction.objects.get(
            workspace__slug=slug,
            project_id=project_id,
            activity_id=activity_id,
            reaction=reaction_code,
            actor=request.user,
        )
        issue_activity_reaction.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
