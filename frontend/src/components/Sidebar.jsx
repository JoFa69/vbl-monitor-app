
import React, { useEffect, useState } from 'react';
import { LayoutDashboard, Settings, Map, BarChart3, Search, Calendar, Clock } from 'lucide-react';
import { fetchDashboardMetadata, fetchLineStops } from '../services/api';

const Sidebar = ({ activeTab, onTabChange, filters, onFilterChange, isCollapsed, toggleCollapse }) => {
    const [metadata, setMetadata] = useState(null);
    const [availableStops, setAvailableStops] = useState([]);

    // Load Metadata for Dropdowns
    useEffect(() => {
        const loadMeta = async () => {
            try {
                const meta = await fetchDashboardMetadata();
                setMetadata(meta);

                // Set initial dates if empty
                if (!filters.date_from) {
                    onFilterChange(prev => ({
                        ...prev,
                        date_from: meta.date_range.min,
                        date_to: meta.date_range.max
                    }));
                }
            } catch (e) {
                console.error("Meta load failed", e);
            }
        };
        loadMeta();
    }, []);

    // Load Stops when Line changes
    useEffect(() => {
        const loadStops = async () => {
            const lineId = filters.line;
            if (lineId) {
                const stops = await fetchLineStops(lineId, filters.route);
                setAvailableStops(stops || []);
            } else {
                setAvailableStops([]);
            }
        };
        loadStops();
    }, [filters.line, filters.route]);

    const navItems = [
        { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
        { id: 'analytics', label: 'Analytics', icon: BarChart3 },
        { id: 'heatmap', label: 'Lastteppich', icon: Map },
        { id: 'map', label: 'Karte (Future)', icon: Map, disabled: true },
        { id: 'settings', label: 'Einstellungen', icon: Settings },
    ];

    // Presets
    const applyPreset = (type) => {
        if (!metadata || !metadata.config) return;
        const config = metadata.config;
        let time_presets = {};
        try {
            time_presets = typeof config.time_presets === 'string' ? JSON.parse(config.time_presets) : config.time_presets;
        } catch (e) { }

        const update = { ...filters };
        update.time_from = '';
        update.time_to = '';

        if (type === 'day') {
            // Default
        } else if (type === 'morning') {
            if (time_presets?.morning) {
                update.time_from = time_presets.morning.start;
                update.time_to = time_presets.morning.end;
            } else {
                update.time_from = '06:00'; update.time_to = '09:00';
            }
        } else if (type === 'evening') {
            if (time_presets?.evening) {
                update.time_from = time_presets.evening.start;
                update.time_to = time_presets.evening.end;
            } else {
                update.time_from = '16:00'; update.time_to = '19:00';
            }
        }
        onFilterChange(update);
    };

    const handleLineChange = (e) => {
        onFilterChange({ ...filters, line: e.target.value === 'all' ? '' : e.target.value, route: '', stop: '' });
    };

    return (
        <aside
            className={`${isCollapsed ? 'w-20' : 'w-80'} bg-[#1A3A4E] text-white h-screen flex flex-col fixed left-0 top-0 shadow-xl z-50 transition-all duration-300`}
        >
            {/* Header */}
            <div className={`p-6 border-b border-slate-700 flex items-center ${isCollapsed ? 'justify-center' : 'justify-between'}`}>
                {!isCollapsed && (
                    <div>
                        <h1 className="text-2xl font-bold text-white tracking-tight">VBL Monitor</h1>
                        <p className="text-xs text-slate-300 mt-1 opacity-80">Version 2.0</p>
                    </div>
                )}
                {isCollapsed && <span className="font-bold text-xl">VBL</span>}
            </div>

            {/* Navigation */}
            <nav className="p-4 space-y-2 flex-shrink-0">
                {navItems.map((item) => {
                    const Icon = item.icon;
                    return (
                        <button
                            key={item.id}
                            onClick={() => !item.disabled && onTabChange(item.id)}
                            disabled={item.disabled}
                            title={isCollapsed ? item.label : ''}
                            className={`w-full flex items-center ${isCollapsed ? 'justify-center' : 'gap-3'} px-4 py-3 rounded-lg transition-all text-sm font-medium
                                ${activeTab === item.id
                                    ? 'bg-vbl-red text-white shadow-md'
                                    : 'text-slate-300 hover:bg-slate-700 hover:text-white'}
                                ${item.disabled ? 'opacity-50 cursor-not-allowed' : ''}
                            `}
                        >
                            <Icon size={20} />
                            {!isCollapsed && <span>{item.label}</span>}
                        </button>
                    );
                })}
            </nav>

            {/* Collapse Toggle */}
            <div className="px-4 py-2 flex justify-center border-t border-slate-700/50">
                <button
                    onClick={toggleCollapse}
                    className="p-2 text-slate-400 hover:text-white transition-colors"
                >
                    {isCollapsed ? '➡' : '⬅ Einklappen'}
                </button>
            </div>


            {/* Filters Section - Hidden when collapsed */}
            {!isCollapsed && (activeTab === 'dashboard' || activeTab === 'analytics' || activeTab === 'heatmap') && (
                <div className="flex-1 overflow-y-auto px-6 py-4 border-t border-slate-700 space-y-6">

                    {/* Metric Switch */}
                    <div className="bg-slate-800 p-1 rounded-lg flex text-xs font-medium">
                        <button
                            onClick={() => onFilterChange({ ...filters, metric: 'arrival' })}
                            className={`flex-1 py-1.5 rounded-md transition-colors ${filters.metric === 'arrival' ? 'bg-white text-[#1A3A4E]' : 'text-slate-400 hover:text-white'}`}
                        >
                            Ankunft
                        </button>
                        <button
                            onClick={() => onFilterChange({ ...filters, metric: 'departure' })}
                            className={`flex-1 py-1.5 rounded-md transition-colors ${filters.metric === 'departure' ? 'bg-white text-[#1A3A4E]' : 'text-slate-400 hover:text-white'}`}
                        >
                            Abfahrt
                        </button>
                    </div>

                    {/* Presets */}
                    <div>
                        <label className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2 block">Presets</label>
                        <div className="grid grid-cols-3 gap-2">
                            <button onClick={() => applyPreset('day')} className="py-1 px-2 bg-slate-700 hover:bg-slate-600 rounded text-xs text-white">Tag</button>
                            <button onClick={() => applyPreset('morning')} className="py-1 px-2 bg-slate-700 hover:bg-slate-600 rounded text-xs text-white">Morgens</button>
                            <button onClick={() => applyPreset('evening')} className="py-1 px-2 bg-slate-700 hover:bg-slate-600 rounded text-xs text-white">Abends</button>
                        </div>
                    </div>

                    {/* Date Range */}
                    <div>
                        <label className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2 block flex items-center gap-2">
                            <Calendar size={12} /> Datum
                        </label>
                        <div className="grid grid-cols-2 gap-2">
                            <input type="date" className="bg-slate-700 border-none rounded text-xs px-2 py-1 text-white focus:ring-1 focus:ring-vbl-red"
                                value={filters.date_from} onChange={e => onFilterChange({ ...filters, date_from: e.target.value })} />
                            <input type="date" className="bg-slate-700 border-none rounded text-xs px-2 py-1 text-white focus:ring-1 focus:ring-vbl-red"
                                value={filters.date_to} onChange={e => onFilterChange({ ...filters, date_to: e.target.value })} />
                        </div>
                    </div>

                    {/* Time Range */}
                    <div>
                        <label className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2 block flex items-center gap-2">
                            <Clock size={12} /> Uhrzeit
                        </label>
                        <div className="grid grid-cols-2 gap-2">
                            <input type="time" className="bg-slate-700 border-none rounded text-xs px-2 py-1 text-white focus:ring-1 focus:ring-vbl-red"
                                value={filters.time_from} onChange={e => onFilterChange({ ...filters, time_from: e.target.value })} />
                            <input type="time" className="bg-slate-700 border-none rounded text-xs px-2 py-1 text-white focus:ring-1 focus:ring-vbl-red"
                                value={filters.time_to} onChange={e => onFilterChange({ ...filters, time_to: e.target.value })} />
                        </div>
                    </div>

                    {/* Line Selection */}
                    <div>
                        <label className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2 block">Linie</label>
                        <select
                            className="w-full bg-slate-700 border-none rounded text-sm px-3 py-2 text-white focus:ring-1 focus:ring-vbl-red"
                            value={filters.line || 'all'}
                            onChange={handleLineChange}
                        >
                            <option value="all">Alle Linien</option>
                            {metadata && metadata.lines && Object.keys(metadata.lines).map(l => (
                                <option key={l} value={l}>Linie {l}</option>
                            ))}
                        </select>
                    </div>

                    {/* Route Selection */}
                    {filters.line && filters.line !== 'all' && metadata && metadata.lines && metadata.lines[filters.line] && (
                        <div>
                            <label className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2 block">Route</label>
                            <select
                                className="w-full bg-slate-700 border-none rounded text-sm px-3 py-2 text-white focus:ring-1 focus:ring-vbl-red"
                                value={filters.route || ''}
                                onChange={e => onFilterChange({ ...filters, route: e.target.value, stop: '' })}
                            >
                                <option value="">Alle Routen</option>
                                {metadata.lines[filters.line].map((route, idx) => (
                                    <option key={idx} value={route.name}>
                                        {route.name}
                                    </option>
                                ))}
                            </select>
                        </div>
                    )}

                    {/* Day Type Selection */}
                    <div>
                        <label className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2 block">Tagesklasse</label>
                        <select
                            className="w-full bg-slate-700 border-none rounded text-sm px-3 py-2 text-white focus:ring-1 focus:ring-vbl-red"
                            value={filters.day_class || ''}
                            onChange={e => onFilterChange({ ...filters, day_class: e.target.value })}
                        >
                            <option value="">Alle Tage</option>
                            <option value="Mo-Fr (Schule)">Mo-Fr (Schule)</option>
                            <option value="Mo-Fr (Ferien)">Mo-Fr (Ferien)</option>
                            <option value="Samstag">Samstag</option>
                            <option value="Sonn-/Feiertag">Sonn-/Feiertag</option>
                        </select>
                    </div>

                    {/* Heatmap Specific Options */}
                    {activeTab === 'heatmap' && (
                        <div className="pt-4 border-t border-slate-700 space-y-4">
                            <label className="text-xs font-bold text-slate-400 uppercase tracking-wider block">Ansichts-Modus</label>

                            {/* Granularity */}
                            <div className="grid grid-cols-2 gap-2">
                                {[15, 30, 60].map(m => (
                                    <button
                                        key={m}
                                        onClick={() => onFilterChange({ ...filters, granularity: m, time_from: '', time_to: '' })}
                                        className={`py-1 px-2 rounded text-xs transition-colors ${parseInt(filters.granularity) === m ? 'bg-vbl-red text-white' : 'bg-slate-700 text-slate-300 hover:bg-slate-600'}`}
                                    >
                                        {m} Min
                                    </button>
                                ))}
                                <button
                                    onClick={() => onFilterChange({ ...filters, granularity: 'trip', time_from: '', time_to: '' })}
                                    className={`py-1 px-2 rounded text-xs transition-colors ${filters.granularity === 'trip' ? 'bg-vbl-red text-white' : 'bg-slate-700 text-slate-300 hover:bg-slate-600'}`}
                                >
                                    Einzel-Fahrten
                                </button>
                                <button
                                    onClick={() => onFilterChange({ ...filters, granularity: 'pattern', time_from: '', time_to: '' })}
                                    className={`py-1 px-2 rounded text-xs transition-colors ${filters.granularity === 'pattern' ? 'bg-vbl-red text-white' : 'bg-slate-700 text-slate-300 hover:bg-slate-600'}`}
                                >
                                    Muster-Sicht
                                </button>
                            </div>

                            {/* Trip Type Filter */}
                            <label className="flex items-center space-x-2 cursor-pointer text-sm text-slate-300 hover:text-white">
                                <input
                                    type="checkbox"
                                    className="form-checkbox rounded bg-slate-700 border-none text-vbl-red focus:ring-0"
                                    checked={filters.trip_type_regular || false}
                                    onChange={e => onFilterChange({ ...filters, trip_type_regular: e.target.checked })}
                                />
                                <span>Nur reguläre Fahrten</span>
                            </label>
                        </div>
                    )}

                    {/* Stop Selection - Only for Dashboard/Analytics, maybe not Heatmap? Heatmap shows all stops. */}
                    {activeTab !== 'heatmap' && (
                        <div>
                            <label className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2 block">Haltestelle</label>
                            <input
                                type="text"
                                placeholder="Suchen..."
                                list="stops-list"
                                className="w-full bg-slate-700 border-none rounded text-sm px-3 py-2 text-white focus:ring-1 focus:ring-vbl-red placeholder-slate-400"
                                value={filters.stop}
                                onChange={e => onFilterChange({ ...filters, stop: e.target.value })}
                            />
                            <datalist id="stops-list">
                                {availableStops.map((s, idx) => (
                                    <option key={idx} value={s.value} />
                                ))}
                            </datalist>
                        </div>
                    )}
                </div>
            )}
        </aside>
    );
};

export default Sidebar;
