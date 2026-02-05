<template>
  <div class="app-shell">
    <header class="app-header">
      <div>
        <p class="eyebrow">批量地理编码工具</p>
        <h1>Excel 地址批量转经纬度</h1>
        <p class="subtext">
          上传 Excel、指定地址列并选择地图服务商，自动追加经纬度到表格末尾列。
        </p>
      </div>
      <button class="ghost" @click="fillMockData">一键填写 Mock 数据</button>
    </header>

    <main class="layout">
      <section class="panel">
        <div class="card">
          <h2>1. 上传 Excel</h2>
          <input type="file" accept=".xlsx,.xls" @change="handleFileChange" />
          <p v-if="fileName" class="hint">已加载：{{ fileName }}</p>
        </div>

        <div class="card">
          <h2>2. 配置解析</h2>
          <label class="field">
            <span>地址列名</span>
            <select v-model="columnName">
              <option value="" disabled>请选择列名</option>
              <option v-for="header in headers" :key="header" :value="header">
                {{ header }}
              </option>
            </select>
          </label>
          <label class="field">
            <span>地图服务商</span>
            <select v-model="provider">
              <option value="mapbox">Mapbox</option>
              <option value="here">HERE</option>
            </select>
          </label>
          <label class="field">
            <span>API Key</span>
            <input v-model="providerApiKey" type="password" placeholder="输入地理编码 API Key" />
          </label>
          <div class="actions">
            <button class="primary" :disabled="!canStart" @click="startGeocode">
              开始转换
            </button>
            <button class="secondary" :disabled="!canDownload" @click="downloadExcel">
              下载结果
            </button>
          </div>
        </div>

        <div class="card">
          <h2>3. 进度</h2>
          <div class="progress">
            <div class="progress-row">
              <span>当前地址</span>
              <strong>{{ progress.current || "-" }}</strong>
            </div>
            <div class="progress-row">
              <span>已请求数量</span>
              <strong>{{ progress.processed }}</strong>
            </div>
            <div class="progress-row">
              <span>待请求数量</span>
              <strong>{{ progress.pending }}</strong>
            </div>
            <div class="progress-bar">
              <div class="progress-fill" :style="{ width: progress.percent + '%' }"></div>
            </div>
          </div>
        </div>

        <div class="card">
          <h2>4. 日志</h2>
          <div class="log" v-if="logs.length">
            <div v-for="(item, index) in logs" :key="index" class="log-item">
              <div class="log-title">
                <strong>{{ item.address }}</strong>
                <span class="tag">{{ item.type }}</span>
              </div>
              <div class="log-body">
                <p><span>请求</span> {{ item.request }}</p>
                <p><span>返回</span> {{ item.response }}</p>
              </div>
            </div>
          </div>
          <p v-else class="hint">暂无错误日志。</p>
        </div>
      </section>

      <section class="map-panel">
        <div class="map-wrapper">
          <div ref="mapContainer" class="map"></div>
          <div class="map-config">
            <h3>地图配置</h3>
            <label>
              <span>Mapbox API Key</span>
              <input v-model="mapApiKey" type="password" placeholder="用于地图展示" />
            </label>
            <button class="secondary" @click="applyMapKey">应用</button>
          </div>
          <div v-if="!mapReady" class="map-empty">
            <p>请在右下角填写 Mapbox API Key 以加载地图。</p>
          </div>
        </div>
      </section>
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import mapboxgl from "mapbox-gl";
import * as XLSX from "xlsx";

const headers = ref([]);
const rows = ref([]);
const fileName = ref("");
const columnName = ref("");
const provider = ref("mapbox");
const providerApiKey = ref("");
const mapApiKey = ref("");
const logs = ref([]);
const cache = new Map();
const mapContainer = ref(null);
const geocodeState = reactive({
  total: 0,
  processed: 0,
  current: "",
  running: false,
});
const points = ref([]);

let mapInstance = null;
let mapMarkers = [];

const canStart = computed(() => {
  return (
    !geocodeState.running &&
    rows.value.length > 0 &&
    columnName.value &&
    providerApiKey.value
  );
});

const canDownload = computed(() => rows.value.length > 0 && points.value.length > 0);

const progress = computed(() => {
  const percent = geocodeState.total
    ? Math.round((geocodeState.processed / geocodeState.total) * 100)
    : 0;
  return {
    current: geocodeState.current,
    processed: geocodeState.processed,
    pending: Math.max(geocodeState.total - geocodeState.processed, 0),
    percent,
  };
});

const mapReady = computed(() => Boolean(mapInstance));

const resetProgress = () => {
  geocodeState.total = 0;
  geocodeState.processed = 0;
  geocodeState.current = "";
  geocodeState.running = false;
};

const handleFileChange = (event) => {
  const file = event.target.files?.[0];
  if (!file) return;
  fileName.value = file.name;

  const reader = new FileReader();
  reader.onload = (e) => {
    const data = new Uint8Array(e.target.result);
    const workbook = XLSX.read(data, { type: "array" });
    const sheetName = workbook.SheetNames[0];
    const sheet = workbook.Sheets[sheetName];
    const sheetRows = XLSX.utils.sheet_to_json(sheet, { header: 1, raw: false });
    if (sheetRows.length === 0) return;
    headers.value = sheetRows[0].filter(Boolean).map((header) => String(header));
    const bodyRows = sheetRows.slice(1).map((row) => {
      const record = {};
      headers.value.forEach((header, index) => {
        record[header] = row[index] ?? "";
      });
      return record;
    });
    rows.value = bodyRows;
    columnName.value = headers.value[0] || "";
    logs.value = [];
    points.value = [];
    cache.clear();
    resetProgress();
  };
  reader.readAsArrayBuffer(file);
};

