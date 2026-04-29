/**
 * api.js — Shared API client and chart utilities.
 *
 * This is the single source of truth for all backend API calls.
 * Uses window.location.origin as the base URL so it works in any
 * environment without hardcoded URLs.
 *
 * Exports: ApiClient, ChartManager, populateSelect, showError, showLoading
 */

const API_BASE = `${window.location.origin}/api/v1`;

// ================================================================ //
//                         API CLIENT                                //
// ================================================================ //

export const ApiClient = {
    /**
     * Generic GET request with consistent error handling.
     * Returns the `data` field from the response on success.
     * Throws an Error with the server message on failure.
     */
    async get(endpoint) {
        const res = await fetch(`${API_BASE}${endpoint}`);
        const json = await res.json();

        if (!res.ok || json.status === "error") {
            throw new Error(json.message || `Request failed (${res.status})`);
        }
        return json.data;
    },

    // ---- GDP ---- //
    getGdpYears() {
        return this.get("/gdp/years");
    },
    getGdpCountries() {
        return this.get("/gdp/countries");
    },
    getGdpTop(year, minPopulation = 0) {
        return this.get(`/gdp/top?year=${year}&min_population=${minPopulation}`);
    },
    getGdpCompare(c1, c2) {
        return this.get(`/gdp/compare?country1=${encodeURIComponent(c1)}&country2=${encodeURIComponent(c2)}`);
    },

    // ---- Inflation ---- //
    getInflationCountries() {
        return this.get("/inflation/countries");
    },
    getInflation(country) {
        return this.get(`/inflation/${encodeURIComponent(country)}`);
    },

    // ---- Food ---- //
    getFoodCountries() {
        return this.get("/food/countries");
    },
    getFoodCompare(c1, c2) {
        return this.get(`/food/compare?country1=${encodeURIComponent(c1)}&country2=${encodeURIComponent(c2)}`);
    },

    // ---- Population ---- //
    getPopulationMetadata() {
        return this.get("/population/metadata");
    },
    getPopulationDistribution(country, year) {
        return this.get(`/population/distribution?country=${encodeURIComponent(country)}&year=${year}`);
    },
    getPopulationTrend(country) {
        return this.get(`/population/trend?country=${encodeURIComponent(country)}`);
    },

    // ---- Wages ---- //
    getWageCountries() {
        return this.get("/wages/countries");
    },
    getWages(country) {
        return this.get(`/wages/${encodeURIComponent(country)}`);
    },

    // ---- Debt ---- //
    getDebt(year = "2022") {
        return this.get(`/debt?year=${year}`);
    },

    // ---- Growth ---- //
    getGrowthCountries() {
        return this.get("/growth/countries");
    },
    getGrowth(country) {
        return this.get(`/growth/${encodeURIComponent(country)}`);
    },
};

// ================================================================ //
//                       CHART MANAGER                               //
// ================================================================ //

/**
 * Creates or replaces a Chart.js chart instance.
 * Destroys the previous instance if one exists on a given canvas.
 *
 * Usage:
 *   myChart = ChartManager.create(myChart, { canvasId, type, data, options });
 */
export const ChartManager = {
    create(existingChart, { canvasId, type, data, options }) {
        if (existingChart) existingChart.destroy();

        const ctx = document.getElementById(canvasId).getContext("2d");
        return new Chart(ctx, { type, data, options });
    },
};

// ================================================================ //
//                         DOM UTILITIES                              //
// ================================================================ //

/**
 * Populate a <select> element with option values.
 * @param {string} selectId - The ID of the select element.
 * @param {string[]} options - Array of option values/labels.
 * @param {object|null} placeholder - Optional {value, text} for a default option.
 */
export function populateSelect(selectId, options, placeholder = null) {
    const select = document.getElementById(selectId);
    if (!select) return;

    select.innerHTML = "";

    if (placeholder) {
        const opt = document.createElement("option");
        opt.value = placeholder.value ?? "";
        opt.textContent = placeholder.text ?? "Select an option";
        select.appendChild(opt);
    }

    options.forEach((value) => {
        const opt = document.createElement("option");
        opt.value = value;
        opt.textContent = value;
        select.appendChild(opt);
    });
}

/**
 * Show a temporary error message in the element with the given ID.
 */
export function showError(elementId, message, durationMs = 5000) {
    const el = document.getElementById(elementId);
    if (!el) {
        console.error(message);
        return;
    }
    el.textContent = message;
    el.classList.add("visible");
    setTimeout(() => el.classList.remove("visible"), durationMs);
}

/**
 * Toggle loading indicator visibility.
 */
export function showLoading(elementId, visible) {
    const el = document.getElementById(elementId);
    if (!el) return;
    el.classList.toggle("visible", visible);
}

/**
 * Set up tab switching for elements with class "tab-button".
 */
export function initTabs() {
    document.querySelectorAll(".tab-button").forEach((btn) => {
        btn.addEventListener("click", () => {
            const tabId = btn.dataset.tab;

            document.querySelectorAll(".tab-content").forEach((c) => c.classList.remove("active"));
            document.querySelectorAll(".tab-button").forEach((b) => b.classList.remove("active"));

            const tab = document.getElementById(tabId);
            if (tab) tab.classList.add("active");
            btn.classList.add("active");
        });
    });
}
