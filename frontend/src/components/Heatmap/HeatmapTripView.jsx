import React from 'react';
import { getCellColor } from '../../utils/heatmapUtils';

const HeatmapTripView = ({ data, filters, onFilterChange }) => {
    // 1. Safety Check
    if (!data || !data.grid || data.grid.length === 0) {
        return (
            <div className="flex flex-col items-center justify-center h-64 text-slate-400">
                <p>Keine Fahrtdaten verfügbar.</p>
            </div>
        );
    }

    const { grid, stops, trips } = data;

    // Layout Constants
    const CELL_WIDTH = 50;
    const CELL_HEIGHT = 35;
    const HEADER_HEIGHT = 100; // Increased for vertical text
    const FIRST_COL_WIDTH = 200;

    // Safety for missing metadata (fallback to indices if lists are empty)
    const effectiveStops = stops || grid.map((_, i) => `Stop ${i + 1}`);
    const effectiveTrips = trips || grid[0].map((_, i) => ({ label: `${i + 1}`, id: i }));

    // Calculate total width
    const totalWidth = FIRST_COL_WIDTH + (grid[0].length * CELL_WIDTH);

    return (
        <div className="w-full h-[600px] overflow-auto border border-slate-200 rounded bg-white relative">
            <div
                style={{
                    display: 'grid',
                    gridTemplateColumns: `${FIRST_COL_WIDTH}px repeat(${grid[0].length}, ${CELL_WIDTH}px)`,
                    minWidth: 'max-content',
                }}
            >
                {/* 1. HEADER ROW */}
                {/* Top-Left Empty Corner */}
                <div
                    className="sticky top-0 left-0 z-20 bg-slate-100 border-b border-r border-slate-200 flex items-center justify-center font-bold text-xs text-slate-500 shadow-sm"
                    style={{ height: HEADER_HEIGHT, width: FIRST_COL_WIDTH, minWidth: FIRST_COL_WIDTH }}
                >
                    <div className="flex flex-col items-center gap-1">
                        <span>Haltestellle</span>
                        <span className="text-[10px] font-normal text-slate-400">vs</span>
                        {filters?.granularity === 'trip' && filters?.time_from ? (
                            <span className="text-blue-600 font-bold">{filters.time_from.substring(0, 5)}</span>
                        ) : (
                            <span>Muster</span>
                        )}
                    </div>
                </div>

                {/* Trip Headers */}
                {effectiveTrips.map((trip, colIndex) => {
                    // Logic for Drill-Through
                    const isPatternView = filters?.granularity === 'pattern';
                    const isTripView = filters?.granularity === 'trip';

                    // Label: In Pattern View -> Time (x_labels or trip.label). In Trip View -> Date (trip.date)
                    let displayLabel = (data.x_labels && data.x_labels[colIndex]) ? data.x_labels[colIndex] : trip.label;
                    if (isTripView && trip.date) {
                        displayLabel = trip.date;
                    }

                    // Time for Drill calculation (always use time from data or trip.label if x_labels missing)
                    const timeForLogic = (data.x_labels && data.x_labels[colIndex]) ? data.x_labels[colIndex] : trip.label;

                    const handleHeaderClick = () => {
                        if (!isPatternView || !onFilterChange || !filters) return;

                        try {
                            // Fix: Extract strict time by simple split (robust against '06:30 (n=5)')
                            const timeClean = timeForLogic.split(' ')[0];

                            // Validate format roughly (HH:MM)
                            if (!timeClean.includes(':')) {
                                console.warn("Invalid time format for drill-down:", timeClean);
                                return;
                            }

                            const [hh, mm] = timeClean.split(':');

                            // FILTER STRICTLY ON THIS MINUTE
                            const tf = `${hh}:${mm}:00`;
                            const tt = `${hh}:${mm}:59`;

                            console.log(`DRILLTHROUGH EXECUTED: ${tf} - ${tt}`);

                            onFilterChange({
                                ...filters,
                                granularity: 'trip',
                                time_from: tf,
                                time_to: tt
                            });

                        } catch (e) {
                            console.error("Error calculating drill-down time", e);
                        }
                    };

                    return (
                        <div
                            key={`header-${colIndex}`}
                            className={`sticky top-0 z-10 bg-slate-50 border-b border-slate-200 flex flex-col items-center justify-end pb-2 text-[10px] text-slate-600 font-medium px-1 group ${isPatternView ? 'hover:bg-blue-50 cursor-pointer' : 'hover:bg-slate-100'}`}
                            style={{ height: HEADER_HEIGHT, width: CELL_WIDTH, minWidth: CELL_WIDTH }}
                            title={isPatternView ? `Klicken um Einzelfahrten für ~${timeForLogic} zu sehen` : `Zeit: ${trip.label}\nDatum: ${trip.date || 'unknown'}\nRoute: ${trip.vehicle || 'N/A'}\nID: ${trip.id}`}
                            onClick={handleHeaderClick}
                        >
                            {/* Vertical Text */}
                            <div className="rotate-[-90deg] translate-y-[-10px] whitespace-nowrap origin-bottom pointer-events-none">
                                <span className={`font-bold ${isPatternView ? 'text-blue-600 underline decoration-blue-300' : 'text-slate-700'}`}>
                                    {displayLabel}
                                </span>
                                {/* Show Route (Pattern) or nothing (Trip) */}
                                {trip.vehicle && isPatternView && (
                                    <span className="ml-2 text-[9px] text-slate-400 font-normal">
                                        {trip.vehicle.length > 20 ? trip.vehicle.substring(0, 18) + '..' : trip.vehicle}
                                    </span>
                                )}
                            </div>
                        </div>
                    );
                })}

                {/* 2. DATA ROWS */}
                {grid.map((row, rowIndex) => (
                    <React.Fragment key={`row-${rowIndex}`}>
                        {/* Stop Name (Sticky Left Column) */}
                        <div
                            className="sticky left-0 z-10 bg-white border-r border-b border-slate-100 flex items-center px-3 text-xs text-slate-700 font-medium truncate"
                            style={{
                                height: CELL_HEIGHT,
                                width: FIRST_COL_WIDTH,
                                top: 'auto', // Prevent sticky top conflict
                                position: 'sticky',
                                left: 0
                            }}
                            title={effectiveStops[rowIndex]}
                        >
                            {effectiveStops[rowIndex]}
                        </div>

                        {/* Grid Cells */}
                        {row.map((value, colIndex) => {
                            const bg = value !== null ? getCellColor({ delay: value }, 'trip_deviation') : '#f9fafb'; // empty/null color
                            const trip = effectiveTrips[colIndex];

                            // Build Tooltip
                            let tooltip = `Stop: ${effectiveStops[rowIndex]}\n`;
                            tooltip += `Zeit: ${trip.label}\n`;

                            if (trip.trip_count) {
                                // Pattern View Tooltip
                                tooltip += `Route: ${trip.vehicle}\n`;
                                tooltip += `Basis: ${trip.trip_count} Fahrten\n`;
                                tooltip += `Ø Verspätung: ${value}s`;
                            } else {
                                // Trip View Tooltip
                                tooltip += `Fahrt-ID: ${trip.id}\n`;
                                if (trip.vehicle) tooltip += `Fahrzeug: ${trip.vehicle}\n`;
                                tooltip += `Verspätung: ${value}s`;
                            }

                            return (
                                <div
                                    key={`cell-${rowIndex}-${colIndex}`}
                                    className="flex items-center justify-center text-xs border-b border-r border-slate-50 text-slate-600 hover:bg-slate-100 transition-colors cursor-default"
                                    style={{
                                        width: CELL_WIDTH,
                                        height: CELL_HEIGHT,
                                        backgroundColor: bg
                                    }}
                                    title={tooltip}
                                >
                                    {value !== null ? value : '.'}
                                </div>
                            );
                        })}
                    </React.Fragment>
                ))}
            </div>
        </div>
    );
};

export default HeatmapTripView;
