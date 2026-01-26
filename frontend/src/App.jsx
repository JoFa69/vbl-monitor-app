
import React, { useState, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import Dashboard from './components/Dashboard';
import Settings from './components/Settings';
import HeatmapPage from './pages/HeatmapPage';

function App() {
  const [activeTab, setActiveTab] = useState('dashboard');

  // Lifted Filter State
  const [filters, setFilters] = useState({
    date_from: '',
    date_to: '',
    time_from: '',
    time_to: '',
    line: '',
    route: '',
    stop: '',
    day_class: '',
    metric: 'arrival', // 'arrival' or 'departure'
    granularity: 60
  });

  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);

  // Auto-collapse on Heatmap
  useEffect(() => {
    if (activeTab === 'heatmap') {
      setIsSidebarCollapsed(true);
    } else {
      setIsSidebarCollapsed(false);
    }
  }, [activeTab]);

  return (
    <div className="flex bg-slate-50 min-h-screen font-sans text-slate-900">
      <Sidebar
        activeTab={activeTab}
        onTabChange={setActiveTab}
        filters={filters}
        onFilterChange={(newFilters) => {
          // Intercept Filter Changes for Logic
          let finalFilters = typeof newFilters === 'function' ? newFilters(filters) : newFilters;

          // Auto-Switch Logic: Trip View vs Pattern View
          // If granularity is 'trip' or 'pattern', check date range
          if (finalFilters.granularity === 'trip' || finalFilters.granularity === 'pattern') {
            const d1 = new Date(finalFilters.date_from);
            const d2 = new Date(finalFilters.date_to);

            // If dates are valid
            if (!isNaN(d1) && !isNaN(d2)) {
              const diffTime = Math.abs(d2 - d1);
              const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

              if (diffDays > 0) { // e.g. 2025-11-01 to 2025-11-02 is diffDays=1 (which implies 2 days span if inclusive? actually d2-d1 usually gives difference. Single day same date is 0.)
                // Wait, date input values are strings YYYY-MM-DD.
                // Same day: 2025-11-01 - 2025-11-01 = 0 ms using Date.parse?
                // If diff > 0 (meaning more than 1 day selected, e.g. Start != End), force 'pattern'.
                // Exception: Maybe user wants 'trip' for multiple days? Usually too much data.
                // Let's enforce Pattern for > 1 day.
                if (finalFilters.granularity === 'trip') {
                  // Only force Pattern View if NO specific time window is set (Drill-Down safety)
                  if (!finalFilters.time_from && !finalFilters.time_to) {
                    console.log("Auto-Switching to Pattern View (Range > 1 Day & No Time Filter)");
                    finalFilters.granularity = 'pattern';
                  }
                }
              } else {
                // Single Day
                if (finalFilters.granularity === 'pattern') {
                  console.log("Auto-Switching to Trip View (Single Day)");
                  finalFilters.granularity = 'trip';
                }
              }
            }
          }

          setFilters(finalFilters);
        }}
        isCollapsed={isSidebarCollapsed}
        toggleCollapse={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
      />

      <main className={`flex-1 transition-all duration-300 ${isSidebarCollapsed ? 'ml-20' : 'ml-80'}`}>
        {activeTab === 'dashboard' && <Dashboard filters={filters} onFilterChange={setFilters} />}
        {activeTab === 'analytics' && <Dashboard filters={filters} onFilterChange={setFilters} /> /* Placeholder reuse */}
        {activeTab === 'heatmap' && <HeatmapPage filters={filters} onFilterChange={setFilters} />}
        {activeTab === 'settings' && <Settings />}
      </main>
    </div>
  );
}

export default App;
