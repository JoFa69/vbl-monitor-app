import React, { useState, useEffect, useMemo } from 'react';
import { Card, CardContent, CardHeader } from '../components/ui/Card';
import { fetchHeatmapStats } from '../services/api';
import { Activity, Map } from 'lucide-react';
import ErrorBoundary from '../components/ui/ErrorBoundary';
import HeatmapStandardView from '../components/Heatmap/HeatmapStandardView';
import HeatmapTripView from '../components/Heatmap/HeatmapTripView';
import { prepareTimeSlots, buildDataMatrix } from '../utils/heatmapUtils';

// Fallback Component
const ErrorFallback = ({ error }) => (
    <div className="p-6 bg-red-50 border border-red-200 rounded-md flex flex-col items-center text-center">
        <h3 className="text-red-800 font-bold mb-2">Anzeige-Fehler</h3>
        <p className="text-red-600 text-sm mb-4">Der Lastteppich konnte nicht komplett geladen werden.</p>
        <pre className="text-xs text-red-500 bg-red-100 p-2 rounded overflow-auto max-w-full">
            {error.message}
        </pre>
    </div>
);

const HeatmapPage = ({ filters, onFilterChange }) => {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [viewMetric, setViewMetric] = useState('punctuality');

    useEffect(() => {
        if (!filters.route) {
            setData(null);
            return;
        }

        const loadData = async () => {
            setLoading(true);
            setError(null);
            try {
                const result = await fetchHeatmapStats(filters);
                if (result.error) {
                    setError(result.error);
                } else {
                    setData(result);
                }
            } catch (err) {
                console.error("Heatmap load failed", err);
                setError("Fehler beim Laden der Heatmap-Daten.");
            } finally {
                setLoading(false);
            }
        };

        loadData();
    }, [filters]);

    // Process Data
    const timeSlots = useMemo(() => prepareTimeSlots(data), [data]);
    const matrix = useMemo(() => buildDataMatrix(data), [data]);

    // SPY LOGGING
    console.log("HeatmapPage Render:", {
        granularity: filters.granularity,
        hasData: !!data,
        hasStops: !!data?.stops,
        dataGrid: !!data?.grid
    });

    if (!filters.route) {
        return (
            <div className="flex flex-col h-full bg-slate-50/50">
                <div className="flex-1 flex flex-col justify-center items-center text-slate-400">
                    <Map className="w-16 h-16 mb-4 opacity-20" />
                    <h3 className="text-xl font-bold text-slate-600 mb-2">Keine Route ausgewählt</h3>
                    <p className="max-w-md text-center">
                        Bitte wählen Sie in der Sidebar eine <strong>Linie</strong> und eine <strong>Route</strong>, um den Lastteppich zu generieren.
                    </p>
                </div>
            </div>
        );
    }

    return (
        <div className="p-4 md:p-8 max-w-[1900px] overflow-hidden flex flex-col h-full">

            {/* Tier 1: View Toolbar (Sticky) */}
            <div className="flex justify-between items-center mb-4 sticky top-0 bg-slate-50 z-30 py-4 border-b border-slate-200">
                <div className="flex items-center gap-4">
                    <h2 className="text-xl font-bold text-slate-800 flex items-center gap-2">
                        <Activity className="w-5 h-5 text-vbl-red" />
                        Analysis
                    </h2>

                    <div className="h-6 w-px bg-slate-300 mx-2"></div>

                    <div className="flex items-center gap-2">
                        <div className="text-xs text-slate-400">
                            {filters.granularity === 'trip' ? "Einzel-Fahrten Plan" :
                                filters.granularity === 'pattern' ? "Muster-Vergleich" :
                                    `Intervall: ${filters.granularity} Min`}
                        </div>
                        {filters.granularity === 'trip' && (
                            <button
                                onClick={() => onFilterChange({ ...filters, granularity: 'pattern', time_from: null, time_to: null })}
                                className="ml-2 px-2 py-0.5 text-xs bg-slate-200 hover:bg-slate-300 text-slate-600 rounded border border-slate-300 transition-colors"
                            >
                                ← Zurück zur Übersicht
                            </button>
                        )}
                    </div>
                </div>

                <div className="flex items-center gap-4">
                    {/* Metric Selector */}
                    <div className="flex items-center gap-2 bg-white border border-slate-200 rounded-md px-2 py-1 shadow-sm">
                        <span className="text-xs text-slate-400 font-bold uppercase tracking-wider">Metrik</span>
                        <select
                            value={viewMetric}
                            onChange={(e) => setViewMetric(e.target.value)}
                            className="text-sm border-none bg-transparent focus:ring-0 font-bold text-slate-700 cursor-pointer py-0 pl-1 pr-6"
                        >
                            <option value="punctuality">Pünktlichkeit (%)</option>
                            <option value="median">Median (P3)</option>
                            <option value="stress">Stress (P1)</option>
                        </select>
                    </div>
                </div>
            </div>

            {loading && <div className="p-8 text-center text-slate-500 animate-pulse">Lade Daten für Cockpit...</div>}
            {error && <div className="p-8 text-center text-red-500">{error}</div>}

            {
                data && (data.stops || data.grid) && (
                    <Card className="flex-1 overflow-hidden flex flex-col border-none shadow-md">
                        <CardHeader className="py-3 px-4 bg-slate-100 border-b">
                            <div className="flex justify-between text-xs text-slate-500">
                                <span>Route: <strong>{filters.route}</strong></span>
                                {filters.granularity === 'trip' ? (
                                    <span><strong>{data.trips?.length || 0}</strong> Fahrten angezeigt</span>
                                ) : filters.granularity === 'pattern' ? (
                                    <span><strong>{data.trips?.length || 0}</strong> Muster angezeigt</span>
                                ) : (
                                    <span className="flex items-center gap-4">
                                        <span>Total Fahrten: {data.data?.reduce((acc, curr) => acc + curr.total, 0) || 0}</span>
                                    </span>
                                )}
                            </div>
                        </CardHeader>
                        <CardContent className="p-0 overflow-auto relative flex-1">
                            <ErrorBoundary FallbackComponent={ErrorFallback}>
                                {filters.granularity === 'trip' || filters.granularity === 'pattern' ? (
                                    <HeatmapTripView
                                        data={data}
                                        matrix={matrix}
                                        filters={filters}
                                        onFilterChange={onFilterChange}
                                    />
                                ) : (
                                    <HeatmapStandardView data={data} matrix={matrix} timeSlots={timeSlots} viewMetric={viewMetric} />
                                )}
                            </ErrorBoundary>
                        </CardContent>
                    </Card>
                )
            }
        </div >
    );
};

export default HeatmapPage;
