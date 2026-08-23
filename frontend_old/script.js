    // Common utility functions for all pages

    // Base API URL with /api prefix
    const API_BASE_URL = 'https://dhp-project-2-1n7f.onrender.com/api';

    // GDP APIs
    async function fetchGDPData(year = '2023', population = 0) {
        const res = await fetch(`${API_BASE_URL}/gdp/data?year=${year}&population=${population}`);
        return res.json();
    }

    async function fetchGDPCountries() {
        const res = await fetch(`${API_BASE_URL}/gdp/countries`);
        return res.json();
    }

    async function fetchGDPTop10(year, min_population = 0) {
        const res = await fetch(`${API_BASE_URL}/gdp?year=${year}&min_population=${min_population}`);
        return res.json();
    }

    async function compareGDPCountries(country1, country2) {
        const res = await fetch(`${API_BASE_URL}/compare?country1=${country1}&country2=${country2}`);
        return res.json();
    }

    // Inflation APIs
    async function fetchInflationData(country) {
        const res = await fetch(`${API_BASE_URL}/inflation/${country}`);
        return res.json();
    }

    async function fetchInflationCountries() {
        const res = await fetch(`${API_BASE_URL}/inflation/countries`);
        return res.json();
    }

    // Food APIs
    async function fetchFoodCountries() {
        const res = await fetch(`${API_BASE_URL}/food/countries`);
        return res.json();
    }

    async function fetchFoodHistogramData(country1, country2) {
        const res = await fetch(`${API_BASE_URL}/food/histogram?country1=${country1}&country2=${country2}`);
        return res.json();
    }

    async function fetchFoodLineData(country1, country2) {
        const res = await fetch(`${API_BASE_URL}/food/line?country1=${country1}&country2=${country2}`);
        return res.json();
    }

    // Population APIs
    async function fetchPopulationData(year, country) {
        const res = await fetch(`${API_BASE_URL}/population?year=${year}&country=${country}`);
        return res.json();
    }

    async function fetchPopulationLineData(country) {
        const res = await fetch(`${API_BASE_URL}/population/line?country=${country}`);
        return res.json();
    }

    async function fetchPopulationMetadata() {
        const res = await fetch(`${API_BASE_URL}/population/metadata`);
        return res.json();
    }

    // Wages APIs
    async function fetchWageCountries() {
        const res = await fetch(`${API_BASE_URL}/wages/countries`);
        return res.json();
    }

    async function fetchWagesByCountry(country) {
        const res = await fetch(`${API_BASE_URL}/wages/${country}`);
        return res.json();
    }

    // Debt APIs
    async function fetchDebtData(year = '2022') {
        const res = await fetch(`${API_BASE_URL}/debt?year=${year}`);
        return res.json();
    }

    // Real Growth APIs
    async function fetchGrowthCountries() {
        const res = await fetch(`${API_BASE_URL}/growth/countries`);
        return res.json();
    }

    async function fetchRealGrowthData(country) {
        const res = await fetch(`${API_BASE_URL}/growth/${country}`);
        return res.json();
    }

    // Utility: Show active tab
    function showTab(tabId) {
        document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
        document.querySelectorAll('.tab-button').forEach(button => button.classList.remove('active'));

        const selectedTab = document.getElementById(tabId);
        if (selectedTab) selectedTab.classList.add('active');

        const activeButton = document.querySelector(`[data-tab="${tabId}"]`);
        if (activeButton) activeButton.classList.add('active');
    }

    // Utility: Populate select options
    function populateSelect(selectId, options, defaultOption = null) {
        const select = document.getElementById(selectId);
        if (!select) return;

        select.innerHTML = '';
        if (defaultOption) {
            const opt = document.createElement('option');
            opt.value = defaultOption.value || '';
            opt.textContent = defaultOption.text || 'Select an option';
            select.appendChild(opt);
        }

        options.forEach(value => {
            const opt = document.createElement('option');
            opt.value = value;
            opt.textContent = value;
            select.appendChild(opt);
        });
    }

    // Utility: Format numbers
    function formatNumber(number, prefix = '', decimals = 0) {
        if (number === null || number === undefined || isNaN(number)) return 'N/A';
        return prefix + Number(number).toLocaleString(undefined, {
            minimumFractionDigits: decimals,
            maximumFractionDigits: decimals
        });
    }

    // Utility: Create or update chart
    function createOrUpdateChart(chartInstance, config) {
        if (chartInstance) chartInstance.destroy();
        return new Chart(document.getElementById(config.canvasId).getContext('2d'), {
            type: config.type,
            data: config.data,
            options: config.options
        });
    }

    // Utility: Handle API errors
    function handleApiError(error) {
        console.error('API Error:', error);
        alert('An error occurred while fetching data. Please try again later.');
    }

    // Initialize tab logic on DOM ready
    document.addEventListener('DOMContentLoaded', function () {
        const tabButtons = document.querySelectorAll('.tab-button');
        if (tabButtons.length > 0) {
            tabButtons.forEach(button => {
                button.addEventListener('click', () => {
                    const tabId = button.dataset.tab;
                    showTab(tabId);
                });
            });
            showTab(tabButtons[0].dataset.tab);
        }
    });
