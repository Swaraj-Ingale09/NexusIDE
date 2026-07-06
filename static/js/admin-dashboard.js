// Admin Dashboard Script
function adminDashboard() {
  return {
    activeTab: 'overview',
    summary: {},
    satisfaction: {},
    users: [],
    activities: [],
    satisfactions: [],
    selectedUserDetail: null,
    searchUser: '',
    overviewChart: null,

    async init() {
      // Check if user is admin
      const token = localStorage.getItem('access_token');
      if (!token) {
        window.location.href = '/login/';
        return;
      }

      // Load dashboard data
      await this.loadDashboardData();
      await this.loadUsers();
      await this.loadActivities();
      await this.loadSatisfaction();
      
      // Initialize chart
      this.initializeChart();
    },

    async loadDashboardData() {
      try {
        const token = localStorage.getItem('access_token');
        const response = await fetch('/admin/dashboard/', {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });

        if (response.ok) {
          const data = await response.json();
          this.summary = data.summary;
          this.satisfaction = data.satisfaction;
        } else if (response.status === 403) {
          alert('Access Denied: Admin privileges required');
          window.location.href = '/';
        }
      } catch (error) {
        console.error('Error loading dashboard:', error);
      }
    },

    async loadUsers() {
      try {
        const token = localStorage.getItem('access_token');
        const response = await fetch('/admin/users/', {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });

        if (response.ok) {
          this.users = await response.json();
        }
      } catch (error) {
        console.error('Error loading users:', error);
      }
    },

    async loadActivities() {
      try {
        const token = localStorage.getItem('access_token');
        const response = await fetch('/admin/activities/', {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });

        if (response.ok) {
          this.activities = await response.json();
        }
      } catch (error) {
        console.error('Error loading activities:', error);
      }
    },

    async loadSatisfaction() {
      try {
        const token = localStorage.getItem('access_token');
        const response = await fetch('/user/satisfaction/', {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });

        if (response.ok) {
          this.satisfactions = await response.json();
        }
      } catch (error) {
        console.error('Error loading satisfaction:', error);
      }
    },

    async viewUserDetail(userId) {
      try {
        const token = localStorage.getItem('access_token');
        const response = await fetch(`/admin/users/${userId}/`, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });

        if (response.ok) {
          this.selectedUserDetail = await response.json();
        }
      } catch (error) {
        console.error('Error loading user detail:', error);
      }
    },

    initializeChart() {
      setTimeout(() => {
        const canvas = document.getElementById('overviewChart');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        
        // Simple overview chart showing user engagement
        this.overviewChart = new Chart(ctx, {
          type: 'doughnut',
          data: {
            labels: ['Active Users', 'Total Sessions'],
            datasets: [{
              data: [
                this.summary.active_users || 0,
                (this.summary.total_sessions || 1) - (this.summary.active_users || 0)
              ],
              backgroundColor: [
                'rgba(34, 211, 238, 0.8)',
                'rgba(124, 58, 237, 0.8)'
              ],
              borderColor: [
                'var(--cyan)',
                'var(--violet)'
              ],
              borderWidth: 2
            }]
          },
          options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
              legend: {
                position: 'bottom',
                labels: {
                  color: 'var(--text-secondary)',
                  padding: 15,
                  font: {
                    size: 13,
                    weight: '600'
                  }
                }
              }
            }
          }
        });
      }, 100);
    },

    get filteredUsers() {
      if (!this.searchUser) {
        return this.users;
      }
      
      const search = this.searchUser.toLowerCase();
      return this.users.filter(user =>
        user.username.toLowerCase().includes(search) ||
        user.email.toLowerCase().includes(search) ||
        (user.first_name && user.first_name.toLowerCase().includes(search)) ||
        (user.last_name && user.last_name.toLowerCase().includes(search))
      );
    },

    logout() {
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      localStorage.removeItem('nexuside_user');
      window.location.href = '/';
    }
  }
}
