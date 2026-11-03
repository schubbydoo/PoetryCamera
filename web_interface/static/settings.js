/**
 * Poetry Camera - Settings JavaScript
 */

document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('btn-save-printer').addEventListener('click', savePrinterSettings);
    document.getElementById('btn-test-print').addEventListener('click', testPrint);
    document.getElementById('btn-save-zoltar').addEventListener('click', saveZoltarSettings);
    loadZoltarSettings();

    // Printer type change handler
    document.getElementById('printer-type').addEventListener('change', updatePrinterVisibility);

    // Initialize printer visibility
    updatePrinterVisibility();
});

// ==================== Printer Visibility ====================

function updatePrinterVisibility() {
    const printerType = document.getElementById('printer-type').value;
    const catSettings = document.getElementById('cat-printer-settings');
    const networkSettings = document.getElementById('network-printer-settings');

    if (printerType === 'cat_printer') {
        catSettings.style.display = 'block';
        networkSettings.style.display = 'none';
    } else if (printerType === 'network_printer') {
        catSettings.style.display = 'none';
        networkSettings.style.display = 'block';
    } else {
        // Both
        catSettings.style.display = 'block';
        networkSettings.style.display = 'block';
    }
}

// ==================== Save Printer Settings ====================

async function savePrinterSettings() {
    const btn = document.getElementById('btn-save-printer');

    const config = {
        type: document.getElementById('printer-type').value,
        cat_printer: {
            name: document.getElementById('cat-printer-name').value,
            mac_address: document.getElementById('cat-printer-mac').value
        },
        network_printer: {
            address: document.getElementById('network-printer-address').value,
            port: parseInt(document.getElementById('network-printer-port').value) || 9100
        }
    };

    setButtonLoading(btn, true);

    try {
        const result = await apiCall('/api/settings/printer', 'POST', config);

        if (result.success) {
            showNotification('Printer settings saved!', 'success');
        } else {
            showNotification(result.error || 'Failed to save settings', 'danger');
        }
    } catch (error) {
        showNotification('Error saving settings: ' + error.message, 'danger');
    } finally {
        setButtonLoading(btn, false);
    }
}

// ==================== Test Print ====================

async function testPrint() {
    const btn = document.getElementById('btn-test-print');
    setButtonLoading(btn, true);
    try {
        const result = await apiCall('/api/printer/test', 'POST');
        if (result.success) {
            showNotification('Test print sent to printer!', 'success');
        } else {
            showNotification(result.error || 'Failed to send test print', 'danger');
        }
    } catch (error) {
        showNotification(error.message, 'danger');
    } finally {
        setButtonLoading(btn, false);
    }
}

// ==================== Zoltar (lucky numbers) ====================

function showZoltar(config) {
    document.getElementById('zoltar-enabled').checked = !!config.enabled;
    document.getElementById('zoltar-address').value = config.address || '';
    document.getElementById('zoltar-token').value = '';
    document.getElementById('zoltar-token-help').textContent =
        config.token_set ? 'A token is saved. Leave blank to keep it.' : 'No token saved yet.';
}

async function loadZoltarSettings() {
    try {
        const result = await apiCall('/api/settings/zoltar', 'GET');
        if (result.success) showZoltar(result.config);
    } catch (error) { /* tab stays empty */ }
}

async function saveZoltarSettings() {
    const btn = document.getElementById('btn-save-zoltar');
    setButtonLoading(btn, true);
    try {
        const result = await apiCall('/api/settings/zoltar', 'POST', {
            enabled: document.getElementById('zoltar-enabled').checked,
            address: document.getElementById('zoltar-address').value,
            token: document.getElementById('zoltar-token').value
        });
        if (result.success) {
            showZoltar(result.config);
            showNotification('Zoltar settings saved!', 'success');
        } else {
            showNotification(result.error || 'Failed to save settings', 'danger');
        }
    } catch (error) {
        showNotification('Error saving settings: ' + error.message, 'danger');
    } finally {
        setButtonLoading(btn, false);
    }
}
