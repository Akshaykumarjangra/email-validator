document.addEventListener('DOMContentLoaded', () => {
    const verifyBtn = document.getElementById('verifyBtn');
    if (!verifyBtn) return; // Not logged in

    const clearBtn = document.getElementById('clearBtn');
    const exportBtn = document.getElementById('exportBtn');
    const emailInput = document.getElementById('emailInput');
    const resultsSection = document.getElementById('resultsSection');
    const resultsTable = document.getElementById('resultsTable').querySelector('tbody');
    const loader = document.getElementById('loader');
    const loaderText = document.getElementById('loaderText');

    const countValid = document.getElementById('countValid');
    const countRisky = document.getElementById('countRisky');
    const countInvalid = document.getElementById('countInvalid');

    let currentResults = [];

    // Real-time metrics update
    async function updateMetrics() {
        try {
            const res = await fetch('/api/stats');
            if (res.ok) {
                const stats = await res.json();
                // We update the DOM elements if they exist (metrics grid)
                const usageText = document.querySelector('.metric-card .value');
                const progressFill = document.querySelector('.progress-fill');
                if (usageText) {
                    usageText.textContent = `${stats.credits_used} / ${stats.credits_total}`;
                    const percent = (stats.credits_used / stats.credits_total) * 100;
                    progressFill.style.width = `${percent}%`;
                }
            }
        } catch (e) {
            console.error("Failed to update metrics", e);
        }
    }

    verifyBtn.addEventListener('click', async () => {
        const text = emailInput.value.trim();
        if (!text) return alert('Please enter some emails first.');

        const emails = text.split(/[,\n\s]+/).filter(e => e.trim());
        if (emails.length > 1000) {
            return alert('Batch limit exceeded. Max 1,000 emails per request.');
        }

        loader.classList.remove('hidden');
        loaderText.textContent = `Verifying ${emails.length} mailboxes...`;

        try {
            const response = await fetch('/api/verify', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ emails: text })
            });

            if (response.status === 403) {
                const err = await response.json();
                return alert(err.error || 'Trial limit reached.');
            }

            if (!response.ok) throw new Error('Verification failed');

            const results = await response.json();
            displayResults(results);
            updateMetrics(); // Refresh usage numbers
        } catch (error) {
            alert('Error: ' + error.message);
        } finally {
            loader.classList.add('hidden');
        }
    });

    clearBtn.addEventListener('click', () => {
        emailInput.value = '';
        resultsSection.classList.add('hidden');
        resultsTable.innerHTML = '';
        currentResults = [];
    });

    exportBtn.addEventListener('click', async () => {
        if (!currentResults.length) return;

        try {
            const response = await fetch('/api/export', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ results: currentResults })
            });

            if (!response.ok) throw new Error('Export failed');

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'verified_emails.csv';
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
        } catch (error) {
            alert('Export error: ' + error.message);
        }
    });

    function displayResults(results) {
        currentResults = results;
        resultsTable.innerHTML = '';
        resultsSection.classList.remove('hidden');

        let valid = 0, risky = 0, invalid = 0;

        results.forEach(res => {
            const row = document.createElement('tr');
            const statusClass = `status-${res.status.toLowerCase()}`;

            if (res.status === 'Valid') valid++;
            if (res.status === 'Risky') risky++;
            if (res.status === 'Invalid' || res.status === 'Error') invalid++;

            row.innerHTML = `
                <td>${res.email}</td>
                <td class="${statusClass}">${res.status}</td>
                <td style="font-size: 0.9rem; color: #94a3b8;">${res.details}</td>
            `;
            resultsTable.appendChild(row);
        });

        countValid.textContent = valid;
        countRisky.textContent = risky;
        countInvalid.textContent = invalid;

        resultsSection.scrollIntoView({ behavior: 'smooth' });
    }

    // Periodically update metrics
    setInterval(updateMetrics, 30000);
});
