
import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/Card';
import { fetchSettings, saveSettings } from '../services/api';
import { Save, AlertCircle, CheckCircle } from 'lucide-react';

const InputGroup = ({ label, children, description }) => (
    <div className="mb-6">
        <label className="block text-sm font-medium text-slate-700 mb-1">{label}</label>
        {description && <p className="text-xs text-slate-500 mb-2">{description}</p>}
        {children}
    </div>
);

const Settings = () => {
    const [config, setConfig] = useState({
        threshold_early: '-60',
        threshold_late: '180',
        threshold_critical: '300',
        outlier_min: '-1200',
        outlier_max: '3600',
        ignore_outliers: 'false',
        time_presets: {
            morning: { start: '06:00', end: '09:00' },
            evening: { start: '16:00', end: '19:00' }
        }
    });

    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [msg, setMsg] = useState(null);

    useEffect(() => {
        const load = async () => {
            try {
                const data = await fetchSettings();
                // Ensure defaults if API returns nulls
                const defaults = {
                    morning: { start: '06:00', end: '09:00' },
                    evening: { start: '16:00', end: '19:00' }
                };

                let loadedPresets = data.time_presets || defaults;

                setConfig({
                    ...data,
                    ignore_outliers: data.ignore_outliers || 'false',
                    time_presets: loadedPresets
                });
            } catch (err) {
                setMsg({ type: 'error', text: 'Fehler beim Laden der Einstellungen' });
            } finally {
                setLoading(false);
            }
        };
        load();
    }, []);

    const handleChange = (key, value) => {
        setConfig(prev => ({ ...prev, [key]: value }));
    };

    const handlePresetChange = (period, type, value) => {
        setConfig(prev => ({
            ...prev,
            time_presets: {
                ...prev.time_presets,
                [period]: {
                    ...prev.time_presets[period],
                    [type]: value
                }
            }
        }));
    };

    const onSave = async () => {
        setSaving(true);
        setMsg(null);
        try {
            await saveSettings(config);
            setMsg({ type: 'success', text: 'Einstellungen erfolgreich gespeichert!' });
            setTimeout(() => setMsg(null), 3000);
        } catch (err) {
            setMsg({ type: 'error', text: 'Fehler beim Speichern' });
        } finally {
            setSaving(false);
        }
    };

    if (loading) return <div className="p-8">Lade Einstellungen...</div>;

    return (
        <div className="p-8 max-w-[1000px] mx-auto">
            <h1 className="text-2xl font-bold mb-6 text-slate-800">Einstellungen</h1>

            {msg && (
                <div className={`mb-6 p-4 rounded-lg flex items-center gap-2 ${msg.type === 'success' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                    {msg.type === 'success' ? <CheckCircle size={20} /> : <AlertCircle size={20} />}
                    {msg.text}
                </div>
            )}

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Punctuality Thresholds */}
                <Card>
                    <CardHeader>
                        <CardTitle>Schwellenwerte (Pünktlichkeit)</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="grid grid-cols-1 gap-4">
                            <InputGroup label="Zu Früh (Sekunden)" description="Bis zu diesem Wert gilt eine Fahrt als 'Zu Früh' (z.B. -60 für 1 Min zu früh)">
                                <input
                                    type="number"
                                    value={config.threshold_early}
                                    onChange={e => handleChange('threshold_early', e.target.value)}
                                    className="w-full px-3 py-2 border rounded-md focus:ring-vbl-red focus:border-vbl-red"
                                />
                            </InputGroup>

                            <InputGroup label="Verspätung Toleranz (Sekunden)" description="Bis zu diesem Wert gilt eine Fahrt als 'Pünktlich' (z.B. 180 für 3 Min)">
                                <input
                                    type="number"
                                    value={config.threshold_late}
                                    onChange={e => handleChange('threshold_late', e.target.value)}
                                    className="w-full px-3 py-2 border rounded-md"
                                />
                            </InputGroup>

                            <InputGroup label="Kritische Verspätung (Sekunden)" description="Ab diesem Wert gilt eine Fahrt als 'Stark Verspätet' (z.B. 300 für 5 Min)">
                                <input
                                    type="number"
                                    value={config.threshold_critical}
                                    onChange={e => handleChange('threshold_critical', e.target.value)}
                                    className="w-full px-3 py-2 border rounded-md"
                                />
                            </InputGroup>
                        </div>
                    </CardContent>
                </Card>

                {/* Data Filtering / Outliers */}
                <Card>
                    <CardHeader>
                        <CardTitle>Datenbereinigung</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="flex items-center gap-3 mb-6">
                            <input
                                type="checkbox"
                                id="ignore_outliers"
                                checked={config.ignore_outliers === 'true'}
                                onChange={e => handleChange('ignore_outliers', e.target.checked ? 'true' : 'false')}
                                className="w-4 h-4 text-vbl-red focus:ring-vbl-red border-gray-300 rounded"
                            />
                            <label htmlFor="ignore_outliers" className="text-sm font-medium text-slate-700">Ausreißer ignorieren</label>
                        </div>

                        {config.ignore_outliers === 'true' && (
                            <div className="pl-6 border-l-2 border-slate-200">
                                <InputGroup label="Minimale Abweichung (Sekunden)">
                                    <input
                                        type="number"
                                        value={config.outlier_min}
                                        onChange={e => handleChange('outlier_min', e.target.value)}
                                        className="w-full px-3 py-2 border rounded-md"
                                    />
                                </InputGroup>
                                <InputGroup label="Maximale Abweichung (Sekunden)">
                                    <input
                                        type="number"
                                        value={config.outlier_max}
                                        onChange={e => handleChange('outlier_max', e.target.value)}
                                        className="w-full px-3 py-2 border rounded-md"
                                    />
                                </InputGroup>
                            </div>
                        )}
                    </CardContent>
                </Card>

                {/* Time Presets (HVZ) */}
                <Card className="md:col-span-2">
                    <CardHeader>
                        <CardTitle>HVZ Zeitfenster (Schnellwahl)</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                            <div>
                                <h4 className="font-semibold text-slate-900 mb-4 flex items-center gap-2">
                                    ☀️ Morgens
                                </h4>
                                <div className="flex gap-4">
                                    <div className="flex-1">
                                        <label className="text-xs text-slate-500">Von</label>
                                        <input
                                            type="time"
                                            value={config.time_presets?.morning?.start || ''}
                                            onChange={e => handlePresetChange('morning', 'start', e.target.value)}
                                            className="w-full px-3 py-2 border rounded-md"
                                        />
                                    </div>
                                    <div className="flex-1">
                                        <label className="text-xs text-slate-500">Bis</label>
                                        <input
                                            type="time"
                                            value={config.time_presets?.morning?.end || ''}
                                            onChange={e => handlePresetChange('morning', 'end', e.target.value)}
                                            className="w-full px-3 py-2 border rounded-md"
                                        />
                                    </div>
                                </div>
                            </div>

                            <div>
                                <h4 className="font-semibold text-slate-900 mb-4 flex items-center gap-2">
                                    🌙 Abends
                                </h4>
                                <div className="flex gap-4">
                                    <div className="flex-1">
                                        <label className="text-xs text-slate-500">Von</label>
                                        <input
                                            type="time"
                                            value={config.time_presets?.evening?.start || ''}
                                            onChange={e => handlePresetChange('evening', 'start', e.target.value)}
                                            className="w-full px-3 py-2 border rounded-md"
                                        />
                                    </div>
                                    <div className="flex-1">
                                        <label className="text-xs text-slate-500">Bis</label>
                                        <input
                                            type="time"
                                            value={config.time_presets?.evening?.end || ''}
                                            onChange={e => handlePresetChange('evening', 'end', e.target.value)}
                                            className="w-full px-3 py-2 border rounded-md"
                                        />
                                    </div>
                                </div>
                            </div>
                        </div>
                    </CardContent>
                </Card>
            </div>

            <div className="mt-8 flex justify-end">
                <button
                    onClick={onSave}
                    disabled={saving}
                    className="bg-vbl-red text-white px-6 py-2 rounded-lg font-medium shadow-sm hover:bg-red-700 transition-colors flex items-center gap-2 disabled:opacity-50"
                >
                    <Save size={18} />
                    {saving ? 'Speichere...' : 'Einstellungen speichern'}
                </button>
            </div>
        </div>
    );
};

export default Settings;
