<template>
  <section class="visual-page">
    <div class="visual-top">
      <div ref="mapContainer" class="visual-map"></div>
      <div v-if="!mapReady" class="visual-map-empty">请输入设置中的 Mapbox 地图 Key 以启用可视化。</div>
      <div v-if="isProcessing" class="visual-map-mask">
        <div class="mask-card">正在处理数据并加载地图要素...</div>
      </div>
    </div>

    <div class="visual-bottom">
      <div class="dataset-tabs" role="tablist">
        <div v-for="dataset in datasets" :key="dataset.id" class="dataset-tab-item">
          <button
            :class="['mode-button', { active: dataset.id === activeDatasetId }]"
            type="button"
            @click="activeDatasetId = dataset.id"
          >
            {{ dataset.name }} ({{ dataset.rows.length }})
          </button>
          <button
            v-if="dataset.id === activeDatasetId"
            class="icon-button dataset-delete"
            type="button"
            :disabled="datasets.length <= 1"
            @click="removeDataset(dataset.id)"
            aria-label="删除当前数据集"
          >
            ×
          </button>
        </div>
        <button class="secondary add-dataset" type="button" @click="addDataset">+ 添加数据集</button>
      </div>

      <div class="dataset-toolbar">
        <label class="secondary action-button upload-btn">
          上传文件
          <input type="file" accept=".geojson,.json,.csv" @change="handleFileUpload" :disabled="isProcessing" />
        </label>
        <button class="secondary action-button" type="button" @click="showPaste = !showPaste" :disabled="isProcessing">粘贴数据</button>
        <button class="secondary" type="button" @click="activateDrawPoint" :disabled="isProcessing">地图绘制点</button>
      </div>

      <div v-if="showPaste" class="paste-box">
        <textarea
          v-model="pasteInput"
          rows="4"
          placeholder="支持粘贴 geojson / csv / wkt (POINT, LINESTRING, POLYGON, MULTIPOLYGON)"
        />
        <button class="primary" type="button" @click="handlePasteImport" :disabled="isProcessing">解析并导入</button>
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
            <tr
              v-for="row in activeDataset.rows"
              :key="row.featureKey"
              :ref="bindRowRef(row.featureKey)"
              :class="{ 'table-row-active': selectedFeatureKey === row.featureKey }"
            >
              <td>{{ row.gid }}</td>
              <td>
                <span class="geometry-badge">{{ row.geometryType }}</span>
              </td>
              <td v-for="col in activeDataset.extraColumns" :key="col">{{ row.properties[col] ?? '-' }}</td>
              <td><button class="secondary small" type="button" @click="locateFeature(row)">定位</button></td>
              <td><button class="secondary small" type="button" @click="removeFeature(row.featureKey)">删除</button></td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import mapboxgl from "mapbox-gl";

const props = defineProps({
  mapApiKey: { type: String, default: "" },
});

const mapContainer = ref(null);
const mapReady = ref(false);
const showPaste = ref(false);
const pasteInput = ref("");
const isProcessing = ref(false);

const datasets = ref([{ id: 1, name: "数据集 1", rows: [], extraColumns: [] }]);
const activeDatasetId = ref(1);
const selectedFeatureKey = ref("");

const rowElementMap = new Map();
let featureCounter = 1;
let map = null;
let drawPointMode = false;
let mapPopup = null;
const pointLayerPrefix = "viz-dataset-point-layer-";
const pointSourcePrefix = "viz-dataset-point-source-";

const activeDataset = computed(() => datasets.value.find((d) => d.id === activeDatasetId.value));

const bindRowRef = (featureKey) => (el) => {
  if (el) rowElementMap.set(featureKey, el);
  else rowElementMap.delete(featureKey);
};

const highlightFilter = (geometryType) => [
  "all",
  ["==", ["geometry-type"], geometryType],
  ["==", ["coalesce", ["get", "__featureKey"], ""], selectedFeatureKey.value || ""],
];

