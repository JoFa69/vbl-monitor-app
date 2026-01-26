
import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/Card';
import { Clock, AlertTriangle, XCircle, CheckCircle, Timer } from 'lucide-react';

const KPITile = ({ title, value, subtext, icon: Icon, colorClass, borderClass }) => (
    <Card className={`border-l-4 ${borderClass}`}>
        <CardContent className="p-4 flex items-center justify-between">
            <div>
                <p className="text-sm font-medium text-slate-500">{title}</p>
                <div className="text-2xl font-bold mt-1">{value}</div>
                {subtext && <p className="text-xs text-slate-400 mt-1">{subtext}</p>}
            </div>
            {Icon && <div className={`p-3 rounded-full ${colorClass} bg-opacity-10`}>
                <Icon className={`w-6 h-6 ${colorClass.replace('bg-', 'text-')}`} />
            </div>}
        </CardContent>
    </Card>
);

const KPIStats = ({ data, config }) => {
    if (!data) return <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 animate-pulse">
        {[1, 2, 3, 4].map(i => <div key={i} className="h-24 bg-slate-100 rounded-lg"></div>)}
    </div>;

    const { stats, cancellation_stats, percentages, total } = data;

    // Calculations logic is already done in backend! passing in prepared data.
    // config contains thresholds.

    return (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4 mb-6">
            <KPITile
                title="Total Fahrten"
                value={total.toLocaleString()}
                subtext="Im gewählten Zeitraum"
                icon={Timer}
                colorClass="text-slate-600"
                borderClass="border-slate-400"
            />

            <KPITile
                title="Zu Früh"
                value={`${percentages.early || 0}%`}
                subtext={`< ${config.threshold_early}s`}
                icon={AlertTriangle}
                colorClass="text-blue-500"
                borderClass="border-blue-500"
            />

            <KPITile
                title="Pünktlich"
                value={`${percentages.on_time || 0}%`}
                subtext={`${config.threshold_early}s bis ${config.threshold_late}s`}
                icon={CheckCircle}
                colorClass="text-green-500"
                borderClass="border-green-500"
            />

            <KPITile
                title="Verspätet"
                value={`${percentages.late_slight || 0}%`}
                subtext={`${config.threshold_late}s bis ${config.threshold_critical}s`}
                icon={Clock}
                colorClass="text-yellow-500"
                borderClass="border-yellow-500"
            />

            <KPITile
                title="Stark Verspätet"
                value={`${percentages.late_severe || 0}%`}
                subtext={`> ${config.threshold_critical}s`}
                icon={AlertTriangle}
                colorClass="text-red-500"
                borderClass="border-red-500"
            />

            <KPITile
                title="Ausfälle"
                value={`${cancellation_stats.total_cancelled_trips || 0}`}
                subtext={`${cancellation_stats.cancellation_rate || 0}% Rate`}
                icon={XCircle}
                colorClass="text-purple-500"
                borderClass="border-purple-500"
            />
        </div>
    );
};

export default KPIStats;
