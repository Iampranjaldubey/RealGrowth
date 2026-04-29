/**
 * wages.js — Average Wages page logic.
 */

import { ApiClient, ChartManager, populateSelect } from "../api.js";

let wagesChart = null;

async function loadChart(country) {
    if (!country) return;
    try {
        const data = await ApiClient.getWages(country);
        const years = Object.keys(data);
        const values = Object.values(data);

        wagesChart = ChartManager.create(wagesChart, {
            canvasId: "wagesChart",
            type: "line",
            data: {
                labels: years,
                datasets: [{
                    label: `${country} Average Wages (USD)`,
                    data: values,
                    borderColor: "#4F46E5",
                    backgroundColor: "rgba(79, 70, 229, 0.1)",
                    borderWidth: 3, fill: true, tension: 0.2,
                }],
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                plugins: {
                    title: { display: true, text: `Average Wages — ${country}`, font: { size: 16 } },
                    tooltip: { callbacks: { label: (ctx) => `Wage: $${ctx.parsed.y.toLocaleString()}` } },
                },
                scales: {
                    x: { title: { display: true, text: "Year" } },
                    y: {
                        title: { display: true, text: "Average Wage (USD)" },
                        ticks: { callback: (v) => "$" + v.toLocaleString() },
                    },
                },
            },
        });
    } catch (err) {
        console.error("Wages chart error:", err);
        alert("Failed to load wage data.");
    }
}

async function init() {
    try {
        const countries = await ApiClient.getWageCountries();
        populateSelect("countrySelect", countries, { value: "", text: "-- Select a Country --" });
    } catch (err) {
        console.error("Wages init error:", err);
    }

    document.getElementById("countrySelect").addEventListener("change", function () {
        loadChart(this.value);
    });
}

document.addEventListener("DOMContentLoaded", init);
