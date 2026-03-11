<template>
  <section class="visual-page">
    <div class="visual-top" :style="{ flexBasis: `${topPanelHeight}%` }">
      <div ref="mapContainer" class="visual-map"></div>
      <div v-if="!mapReady" class="visual-map-empty">请输入设置中的 Mapbox 地图 Key 以启用可视化。</div>
    </div>

    <div class="resize-handle">
      <span>上下栏高度：{{ topPanelHeight }}%</span>
      <input v-model="topPanelHeight" type="range" min="30" max="80" />
    </div>

    <div class="visual-bottom">
      <div class="dataset-toolbar">
        <button class="secondary" type="button" @click="addDataset">+ 添加数据集</button>
        <label class="secondary upload-btn">
          上传文件
          <input type="file" accept=".geojson,.json,.csv" @change="handleFileUpload" />
        </label>
        <button class="secondary" type="button" @click="showPaste = !showPaste">粘贴数据</button>
        <button class="secondary" type="button" @click="activateDrawPoint">地图绘制点</button>
      </div>

      <div v-if="showPaste" class="paste-box">
        <textarea
          v-model="pasteInput"
          rows="4"
          placeholder="支持粘贴 geojson / csv / wkt (POINT, LINESTRING, POLYGON, MULTIPOLYGON)"
        />
        <button class="primary" type="button" @click="handlePasteImport">解析并导入</button>
      </div>

      <div class="dataset-tabs" role="tablist">
        <button
          v-for="dataset in datasets"
          :key="dataset.id"
          :class="['mode-button', { active: dataset.id === activeDatasetId }]"
          type="button"
          @click="activeDatasetId = dataset.id"
        >
          {{ dataset.name }} ({{ dataset.rows.length }})
        </button>
      </div>

      <div v-if="activeDataset" class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>GID</th>
              <th>GEOMETRY</th>
              <th v-for="col in activeDataset.extraColumns" :key="col">{{ col }}</th>
              <th>定位</th>
              <th>删除</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in activeDataset.rows" :key="row.gid">
              <td>{{ row.gid }}</td>
              <td>
                <span class="geometry-badge">{{ row.geometryType }}</span>
              </td>
              <td v-for="col in activeDataset.extraColumns" :key="col">{{ row.properties[col] ?? '-' }}</td>
              <td><button class="secondary small" type="button" @click="locateFeature(row.feature)">定位</button></td>
              <td><button class="secondary small" type="button" @click="removeFeature(row.gid)">删除</button></td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import mapboxgl from "mapbox-gl";

const props = defineProps({
  mapApiKey: { type: String, default: "" },
});

const topPanelHeight = ref(58);
const mapContainer = ref(null);
const mapReady = ref(false);
const showPaste = ref(false);
const pasteInput = ref("");

const datasets = ref([{ id: 1, name: "数据集 1", rows: [], features: [], extraColumns: [] }]);
const activeDatasetId = ref(1);

let map = null;
let drawPointMode = false;

const activeDataset = computed(() => datasets.value.find((d) => d.id === activeDatasetId.value));

const ensureMap = () => {
  if (!props.mapApiKey || !mapContainer.value || map) return;
  mapboxgl.accessToken = props.mapApiKey;
  map = new mapboxgl.Map({
    container: mapContainer.value,
    style: "mapbox://styles/mapbox/streets-v12",
    center: [116.397, 39.908],
    zoom: 4,
  });
  map.on("load", () => {
    mapReady.value = true;
    map.addSource("viz-source", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
    map.addLayer({
      id: "viz-fill",
      type: "fill",
      source: "viz-source",
      filter: ["==", ["geometry-type"], "Polygon"],
      paint: { "fill-color": "#2563eb", "fill-opacity": 0.2 },
    });
    map.addLayer({
      id: "viz-line",
      type: "line",
      source: "viz-source",
      filter: ["==", ["geometry-type"], "LineString"],
      paint: { "line-color": "#0ea5e9", "line-width": 3 },
    });
    map.addLayer({
      id: "viz-point",
      type: "circle",
      source: "viz-source",
      filter: ["==", ["geometry-type"], "Point"],
      paint: { "circle-color": "#f97316", "circle-radius": 6 },
    });
    map.on("click", (event) => {
      if (!drawPointMode) return;
      appendRowsFromFeatures([
        {
          type: "Feature",
          geometry: { type: "Point", coordinates: [event.lngLat.lng, event.lngLat.lat] },
          properties: {},
        },
      ]);
      drawPointMode = false;
    });
    refreshSource();
  });
};

const parseWkt = (text) => {
  const raw = text.trim();
  const upper = raw.toUpperCase();
  const extractPairs = (body) =>
    body
      .split(",")
      .map((pair) => pair.trim().split(/\s+/).map(Number))
      .filter((pair) => pair.length >= 2 && pair.every((v) => Number.isFinite(v)))
      .map((pair) => [pair[0], pair[1]]);

  if (upper.startsWith("POINT")) {
    const m = raw.match(/POINT\s*\(([^)]+)\)/i);
    if (!m) return null;
    const pair = m[1].trim().split(/\s+/).map(Number);
    if (pair.length < 2) return null;
    return { type: "Point", coordinates: [pair[0], pair[1]] };
  }
  if (upper.startsWith("LINESTRING")) {
    const m = raw.match(/LINESTRING\s*\(([^)]+)\)/i);
    if (!m) return null;
    return { type: "LineString", coordinates: extractPairs(m[1]) };
  }
  if (upper.startsWith("POLYGON")) {
    const m = raw.match(/POLYGON\s*\(\((.+)\)\)/i);
    if (!m) return null;
    return { type: "Polygon", coordinates: [extractPairs(m[1])] };
  }
  if (upper.startsWith("MULTIPOLYGON")) {
    const m = raw.match(/MULTIPOLYGON\s*\(\((.+)\)\)/i);
    if (!m) return null;
    const polygons = m[1]
      .split(/\)\s*\),\s*\(\(/)
      .map((segment) => [extractPairs(segment.replaceAll("(", "").replaceAll(")", ""))]);
    return { type: "MultiPolygon", coordinates: polygons };
  }
  return null;
};

