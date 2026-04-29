/**
 * inflation.js — Inflation Rate page logic.
 */

import { ApiClient, ChartManager, populateSelect } from "../api.js";

let inflationChart = null;
const years = Array.from({ length: 15 }, (_, i) => 2010 + i);

async function loadChart(country) {
    if (!country) return;
    try {
        const data = await ApiClient.getInflation(country);
        inflationChart = ChartManager.create(inflationChart, {
            canvasId: "inflationChart",
            type: "line",
            data: {
                labels: years,
                datasets: [{
                    label: `${data.country} Inflation Rate (%)`,
                    data: data.values,
                    borderColor: "#4F46E5",
                    backgroundColor: "rgba(79, 70, 229, 0.1)",
                    borderWidth: 3, fill: true, tension: 0.2,
                }],
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                plugins: {
                    title: { display: true, text: `Inflation Rate — ${data.country}`, font: { size: 16 } },
                    tooltip: { callbacks: { label: (ctx) => `Inflation: ${ctx.parsed.y.toFixed(2)}%` } },
                },
                scales: {
                    x: { title: { display: true, text: "Year" } },
                    y: {
                        title: { display: true, text: "Inflation Rate (%)" },
                        ticks: { callback: (v) => v + "%" },
                    },
                },
            },
        });
    } catch (err) {
        console.error("Inflation chart error:", err);
        alert("Failed to load inflation data.");
    }
}

async function init() {
    try {
        const countries = await ApiClient.getInflationCountries();
        populateSelect("countrySelect", countries, { value: "", text: "-- Select a Country --" });
    } catch (err) {
        console.error("Inflation init error:", err);
    }

    document.getElementById("countrySelect").addEventListener("change", function () {
        loadChart(this.value);
    });
}

document.addEventListener("DOMContentLoaded", init);
