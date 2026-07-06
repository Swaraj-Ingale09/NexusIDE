"""
Leaderboard and Achievements System
Gamification features for user engagement
"""

from typing import Dict, List, Tuple
from datetime import datetime, timedelta
from django.db.models import F, Sum, Count, Q
from django.utils import timezone
from apps.users.models import UserProfile, UserActivity
from apps.problems.models import UserProblemStats, Contest, ContestParticipation


class LeaderboardManager:
    """Manages leaderboards for competitive aspects"""
    
    # Leaderboard types
    TYPE_GLOBAL = 'global'
    TYPE_WEEKLY = 'weekly'
    TYPE_MONTHLY = 'monthly'
    TYPE_CONTEST = 'contest'
    
    @staticmethod
    def get_global_leaderboard(limit: int = 100, offset: int = 0) -> List[Dict]:
        """
        Get global leaderboard by problems solved and XP
        
        Returns list of users with:
        - rank, username, xp_points, level, problems_solved, last_activity
        """
        users = UserProfile.objects.select_related('user').order_by(
            '-xp_points', '-problems_solved'
        )[offset:offset + limit]
        
        leaderboard = []
        for rank, profile in enumerate(users, start=offset + 1):
            leaderboard.append({
                'rank': rank,
                'user_id': profile.user.id,
                'username': profile.user.username,
                'avatar': profile.avatar.url if profile.avatar else None,
                'xp_points': profile.xp_points,
                'level': profile.level,
                'problems_solved': profile.problems_solved,
                'streak_days': profile.streak_days,
                'last_activity': profile.last_activity.isoformat() if profile.last_activity else None,
            })
        
        return leaderboard
    
    @staticmethod
    def get_weekly_leaderboard(limit: int = 50, offset: int = 0) -> List[Dict]:
        """
        Get leaderboard for this week
        Based on activity and problems solved in last 7 days
        """
        week_ago = timezone.now() - timedelta(days=7)
        
        # Get users with activity in past week
        active_users = UserActivity.objects.filter(
            timestamp__gte=week_ago
        ).values('user').distinct()
        
        user_ids = [u['user'] for u in active_users]
        
        users = UserProfile.objects.filter(
            user_id__in=user_ids
        ).select_related('user').order_by('-xp_points')
        
        leaderboard = []
        for rank, profile in enumerate(users[offset:offset + limit], start=offset + 1):
            # Calculate weekly XP
            weekly_activities = UserActivity.objects.filter(
                user=profile.user,
                timestamp__gte=week_ago
            ).count()
            weekly_xp = weekly_activities * 10  # 10 XP per activity
            
            leaderboard.append({
                'rank': rank,
                'user_id': profile.user.id,
                'username': profile.user.username,
                'weekly_xp': weekly_xp,
                'activities': weekly_activities,
                'level': profile.level,
            })
        
        return leaderboard
    
    @staticmethod
    def get_monthly_leaderboard(limit: int = 50, offset: int = 0) -> List[Dict]:
        """Get leaderboard for this month"""
        month_ago = timezone.now() - timedelta(days=30)
        
        active_users = UserActivity.objects.filter(
            timestamp__gte=month_ago
        ).values('user').distinct()
        
        user_ids = [u['user'] for u in active_users]
        users = UserProfile.objects.filter(
            user_id__in=user_ids
        ).select_related('user').order_by('-xp_points')
        
        leaderboard = []
        for rank, profile in enumerate(users[offset:offset + limit], start=offset + 1):
            monthly_activities = UserActivity.objects.filter(
                user=profile.user,
                timestamp__gte=month_ago
            ).count()
            monthly_xp = monthly_activities * 10
            
            leaderboard.append({
                'rank': rank,
                'user_id': profile.user.id,
                'username': profile.user.username,
                'monthly_xp': monthly_xp,
                'activities': monthly_activities,
            })
        
        return leaderboard
    
    @staticmethod
    def get_problem_solving_leaderboard(limit: int = 100) -> List[Dict]:
        """Leaderboard for problem solving"""
        stats = UserProblemStats.objects.select_related('user').order_by(
            '-problems_solved', '-total_accepted'
        )[:limit]
        
        leaderboard = []
        for rank, stat in enumerate(stats, 1):
            acceptance_rate = stat.best_acceptance_rate if stat.total_submissions > 0 else 0
            
            leaderboard.append({
                'rank': rank,
                'user_id': stat.user.id,
                'username': stat.user.username,
                'problems_solved': stat.problems_solved,
                'total_submissions': stat.total_submissions,
                'acceptance_rate': acceptance_rate,
                'easy': stat.easy_solved,
                'medium': stat.medium_solved,
                'hard': stat.hard_solved,
                'expert': stat.expert_solved,
            })
        
        return leaderboard
    
    @staticmethod
    def get_contest_leaderboard(contest_id: int, limit: int = 100) -> List[Dict]:
        """Get leaderboard for a specific contest"""
        participations = ContestParticipation.objects.filter(
            contest_id=contest_id
        ).select_related('user').order_by('rank', '-total_score')[:limit]
        
        leaderboard = []
        for participation in participations:
            leaderboard.append({
                'rank': participation.rank or 0,
                'user_id': participation.user.id,
                'username': participation.user.username,
                'problems_solved': participation.problems_solved,
                'total_score': participation.total_score,
                'penalty_time': participation.penalty_time,
                'finished_at': participation.finished_at.isoformat() if participation.finished_at else None,
            })
        
        return leaderboard
    
    @staticmethod
    def get_user_rank(user_id: int, leaderboard_type: str = 'global') -> Dict:
        """Get a user's rank in specific leaderboard"""
        try:
            profile = UserProfile.objects.get(user_id=user_id)
        except UserProfile.DoesNotExist:
            return {'rank': None, 'error': 'User not found'}
        
        if leaderboard_type == 'global':
            users_above = UserProfile.objects.filter(
                xp_points__gt=profile.xp_points
            ).count()
            return {
                'rank': users_above + 1,
                'xp': profile.xp_points,
                'level': profile.level,
            }
        
        elif leaderboard_type == 'weekly':
            week_ago = timezone.now() - timedelta(days=7)
            weekly_activities = UserActivity.objects.filter(
                user_id=user_id,
                timestamp__gte=week_ago
            ).count()
            
            users_above = 0  # Would need complex query
            return {
                'rank': users_above + 1,
                'weekly_xp': weekly_activities * 10,
            }
        
        elif leaderboard_type == 'problems':
            try:
                stats = UserProblemStats.objects.get(user_id=user_id)
                users_above = UserProblemStats.objects.filter(
                    problems_solved__gt=stats.problems_solved
                ).count()
                return {
                    'rank': users_above + 1,
                    'problems_solved': stats.problems_solved,
                }
            except:
                return {'rank': None}
        
        return {'rank': None}


