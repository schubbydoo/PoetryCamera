/**
 * Poetry Camera - Settings JavaScript
 */

// ==================== Model Suggestions ====================

const MODEL_SUGGESTIONS = {
    openai: [
        { value: "gpt-4o-mini", label: "GPT-4o Mini (Recommended)" },
        { value: "gpt-4o", label: "GPT-4o" },
        { value: "gpt-4-turbo", label: "GPT-4 Turbo" },
        { value: "gpt-4.1-mini", label: "GPT-4.1 Mini" },
        { value: "gpt-4.1", label: "GPT-4.1" },
        { value: "o1-mini", label: "O1 Mini" },
        { value: "o1", label: "O1" },
    ],
    anthropic: [
        { value: "claude-sonnet-4-20250514", label: "Claude Sonnet 4 (Recommended)" },
        { value: "claude-haiku-4-5-20251001", label: "Claude Haiku 4.5 (Fast)" },
        { value: "claude-opus-4-20250514", label: "Claude Opus 4 (Best Quality)" },
    ]
};

const MODEL_HELP_TEXT = {
    openai: "Enter any OpenAI model name (e.g., gpt-4o-mini)",
    anthropic: "Enter any Anthropic model name (e.g., claude-sonnet-4-20250514)"
};

const POEM_FORMAT_DESCRIPTIONS = {
    "limerick": "5 lines, AABBA rhyme. Short, bouncy rhythm — your best bet for pure fun. Great for candid or humorous moments.",
    "ballad stanza": "4-line stanzas, ABAB rhyme. A classic storytelling format — flexible, naturally musical, works for lighthearted and sentimental scenes.",
    "rhyming couplets": "AA BB CC pattern. The simplest rhyme structure — punchy, rhythmic, and consistently reliable.",
    "clerihew": "4-line biographical poem, AABB rhyme. First line is a person's name — perfect when the camera sees people.",
    "sonnet": "14 lines, ABAB CDCD EFEF GG. Strong rhyme throughout but longer — best for dramatic or detailed scenes."
};

// ==================== Initialization ====================

document.addEventListener('DOMContentLoaded', () => {
    // Set up event listeners
    document.getElementById('btn-save-printer').addEventListener('click', savePrinterSettings);
    document.getElementById('btn-save-openai').addEventListener('click', saveOpenAISettings);
    document.getElementById('btn-save-prompts').addEventListener('click', savePrompts);
    document.getElementById('btn-reset-prompts').addEventListener('click', () => openModal('reset-modal'));
    document.getElementById('btn-confirm-reset').addEventListener('click', resetPrompts);

    // Printer type change handler
    document.getElementById('printer-type').addEventListener('change', updatePrinterVisibility);

    // AI provider change handler
    document.getElementById('ai-provider').addEventListener('change', updateModelSuggestions);

    // Poem format change handler
    document.getElementById('poem-format').addEventListener('change', updatePoemFormatDescription);

    // Initialize printer visibility
    updatePrinterVisibility();

    // Initialize model suggestions for current provider
    updateModelSuggestions();

    // Initialize poem format description
    updatePoemFormatDescription();
});

// ==================== AI Provider / Model Suggestions ====================

function updateModelSuggestions() {
    const provider = document.getElementById('ai-provider').value;
    const datalist = document.getElementById('model-suggestions');
    const helpText = document.getElementById('model-help');

    // Clear existing options
    datalist.innerHTML = '';

    // Populate with provider-specific suggestions
    const suggestions = MODEL_SUGGESTIONS[provider] || [];
    suggestions.forEach(s => {
        const option = document.createElement('option');
        option.value = s.value;
        option.textContent = s.label;
        datalist.appendChild(option);
    });

    // Update help text
    if (helpText) {
        helpText.textContent = MODEL_HELP_TEXT[provider] || "Enter a model name";
    }
}

// ==================== Poem Format Description ====================

function updatePoemFormatDescription() {
    const format = document.getElementById('poem-format').value;
    const descEl = document.getElementById('poem-format-description');
    if (descEl) {
        descEl.textContent = POEM_FORMAT_DESCRIPTIONS[format] || '';
    }
}

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

// ==================== Save AI Settings ====================

async function saveOpenAISettings() {
    const btn = document.getElementById('btn-save-openai');

    const config = {
        provider: document.getElementById('ai-provider').value,
        model: document.getElementById('openai-model').value,
        poem_format: document.getElementById('poem-format').value
    };

    setButtonLoading(btn, true);

    try {
        const result = await apiCall('/api/settings/openai', 'POST', config);

        if (result.success) {
            showNotification('AI settings saved!', 'success');
        } else {
            showNotification(result.error || 'Failed to save settings', 'danger');
        }
    } catch (error) {
        showNotification('Error saving settings: ' + error.message, 'danger');
    } finally {
        setButtonLoading(btn, false);
    }
}

// ==================== Save Prompts ====================

async function savePrompts() {
    const btn = document.getElementById('btn-save-prompts');

    const config = {
        poem_prompt: document.getElementById('poem-prompt').value
    };

    setButtonLoading(btn, true);

    try {
        const result = await apiCall('/api/settings/openai', 'POST', config);

        if (result.success) {
            showNotification('Prompt saved!', 'success');
        } else {
            showNotification(result.error || 'Failed to save prompt', 'danger');
        }
    } catch (error) {
        showNotification('Error saving prompt: ' + error.message, 'danger');
    } finally {
        setButtonLoading(btn, false);
    }
}

// ==================== Reset Prompts ====================

async function resetPrompts() {
    const btn = document.getElementById('btn-confirm-reset');

    setButtonLoading(btn, true);

    try {
        const result = await apiCall('/api/settings/reset', 'POST', { section: 'openai' });

        if (result.success) {
            closeModal('reset-modal');
            showNotification('Prompts reset to defaults. Refreshing...', 'success');

            // Reload the page to get fresh defaults
            setTimeout(() => {
                window.location.reload();
            }, 1500);
        } else {
            showNotification(result.error || 'Failed to reset prompts', 'danger');
        }
    } catch (error) {
        showNotification('Error resetting prompts: ' + error.message, 'danger');
    } finally {
        setButtonLoading(btn, false);
    }
}
