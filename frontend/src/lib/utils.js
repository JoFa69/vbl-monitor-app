
export function formatNumber(num) {
    if (num === null || num === undefined) return '';
    // Swiss format: 1'000.00
    return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, "'");
}
