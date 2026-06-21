function showStockAlert() {
    const overlay = document.getElementById('stock-alert-overlay');
    if (!overlay) return;
    overlay.style.display = 'block';
}

function hideStockAlert() {
    const overlay = document.getElementById('stock-alert-overlay');
    if (!overlay) return;
    overlay.style.display = 'none';
}

function initDashboard() {
    const canvas = document.getElementById('ventasChart');
    if (!canvas) return;

    if (window.chart) {
        window.chart.destroy();
    }

    window.chart = new Chart(canvas, {
        type: 'line',
        data: {
            labels: global.labels || [],
            datasets: [{
                label: 'Ventas',
                data: global.datos || [],
                borderWidth: 2,
                fill: true
            }]
        },
        options: {
            responsive: true
        }
    });
}

function initEvents() {
    document.addEventListener('DOMContentLoaded', initDashboard);
    window.addEventListener('contentLoaded', initDashboard);
}

module.exports = {
    showStockAlert,
    hideStockAlert,
    initDashboard,
    initEvents
};