const syncHighlightFilters = () => {
  if (!mapReady.value || !map) return;
  const configs = [
    ["viz-highlight-fill", "Polygon"],
    ["viz-highlight-polygon-outline", "Polygon"],
    ["viz-highlight-line", "LineString"],
    ["viz-highlight-point", "Point"],
  ];
  configs.forEach(([layerId, geometryType]) => {
    if (map.getLayer(layerId)) {
      map.setFilter(layerId, highlightFilter(geometryType));
    }
  });
};

const clearSelection = () => {
  selectedFeatureKey.value = "";
  syncHighlightFilters();
  if (mapPopup) {
    mapPopup.remove();
    mapPopup = null;
  }
};

const getDatasetPointLayerId = (datasetId) => `${pointLayerPrefix}${datasetId}`;
const getDatasetPointSourceId = (datasetId) => `${pointSourcePrefix}${datasetId}`;

const getInteractiveLayerIds = () => [
  "viz-fill",
  "viz-polygon-outline",
  "viz-line",
  ...datasets.value.map((dataset) => getDatasetPointLayerId(dataset.id)),
  "viz-highlight-fill",
  "viz-highlight-polygon-outline",
  "viz-highlight-line",
  "viz-highlight-point",
].filter((layerId) => map?.getLayer(layerId));


const ensureDatasetPointLayer = (datasetId) => {
  if (!mapReady.value || !map) return;
  const sourceId = getDatasetPointSourceId(datasetId);
  const layerId = getDatasetPointLayerId(datasetId);

  if (!map.getSource(sourceId)) {
    map.addSource(sourceId, {
      type: "geojson",
      data: { type: "FeatureCollection", features: [] },
    });
  }

  if (!map.getLayer(layerId)) {
    map.addLayer({
      id: layerId,
      type: "circle",
      source: sourceId,
      paint: {
        "circle-color": "#f97316",
        "circle-radius": 6,
        "circle-stroke-color": "#fff",
        "circle-stroke-width": 1,
      },
    });
  }

};

const removeDatasetPointLayer = (datasetId) => {
  if (!map) return;
  const sourceId = getDatasetPointSourceId(datasetId);
  const layerId = getDatasetPointLayerId(datasetId);
  if (map.getLayer(layerId)) map.removeLayer(layerId);
  if (map.getSource(sourceId)) map.removeSource(sourceId);
};

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
      id: "viz-polygon-outline",
      type: "line",
      source: "viz-source",
      filter: ["==", ["geometry-type"], "Polygon"],
      paint: { "line-color": "#1d4ed8", "line-width": 1 },
    });
    map.addLayer({
      id: "viz-line",
      type: "line",
      source: "viz-source",
      filter: ["==", ["geometry-type"], "LineString"],
      paint: { "line-color": "#0ea5e9", "line-width": 3 },
    });
    map.addLayer({
      id: "viz-highlight-fill",
      type: "fill",
      source: "viz-source",
      filter: highlightFilter("Polygon"),
      paint: { "fill-color": "#f59e0b", "fill-opacity": 0.35 },
    });
    map.addLayer({
      id: "viz-highlight-polygon-outline",
      type: "line",
      source: "viz-source",
      filter: highlightFilter("Polygon"),
      paint: { "line-color": "#f59e0b", "line-width": 3 },
    });
    map.addLayer({
      id: "viz-highlight-line",
      type: "line",
      source: "viz-source",
      filter: highlightFilter("LineString"),
      paint: { "line-color": "#f59e0b", "line-width": 5 },
    });
    map.addLayer({
      id: "viz-highlight-point",
      type: "circle",
      source: "viz-source",
      filter: highlightFilter("Point"),
      paint: {
        "circle-color": "#f59e0b",
        "circle-radius": 8,
        "circle-stroke-color": "#fff",
        "circle-stroke-width": 2,
      },
    });

    map.on("click", (event) => {
      if (drawPointMode) {
        appendRowsFromFeatures([
          {
            type: "Feature",
            geometry: { type: "Point", coordinates: [event.lngLat.lng, event.lngLat.lat] },
            properties: {},
          },
        ]);
        drawPointMode = false;
        return;
      }
      const hits = map.queryRenderedFeatures(event.point, { layers: getInteractiveLayerIds() });
      if (!hits.length) return clearSelection();
      selectFeatureFromMap(hits[0], event.lngLat);
    });

    map.on("mousemove", (event) => {
      const hits = map.queryRenderedFeatures(event.point, { layers: getInteractiveLayerIds() });
      map.getCanvas().style.cursor = hits.length ? "pointer" : "";
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
      .filter((pair) => pair.length >= 2 && pair.every((value) => Number.isFinite(value)))
      .map((pair) => [pair[0], pair[1]]);

  if (upper.startsWith("POINT")) {
    const match = raw.match(/POINT\s*\(([^)]+)\)/i);
    if (!match) return null;
    const pair = match[1].trim().split(/\s+/).map(Number);
    if (pair.length < 2) return null;
    return { type: "Point", coordinates: [pair[0], pair[1]] };
  }
  if (upper.startsWith("LINESTRING")) {
    const match = raw.match(/LINESTRING\s*\(([^)]+)\)/i);
    if (!match) return null;
    return { type: "LineString", coordinates: extractPairs(match[1]) };
  }
  if (upper.startsWith("POLYGON")) {
    const match = raw.match(/POLYGON\s*\(\((.+)\)\)/i);
    if (!match) return null;
    return { type: "Polygon", coordinates: [extractPairs(match[1])] };
  }
  if (upper.startsWith("MULTIPOLYGON")) {
    const match = raw.match(/MULTIPOLYGON\s*\(\((.+)\)\)/i);
    if (!match) return null;
    const polygons = match[1]
      .split(/\)\s*\),\s*\(\(/)
      .map((segment) => [extractPairs(segment.replaceAll("(", "").replaceAll(")", ""))]);
    return { type: "MultiPolygon", coordinates: polygons };
  }
  return null;
};