const fillMockData = () => {
  headers.value = ["地址", "客户"];
  rows.value = [
    { 地址: "上海市浦东新区世纪大道100号", 客户: "星云科技" },
    { 地址: "北京市朝阳区三里屯路11号", 客户: "联动创新" },
    { 地址: "深圳市南山区科技园科苑路15号", 客户: "海风智能" },
    { 地址: "杭州市西湖区文三路90号", 客户: "知行数据" },
    { 地址: "成都市武侯区人民南路四段27号", 客户: "西蜀科技" },
    { 地址: "上海市浦东新区世纪大道100号", 客户: "星云科技" }
  ];
  columnName.value = "地址";
  fileName.value = "mock.xlsx";
  logs.value = [];
  points.value = [];
  cache.clear();
  resetProgress();
};

const buildAddressMap = () => {
  const addressMap = new Map();
  rows.value.forEach((row, index) => {
    const address = String(row[columnName.value] ?? "").trim();
    if (!address) return;
    if (!addressMap.has(address)) {
      addressMap.set(address, []);
    }
    addressMap.get(address).push(index);
  });
  return addressMap;
};

const startGeocode = async () => {
  if (!canStart.value) return;
  logs.value = [];
  points.value = [];
  geocodeState.running = true;
  geocodeState.processed = 0;
  geocodeState.current = "";

  const addressMap = buildAddressMap();
  geocodeState.total = addressMap.size;

  for (const [address, indices] of addressMap.entries()) {
    geocodeState.current = address;
    let result = cache.get(address);
    if (!result) {
      result = await geocodeAddress(address);
      cache.set(address, result);
    }
    geocodeState.processed += 1;

    if (result.success) {
      indices.forEach((rowIndex) => {
        rows.value[rowIndex].纬度 = result.lat;
        rows.value[rowIndex].经度 = result.lng;
      });
      points.value.push({ lat: result.lat, lng: result.lng });
    } else {
      logs.value.push({
        address,
        type: result.type,
        request: result.request,
        response: result.response,
      });
    }
  }

  geocodeState.running = false;
  geocodeState.current = "";
  refreshMarkers();
};

const geocodeAddress = async (address) => {
  const encoded = encodeURIComponent(address);
  if (provider.value === "mapbox") {
    const url = `https://api.mapbox.com/geocoding/v5/mapbox.places/${encoded}.json?access_token=${providerApiKey.value}`;
    try {
      const response = await fetch(url);
      const body = await response.json();
      if (!response.ok) {
        return {
          success: false,
          type: "network_error",
          request: url,
          response: JSON.stringify(body),
        };
      }
      if (!body.features || body.features.length === 0) {
        return {
          success: false,
          type: "no_result",
          request: url,
          response: JSON.stringify(body),
        };
      }
      const [lng, lat] = body.features[0].center;
      return { success: true, lat, lng };
    } catch (error) {
      return {
        success: false,
        type: "network_error",
        request: url,
        response: String(error),
      };
    }
  }

  const url = `https://geocode.search.hereapi.com/v1/geocode?q=${encoded}&apiKey=${providerApiKey.value}`;
  try {
    const response = await fetch(url);
    const body = await response.json();
    if (!response.ok) {
      return {
        success: false,
        type: "network_error",
        request: url,
        response: JSON.stringify(body),
      };
    }
    if (!body.items || body.items.length === 0) {
      return {
        success: false,
        type: "no_result",
        request: url,
        response: JSON.stringify(body),
      };
    }
    const { lat, lng } = body.items[0].position;
    return { success: true, lat, lng };
  } catch (error) {
    return {
      success: false,
      type: "network_error",
      request: url,
      response: String(error),
    };
  }
};

const downloadExcel = () => {
  const outputHeaders = [...headers.value, "纬度", "经度"];
  const data = [outputHeaders];
  rows.value.forEach((row) => {
    const rowData = headers.value.map((header) => row[header] ?? "");
    rowData.push(row.纬度 ?? "", row.经度 ?? "");
    data.push(rowData);
  });
  const worksheet = XLSX.utils.aoa_to_sheet(data);
  const workbook = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(workbook, worksheet, "Geocode");
  XLSX.writeFile(workbook, `geocode_${fileName.value || "result.xlsx"}`);
};

const applyMapKey = () => {
  if (!mapApiKey.value) return;
  initMap();
};

const initMap = () => {
  if (!mapContainer.value || !mapApiKey.value) return;
  mapboxgl.accessToken = mapApiKey.value;
  if (mapInstance) {
    mapInstance.remove();
    mapInstance = null;
  }
  mapInstance = new mapboxgl.Map({
    container: mapContainer.value,
    style: "mapbox://styles/mapbox/streets-v12",
    center: [116.397389, 39.908722],
    zoom: 3,
  });
  mapInstance.addControl(new mapboxgl.NavigationControl(), "top-right");
  mapInstance.on("load", refreshMarkers);
};

const refreshMarkers = () => {
  if (!mapInstance) return;
  mapMarkers.forEach((marker) => marker.remove());
  mapMarkers = [];
  if (!points.value.length) return;
  points.value.forEach((point) => {
    const marker = new mapboxgl.Marker({ color: "#2563eb" })
      .setLngLat([point.lng, point.lat])
      .addTo(mapInstance);
    mapMarkers.push(marker);
  });
  if (points.value.length === 1) {
    mapInstance.flyTo({ center: [points.value[0].lng, points.value[0].lat], zoom: 12 });
  }
};

onMounted(() => {
  if (mapApiKey.value) {
    initMap();
  }
});
</script>
