# apps/teams/context_processors.py

from .models import TeamMembership, MembershipStatus


def team_invite_count(request):
    """
    navbar 用：自分宛の未承認招待数（INVITED）
    """
    if not request.user.is_authenticated:
        return {"team_invite_count": 0}

    count = TeamMembership.objects.filter(
        user=request.user,
        is_active=True,
        status=MembershipStatus.INVITED,
        team__is_active=True,
    ).count()

    return {"team_invite_count": count}