const parseCsv = (text) => {
  const normalizedText = text.includes("\n") ? text.replace(/\\r\\n/g, "\n").replace(/\\n/g, "\n") : text;
  const lines = normalizedText.split(/\r?\n/).filter(Boolean);
  if (lines.length < 2) return [];

  const splitCsvLine = (line) => {
    const values = [];
    let current = "";
    let inQuotes = false;

    for (let i = 0; i < line.length; i += 1) {
      const char = line[i];
      const next = line[i + 1];

      if (char === '"') {
        if (inQuotes && next === '"') {
          current += '"';
          i += 1;
        } else {
          inQuotes = !inQuotes;
        }
        continue;
      }

      if (char === "," && !inQuotes) {
        values.push(current.trim());
        current = "";
        continue;
      }

      current += char;
    }

    values.push(current.trim());
    return values;
  };

  const headers = splitCsvLine(lines[0]).map((h) => h.trim());
  return lines.slice(1).map((line) => {
    const values = splitCsvLine(line);
    const row = {};
    headers.forEach((h, i) => {
      row[h] = values[i]?.trim() ?? "";
    });
    return row;
  });
};

const parseCoordinatePairsString = (value) => {
  if (typeof value !== "string" || !value.trim()) return null;
  const pairs = value
    .split(",")
    .map((segment) => segment.trim().split(/\s+/).map(Number))
    .filter((pair) => pair.length >= 2 && Number.isFinite(pair[0]) && Number.isFinite(pair[1]))
    .map((pair) => [pair[0], pair[1]]);

  if (pairs.length < 2) return null;
  if (pairs.length >= 4) {
    const first = pairs[0];
    const last = pairs[pairs.length - 1];
    const isClosed = first[0] === last[0] && first[1] === last[1];
    return {
      type: "Polygon",
      coordinates: [isClosed ? pairs : [...pairs, first]],
    };
  }
  return { type: "LineString", coordinates: pairs };
};

const detectGeometryFromRow = (row) => {
  const keys = Object.keys(row);
  const lowerKeyMap = Object.fromEntries(keys.map((k) => [k.toLowerCase(), k]));
  const wktKey = Object.keys(lowerKeyMap).find((k) => ["wkt", "geometry", "geom", "the_geom"].some((f) => k.includes(f)));
  if (wktKey && typeof row[lowerKeyMap[wktKey]] === "string") {
    const maybe = parseWkt(row[lowerKeyMap[wktKey]]);
    if (maybe) return maybe;
    try {
      const geometry = JSON.parse(row[lowerKeyMap[wktKey]]);
      if (geometry?.type && geometry?.coordinates) return geometry;
    } catch {
      // ignore
    }
  }

  const lngKey = Object.keys(lowerKeyMap).find((k) => ["lng", "lon", "long", "longitude", "x"].includes(k));
  const latKey = Object.keys(lowerKeyMap).find((k) => ["lat", "latitude", "y"].includes(k));
  if (lngKey && latKey) {
    const lng = Number(row[lowerKeyMap[lngKey]]);
    const lat = Number(row[lowerKeyMap[latKey]]);
    if (Number.isFinite(lng) && Number.isFinite(lat)) {
      return { type: "Point", coordinates: [lng, lat] };
    }
  }

  const coordsKey = Object.keys(lowerKeyMap).find((k) => ["coords", "coordinates", "path", "boundary"].some((name) => k.includes(name)));
  if (coordsKey) {
    const coordValue = row[lowerKeyMap[coordsKey]];
    try {
      const parsed = JSON.parse(coordValue);
      if (Array.isArray(parsed)) {
        if (typeof parsed[0] === "number") return { type: "Point", coordinates: parsed };
        if (Array.isArray(parsed[0]) && typeof parsed[0][0] === "number") return { type: "LineString", coordinates: parsed };
        if (Array.isArray(parsed[0]) && Array.isArray(parsed[0][0])) return { type: "Polygon", coordinates: parsed };
      }
    } catch {
      const parsedPairs = parseCoordinatePairsString(coordValue);
      if (parsedPairs) return parsedPairs;
    }
  }
  return null;
};

