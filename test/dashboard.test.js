/**
 * @jest-environment jsdom
 */

const {
    showStockAlert,
    hideStockAlert,
    initDashboard
} = require('../static/js/dashboard');

describe('Dashboard', () => {

    beforeEach(() => {
        document.body.innerHTML = `
            <div id="stock-alert-overlay" style="display:none;"></div>
            <canvas id="ventasChart"></canvas>
        `;

        global.labels = ['Lunes', 'Martes'];
        global.datos = [100, 200];

        global.Chart = jest.fn().mockImplementation(() => {
            return {
                destroy: jest.fn()
            };
        });

        window.chart = null;
    });

    // ALERTAS
    test('Debe mostrar alerta de stock', () => {
        showStockAlert();

        const overlay = document.getElementById('stock-alert-overlay');
        expect(overlay.style.display).toBe('block');
    });

    test('Debe ocultar alerta de stock', () => {
        const overlay = document.getElementById('stock-alert-overlay');
        overlay.style.display = 'block';

        hideStockAlert();

        expect(overlay.style.display).toBe('none');
    });

    // CHART
    test('Debe crear una gráfica', () => {
        initDashboard();

        expect(global.Chart).toHaveBeenCalled();
        expect(window.chart).not.toBeNull();
    });

    test('Debe destruir gráfica anterior antes de crear una nueva', () => {
        const destroyMock = jest.fn();

        window.chart = {
            destroy: destroyMock
        };

        initDashboard();

        expect(destroyMock).toHaveBeenCalled();
        expect(global.Chart).toHaveBeenCalled();
    });

});