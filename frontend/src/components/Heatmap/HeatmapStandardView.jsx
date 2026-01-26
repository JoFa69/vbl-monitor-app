import React from 'react';
import { getCellColor, getCellValue } from '../../utils/heatmapUtils';

const HeatmapStandardView = ({ data, matrix, timeSlots, viewMetric }) => {
    return (
        <div className="inline-block min-w-full">
            <div
                className="grid gap-[1px] bg-slate-200"
                style={{ gridTemplateColumns: `minmax(250px, auto) repeat(${timeSlots.length}, minmax(60px, 1fr))` }}
            >
                {/* Time Header */}
                <div className="bg-white p-2 sticky top-0 left-0 z-20 font-bold text-xs text-slate-600 border-b shadow-sm">
                    Haltestelle \ Uhrzeit
                </div>
                {timeSlots.map(ts => (
                    <div key={ts} className="bg-white p-2 sticky top-0 z-10 text-xs font-bold text-slate-600 text-center border-b group hover:bg-slate-50">
                        <div className="transform -rotate-45 origin-bottom translate-y-1">{ts}</div>
                    </div>
                ))}

                {/* Rows */}
                {data.stops.map(stop => (
                    <React.Fragment key={stop}>
                        <div className="bg-white px-3 py-2 text-xs font-medium text-slate-700 sticky left-0 z-10 border-r flex items-center shadow-sm whitespace-nowrap overflow-hidden text-ellipsis hover:w-auto hover:z-30 hover:bg-slate-50">
                            {stop}
                        </div>
                        {timeSlots.map(ts => {
                            const cell = matrix[stop]?.[ts];
                            return (
                                <div
                                    key={`${stop}-${ts}`}
                                    className="h-10 relative group border border-transparent hover:border-slate-400 z-0 hover:z-20"
                                    style={{ backgroundColor: getCellColor(cell, viewMetric) }}
                                >
                                    <div className="w-full h-full flex items-center justify-center text-xs font-medium text-slate-700">
                                        {getCellValue(cell, viewMetric)}
                                    </div>
                                    {/* Tooltip */}
                                    {cell && (
                                        <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 hidden group-hover:block bg-white text-slate-800 rounded-lg shadow-2xl z-50 min-w-[300px] border border-slate-200 p-0 animate-in fade-in zoom-in-95 duration-100">
                                            <div className="bg-slate-50 px-4 py-2 rounded-t-lg border-b border-slate-100 flex justify-between items-center">
                                                <span className="font-bold text-sm truncate max-w-[180px]">{stop}</span>
                                                <span className="text-xs font-mono bg-white px-2 py-0.5 rounded border">{ts} Uhr</span>
                                            </div>
                                            <div className="p-4 space-y-4">
                                                <div className="grid grid-cols-3 gap-2 text-center">
                                                    <div className="bg-slate-50 p-2 rounded">
                                                        <div className="text-[10px] uppercase text-slate-400 font-bold">Total</div>
                                                        <div className="font-bold text-lg">{cell.total}</div>
                                                    </div>
                                                    <div className="bg-slate-50 p-2 rounded">
                                                        <div className="text-[10px] uppercase text-slate-400 font-bold">Pünktlich</div>
                                                        <div className={`font-bold text-lg ${(cell.on_time / cell.total > 0.8) ? 'text-emerald-600' : 'text-amber-600'}`}>
                                                            {Math.round((cell.on_time / cell.total) * 100)}%
                                                        </div>
                                                    </div>
                                                    <div className="bg-slate-50 p-2 rounded">
                                                        <div className="text-[10px] uppercase text-slate-400 font-bold">Ø Delay</div>
                                                        <div className="font-bold text-lg">{cell.avg_delay}s</div>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    )}
                                </div>
                            );
                        })}
                    </React.Fragment>
                ))}
            </div>
        </div>
    );
};

export default HeatmapStandardView;
