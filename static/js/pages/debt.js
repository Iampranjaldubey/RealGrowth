/**
 * debt.js — Debt-to-GDP Ratio world map page logic.
 * Uses D3.js and TopoJSON to render a choropleth map.
 */

const API_BASE = `${window.location.origin}/api/v1`;

// Map dimensions
const width = 960;
const height = 500;

// Color scale for debt ranges
const colorScale = d3.scaleThreshold()
    .domain([50, 100, 150, 200])
    .range(["#ffffcc", "#a1dab4", "#41b6c4", "#2c7fb8", "#253494"]);

// Create SVG
const svg = d3.select("#map").append("svg")
    .attr("width", "100%")
    .attr("height", height)
    .attr("viewBox", `0 0 ${width} ${height}`)
    .attr("preserveAspectRatio", "xMidYMid meet");

const g = svg.append("g");

// Projection & path
const projection = d3.geoNaturalEarth1()
    .scale(width / 2 / Math.PI)
    .translate([width / 2, height / 2]);

const path = d3.geoPath().projection(projection);

// Tooltip
const tooltip = d3.select("body").append("div")
    .attr("class", "tooltip")
    .style("opacity", 0)
    .style("position", "absolute")
    .style("pointer-events", "none");

function showStatus(message, isError = false) {
    const el = document.getElementById("status-message");
    if (!el) return;
    el.textContent = message;
    el.style.color = isError ? "#ef4444" : "#10b981";
}

async function fetchDebtData(year) {
    const res = await fetch(`${API_BASE}/debt?year=${year}`);
    const json = await res.json();
    if (json.status !== "success") throw new Error(json.message || "Failed to fetch debt data");
    return json.data;
}

async function updateMap() {
    const year = document.getElementById("yearSelect").value;
    showStatus(`Loading debt data for ${year}...`);

    try {
        const data = await fetchDebtData(year);

        if (!data || data.length === 0) {
            showStatus(`No data available for ${year}`, true);
            return;
        }

        // Build lookup
        const debtMap = {};
        data.forEach((d) => {
            if (d.country && d.value != null) debtMap[d.country] = parseFloat(d.value);
        });

        // Update colors
        svg.selectAll(".country")
            .attr("fill", (d) => {
                const name = d.properties.name;
                return debtMap[name] !== undefined ? colorScale(debtMap[name]) : "#ccc";
            })
            .on("mouseover", (event, d) => {
                const name = d.properties.name;
                const val = debtMap[name];
                tooltip.transition().duration(200).style("opacity", 0.9);
                tooltip.html(`<strong>${name}</strong><br>Debt-to-GDP: ${val !== undefined ? val.toFixed(2) + '%' : 'No data'}`)
                    .style("left", (event.pageX + 10) + "px")
                    .style("top", (event.pageY - 28) + "px");
            })
            .on("mouseout", () => {
                tooltip.transition().duration(400).style("opacity", 0);
            });

        showStatus(`Map updated — ${Object.keys(debtMap).length} countries with data for ${year}`);
    } catch (err) {
        console.error("Debt map error:", err);
        showStatus(`Error: ${err.message}`, true);
    }
}

// Make updateMap available globally for the onchange handler
window.updateMap = updateMap;

// Load world map
Promise.all([
    d3.json("https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json"),
]).then(([world]) => {
    showStatus("World map loaded. Fetching debt data...");
    const countries = topojson.feature(world, world.objects.countries).features;

    g.selectAll("path")
        .data(countries)
        .enter().append("path")
        .attr("class", "country")
        .attr("d", path)
        .attr("fill", "#ccc");

    updateMap();
}).catch((err) => {
    console.error("Map load error:", err);
    showStatus("Error loading map data.", true);
});