class AchievementManager:
    """Manages achievements and badges"""
    
    # Achievement definitions
    ACHIEVEMENTS = {
        'first_problem': {
            'title': 'First Steps',
            'description': 'Solve your first problem',
            'icon': 'trophy',
            'xp_reward': 50,
            'condition': lambda user: UserProblemStats.objects.get(user=user).problems_solved >= 1
        },
        'problem_master': {
            'title': 'Problem Master',
            'description': 'Solve 50 problems',
            'icon': 'crown',
            'xp_reward': 500,
            'condition': lambda user: UserProblemStats.objects.get(user=user).problems_solved >= 50
        },
        'legendary': {
            'title': 'Legendary Coder',
            'description': 'Solve 500 problems',
            'icon': 'star',
            'xp_reward': 5000,
            'condition': lambda user: UserProblemStats.objects.get(user=user).problems_solved >= 500
        },
        'speedster': {
            'title': 'Speedster',
            'description': 'Solve a problem in under 30 seconds',
            'icon': 'zap',
            'xp_reward': 200,
        },
        'streak_7': {
            'title': 'On Fire',
            'description': 'Maintain 7-day streak',
            'icon': 'flame',
            'xp_reward': 300,
            'condition': lambda user: UserProfile.objects.get(user=user).streak_days >= 7
        },
        'streak_30': {
            'title': 'Unstoppable',
            'description': 'Maintain 30-day streak',
            'icon': 'zap-off',
            'xp_reward': 1000,
            'condition': lambda user: UserProfile.objects.get(user=user).streak_days >= 30
        },
        'helper': {
            'title': 'Helper',
            'description': 'Comment on 10 problems or posts',
            'icon': 'help-circle',
            'xp_reward': 200,
        },
        'perfect_week': {
            'title': 'Perfect Week',
            'description': 'Solve at least one problem daily for 7 days',
            'icon': 'calendar',
            'xp_reward': 400,
        },
        'early_bird': {
            'title': 'Early Bird',
            'description': 'Solve 5 easy problems',
            'icon': 'sunrise',
            'xp_reward': 100,
            'condition': lambda user: UserProblemStats.objects.get(user=user).easy_solved >= 5
        },
        'intermediate': {
            'title': 'Intermediate',
            'description': 'Solve 10 medium problems',
            'icon': 'trending-up',
            'xp_reward': 300,
            'condition': lambda user: UserProblemStats.objects.get(user=user).medium_solved >= 10
        },
        'expert': {
            'title': 'Expert',
            'description': 'Solve 5 hard problems',
            'icon': 'award',
            'xp_reward': 500,
            'condition': lambda user: UserProblemStats.objects.get(user=user).hard_solved >= 5
        },
        'hacker': {
            'title': 'Hacker',
            'description': 'Solve 10 hard or expert problems',
            'icon': 'lock',
            'xp_reward': 1000,
            'condition': lambda user: (UserProblemStats.objects.get(user=user).hard_solved + 
                                      UserProblemStats.objects.get(user=user).expert_solved) >= 10
        },
    }
    
    @staticmethod
    def check_achievements(user) -> List[Dict]:
        """Check and award applicable achievements"""
        awarded = []
        
        try:
            profile = UserProfile.objects.get(user=user)
            stats = UserProblemStats.objects.get(user=user)
        except:
            return awarded
        
        for achievement_key, achievement_def in AchievementManager.ACHIEVEMENTS.items():
            # Check if already has achievement
            if profile.achievements.filter(title=achievement_def['title']).exists():
                continue
            
            # Check condition
            if 'condition' in achievement_def:
                try:
                    if achievement_def['condition'](user):
                        awarded.append({
                            'key': achievement_key,
                            'title': achievement_def['title'],
                            'description': achievement_def['description'],
                            'icon': achievement_def['icon'],
                            'xp_reward': achievement_def['xp_reward'],
                        })
                except:
                    pass
        
        return awarded
    
    @staticmethod
    def get_user_achievements(user_id: int) -> List[Dict]:
        """Get all achievements for a user"""
        try:
            profile = UserProfile.objects.get(user_id=user_id)
        except:
            return []
        
        achievements = []
        for achievement in profile.achievements.all():
            achievements.append({
                'title': achievement.title,
                'description': achievement.description,
                'icon': achievement.icon,
                'earned_at': achievement.earned_at.isoformat(),
            })
        
        return achievements
    
    @staticmethod
    def get_next_achievement(user_id: int) -> Dict:
        """Get next achievable achievement"""
        try:
            stats = UserProblemStats.objects.get(user_id=user_id)
        except:
            return {}
        
        # Next goal based on problems solved
        problem_count = stats.problems_solved
        
        if problem_count < 1:
            return {
                'achievement': 'First Steps',
                'progress': f'{problem_count}/1',
                'description': 'Solve your first problem'
            }
        elif problem_count < 50:
            return {
                'achievement': 'Problem Master',
                'progress': f'{problem_count}/50',
                'description': 'Solve 50 problems'
            }
        elif problem_count < 500:
            return {
                'achievement': 'Legendary Coder',
                'progress': f'{problem_count}/500',
                'description': 'Solve 500 problems'
            }
        
        return {'achievement': 'No more achievements available'}
