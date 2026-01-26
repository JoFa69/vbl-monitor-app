
import React, { useState, useEffect } from 'react';
import KPIStats from './KPIStats';
import { HourlyChart, WeekdayChart } from './charts/Charts';
import ProblematicStops from './ProblematicStops';
import {
    fetchDashboardMetadata,
    fetchKPIs,
    fetchHourlyStats,
    fetchWeekdayStats,
    fetchProblematicStops
} from '../services/api';

const Dashboard = ({ filters, onFilterChange }) => {
    const [metadata, setMetadata] = useState(null);
    const [loading, setLoading] = useState(true);

    // Data State
    const [kpiData, setKpiData] = useState(null);
    const [hourlyData, setHourlyData] = useState(null);
    const [weekdayData, setWeekdayData] = useState(null);
    const [stopsData, setStopsData] = useState(null);

    // Initial Load (Metadata)
    useEffect(() => {
        const init = async () => {
            try {
                const meta = await fetchDashboardMetadata();
                setMetadata(meta);
            } catch (err) {
                console.error("Failed to load metadata", err);
            }
        };
        init();
    }, []);

    // Fetch Data on Filter Change
    useEffect(() => {
        // Basic debounce check? Or just fetch.
        if (!filters.date_from || !filters.date_to) return;

        const fetchData = async () => {
            setLoading(true);
            try {
                // Parallel fetching
                const [kpis, hourly, weekday, stops] = await Promise.all([
                    fetchKPIs(filters),
                    fetchHourlyStats(filters),
                    fetchWeekdayStats(filters),
                    fetchProblematicStops(filters)
                ]);

                const parse = (d) => (typeof d === 'string' ? JSON.parse(d) : d);

                setKpiData(parse(kpis));
                setHourlyData(parse(hourly));
                setWeekdayData(parse(weekday));
                setStopsData(parse(stops));
            } catch (err) {
                console.error("Error fetching dashboard data", err);
            } finally {
                setLoading(false);
            }
        };

        fetchData();
    }, [filters]);

    // Handle Granularity Change
    const handleGranularityChange = (val) => {
        onFilterChange({ ...filters, granularity: val });
    };

    if (!metadata) return <div className="p-8 text-center text-slate-500">Lade Applikation...</div>;

    return (
        <div className="p-8 max-w-[1600px] mx-auto">
            <div className="flex justify-between items-center mb-6">
                <h2 className="text-2xl font-bold text-slate-800">Übersicht</h2>
                <div className="text-sm text-slate-500">
                    Datenbasis: {filters.metric === 'arrival' ? 'Ankunftszeiten' : 'Abfahrtszeiten'}
                </div>
            </div>

            {loading && <div className="fixed top-4 right-4 bg-vbl-red text-white px-4 py-2 rounded-full shadow-lg text-sm animate-pulse z-50 font-medium">Lade Daten...</div>}

            <KPIStats data={kpiData} config={metadata.config} />

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
                <HourlyChart
                    data={hourlyData}
                    currentGranularity={filters.granularity}
                    onGranularityChange={handleGranularityChange}
                />
                <WeekdayChart data={weekdayData} />
            </div>

            <div className="grid grid-cols-1 gap-6">
                <ProblematicStops data={stopsData} />
            </div>
        </div>
    );
};

export default Dashboard;
