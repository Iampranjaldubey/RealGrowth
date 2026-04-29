/**
 * food.js — Food Price Comparison page logic.
 * Handles histogram (bar) and line chart for healthy diet costs.
 */

import { ApiClient, ChartManager, populateSelect, initTabs } from "../api.js";

let histogramChart = null;
let lineChart = null;

async function loadHistogram() {
    const c1 = document.getElementById("country1").value;
    const c2 = document.getElementById("country2").value;
    if (!c1 || !c2) { alert("Please select two countries"); return; }

    try {
        const data = await ApiClient.getFoodCompare(c1, c2);
        const labels = data.map((d) => d.year);
        const d1 = data.map((d) => d[c1]);
        const d2 = data.map((d) => d[c2]);

        histogramChart = ChartManager.create(histogramChart, {
            canvasId: "histogramChart",
            type: "bar",
            data: {
                labels,
                datasets: [
                    { label: c1, data: d1, backgroundColor: "rgba(239, 68, 68, 0.65)" },
                    { label: c2, data: d2, backgroundColor: "rgba(79, 70, 229, 0.65)" },
                ],
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                plugins: { title: { display: true, text: `Food Price Comparison: ${c1} vs ${c2}`, font: { size: 16 } } },
                scales: {
                    y: { beginAtZero: true, title: { display: true, text: "Price (USD)" } },
                    x: { title: { display: true, text: "Year" } },
                },
            },
        });
    } catch (err) {
        console.error("Food histogram error:", err);
        alert("Failed to load food price data.");
    }
}

async function loadLineChart() {
    const c1 = document.getElementById("country1_line").value;
    const c2 = document.getElementById("country2_line").value;
    if (!c1 || !c2) { alert("Please select two countries"); return; }

    try {
        const data = await ApiClient.getFoodCompare(c1, c2);
        const labels = data.map((d) => d.year);
        const d1 = data.map((d) => d[c1]);
        const d2 = data.map((d) => d[c2]);

        lineChart = ChartManager.create(lineChart, {
            canvasId: "lineChart",
            type: "line",
            data: {
                labels,
                datasets: [
                    { label: c1, data: d1, borderColor: "rgba(239, 68, 68, 1)", backgroundColor: "rgba(239, 68, 68, 0.1)", fill: true, tension: 0.2 },
                    { label: c2, data: d2, borderColor: "rgba(79, 70, 229, 1)", backgroundColor: "rgba(79, 70, 229, 0.1)", fill: true, tension: 0.2 },
                ],
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                plugins: { title: { display: true, text: `Food Price Trends: ${c1} vs ${c2}`, font: { size: 16 } } },
                scales: {
                    y: { beginAtZero: true, title: { display: true, text: "Price (USD)" } },
                    x: { title: { display: true, text: "Year" } },
                },
            },
        });
    } catch (err) {
        console.error("Food line chart error:", err);
        alert("Failed to load food trend data.");
    }
}

async function init() {
    initTabs();

    try {
        const countries = await ApiClient.getFoodCountries();
        ["country1", "country2", "country1_line", "country2_line"].forEach((id) =>
            populateSelect(id, countries)
        );
        if (countries.length >= 2) {
            document.getElementById("country1").value = countries[0];
            document.getElementById("country2").value = countries[1];
            document.getElementById("country1_line").value = countries[0];
            document.getElementById("country2_line").value = countries[1];
            loadHistogram();
            loadLineChart();
        }
    } catch (err) {
        console.error("Food init error:", err);
    }

    document.getElementById("histogramBtn").addEventListener("click", loadHistogram);
    document.getElementById("lineBtn").addEventListener("click", loadLineChart);
}

document.addEventListener("DOMContentLoaded", init);
