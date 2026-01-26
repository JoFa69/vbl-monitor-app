export const THEME = {
    colors: {
        vblRed: '#E30613',
        vblGrey: '#58585A',
        vblLightGrey: '#F4F4F4',
        punctual: '#86bd28', // Explicitly requested Green
        warning: '#f59e0b', // Amber/Orange
        late: '#ef4444', // Red
        lateSevere: '#7f1d1d', // Dark Red
        empty: '#f8fafc',
    },
    thresholds: {
        early: -60,
        late: 180,
        critical: 300,
    }
};
