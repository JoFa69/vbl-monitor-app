import axios from 'axios';

const API_BASE_URL = 'http://localhost:8081/api';

const api = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        'Content-Type': 'application/json',
    },
});

export const fetchDashboardMetadata = async () => {
    const response = await api.get('/dashboard-metadata');
    return response.data;
};

export const fetchStats = async (filters) => {
    const response = await api.get('/stats', { params: filters });
    return response.data;
};

export const fetchKPIs = async (filters) => {
    // KPI endpoint returns stats + cancellations + percentages + total + config
    const response = await api.get('/components/kpi-stats', { params: filters }); // Using the endpoint defined in dashboard.py
    return response.data;
};

export const fetchHourlyStats = async (filters) => {
    const response = await api.get('/stats/hourly', { params: filters });
    return response.data;
};

export const fetchWeekdayStats = async (filters) => {
    const response = await api.get('/stats/weekday', { params: filters });
    return response.data;
};

export const fetchProblematicStops = async (filters) => {
    const response = await api.get('/stats/stops', { params: filters });
    return response.data;
};

export const fetchWorstTrips = async (filters) => {
    const response = await api.get('/stats/worst-trips', { params: filters });
    return response.data;
};

export const fetchDwellTime = async (filters) => {
    const response = await api.get('/stats/dwell-time', { params: filters });
    return response.data;
};

export const fetchLineStops = async (lineId, route) => {
    const params = {};
    if (route) params.route = route;
    const response = await api.get(`/lines/${lineId}/stops`, { params });
    return response.data;
};



export const fetchHeatmapStats = async (filters) => {
    const response = await api.get('/stats/heatmap', { params: filters });
    return response.data;
};

export const fetchSettings = async () => {
    const response = await api.get('/v1/settings');
    return response.data;
};

export const saveSettings = async (settings) => {
    const response = await api.post('/v1/settings', settings);
    return response.data;
};

export default api;
