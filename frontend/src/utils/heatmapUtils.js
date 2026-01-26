import { THEME } from '../config/theme';

export const getCellColor = (stats, viewMetric = 'punctuality') => {
    if (!stats || stats.total === 0) return THEME.colors.empty;

    if (viewMetric === 'punctuality') {
        const rate = (stats.on_time / stats.total) * 100;
        // Simple Hue Scale: 0 (Red) -> 120 (Green)
        // Adjust logic if strictly following requested colors
        const hue = Math.max(0, Math.min(120, (rate / 100) * 120));
        return `hsl(${hue}, 70%, 85%)`;
    }

    if (viewMetric === 'median') {
        const val = stats.p3; // Median
        let hue = 120;
        if (val <= 0) hue = 120;
        else if (val > 300) hue = 0;
        else {
            hue = 120 - (val / 300) * 120;
        }
        return `hsl(${hue}, 80%, 90%)`;
    }

    if (viewMetric === 'stress') {
        const val = stats.p1;
        let alpha = 90;
        let hue = 0;

        if (val < 60) { hue = 120; alpha = 90; }
        else if (val < 180) { hue = 60; alpha = 90; }
        else {
            hue = 0;
            const intensity = Math.min(1, Math.max(0, (val - 180) / 600));
            return `rgba(255, ${200 * (1 - intensity)}, ${200 * (1 - intensity)}, 0.3)`;
        }
        return `hsl(${hue}, 80%, ${alpha}%)`;
    }

    // Default for Trip View (single cell deviation)
    if (viewMetric === 'trip_deviation') {
        const delay = stats.delay; // seconds
        if (delay < 60) return '#dcfce7'; // green-100 (Tailwind match, or use hsl)
        if (delay < 180) return '#fef9c3'; // yellow-100
        return '#fee2e2'; // red-100
    }

    return THEME.colors.empty;
};

export const getCellValue = (stats, viewMetric = 'punctuality') => {
    if (!stats) return '-';

    // Trip View Logic handle separately or pass specific metric
    if (viewMetric === 'trip_deviation') {
        const delay = stats.delay;
        return delay > 0 ? `+${Math.round(delay / 60)}` : Math.round(delay / 60);
    }

    if (viewMetric === 'punctuality') return `${Math.round((stats.on_time / stats.total) * 100)}%`;
    if (viewMetric === 'median') return `${Math.round(stats.p3)}s`;
    if (viewMetric === 'stress') return `${Math.round(stats.p1)}s`;

    return '';
};

export const prepareTimeSlots = (data) => {
    const timeSlotsSet = new Set((data?.data || []).map(d => d.time_slot));
    return Array.from(timeSlotsSet).sort((a, b) => {
        const getH = (t) => parseInt(t.split(':')[0], 10);
        const valA = getH(a) < 4 ? getH(a) + 24 : getH(a);
        const valB = getH(b) < 4 ? getH(b) + 24 : getH(b);
        return valA - valB;
    });
};

export const buildDataMatrix = (data) => {
    const matrix = {};
    if (data?.data) {
        data.data.forEach(item => {
            if (!matrix[item.stop_name]) matrix[item.stop_name] = {};
            const key = item.trip_id || item.time_slot;
            if (key) matrix[item.stop_name][key] = item;
        });
    }
    return matrix;
};