const parseCsv = (text) => {
  const normalizedText = text.includes("\\n") ? text.replace(/\\r\\n/g, "\n").replace(/\\n/g, "\n") : text;
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

  const headers = splitCsvLine(lines[0]).map((header) => header.trim());
  return lines.slice(1).map((line) => {
    const values = splitCsvLine(line);
    const row = {};
    headers.forEach((header, index) => {
      row[header] = values[index]?.trim() ?? "";
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
  const lowerKeyMap = Object.fromEntries(keys.map((key) => [key.toLowerCase(), key]));

  const wktKey = Object.keys(lowerKeyMap).find((key) =>
    ["wkt", "geometry", "geom", "the_geom"].some((field) => key.includes(field))
  );
  if (wktKey && typeof row[lowerKeyMap[wktKey]] === "string") {
    const maybeGeometry = parseWkt(row[lowerKeyMap[wktKey]]);
    if (maybeGeometry) return maybeGeometry;
    try {
      const geometry = JSON.parse(row[lowerKeyMap[wktKey]]);
      if (geometry?.type && geometry?.coordinates) return geometry;
    } catch {
      // ignore json parse error
    }
  }

  const lngKey = Object.keys(lowerKeyMap).find((key) => ["lng", "lon", "long", "longitude", "x"].includes(key));
  const latKey = Object.keys(lowerKeyMap).find((key) => ["lat", "latitude", "y"].includes(key));
  if (lngKey && latKey) {
    const lng = Number(row[lowerKeyMap[lngKey]]);
    const lat = Number(row[lowerKeyMap[latKey]]);
    if (Number.isFinite(lng) && Number.isFinite(lat)) {
      return { type: "Point", coordinates: [lng, lat] };
    }
  }

  const coordsKey = Object.keys(lowerKeyMap).find((key) =>
    ["coords", "coordinates", "path", "boundary"].some((field) => key.includes(field))
  );
  if (coordsKey) {
    const coordValue = row[lowerKeyMap[coordsKey]];
    try {
      const parsed = JSON.parse(coordValue);
      if (Array.isArray(parsed)) {
        if (typeof parsed[0] === "number") return { type: "Point", coordinates: parsed };
        if (Array.isArray(parsed[0]) && typeof parsed[0][0] === "number") {
          return { type: "LineString", coordinates: parsed };
        }
        if (Array.isArray(parsed[0]) && Array.isArray(parsed[0][0])) {
          return { type: "Polygon", coordinates: parsed };
        }
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
    // ignore json parse error
  }

  if (/^(POINT|LINESTRING|POLYGON|MULTIPOLYGON)/i.test(trimmed)) {
    return trimmed
      .split(/\r?\n/)
      .map((line) => parseWkt(line))
      .filter(Boolean)
      .map((geometry) => ({ type: "Feature", geometry, properties: {} }));
  }

  return parseCsv(trimmed)
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

  const nextRows = features.map((feature, index) => {
    const gid = start + index;
    const featureKey = `d${activeDataset.value.id}-f${featureCounter}`;
    featureCounter += 1;
    const normalizedFeature = {
      ...feature,
      properties: {
        ...(feature.properties || {}),
        __gid: gid,
        __datasetId: activeDataset.value.id,
        __featureKey: featureKey,
      },
    };

    return {
      gid,
      featureKey,
      geometryType: normalizedFeature.geometry?.type || "Unknown",
      properties: normalizedFeature.properties || {},
      feature: normalizedFeature,
    };
  });

  const extraColumns = new Set(activeDataset.value.extraColumns);
  nextRows.forEach((row) => {
    Object.keys(row.properties || {}).forEach((key) => {
      if (!key.toLowerCase().startsWith("__") && !["gid", "geometry"].includes(key.toLowerCase())) {
        extraColumns.add(key);
      }
    });
  });

  activeDataset.value.rows.push(...nextRows);
  activeDataset.value.extraColumns = Array.from(extraColumns);
  refreshSource();
};

const refreshSource = () => {
  if (!mapReady.value || !map) return;
  const allFeatures = datasets.value.flatMap((dataset) => dataset.rows.map((row) => row.feature));
  map.getSource("viz-source")?.setData({ type: "FeatureCollection", features: allFeatures });

  datasets.value.forEach((dataset) => {
    ensureDatasetPointLayer(dataset.id);
    const sourceId = getDatasetPointSourceId(dataset.id);
    const pointFeatures = dataset.rows
      .map((row) => row.feature)
      .filter((feature) => feature?.geometry?.type === "Point");
    map.getSource(sourceId)?.setData({ type: "FeatureCollection", features: pointFeatures });
  });
};

const addDataset = () => {
  const nextId = Math.max(...datasets.value.map((dataset) => dataset.id)) + 1;
  datasets.value.push({ id: nextId, name: `数据集 ${nextId}`, rows: [], extraColumns: [] });
  activeDatasetId.value = nextId;
};

const removeDataset = (datasetId) => {
  if (datasets.value.length <= 1) return;
  datasets.value = datasets.value.filter((dataset) => dataset.id !== datasetId);
  removeDatasetPointLayer(datasetId);
  if (activeDatasetId.value === datasetId) {
    activeDatasetId.value = datasets.value[0]?.id ?? 1;
  }
  clearSelection();
  refreshSource();
};

const waitForMapFlush = async () => {
  await nextTick();
  await new Promise((resolve) => {
    requestAnimationFrame(() => requestAnimationFrame(resolve));
  });
};

const importFeaturesWithMask = async (rawText) => {
  if (!rawText) return;
  isProcessing.value = true;
  try {
    const features = parseContentToFeatures(rawText);
    appendRowsFromFeatures(features);
    await waitForMapFlush();
  } finally {
    isProcessing.value = false;
  }
};

const handleFileUpload = async (event) => {
  const file = event.target.files?.[0];
  if (!file) return;
  const text = await file.text();
  await importFeaturesWithMask(text);
  event.target.value = "";
};

const handlePasteImport = async () => {
  await importFeaturesWithMask(pasteInput.value);
  pasteInput.value = "";
};

const extractBounds = (geometry) => {
  const values = JSON.stringify(geometry?.coordinates || [])
    .match(/-?\d+(\.\d+)?/g)
    ?.map(Number);
  if (!values || values.length < 2) return null;
  const lngs = values.filter((_, index) => index % 2 === 0);
  const lats = values.filter((_, index) => index % 2 === 1);
  if (!lngs.length || !lats.length) return null;
  return {
    minLng: Math.min(...lngs),
    minLat: Math.min(...lats),
    maxLng: Math.max(...lngs),
    maxLat: Math.max(...lats),
  };
};

const popupHtml = (properties = {}) => {
  const entries = Object.entries(properties).filter(([key]) => !key.startsWith("__"));
  if (!entries.length) return "<div style='font-size:12px;color:#64748b'>无扩展属性</div>";
  return `<div style='min-width:180px'>${entries
    .map(
      ([key, value]) =>
        `<div style='display:flex;gap:8px;font-size:12px;line-height:1.5'><strong style='min-width:80px'>${key}</strong><span>${
          value === "" || value == null ? "-" : String(value)
        }</span></div>`
    )
    .join("")}</div>`;
};

const focusRow = async (featureKey) => {
  await nextTick();
  const el = rowElementMap.get(featureKey);
  if (el) {
    el.scrollIntoView({ behavior: "smooth", block: "center" });
  }
};

const selectFeatureByMeta = async ({ datasetId, featureKey, lngLat, properties }) => {
  if (!featureKey) return;
  if (datasetId && activeDatasetId.value !== datasetId) {
    activeDatasetId.value = datasetId;
    await nextTick();
  }
  selectedFeatureKey.value = featureKey;
  syncHighlightFilters();
  await focusRow(featureKey);

  if (mapPopup) {
    mapPopup.remove();
    mapPopup = null;
  }
  if (lngLat && map) {
    mapPopup = new mapboxgl.Popup({ closeButton: false, offset: 14 })
      .setLngLat(lngLat)
      .setHTML(popupHtml(properties))
      .addTo(map);
  }
};

const selectFeatureFromMap = async (feature, lngLat) => {
  const datasetId = Number(feature?.properties?.__datasetId);
  const featureKey = feature?.properties?.__featureKey || "";
  await selectFeatureByMeta({ datasetId, featureKey, lngLat, properties: feature?.properties || {} });
};

const locateFeature = async (row) => {
  if (!mapReady.value || !row?.feature?.geometry) return;
  const geometry = row.feature.geometry;

  if (geometry.type === "Point") {
    map.flyTo({ center: geometry.coordinates, zoom: 12 });
    await selectFeatureByMeta({
      datasetId: activeDatasetId.value,
      featureKey: row.featureKey,
      lngLat: { lng: geometry.coordinates[0], lat: geometry.coordinates[1] },
      properties: row.properties,
    });
    return;
  }

  const bounds = extractBounds(geometry);
  if (bounds) {
    map.fitBounds(
      [
        [bounds.minLng, bounds.minLat],
        [bounds.maxLng, bounds.maxLat],
      ],
      { padding: 40 }
    );
    await selectFeatureByMeta({
      datasetId: activeDatasetId.value,
      featureKey: row.featureKey,
      lngLat: { lng: (bounds.minLng + bounds.maxLng) / 2, lat: (bounds.minLat + bounds.maxLat) / 2 },
      properties: row.properties,
    });
  }
};

const removeFeature = (featureKey) => {
  if (!activeDataset.value) return;
  activeDataset.value.rows = activeDataset.value.rows.filter((row) => row.featureKey !== featureKey);
  if (selectedFeatureKey.value === featureKey) {
    clearSelection();
  }
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

watch(selectedFeatureKey, () => {
  syncHighlightFilters();
});

watch(activeDatasetId, () => {
  clearSelection();
});

onBeforeUnmount(() => {
  if (mapPopup) {
    mapPopup.remove();
    mapPopup = null;
  }
  if (map) map.remove();
});
</script>
