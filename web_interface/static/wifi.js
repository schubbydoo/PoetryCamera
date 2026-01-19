/**
 * Poetry Camera - WiFi Management JavaScript
 */

let selectedSSID = null;

// ==================== Initialization ====================

document.addEventListener('DOMContentLoaded', () => {
    // Load initial data
    loadSavedNetworks();
    
    // Set up event listeners
    document.getElementById('btn-scan').addEventListener('click', scanNetworks);
    document.getElementById('btn-add-network').addEventListener('click', addNetwork);
    document.getElementById('btn-modal-connect').addEventListener('click', connectFromModal);
    document.getElementById('btn-confirm-forget').addEventListener('click', forgetNetwork);
    
    // Auto-scan on page load
    scanNetworks();
});

// ==================== Network Scanning ====================

async function scanNetworks() {
    const btn = document.getElementById('btn-scan');
    const loading = document.getElementById('scan-loading');
    const table = document.getElementById('available-networks');
    
    setButtonLoading(btn, true);
    loading.style.display = 'block';
    table.querySelector('tbody').innerHTML = '';
    
    try {
        const result = await apiCall('/api/wifi/scan');
        
        if (result.success && result.networks) {
            displayAvailableNetworks(result.networks);
        } else {
            table.querySelector('tbody').innerHTML = `
                <tr>
                    <td colspan="4" class="has-text-centered has-text-danger">
                        Failed to scan networks
                    </td>
                </tr>
            `;
        }
    } catch (error) {
        showNotification('Failed to scan networks: ' + error.message, 'danger');
        table.querySelector('tbody').innerHTML = `
            <tr>
                <td colspan="4" class="has-text-centered has-text-danger">
                    Error scanning networks
                </td>
            </tr>
        `;
    } finally {
        setButtonLoading(btn, false);
        loading.style.display = 'none';
    }
}

function displayAvailableNetworks(networks) {
    const tbody = document.querySelector('#available-networks tbody');
    
    if (networks.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="4" class="has-text-centered has-text-grey">
                    No networks found
                </td>
            </tr>
        `;
        return;
    }
    
    tbody.innerHTML = networks.map(network => `
        <tr>
            <td>
                <span class="icon"><i class="fas fa-wifi"></i></span>
                ${escapeHtml(network.ssid)}
            </td>
            <td>
                ${createSignalBars(network.signal)}
                <span class="is-size-7 has-text-grey ml-1">${network.signal}%</span>
            </td>
            <td>
                <span class="tag is-${network.security === 'Open' ? 'warning' : 'info'} is-light is-small">
                    ${network.security === 'Open' ? 'Open' : '<i class="fas fa-lock"></i>'}
                </span>
            </td>
            <td>
                <button class="button is-small is-primary" onclick="showConnectModal('${escapeHtml(network.ssid)}')">
                    Connect
                </button>
            </td>
        </tr>
    `).join('');
}

// ==================== Saved Networks ====================

async function loadSavedNetworks() {
    const loading = document.getElementById('saved-networks-loading');
    const table = document.getElementById('saved-networks');
    
    loading.style.display = 'block';
    
    try {
        const result = await apiCall('/api/wifi/networks');
        
        if (result.success && result.networks) {
            displaySavedNetworks(result.networks);
        }
    } catch (error) {
        console.error('Failed to load saved networks:', error);
    } finally {
        loading.style.display = 'none';
    }
}

function displaySavedNetworks(networks) {
    const tbody = document.querySelector('#saved-networks tbody');
    
    if (networks.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td class="has-text-centered has-text-grey">
                    No saved networks
                </td>
            </tr>
        `;
        return;
    }
    
    tbody.innerHTML = networks.map(network => `
        <tr>
            <td>
                <span class="icon"><i class="fas fa-star has-text-warning"></i></span>
                ${escapeHtml(network.name)}
                ${network.autoconnect ? '<span class="tag is-small is-light ml-2">Auto</span>' : ''}
            </td>
            <td style="width: 80px;">
                <button class="button is-small is-danger is-outlined" 
                        onclick="showForgetModal('${escapeHtml(network.name)}')">
                    <span class="icon"><i class="fas fa-trash"></i></span>
                </button>
            </td>
        </tr>
    `).join('');
}

