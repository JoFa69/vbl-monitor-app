
import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/Card';

const ProblematicStops = ({ data }) => {
    if (!data) return null;

    return (
        <Card className="col-span-1 lg:col-span-2">
            <CardHeader>
                <CardTitle>Problematische Haltestellen</CardTitle>
            </CardHeader>
            <CardContent className="overflow-auto max-h-[400px]">
                <table className="w-full text-sm text-left">
                    <thead className="text-xs text-slate-500 uppercase bg-slate-50 sticky top-0">
                        <tr>
                            <th className="px-4 py-2">Haltestelle</th>
                            <th className="px-4 py-2 text-right">Ø Delay</th>
                            <th className="px-4 py-2 text-right">Total</th>
                            <th className="px-4 py-2 text-right">Zu Früh</th>
                            <th className="px-4 py-2 text-right">Pünktlich</th>
                            <th className="px-4 py-2 text-right">Verspätet</th>
                            <th className="px-4 py-2 text-right">Stark Versp.</th>
                        </tr>
                    </thead>
                    <tbody>
                        {data.map((stop, idx) => (
                            <tr key={idx} className="border-b hover:bg-slate-50">
                                <td className="px-4 py-2 font-medium">{stop.stop_name}</td>
                                <td className="px-4 py-2 text-right">{stop.avg_delay_seconds}s</td>
                                <td className="px-4 py-2 text-right">{stop.total_trips}</td>
                                <td className="px-4 py-2 text-right text-blue-500">{stop.pct_early}%</td>
                                <td className="px-4 py-2 text-right text-green-500">{stop.pct_on_time}%</td>
                                <td className="px-4 py-2 text-right text-yellow-500">{stop.pct_late_slight}%</td>
                                <td className="px-4 py-2 text-right text-red-500 font-bold">{stop.pct_late_severe}%</td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </CardContent>
        </Card>
    );
};

export default ProblematicStops;
