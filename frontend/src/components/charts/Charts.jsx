
import React, { useState } from 'react';
import { Bar, Line } from 'react-chartjs-2';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/Card';
import '../../lib/chartConfig';
import { formatNumber } from '../../lib/utils';
import { clsx } from 'clsx';

const CHART_COLORS = {
    early: '#3b82f6',
    on_time: '#22c55e',
    late_slight: '#eab308',
    late_severe: '#ef4444'
};

const CHART_LABELS = {
    early: 'Zu Früh',
    on_time: 'Pünktlich',
    late_slight: 'Verspätet',
    late_severe: 'Stark Verspätet'
};

const Tabs = ({ activeTab, onTabChange }) => (
    <div className="flex gap-2 mb-4 bg-slate-100 p-1 rounded-lg w-fit">
        <button
            onClick={() => onTabChange('overview')}
            className={clsx("px-3 py-1.5 rounded-md text-xs font-medium transition-colors",
                activeTab === 'overview' ? "bg-white shadow-sm text-slate-800" : "text-slate-500 hover:text-slate-700")}
        >
            Übersicht (100%)
        </button>
        {Object.keys(CHART_COLORS).map(key => (
            <button
                key={key}
                onClick={() => onTabChange(key)}
                className={clsx("px-3 py-1.5 rounded-md text-xs font-medium transition-colors border-l-2",
                    activeTab === key ? "bg-white shadow-sm text-slate-800" : "text-slate-500 hover:text-slate-700")}
                style={{ borderLeftColor: CHART_COLORS[key] }}
            >
                {CHART_LABELS[key]}
            </button>
        ))}
    </div>
);

const ChartDataBuilder = (type, data, tab) => {
    // Labels
    const labels = data.labels;

    if (tab === 'overview') {
        // Stacked 100% Bar
        // We need to normalize data to percentages for visual accuracy if strict requirements,
        // BUT Chart.js stacked bar usually stacks absolute values. 
        // Request: "Y-Achse: Muss zwingend 0% bis 100% anzeigen. Normiere...".
        // To do this properly, we calculate totals per column and convert to %.

        // Helper to get value at index safely
        const getVal = (ds, idx) => data.datasets[ds][idx] || 0;

        const percentages = labels.map((_, idx) => {
            const total = getVal('early', idx) + getVal('on_time', idx) + getVal('late_slight', idx) + getVal('late_severe', idx);
            if (total === 0) return { early: 0, on_time: 0, late_slight: 0, late_severe: 0 };
            return {
                early: (getVal('early', idx) / total) * 100,
                on_time: (getVal('on_time', idx) / total) * 100,
                late_slight: (getVal('late_slight', idx) / total) * 100,
                late_severe: (getVal('late_severe', idx) / total) * 100,
            };
        });

        return {
            labels,
            datasets: [
                { label: 'Zu Früh', data: percentages.map(p => p.early), backgroundColor: CHART_COLORS.early },
                { label: 'Pünktlich', data: percentages.map(p => p.on_time), backgroundColor: CHART_COLORS.on_time },
                { label: 'Verspätet', data: percentages.map(p => p.late_slight), backgroundColor: CHART_COLORS.late_slight },
                { label: 'Stark Verspätet', data: percentages.map(p => p.late_severe), backgroundColor: CHART_COLORS.late_severe },
            ]
        };
    } else {
        // Line Chart for single category (Absolute values? Or percentage? usually absolute count or % rate)
        // Request says: "[Zu früh]... -> Zeigt Liniendiagramm (nur diese Kategorie)."
        // Usually trend analysis uses percentages to be comparable across hours with different volume.
        // Let's assume percentages again for consistency, OR absolute?
        // "Prozent-Charts statt Absolut" applies generally. Let's use % Rate for Trend.

        const getVal = (ds, idx) => data.datasets[ds][idx] || 0;
        const dataset = labels.map((_, idx) => {
            const total = getVal('early', idx) + getVal('on_time', idx) + getVal('late_slight', idx) + getVal('late_severe', idx);
            const val = getVal(tab, idx);
            return total > 0 ? (val / total) * 100 : 0;
        });

        return {
            labels,
            datasets: [
                {
                    label: CHART_LABELS[tab],
                    data: dataset,
                    borderColor: CHART_COLORS[tab],
                    backgroundColor: CHART_COLORS[tab],
                    tension: 0.3,
                    fill: false
                }
            ]
        };
    }
};

const CommonOptions = (isStacked) => ({
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
        legend: { position: 'top', align: 'end', labels: { boxWidth: 10, usePointStyle: true } },
        tooltip: {
            callbacks: {
                label: (ctx) => `${ctx.dataset.label}: ${formatNumber(ctx.raw.toFixed(1))}%`
            }
        }
    },
    scales: {
        x: { stacked: isStacked, grid: { display: false } },
        y: {
            stacked: isStacked,
            beginAtZero: true,
            max: 100,
            ticks: { callback: v => v + '%' },
            grid: { color: '#f1f5f9' }
        },
    },
});


export const HourlyChart = ({ data, currentGranularity, onGranularityChange }) => {
    const [tab, setTab] = useState('overview');
    if (!data) return <div className="h-64 bg-slate-50 rounded animate-pulse" />;

    const chartData = ChartDataBuilder('hourly', data, tab);
    const options = CommonOptions(tab === 'overview');

    return (
        <Card className="col-span-1">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle>Pünktlichkeit nach Uhrzeit</CardTitle>
                <div className="flex bg-slate-100 rounded-md p-0.5">
                    {[15, 30, 60].map(val => (
                        <button
                            key={val}
                            onClick={() => onGranularityChange(val)}
                            className={clsx(
                                "px-2 py-1 text-[10px] font-medium rounded transition-all",
                                currentGranularity === val
                                    ? "bg-white text-slate-800 shadow-sm"
                                    : "text-slate-500 hover:text-slate-700 hover:bg-slate-200"
                            )}
                        >
                            {val === 60 ? '1Std' : `${val}m`}
                        </button>
                    ))}
                </div>
            </CardHeader>
            <CardContent className="h-96">
                <Tabs activeTab={tab} onTabChange={setTab} />
                <div className="h-80 w-full">
                    {tab === 'overview'
                        ? <Bar options={options} data={chartData} />
                        : <Line options={options} data={chartData} />
                    }
                </div>
            </CardContent>
        </Card>
    );
};

export const WeekdayChart = ({ data }) => {
    const [tab, setTab] = useState('overview');
    if (!data) return <div className="h-64 bg-slate-50 rounded animate-pulse" />;

    const chartData = ChartDataBuilder('weekday', data, tab);
    const options = CommonOptions(tab === 'overview');

    return (
        <Card className="col-span-1">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle>Pünktlichkeit nach Wochentag</CardTitle>
            </CardHeader>
            <CardContent className="h-96">
                <Tabs activeTab={tab} onTabChange={setTab} />
                <div className="h-80 w-full">
                    {tab === 'overview'
                        ? <Bar options={options} data={chartData} />
                        : <Line options={options} data={chartData} />
                    }
                </div>
            </CardContent>
        </Card>
    );
};