const parseContentToFeatures = (text) => {
  const trimmed = text.trim();
  if (!trimmed) return [];
  try {
    const json = JSON.parse(trimmed);
    if (json.type === "FeatureCollection") return json.features || [];
    if (json.type === "Feature") return [json];
    if (json.type && json.coordinates) return [{ type: "Feature", geometry: json, properties: {} }];
  } catch {
    // ignore
  }

  if (/^(POINT|LINESTRING|POLYGON|MULTIPOLYGON)/i.test(trimmed)) {
    const geometries = trimmed
      .split(/\r?\n/)
      .map((line) => parseWkt(line))
      .filter(Boolean);
    return geometries.map((geometry) => ({ type: "Feature", geometry, properties: {} }));
  }

  const csvRows = parseCsv(trimmed);
  return csvRows
    .map((row) => {
      const geometry = detectGeometryFromRow(row);
      if (!geometry) return null;
      return { type: "Feature", geometry, properties: row };
    })
    .filter(Boolean);
};

const appendRowsFromFeatures = (features) => {
  if (!activeDataset.value) return;
  const start = activeDataset.value.rows.length + 1;
  const nextRows = features.map((feature, index) => ({
    gid: start + index,
    geometryType: feature.geometry?.type || "Unknown",
    properties: feature.properties || {},
    feature,
  }));
  const extraColumns = new Set(activeDataset.value.extraColumns);
  nextRows.forEach((row) => {
    Object.keys(row.properties || {}).forEach((key) => {
      if (!["gid", "geometry"].includes(key.toLowerCase())) {
        extraColumns.add(key);
      }
    });
  });
  activeDataset.value.rows.push(...nextRows);
  activeDataset.value.features.push(...features);
  activeDataset.value.extraColumns = Array.from(extraColumns);
  refreshSource();
};

const refreshSource = () => {
  if (!mapReady.value || !map) return;
  const allFeatures = datasets.value.flatMap((dataset) => dataset.rows.map((row) => row.feature));
  map.getSource("viz-source")?.setData({ type: "FeatureCollection", features: allFeatures });
};

const addDataset = () => {
  const nextId = Math.max(...datasets.value.map((dataset) => dataset.id)) + 1;
  datasets.value.push({ id: nextId, name: `数据集 ${nextId}`, rows: [], features: [], extraColumns: [] });
  activeDatasetId.value = nextId;
};

const handleFileUpload = async (event) => {
  const file = event.target.files?.[0];
  if (!file) return;
  const text = await file.text();
  appendRowsFromFeatures(parseContentToFeatures(text));
  event.target.value = "";
};

const handlePasteImport = () => {
  appendRowsFromFeatures(parseContentToFeatures(pasteInput.value));
  pasteInput.value = "";
};

const locateFeature = (feature) => {
  if (!mapReady.value || !feature?.geometry) return;
  const g = feature.geometry;
  if (g.type === "Point") {
    map.flyTo({ center: g.coordinates, zoom: 12 });
    return;
  }
  const coords = JSON.stringify(g.coordinates).match(/-?\d+(\.\d+)?/g)?.map(Number) || [];
  if (coords.length >= 4) {
    const lngs = coords.filter((_, idx) => idx % 2 === 0);
    const lats = coords.filter((_, idx) => idx % 2 === 1);
    map.fitBounds(
      [
        [Math.min(...lngs), Math.min(...lats)],
        [Math.max(...lngs), Math.max(...lats)],
      ],
      { padding: 40 }
    );
  }
};

const removeFeature = (gid) => {
  if (!activeDataset.value) return;
  activeDataset.value.rows = activeDataset.value.rows.filter((row) => row.gid !== gid);
  refreshSource();
};

const activateDrawPoint = () => {
  drawPointMode = true;
};

onMounted(() => {
  ensureMap();
});

watch(
  () => props.mapApiKey,
  () => {
    ensureMap();
  }
);

onBeforeUnmount(() => {
  if (map) map.remove();
});
</script>
