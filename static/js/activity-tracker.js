/**
 * Activity Tracker - Automatically track user actions
 * This module tracks all user activities for admin dashboard
 */

class ActivityTracker {
  constructor() {
    this.apiUrl = '/activity/track/';
  }

  /**
   * Track a user activity
   * @param {string} activityType - Type of activity
   * @param {string} description - Optional description
   */
  async track(activityType, description = '') {
    try {
      const token = localStorage.getItem('access_token');
      if (!token) return; // Not logged in

      const response = await fetch(this.apiUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          activity_type: activityType,
          description: description
        })
      });

      if (response.ok) {
        console.log(`✓ Activity tracked: ${activityType}`);
      }
    } catch (error) {
      console.error('Error tracking activity:', error);
    }
  }

  /**
   * Track code compilation
   */
  trackCompilation() {
    this.track('compile', 'Compiled code in editor');
  }

  /**
   * Track snippet creation
   * @param {string} snippetName - Name of snippet
   */
  trackSnippetCreate(snippetName) {
    this.track('snippet_create', `Created snippet: ${snippetName}`);
  }

  /**
   * Track snippet view
   * @param {string} snippetName - Name of snippet
   */
  trackSnippetView(snippetName) {
    this.track('snippet_view', `Viewed snippet: ${snippetName}`);
  }

  /**
   * Track project creation
   * @param {string} projectName - Name of project
   */
  trackProjectCreate(projectName) {
    this.track('project_create', `Created project: ${projectName}`);
  }

  /**
   * Track project edit
   * @param {string} projectName - Name of project
   */
  trackProjectEdit(projectName) {
    this.track('project_edit', `Edited project: ${projectName}`);
  }

  /**
   * Track community post
   */
  trackCommunityPost() {
    this.track('community_post', 'Posted in community');
  }

  /**
   * Track community like
   */
  trackCommunityLike() {
    this.track('community_like', 'Liked community post');
  }

  /**
   * Track community comment
   */
  trackCommunityComment() {
    this.track('community_comment', 'Commented on post');
  }

  /**
   * Track AI chat usage
   */
  trackAIChat() {
    this.track('ai_chat', 'Used AI assistant');
  }

  /**
   * Track code formatting
   */
  trackFormatCode() {
    this.track('format_code', 'Formatted code');
  }

  /**
   * Track code analysis
   */
  trackAnalyzeCode() {
    this.track('analyze_code', 'Analyzed code');
  }
}

// Initialize globally
const activityTracker = new ActivityTracker();

// Example usage in your code:
// activityTracker.trackCompilation()
// activityTracker.trackSnippetCreate('my_snippet')
// activityTracker.trackAIChat()
// etc.

console.log('✓ Activity Tracker loaded');
