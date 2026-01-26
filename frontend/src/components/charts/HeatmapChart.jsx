import React, { useMemo } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card';

const HeatmapChart = ({ data, title = "Pünktlichkeit Heatmap" }) => {
    // 1. Process Data
    const { dates, timeSlots, matrix, maxValue } = useMemo(() => {
        if (!data || data.length === 0) return { dates: [], timeSlots: [], matrix: {}, maxValue: 0 };

        // Unique Dates and TimeSlots
        const datesSet = new Set(data.map(d => d.date));
        const timeSlotsSet = new Set(data.map(d => d.time_slot));

        const sortedDates = Array.from(datesSet).sort();
        const sortedTimeSlots = Array.from(timeSlotsSet).sort((a, b) => {
            // Fix sorting (00-03 should be after 23 conceptually if traffic day? 
            // Or just string sort if 05...23...00...02)
            // Existing backend logic sorts them correctly (04..23..00..03) using custom sort order.
            // So we rely on the order they appear or we strictly sort by standard time?
            // If backend sorts them, let's respect that order if we can.
            // But we collected them in a Set, so order is lost.
            // Let's rely on standard string comparison for now, or check generic "traffic day" logic.
            // Simple string sort: 00 comes first.
            // If we want 05:00 first, we need custom logic.
            // Let's use a simple heuristic: if hour < 4, add 24 to it for comparison.
            const getH = (t) => parseInt(t.split(':')[0], 10);
            const valA = getH(a) < 4 ? getH(a) + 24 : getH(a);
            const valB = getH(b) < 4 ? getH(b) + 24 : getH(b);
            return valA - valB;
        });

        const mat = {};
        let max = 0;

        data.forEach(item => {
            if (!mat[item.date]) mat[item.date] = {};
            // Punctuality %
            const total = item.total;
            const onTime = item.on_time; // Only 'on_time'? Or early+on_time? Usually strictly on_time for 'Pünktlichkeit'.
            // Actually 'early' is often considered OK too, but technically 'Zu Früh' is bad.
            // Let's stick to 'on_time' stats logic.
            const rate = total > 0 ? (onTime / total) * 100 : 0;

            mat[item.date][item.time_slot] = {
                rate,
                total,
                details: item
            };
            if (total > max) max = total;
        });

        return { dates: sortedDates, timeSlots: sortedTimeSlots, matrix: mat, maxValue: max };
    }, [data]);

    if (!data || data.length === 0) {
        return (
            <Card className="w-full">
                <CardHeader>
                    <CardTitle>{title}</CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="h-64 flex items-center justify-center text-slate-400">
                        Keine Daten verfügbar
                    </div>
                </CardContent>
            </Card>
        );
    }

    // Color Scale Function
    const getColor = (rate, total) => {
        if (!total || total === 0) return 'bg-slate-100'; // No data
        // Green > 90, Yellow > 80, Red otherwise?
        // Or Gradient.
        // Let's use opacity of green for good, red for bad? 
        // Or standard heatmap colors: Red (0%) -> Yellow (50%) -> Green (100%).

        // HSL: Red=0, Green=120.
        // We can map rate (0-100) to Hue (0-120).
        // Maybe cap at 0 and 100.
        const hue = Math.max(0, Math.min(120, (rate / 100) * 120));
        return `hsl(${hue}, 70%, 50%)`;
    };

    return (
        <Card className="w-full overflow-hidden">
            <CardHeader>
                <CardTitle>{title}</CardTitle>
            </CardHeader>
            <CardContent className="p-0 overflow-x-auto">
                <div className="p-4 min-w-[800px]">
                    <div className="grid gap-1" style={{ gridTemplateColumns: `auto repeat(${timeSlots.length}, 1fr)` }}>
                        {/* Header Row */}
                        <div className="text-xs font-semibold text-slate-500 text-right pr-2">Datum</div>
                        {timeSlots.map(ts => (
                            <div key={ts} className="text-xs font-semibold text-slate-500 text-center transform -rotate-45 origin-bottom translate-y-2">
                                {ts}
                            </div>
                        ))}

                        {/* Data Rows */}
                        {dates.map(date => (
                            <React.Fragment key={date}>
                                <div className="text-xs font-medium text-slate-600 whitespace-nowrap self-center pr-2 text-right">
                                    {new Date(date).toLocaleDateString('de-CH', { day: '2-digit', month: '2-digit' })}
                                </div>
                                {timeSlots.map(ts => {
                                    const cell = matrix[date]?.[ts];
                                    const rate = cell ? cell.rate : 0;
                                    const count = cell ? cell.total : 0;

                                    return (
                                        <div
                                            key={`${date}-${ts}`}
                                            className="h-8 w-full rounded-sm transition-all hover:scale-110 hover:z-10 cursor-pointer relative group"
                                            style={{
                                                backgroundColor: cell ? getColor(rate, count) : '#f1f5f9',
                                                border: '1px solid rgba(255,255,255,0.1)'
                                            }}
                                        >
                                            {/* Tooltip */}
                                            {cell && (
                                                <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 hidden group-hover:block bg-slate-800 text-white text-xs rounded p-2 shadow-xl z-50 whitespace-nowrap min-w-[150px]">
                                                    <div className="font-bold border-b border-slate-600 pb-1 mb-1">{date} - {ts}</div>
                                                    <div>Pünktlich: <span className="font-mono">{cell.details.on_time}</span> ({rate.toFixed(1)}%)</div>
                                                    <div>Zu Früh: <span className="font-mono">{cell.details.early}</span></div>
                                                    <div>Verspätet: <span className="font-mono">{cell.details.late_slight}</span></div>
                                                    <div>Stark Verspätet: <span className="font-mono">{cell.details.late_severe}</span></div>
                                                    <div className="mt-1 pt-1 border-t border-slate-600">Total: {count} Fahrten</div>
                                                </div>
                                            )}
                                        </div>
                                    );
                                })}
                            </React.Fragment>
                        ))}
                    </div>
                </div>
            </CardContent>
        </Card>
    );
};

export default HeatmapChart;
