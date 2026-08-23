import React, { useState, useEffect } from 'react';
import {
  ComposableMap,
  Geographies,
  Geography,
  ZoomableGroup,
  Sphere,
  Graticule
} from 'react-simple-maps';
import { scaleThreshold } from 'd3-scale';

// TopoJSON for world map
const geoUrl = "https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json";

// Dark mode friendly color scale for debt
// Domain: <50%, 50-100%, 100-150%, 150-200%, >200%
const colorScale = scaleThreshold()
  .domain([50, 100, 150, 200])
  .range([
    "#06b6d4", // Cyan (Low debt)
    "#10b981", // Emerald
    "#f59e0b", // Amber
    "#ef4444", // Red
    "#831843"  // Deep pink/red (Very high debt)
  ]);

const WorldMap = ({ data, setTooltipContent }) => {
  // Convert array data to map for fast lookup
  // data format: [{ country: "United States", value: 120.5 }, ...]
  const [dataMap, setDataMap] = useState({});

  useEffect(() => {
    if (!data) return;
    const map = {};
    data.forEach(d => {
      map[d.country] = d.value;
    });
    setDataMap(map);
  }, [data]);

  return (
    <div style={{ width: '100%', height: '100%', position: 'relative' }}>
      <ComposableMap
        projectionConfig={{ scale: 140 }}
        style={{ width: "100%", height: "100%" }}
      >
        <ZoomableGroup center={[0, 0]} zoom={1} maxZoom={5}>
          <Sphere stroke="var(--border-glass)" strokeWidth={0.5} />
          <Graticule stroke="var(--border-subtle)" strokeWidth={0.5} />
          
          <Geographies geography={geoUrl}>
            {({ geographies }) =>
              geographies.map((geo) => {
                const countryName = geo.properties.name;
                const value = dataMap[countryName];
                
                return (
                  <Geography
                    key={geo.rsmKey}
                    geography={geo}
                    onMouseEnter={() => {
                      setTooltipContent({
                        name: countryName,
                        value: value !== undefined ? `${value.toFixed(1)}%` : "No data"
                      });
                    }}
                    onMouseLeave={() => {
                      setTooltipContent(null);
                    }}
                    style={{
                      default: {
                        fill: value !== undefined ? colorScale(value) : "var(--bg-tertiary)",
                        stroke: "var(--bg-primary)",
                        strokeWidth: 0.5,
                        outline: "none",
                        transition: "all 250ms"
                      },
                      hover: {
                        fill: value !== undefined ? colorScale(value) : "var(--bg-tertiary)",
                        stroke: "#fff",
                        strokeWidth: 1.5,
                        outline: "none",
                        filter: value !== undefined ? "brightness(1.2)" : "none"
                      },
                      pressed: {
                        fill: value !== undefined ? colorScale(value) : "var(--bg-tertiary)",
                        outline: "none"
                      }
                    }}
                  />
                );
              })
            }
          </Geographies>
        </ZoomableGroup>
      </ComposableMap>
      
      {/* Legend */}
      <div style={{
        position: 'absolute',
        bottom: '20px',
        left: '20px',
        background: 'var(--bg-glass)',
        padding: '12px',
        borderRadius: 'var(--radius-sm)',
        border: '1px solid var(--border-glass)',
        backdropFilter: 'blur(10px)',
        fontSize: '0.8rem'
      }}>
        <div style={{ fontWeight: 600, marginBottom: '8px' }}>Debt-to-GDP Ratio</div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
          {[
            { label: '< 50%', color: "#06b6d4" },
            { label: '50% - 100%', color: "#10b981" },
            { label: '100% - 150%', color: "#f59e0b" },
            { label: '150% - 200%', color: "#ef4444" },
            { label: '> 200%', color: "#831843" }
          ].map((item, i) => (
            <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <div style={{ width: '12px', height: '12px', borderRadius: '2px', background: item.color }} />
              <span style={{ color: 'var(--text-secondary)' }}>{item.label}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default WorldMap;
