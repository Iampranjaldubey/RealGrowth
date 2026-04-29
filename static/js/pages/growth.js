/**
 * growth.js — Real Economic Growth page logic.
 */

import { ApiClient, ChartManager, populateSelect, showError, showLoading } from "../api.js";

let growthChart = null;

async function loadChart(country) {
    if (!country) return;

    showLoading("loading", true);
    try {
        const data = await ApiClient.getGrowth(country);

        growthChart = ChartManager.create(growthChart, {
            canvasId: "growthChart",
            type: "line",
            data: {
                labels: data.years,
                datasets: [{
                    label: `${country} — Real Growth Rate (%)`,
                    data: data.values,
                    borderColor: "#4F46E5",
                    backgroundColor: "rgba(79, 70, 229, 0.1)",
                    borderWidth: 3, fill: true, tension: 0.2,
                }],
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                plugins: {
                    title: { display: true, text: `Real Economic Growth Rate — ${country}`, font: { size: 16 } },
                    tooltip: { callbacks: { label: (ctx) => `Growth: ${ctx.parsed.y.toFixed(2)}%` } },
                },
                scales: {
                    x: { title: { display: true, text: "Year" } },
                    y: {
                        title: { display: true, text: "Growth Rate (%)" },
                        ticks: { callback: (v) => v + "%" },
                    },
                },
            },
        });
    } catch (err) {
        console.error("Growth chart error:", err);
        showError("errorMessage", `Failed to load growth data for ${country}`);
    } finally {
        showLoading("loading", false);
    }
}

async function init() {
    showLoading("loading", true);
    try {
        const countries = await ApiClient.getGrowthCountries();
        populateSelect("countrySelect", countries, { value: "", text: "-- Select a Country --" });

        if (countries.length > 0) {
            document.getElementById("countrySelect").value = countries[0];
            await loadChart(countries[0]);
        }
    } catch (err) {
        console.error("Growth init error:", err);
        showError("errorMessage", "Failed to load countries list");
    } finally {
        showLoading("loading", false);
    }

    document.getElementById("countrySelect").addEventListener("change", function () {
        loadChart(this.value);
    });
}

document.addEventListener("DOMContentLoaded", init);