// ==================== Connect Modal ====================

function showConnectModal(ssid) {
    selectedSSID = ssid;
    document.getElementById('modal-ssid').textContent = ssid;
    document.getElementById('modal-password').value = '';
    document.getElementById('modal-autoconnect').checked = true;
    openModal('connect-modal');
    
    // Focus password field
    setTimeout(() => {
        document.getElementById('modal-password').focus();
    }, 100);
}

async function connectFromModal() {
    const password = document.getElementById('modal-password').value;
    const autoconnect = document.getElementById('modal-autoconnect').checked;
    
    if (!password) {
        showNotification('Please enter a password', 'warning');
        return;
    }
    
    const btn = document.getElementById('btn-modal-connect');
    setButtonLoading(btn, true);
    
    try {
        const result = await apiCall('/api/wifi/connect', 'POST', {
            ssid: selectedSSID,
            password: password,
            autoconnect: autoconnect
        });
        
        if (result.success) {
            showNotification(`Connected to ${selectedSSID}!`, 'success');
            closeModal('connect-modal');
            loadSavedNetworks();
            updateCurrentStatus();
        } else {
            showNotification(result.error || 'Failed to connect', 'danger');
        }
    } catch (error) {
        showNotification('Connection failed: ' + error.message, 'danger');
    } finally {
        setButtonLoading(btn, false);
    }
}

// ==================== Add Network ====================

async function addNetwork() {
    const ssid = document.getElementById('new-ssid').value.trim();
    const password = document.getElementById('new-password').value;
    const autoconnect = document.getElementById('new-autoconnect').checked;
    
    if (!ssid) {
        showNotification('Please enter a network name', 'warning');
        return;
    }
    
    if (!password) {
        showNotification('Please enter a password', 'warning');
        return;
    }
    
    const btn = document.getElementById('btn-add-network');
    setButtonLoading(btn, true);
    
    try {
        const result = await apiCall('/api/wifi/connect', 'POST', {
            ssid: ssid,
            password: password,
            autoconnect: autoconnect
        });
        
        if (result.success) {
            showNotification(`Connected to ${ssid}!`, 'success');
            document.getElementById('new-ssid').value = '';
            document.getElementById('new-password').value = '';
            loadSavedNetworks();
            updateCurrentStatus();
        } else {
            showNotification(result.error || 'Failed to connect', 'danger');
        }
    } catch (error) {
        showNotification('Connection failed: ' + error.message, 'danger');
    } finally {
        setButtonLoading(btn, false);
    }
}

// ==================== Forget Network ====================

function showForgetModal(ssid) {
    selectedSSID = ssid;
    document.getElementById('forget-ssid').textContent = ssid;
    openModal('forget-modal');
}

async function forgetNetwork() {
    const btn = document.getElementById('btn-confirm-forget');
    setButtonLoading(btn, true);
    
    try {
        const result = await apiCall('/api/wifi/forget', 'POST', {
            ssid: selectedSSID
        });
        
        if (result.success) {
            showNotification(`Removed ${selectedSSID}`, 'success');
            closeModal('forget-modal');
            loadSavedNetworks();
        } else {
            showNotification(result.error || 'Failed to remove network', 'danger');
        }
    } catch (error) {
        showNotification('Failed to remove network: ' + error.message, 'danger');
    } finally {
        setButtonLoading(btn, false);
    }
}

// ==================== Status Update ====================

async function updateCurrentStatus() {
    try {
        const result = await apiCall('/api/wifi/status');
        
        if (result.success) {
            const networkSpan = document.getElementById('current-network');
            const ipSpan = document.getElementById('current-ip');
            
            if (result.connected) {
                networkSpan.innerHTML = `<span class="tag is-success is-light">${escapeHtml(result.ssid)}</span>`;
            } else {
                networkSpan.innerHTML = '<span class="tag is-danger is-light">Not connected</span>';
            }
            
            ipSpan.textContent = result.ip_address || 'N/A';
        }
    } catch (error) {
        console.error('Failed to update status:', error);
    }
}

// Helper function (also defined in main.js but needed here for standalone testing)
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
