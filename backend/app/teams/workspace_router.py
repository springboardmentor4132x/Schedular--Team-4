import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr

from app.database.session import get_db
from app.core.dependencies import get_current_user
from app.core.responses import standard_response
from app.database.models import (
    User,
    Team,
    TeamMember,
    WorkspaceInvitation,
)


router = APIRouter(
    prefix="/api/v1/workspace",
    tags=["Workspace Management & Member Invitations"],
)


# ============================================================
# REQUEST MODELS
# ============================================================

class InviteReq(BaseModel):
    team_id: str
    email: EmailStr
    role_name: str = "Marketing Team"


class UpdateMemberRoleReq(BaseModel):
    role_name: str


# ============================================================
# INVITE WORKSPACE MEMBER
# ============================================================

@router.post("/invite")
def invite_workspace_member(
    req: InviteReq,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Invite a user to the workspace.

    If the email already exists in the database:
        - Add the existing user to the workspace immediately.

    If the email does not exist:
        - Create a pending WorkspaceInvitation.
        - Generate a secure invitation token.

    No "User not found" error is returned for unknown emails.
    """

    # --------------------------------------------------------
    # Check workspace/team
    # --------------------------------------------------------

    team = db.query(Team).filter(
        Team.id == req.team_id
    ).first()

    if not team:
        raise HTTPException(
            status_code=404,
            detail="Workspace team not found.",
        )

    # --------------------------------------------------------
    # Check whether user already exists
    # --------------------------------------------------------

    target_user = db.query(User).filter(
        User.email == req.email
    ).first()

    # ========================================================
    # EXISTING USER
    # ========================================================

    if target_user:

        # Check whether already a workspace member
        existing_member = db.query(TeamMember).filter(
            TeamMember.team_id == req.team_id,
            TeamMember.user_id == target_user.id,
        ).first()

        if existing_member:
            raise HTTPException(
                status_code=400,
                detail=f"{req.email} is already a member of this workspace.",
            )

        # Create active workspace membership
        new_member = TeamMember(
            team_id=req.team_id,
            user_id=target_user.id,
            role_in_team=req.role_name,
        )

        db.add(new_member)
        db.commit()
        db.refresh(new_member)

        return standard_response(
            success=True,
            message="Invitation sent successfully. Member added to workspace.",
            data={
                "member_id": new_member.user_id,
                "email": target_user.email,
                "role": req.role_name,
                "status": "active",
            },
        )

    # ========================================================
    # USER DOES NOT EXIST
    # ========================================================

    # Check if invitation is already pending
    existing_invitation = db.query(WorkspaceInvitation).filter(
        WorkspaceInvitation.team_id == req.team_id,
        WorkspaceInvitation.email == req.email,
        WorkspaceInvitation.status == "pending",
    ).first()

    if existing_invitation:
        return standard_response(
            success=True,
            message="Invitation email already pending for this address.",
            data={
                "invitation_id": existing_invitation.id,
                "email": req.email,
                "role": existing_invitation.role_name,
                "status": "pending",
                "token": existing_invitation.token,
            },
        )

    # Generate invitation token
    invitation_token = f"inv_{uuid.uuid4().hex}"

    # Invitation expires after 7 days
    expires_at = datetime.utcnow() + timedelta(days=7)

    invitation = WorkspaceInvitation(
        team_id=req.team_id,
        email=req.email,
        role_name=req.role_name,
        token=invitation_token,
        status="pending",
        expires_at=expires_at,
    )

    db.add(invitation)
    db.commit()
    db.refresh(invitation)

    return standard_response(
        success=True,
        message="Invitation sent successfully. Pending registration token generated.",
        data={
            "invitation_id": invitation.id,
            "email": req.email,
            "role": req.role_name,
            "status": "pending",
            "token": invitation_token,
            "expires_at": expires_at.isoformat(),
        },
    )


# ============================================================
# LIST WORKSPACE MEMBERS
# ============================================================

@router.get("/members")
def list_workspace_members(
    team_id: str = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieve all active workspace members and pending invitations.
    """

    # Check workspace/team
    team = db.query(Team).filter(
        Team.id == team_id
    ).first()

    if not team:
        raise HTTPException(
            status_code=404,
            detail="Workspace team not found.",
        )

    # Get active members
    members = db.query(TeamMember).filter(
        TeamMember.team_id == team_id
    ).all()

    # Get pending invitations
    invitations = db.query(WorkspaceInvitation).filter(
        WorkspaceInvitation.team_id == team_id,
        WorkspaceInvitation.status == "pending",
    ).all()

    member_list = []

    # ========================================================
    # ACTIVE MEMBERS
    # ========================================================

    for member in members:

        user = member.user

        member_list.append(
            {
                "id": member.user_id,
                "user_id": member.user_id,
                "name": user.name if user else "Workspace Member",
                "email": user.email if user else "",
                "role": member.role_in_team,
                "status": "active",
                "joined_at": (
                    member.joined_at.isoformat()
                    if member.joined_at
                    else None
                ),
            }
        )

    # ========================================================
    # PENDING INVITATIONS
    # ========================================================

    for invitation in invitations:

        member_list.append(
            {
                "id": invitation.id,
                "user_id": None,
                "name": invitation.email.split("@")[0].capitalize(),
                "email": invitation.email,
                "role": invitation.role_name,
                "status": "pending",
                "joined_at": (
                    invitation.created_at.isoformat()
                    if invitation.created_at
                    else None
                ),
                "token": invitation.token,
            }
        )

    return standard_response(
        success=True,
        message="Workspace members and invitations retrieved",
        data={
            "members": member_list,
        },
    )


# ============================================================
# UPDATE MEMBER ROLE
# ============================================================

@router.put("/member/{id}")
def update_workspace_member_role(
    id: str,
    req: UpdateMemberRoleReq,
    team_id: str = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update the role of an active member
    or a pending invitation.
    """

    # ========================================================
    # CHECK ACTIVE TEAM MEMBER
    # ========================================================

    member = db.query(TeamMember).filter(
        TeamMember.team_id == team_id,
        TeamMember.user_id == id,
    ).first()

    if member:

        member.role_in_team = req.role_name

        db.commit()
        db.refresh(member)

        return standard_response(
            success=True,
            message="Workspace member role updated successfully",
            data={
                "user_id": id,
                "role": req.role_name,
            },
        )

    # ========================================================
    # CHECK PENDING INVITATION
    # ========================================================

    invitation = db.query(WorkspaceInvitation).filter(
        WorkspaceInvitation.id == id,
        WorkspaceInvitation.team_id == team_id,
    ).first()

    if invitation:

        invitation.role_name = req.role_name

        db.commit()
        db.refresh(invitation)

        return standard_response(
            success=True,
            message="Pending invitation role updated successfully",
            data={
                "invitation_id": id,
                "role": req.role_name,
            },
        )

    # ========================================================
    # NOT FOUND
    # ========================================================

    raise HTTPException(
        status_code=404,
        detail="Workspace member or invitation record not found.",
    )


# ============================================================
# REMOVE WORKSPACE MEMBER / CANCEL INVITATION
# ============================================================

@router.delete("/member/{id}")
def remove_workspace_member(
    id: str,
    team_id: str = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Remove an active workspace member
    or cancel a pending invitation.
    """

    # ========================================================
    # CHECK ACTIVE MEMBER
    # ========================================================

    member = db.query(TeamMember).filter(
        TeamMember.team_id == team_id,
        TeamMember.user_id == id,
    ).first()

    if member:

        db.delete(member)
        db.commit()

        return standard_response(
            success=True,
            message="Member removed from workspace",
            data={
                "user_id": id,
            },
        )

    # ========================================================
    # CHECK PENDING INVITATION
    # ========================================================

    invitation = db.query(WorkspaceInvitation).filter(
        WorkspaceInvitation.id == id,
        WorkspaceInvitation.team_id == team_id,
    ).first()

    if invitation:

        invitation.status = "cancelled"

        db.delete(invitation)
        db.commit()

        return standard_response(
            success=True,
            message="Pending invitation cancelled",
            data={
                "invitation_id": id,
            },
        )

    # ========================================================
    # NOT FOUND
    # ========================================================

    raise HTTPException(
        status_code=404,
        detail="Workspace member or invitation not found.",
    )