<template>
  <div class="app-shell">
    <header class="app-header">
      <div>
        <h1>{{ headerTitle }}</h1>
        <p class="sub-title">支持地址编码、经纬度解码、导航距离计算三种批量处理方式。</p>
      </div>
      <div class="mode-toggle" role="tablist" aria-label="功能切换">
        <button
          v-for="item in modeOptions"
          :key="item.value"
          type="button"
          class="mode-button"
          :class="{ active: mode === item.value }"
          role="tab"
          :aria-selected="mode === item.value"
          @click="mode = item.value"
        >
          {{ item.label }}
        </button>
      </div>
    </header>

    <main class="layout">
      <section class="panel">
        <div class="card">
          <div class="card-header">
            <h2>1. 上传 Excel</h2>
            <button
              class="icon-button"
              :class="{ pulse: mockAnimating }"
              type="button"
              @click="fillMockData"
              aria-label="一键填写 Mock 数据"
            >
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path
                  d="M12 3l1.9 4.3L18 9.2l-4.1 1.9L12 15l-1.9-3.9L6 9.2l4.1-1.9L12 3zm7 9l.9 2.1L22 15l-2.1.9L19 18l-.9-2.1L16 15l2.1-.9L19 12zM4 13l.9 2.1L7 16l-2.1.9L4 19l-.9-2.1L1 16l2.1-.9L4 13z"
                />
              </svg>
            </button>
          </div>
          <div
            class="dropzone"
            :class="{ active: isDragging, loaded: hasData, flash: dropzoneFlash }"
            @dragover.prevent="handleDragOver"
            @dragleave.prevent="handleDragLeave"
            @drop.prevent="handleFileDrop"
          >
            <input type="file" accept=".xlsx,.xls" @change="handleFileChange" />
            <p>拖放 Excel 文件到此处，或点击选择</p>
          </div>
          <p v-if="fileName" class="hint">已加载：{{ fileName }}</p>
        </div>

        <div class="card">
          <h2>2. 配置解析</h2>
          <div v-if="mode === 'geocode'">
            <label class="field">
              <span>地址列名</span>
              <select v-model="columnName">
                <option value="" disabled>请选择列名</option>
                <option v-for="header in headers" :key="header" :value="header">
                  {{ header }}
                </option>
              </select>
            </label>
          </div>
          <div v-else-if="mode === 'reverse'">
            <div class="field">
              <span>经纬度格式</span>
              <div class="option-row">
                <label class="option-pill">
                  <input
                    v-model="reverseColumnMode"
                    type="radio"
                    value="separate"
                  />
                  <span>不同列</span>
                </label>
                <label class="option-pill">
                  <input
                    v-model="reverseColumnMode"
                    type="radio"
                    value="single"
                  />
                  <span>同一列</span>
                </label>
              </div>
            </div>
            <template v-if="reverseColumnMode === 'separate'">
              <label class="field">
                <span>纬度列名</span>
                <select v-model="latColumnName">
                  <option value="" disabled>请选择列名</option>
                  <option v-for="header in headers" :key="header" :value="header">
                    {{ header }}
                  </option>
                </select>
              </label>
              <label class="field">
                <span>经度列名</span>
                <select v-model="lngColumnName">
                  <option value="" disabled>请选择列名</option>
                  <option v-for="header in headers" :key="header" :value="header">
                    {{ header }}
                  </option>
                </select>
              </label>
            </template>
            <template v-else>
              <label class="field">
                <span>经纬度列名</span>
                <select v-model="reverseColumnName">
                  <option value="" disabled>请选择列名</option>
                  <option v-for="header in headers" :key="header" :value="header">
                    {{ header }}
                  </option>
                </select>
              </label>
              <div class="field">
                <span>分隔符</span>
                <div class="option-row">
                  <label class="option-pill">
                    <input
                      v-model="reverseDelimiterMode"
                      type="radio"
                      value="auto"
                    />
                    <span>自动识别 “,”</span>
                  </label>
                  <label class="option-pill">
                    <input
                      v-model="reverseDelimiterMode"
                      type="radio"
                      value="custom"
                    />
                    <span>自定义</span>
                  </label>
                </div>
                <input
                  v-if="reverseDelimiterMode === 'custom'"
                  v-model="reverseDelimiter"
                  type="text"
                  placeholder="例如：| 或 空格"
                />
              </div>
            </template>
          </div>
          <div v-else>
            <div class="field">
              <span>路线输入类型</span>
              <div class="option-row">
                <label class="option-pill">
                  <input v-model="routeInputMode" type="radio" value="address" />
                  <span>地址</span>
                </label>
                <label class="option-pill">
                  <input v-model="routeInputMode" type="radio" value="coordinate" />
                  <span>经纬度</span>
                </label>
              </div>
            </div>
            <label class="field">
              <span>起始地列名</span>
              <select v-model="startColumnName">
                <option value="" disabled>请选择列名</option>
                <option v-for="header in headers" :key="header" :value="header">
                  {{ header }}
                </option>
              </select>
            </label>
            <label class="field">
              <span>目的地列名</span>
              <select v-model="endColumnName">
                <option value="" disabled>请选择列名</option>
                <option v-for="header in headers" :key="header" :value="header">
                  {{ header }}
                </option>
              </select>
            </label>
          </div>
          <label class="field">
            <span>地图服务商</span>
            <select v-model="provider">
              <option value="mapbox">Mapbox</option>
              <option value="here">HERE</option>
              <option value="custom" :disabled="mode === 'reverse'">自定义接口</option>
            </select>
          </label>
          <p v-if="mode === 'reverse'" class="hint">自定义接口暂不支持反编码。</p>
          <template v-if="provider === 'custom'">
            <label class="field">
              <span>App ID</span>
              <input v-model="customAppId" type="text" placeholder="输入 App ID" />
            </label>
            <label class="field">
              <span>Credential</span>
              <input v-model="customCredential" type="password" placeholder="输入 Credential" />
            </label>
            <label class="field">
              <span>Token 接口 URL</span>
              <input v-model="customTokenUrl" type="text" placeholder="getResAppDynamicToken 接口地址" />
            </label>
            <label class="field">
              <span>地理编码接口 URL</span>
              <input v-model="customGeocodeUrl" type="text" placeholder="geographicSearch 接口地址" />
            </label>
            <label v-if="mode === 'route'" class="field">
              <span>导航接口 URL</span>
              <input v-model="customRouteUrl" type="text" placeholder="routeSearch 接口地址" />
            </label>
            <label class="field">
              <span>WebSocket 地址</span>
              <input v-model="customWebSocketUrl" type="text" placeholder="ws://localhost:8765" />
            </label>
          </template>
          <label v-else class="field">
            <span>API Key</span>
            <input v-model="providerApiKey" type="password" placeholder="输入服务商 API Key" />
          </label>
          <div class="actions">
            <button class="primary" :disabled="!canStart" @click="handleStart">
              {{ startLabel }}
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
              <span>{{ progressLabel }}</span>
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
          <div v-if="!mapLoaded" class="map-config">
            <h3>地图配置</h3>
            <label>
              <span>Mapbox API Key</span>
              <input v-model="mapApiKey" type="password" placeholder="用于地图展示" />
            </label>
            <button class="secondary" @click="applyMapKey">应用</button>
          </div>
          <div v-if="!mapLoaded" class="map-empty">
            <p>请在右下角填写 Mapbox API Key 以加载地图。</p>
          </div>
        </div>
      </section>
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from "vue";
import mapboxgl from "mapbox-gl";
import * as XLSX from "xlsx";

const headers = ref([]);
const rows = ref([]);
const fileName = ref("");
const columnName = ref("");
const latColumnName = ref("");
const lngColumnName = ref("");
const reverseColumnMode = ref("separate");
const reverseColumnName = ref("");
const reverseDelimiterMode = ref("auto");
const reverseDelimiter = ref(",");
const startColumnName = ref("");
const endColumnName = ref("");
const routeInputMode = ref("address");
const provider = ref("mapbox");
const providerApiKey = ref("");
const customAppId = ref("");
const customCredential = ref("");
const customTokenUrl = ref("");
const customGeocodeUrl = ref("");
const customRouteUrl = ref("");
const customToken = ref("");
const defaultWebSocketUrl = () => {
  if (typeof window === "undefined") return "ws://localhost:8765";
  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  return `${protocol}://${window.location.hostname}:8765`;
};
const customWebSocketUrl = ref(defaultWebSocketUrl());
const customSocket = ref(null);
const mapApiKey = ref("");
const logs = ref([]);
const geocodeCache = new Map();
const reverseCache = new Map();
const routeCache = new Map();
const mapContainer = ref(null);
const mapLoaded = ref(false);
const isDragging = ref(false);
const dropzoneFlash = ref(false);
const mockAnimating = ref(false);
const geocodeState = reactive({
  total: 0,
  processed: 0,
  current: "",
  running: false,
});
const points = ref([]);
const routeLine = ref(null);
const mode = ref("geocode");

const modeOptions = [
  { value: "geocode", label: "地址编码" },
  { value: "reverse", label: "经纬度解码" },
  { value: "route", label: "导航距离计算" },
];

let mapInstance = null;
let mapMarkers = [];

const storageKeys = {
  provider: "geocode_provider",
  mapboxGeocode: "mapbox_geocode_api_key",
  hereGeocode: "here_geocode_api_key",
  mapboxMap: "mapbox_map_api_key",
  customAppId: "custom_app_id",
  customCredential: "custom_credential",
  customTokenUrl: "custom_token_url",
  customGeocodeUrl: "custom_geocode_url",
  customRouteUrl: "custom_route_url",
  customWebSocketUrl: "custom_websocket_url",
  columnName: "geocode_column_name",
  latColumnName: "reverse_lat_column_name",
  lngColumnName: "reverse_lng_column_name",
  reverseColumnMode: "reverse_column_mode",
  reverseColumnName: "reverse_column_name",
  reverseDelimiterMode: "reverse_delimiter_mode",
  reverseDelimiter: "reverse_delimiter",
  startColumnName: "route_start_column_name",
  endColumnName: "route_end_column_name",
  routeInputMode: "route_input_mode",
  mode: "geocode_mode",
};

const getProviderStorageKey = (currentProvider) =>
  currentProvider === "mapbox" ? storageKeys.mapboxGeocode : storageKeys.hereGeocode;

const canStart = computed(() => {
  if (geocodeState.running || rows.value.length === 0) {
    return false;
  }
  if (provider.value === "custom") {
    if (mode.value === "reverse") {
      return false;
    }
    if (mode.value === "route") {
      return Boolean(
        customAppId.value &&
          customCredential.value &&
          customTokenUrl.value &&
          (routeInputMode.value === "address" ? customGeocodeUrl.value : true) &&
          customRouteUrl.value &&
          customWebSocketUrl.value &&
          startColumnName.value &&
          endColumnName.value
      );
    }
    return Boolean(
      customAppId.value &&
        customCredential.value &&
        customTokenUrl.value &&
        customGeocodeUrl.value &&
        customWebSocketUrl.value &&
        columnName.value
    );
  }
  if (!providerApiKey.value) {
    return false;
  }
  if (mode.value === "geocode") {
    return Boolean(columnName.value);
  }
  if (mode.value === "reverse") {
    if (reverseColumnMode.value === "single") {
      return Boolean(
        reverseColumnName.value &&
          (reverseDelimiterMode.value === "auto" || reverseDelimiter.value)
      );
    }
    return Boolean(latColumnName.value && lngColumnName.value);
  }
  return (
    Boolean(startColumnName.value && endColumnName.value)
  );
});

const canDownload = computed(() => rows.value.length > 0 && points.value.length > 0);
const hasData = computed(() => rows.value.length > 0);
const headerTitle = computed(() => {
  if (mode.value === "reverse") {
    return "Excel 经纬度批量解析地址";
  }
  if (mode.value === "route") {
    return "Excel 批量导航距离计算";
  }
  return "Excel 地址批量转经纬度";
});
const startLabel = computed(() => {
  if (mode.value === "reverse") return "开始解码";
  if (mode.value === "route") return "开始计算";
  return "开始转换";
});
const progressLabel = computed(() => {
  if (mode.value === "reverse") return "当前经纬度";
  if (mode.value === "route") return "当前路线";
  return "当前地址";
});

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

const resetFileData = () => {
  headers.value = [];
  rows.value = [];
  fileName.value = "";
  columnName.value = "";
  latColumnName.value = "";
  lngColumnName.value = "";
  reverseColumnName.value = "";
  startColumnName.value = "";
  endColumnName.value = "";
};

const resetResults = () => {
  logs.value = [];
  points.value = [];
  routeLine.value = null;
  geocodeCache.clear();
  reverseCache.clear();
  routeCache.clear();
  closeCustomSocket();
  resetProgress();
  refreshMarkers();
};

const loadFile = (file) => {
  if (!file) return;
  fileName.value = file.name;
  triggerDropzoneFlash();

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
    const savedColumn = localStorage.getItem(storageKeys.columnName);
    if (savedColumn && headers.value.includes(savedColumn)) {
      columnName.value = savedColumn;
    } else {
      columnName.value = headers.value[0] || "";
    }
    const savedLatColumn = localStorage.getItem(storageKeys.latColumnName);
    if (savedLatColumn && headers.value.includes(savedLatColumn)) {
      latColumnName.value = savedLatColumn;
    } else {
      latColumnName.value = guessColumn(headers.value, ["纬度", "lat"]);
    }
    const savedLngColumn = localStorage.getItem(storageKeys.lngColumnName);
    if (savedLngColumn && headers.value.includes(savedLngColumn)) {
      lngColumnName.value = savedLngColumn;
    } else {
      lngColumnName.value = guessColumn(headers.value, ["经度", "lng", "lon"]);
    }
    const savedReverseColumn = localStorage.getItem(storageKeys.reverseColumnName);
    if (savedReverseColumn && headers.value.includes(savedReverseColumn)) {
      reverseColumnName.value = savedReverseColumn;
    } else {
      reverseColumnName.value = guessColumn(headers.value, ["坐标", "经纬度"]);
    }
    const savedReverseMode = localStorage.getItem(storageKeys.reverseColumnMode);
    if (savedReverseMode === "single" || savedReverseMode === "separate") {
      reverseColumnMode.value = savedReverseMode;
    } else if (latColumnName.value && lngColumnName.value) {
      reverseColumnMode.value = "separate";
    } else if (reverseColumnName.value) {
      reverseColumnMode.value = "single";
    }
    const savedStartColumn = localStorage.getItem(storageKeys.startColumnName);
    if (savedStartColumn && headers.value.includes(savedStartColumn)) {
      startColumnName.value = savedStartColumn;
    } else {
      startColumnName.value = headers.value[0] || "";
    }
  const savedEndColumn = localStorage.getItem(storageKeys.endColumnName);
  if (savedEndColumn && headers.value.includes(savedEndColumn)) {
    endColumnName.value = savedEndColumn;
  } else {
    endColumnName.value = headers.value[1] || headers.value[0] || "";
  }
  const savedRouteInputMode = localStorage.getItem(storageKeys.routeInputMode);
  if (savedRouteInputMode === "address" || savedRouteInputMode === "coordinate") {
    routeInputMode.value = savedRouteInputMode;
  }
  resetResults();
};
  reader.readAsArrayBuffer(file);
};

const handleFileChange = (event) => {
  const file = event.target.files?.[0];
  loadFile(file);
};

const handleDragOver = () => {
  isDragging.value = true;
};

const handleDragLeave = () => {
  isDragging.value = false;
};

const handleFileDrop = (event) => {
  const file = event.dataTransfer?.files?.[0];
  isDragging.value = false;
  loadFile(file);
};

const fillMockData = () => {
  triggerMockAnimation();
  if (mode.value === "reverse") {
    if (reverseColumnMode.value === "single") {
      headers.value = ["经纬度", "客户"];
      rows.value = [
        { 经纬度: "31.2304,121.4737", 客户: "星云科技" },
        { 经纬度: "39.9087,116.3974", 客户: "京华贸易" },
        { 经纬度: "22.5431,114.0579", 客户: "海风智能" },
        { 经纬度: "30.2741,120.1551", 客户: "知行数据" },
        { 经纬度: "30.5728,104.0668", 客户: "西蜀科技" }
      ];
      reverseColumnName.value = "经纬度";
      reverseDelimiterMode.value = "auto";
    } else {
      headers.value = ["纬度", "经度", "客户"];
      rows.value = [
        { 纬度: 31.2304, 经度: 121.4737, 客户: "星云科技" },
        { 纬度: 39.9087, 经度: 116.3974, 客户: "京华贸易" },
        { 纬度: 22.5431, 经度: 114.0579, 客户: "海风智能" },
        { 纬度: 30.2741, 经度: 120.1551, 客户: "知行数据" },
        { 纬度: 30.5728, 经度: 104.0668, 客户: "西蜀科技" }
      ];
      latColumnName.value = "纬度";
      lngColumnName.value = "经度";
    }
  } else if (mode.value === "route") {
    headers.value = ["起点", "终点", "客户"];
    rows.value = [
      { 起点: "上海虹桥站", 终点: "上海迪士尼", 客户: "星云科技" },
      { 起点: "北京南站", 终点: "北京首都机场", 客户: "京华贸易" },
      { 起点: "深圳北站", 终点: "深圳湾口岸", 客户: "海风智能" },
      { 起点: "杭州东站", 终点: "西湖风景区", 客户: "知行数据" },
      { 起点: "成都东站", 终点: "天府国际机场", 客户: "西蜀科技" }
    ];
    startColumnName.value = "起点";
    endColumnName.value = "终点";
  } else {
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
  }
  fileName.value = "mock.xlsx";
  resetResults();
  triggerDropzoneFlash();
};

const triggerDropzoneFlash = () => {
  dropzoneFlash.value = false;
  requestAnimationFrame(() => {
    dropzoneFlash.value = true;
    setTimeout(() => {
      dropzoneFlash.value = false;
    }, 600);
  });
};

const triggerMockAnimation = () => {
  mockAnimating.value = false;
  requestAnimationFrame(() => {
    mockAnimating.value = true;
    setTimeout(() => {
      mockAnimating.value = false;
    }, 500);
  });
};

const guessColumn = (headerList, keywords) => {
  const lowered = headerList.map((header) => header.toLowerCase());
  const hitIndex = lowered.findIndex((header) =>
    keywords.some((keyword) => header.includes(keyword))
  );
  return headerList[hitIndex] || "";
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

const buildRoutePayloads = () =>
  rows.value.map((row, index) => {
    const origin = String(row[startColumnName.value] ?? "").trim();
    const destination = String(row[endColumnName.value] ?? "").trim();
    return { index, origin, destination };
  });

const parseRouteCoordinate = (value) => {
  const raw = String(value ?? "").trim();
  if (!raw) {
    return { success: false, key: "-", message: "坐标为空" };
  }
  const delimiter = raw.includes(",") ? "," : raw.includes("，") ? "，" : "";
  if (!delimiter) {
    return { success: false, key: raw, message: "无法识别坐标分隔符" };
  }
  const parts = raw.split(delimiter).map((item) => item.trim());
  if (parts.length < 2) {
    return { success: false, key: raw, message: "坐标格式不完整" };
  }
  const lat = Number(parts[0]);
  const lng = Number(parts[1]);
  if (!Number.isFinite(lat) || !Number.isFinite(lng)) {
    return { success: false, key: raw, message: "纬度或经度不是有效数字" };
  }
  return { success: true, key: raw, lat, lng };
};

const closeCustomSocket = () => {
  if (customSocket.value) {
    customSocket.value.close();
    customSocket.value = null;
  }
};

const startCustomGeocode = () => {
  if (!canStart.value) return;
  closeCustomSocket();
  logs.value = [];
  points.value = [];
  routeLine.value = null;
  geocodeState.running = true;
  geocodeState.processed = 0;
  geocodeState.current = "";

  const addressMap = buildAddressMap();
  const addresses = Array.from(addressMap.keys());
  geocodeState.total = addresses.length;
  if (addresses.length === 0) {
    geocodeState.running = false;
    return;
  }

  let socket;
  try {
    socket = new WebSocket(customWebSocketUrl.value);
  } catch (error) {
    logs.value.push({
      address: "-",
      type: "network_error",
      request: customWebSocketUrl.value,
      response: `无法连接 WebSocket: ${String(error)}`,
    });
    geocodeState.running = false;
    return;
  }

  customSocket.value = socket;

  socket.onopen = () => {
    socket.send(
      JSON.stringify({
        type: "start",
        payload: {
          config: {
            appId: customAppId.value,
            credential: customCredential.value,
            tokenUrl: customTokenUrl.value,
            geocodeUrl: customGeocodeUrl.value,
          },
          addresses,
        },
      })
    );
  };

  socket.onmessage = (event) => {
    let message;
    try {
      message = JSON.parse(event.data);
    } catch (error) {
      logs.value.push({
        address: "-",
        type: "parse_error",
        request: "WebSocket",
        response: `无法解析后端返回: ${String(error)}`,
      });
      return;
    }

    if (message.type === "progress") {
      const payload = message.payload || {};
      const address = payload.address || "-";
      geocodeState.current = address;
      if (Number.isFinite(payload.processed)) {
        geocodeState.processed = payload.processed;
      } else {
        geocodeState.processed += 1;
      }
      if (payload.success) {
        const lat = payload.lat;
        const lng = payload.lng;
        if (Number.isFinite(lat) && Number.isFinite(lng)) {
          geocodeCache.set(address, { success: true, lat, lng });
          const indices = addressMap.get(address) || [];
          indices.forEach((rowIndex) => {
            rows.value[rowIndex].纬度 = lat;
            rows.value[rowIndex].经度 = lng;
          });
          points.value.push({ lat, lng });
        } else {
          logs.value.push({
            address,
            type: "no_result",
            request: payload.request || "custom",
            response: "未返回可用经纬度",
          });
        }
      } else {
        logs.value.push({
          address,
          type: payload.errorType || "network_error",
          request: payload.request || "custom",
          response: payload.response || "请求失败",
        });
      }
    }

    if (message.type === "complete") {
      geocodeState.running = false;
      geocodeState.current = "";
      closeCustomSocket();
      refreshMarkers();
    }
  };

  socket.onerror = () => {
    logs.value.push({
      address: "-",
      type: "network_error",
      request: customWebSocketUrl.value,
      response: "WebSocket 连接异常",
    });
  };

  socket.onclose = () => {
    if (geocodeState.running) {
      geocodeState.running = false;
      geocodeState.current = "";
      refreshMarkers();
    }
    closeCustomSocket();
  };
};

const startCustomRoute = () => {
  if (!canStart.value) return;
  closeCustomSocket();
  logs.value = [];
  points.value = [];
  routeLine.value = null;
  geocodeState.running = true;
  geocodeState.processed = 0;
  geocodeState.current = "";

  const routes = buildRoutePayloads();
  geocodeState.total = routes.length;
  if (routes.length === 0) {
    geocodeState.running = false;
    return;
  }

  let socket;
  try {
    socket = new WebSocket(customWebSocketUrl.value);
  } catch (error) {
    logs.value.push({
      address: "-",
      type: "network_error",
      request: customWebSocketUrl.value,
      response: `无法连接 WebSocket: ${String(error)}`,
    });
    geocodeState.running = false;
    return;
  }

  customSocket.value = socket;

  socket.onopen = () => {
    socket.send(
      JSON.stringify({
        type: "start",
        payload: {
          mode: "route",
          routeInputMode: routeInputMode.value,
          config: {
            appId: customAppId.value,
            credential: customCredential.value,
            tokenUrl: customTokenUrl.value,
            geocodeUrl: customGeocodeUrl.value,
            routeUrl: customRouteUrl.value,
          },
          routes: routes.map((route) => ({
            origin: route.origin,
            destination: route.destination,
          })),
        },
      })
    );
  };

  socket.onmessage = (event) => {
    let message;
    try {
      message = JSON.parse(event.data);
    } catch (error) {
      logs.value.push({
        address: "-",
        type: "parse_error",
        request: "WebSocket",
        response: `无法解析后端返回: ${String(error)}`,
      });
      return;
    }

    if (message.type === "progress") {
      const payload = message.payload || {};
      const routeIndex = Number(payload.index);
      const route = Number.isFinite(routeIndex) ? routes[routeIndex] : null;
      const address = route ? `${route.origin} -> ${route.destination}` : "-";
      geocodeState.current = address;
      if (Number.isFinite(payload.processed)) {
        geocodeState.processed = payload.processed;
      } else {
        geocodeState.processed += 1;
      }

      if (payload.success && route) {
        const distanceKm = payload.distanceKm;
        const durationMin = payload.durationMin;
        if (distanceKm != null && durationMin != null) {
          rows.value[route.index]["导航距离(km)"] = distanceKm;
          rows.value[route.index]["导航时间(min)"] = durationMin;
        } else {
          logs.value.push({
            address,
            type: "no_result",
            request: payload.request || "custom",
            response: "未返回可用导航数据",
          });
        }
      } else {
        logs.value.push({
          address,
          type: payload.errorType || "network_error",
          request: payload.request || "custom",
          response: payload.response || "请求失败",
        });
      }
    }

    if (message.type === "complete") {
      geocodeState.running = false;
      geocodeState.current = "";
      closeCustomSocket();
      refreshMarkers();
    }
  };

  socket.onerror = () => {
    logs.value.push({
      address: "-",
      type: "network_error",
      request: customWebSocketUrl.value,
      response: "WebSocket 连接异常",
    });
  };

  socket.onclose = () => {
    if (geocodeState.running) {
      geocodeState.running = false;
      geocodeState.current = "";
      refreshMarkers();
    }
    closeCustomSocket();
  };
};

const startGeocode = async () => {
  if (!canStart.value) return;
  logs.value = [];
  points.value = [];
  routeLine.value = null;
  geocodeState.running = true;
  geocodeState.processed = 0;
  geocodeState.current = "";

  const addressMap = buildAddressMap();
  geocodeState.total = addressMap.size;

  for (const [address, indices] of addressMap.entries()) {
    geocodeState.current = address;
    let result = geocodeCache.get(address);
    if (!result) {
      result = await geocodeAddress(address);
      geocodeCache.set(address, result);
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

const startReverseGeocode = async () => {
  if (!canStart.value) return;
  logs.value = [];
  points.value = [];
  routeLine.value = null;
  geocodeState.running = true;
  geocodeState.processed = 0;
  geocodeState.current = "";
  geocodeState.total = rows.value.length;

  for (const row of rows.value) {
    const parsed = parseReverseCoordinates(row);
    geocodeState.current = parsed.key;
    if (!parsed.success) {
      logs.value.push({
        address: parsed.key,
        type: "invalid",
        request: "输入格式错误",
        response: parsed.message,
      });
      geocodeState.processed += 1;
      continue;
    }
    const { lat, lng } = parsed;
    let result = reverseCache.get(parsed.key);
    if (!result) {
      result = await reverseGeocode(lat, lng);
      reverseCache.set(parsed.key, result);
    }
    geocodeState.processed += 1;
    if (result.success) {
      row.解析地址 = result.address;
      row.一级行政区 = result.admin1;
      row.二级行政区 = result.admin2;
      row.三级行政区 = result.admin3;
      points.value.push({ lat, lng, type: "point" });
    } else {
      logs.value.push({
        address: parsed.key,
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

const parseReverseCoordinates = (row) => {
  if (reverseColumnMode.value === "single") {
    const raw = String(row[reverseColumnName.value] ?? "").trim();
    if (!raw) {
      return { success: false, key: "-", message: "经纬度为空" };
    }
    let delimiter = reverseDelimiter.value;
    if (reverseDelimiterMode.value === "auto") {
      delimiter = raw.includes(",") ? "," : raw.includes("，") ? "，" : "";
    }
    if (!delimiter) {
      return { success: false, key: raw, message: "无法识别分隔符" };
    }
    const parts = raw.split(delimiter).map((item) => item.trim());
    if (parts.length < 2) {
      return { success: false, key: raw, message: "经纬度格式不完整" };
    }
    const lat = Number(parts[0]);
    const lng = Number(parts[1]);
    if (!Number.isFinite(lat) || !Number.isFinite(lng)) {
      return { success: false, key: raw, message: "纬度或经度不是有效数字" };
    }
    return { success: true, key: raw, lat, lng };
  }

  const lat = Number(row[latColumnName.value]);
  const lng = Number(row[lngColumnName.value]);
  const key = `${lat},${lng}`;
  if (!Number.isFinite(lat) || !Number.isFinite(lng)) {
    return { success: false, key, message: "纬度或经度不是有效数字" };
  }
  return { success: true, key, lat, lng };
};

const startRoute = async () => {
  if (!canStart.value) return;
  logs.value = [];
  points.value = [];
  routeLine.value = null;
  geocodeState.running = true;
  geocodeState.processed = 0;
  geocodeState.current = "";
  geocodeState.total = rows.value.length;

  for (const row of rows.value) {
    const origin = String(row[startColumnName.value] ?? "").trim();
    const destination = String(row[endColumnName.value] ?? "").trim();
    const routeKey = `${origin}=>${destination}`;
    geocodeState.current = routeKey;
    if (!origin || !destination) {
      logs.value.push({
        address: routeKey,
        type: "invalid",
        request: "输入格式错误",
        response: "起始地或目的地为空",
      });
      geocodeState.processed += 1;
      continue;
    }

    if (routeInputMode.value === "coordinate") {
      const parsedOrigin = parseRouteCoordinate(origin);
      const parsedDestination = parseRouteCoordinate(destination);
      if (!parsedOrigin.success || !parsedDestination.success) {
        logs.value.push({
          address: routeKey,
          type: "invalid",
          request: "输入格式错误",
          response: `${parsedOrigin.message || ""} ${parsedDestination.message || ""}`.trim(),
        });
        geocodeState.processed += 1;
        continue;
      }
      let result = routeCache.get(routeKey);
      if (!result) {
        result = await fetchRoute(
          parsedOrigin.lat,
          parsedOrigin.lng,
          parsedDestination.lat,
          parsedDestination.lng
        );
        routeCache.set(routeKey, result);
      }
      geocodeState.processed += 1;
      if (result.success) {
        row["导航距离(km)"] = result.distanceKm;
        row["导航时间(min)"] = result.durationMin;
        points.value.push(
          { lat: parsedOrigin.lat, lng: parsedOrigin.lng, type: "origin" },
          { lat: parsedDestination.lat, lng: parsedDestination.lng, type: "destination" }
        );
        routeLine.value = result.line;
      } else {
        logs.value.push({
          address: routeKey,
          type: result.type,
          request: result.request,
          response: result.response,
        });
      }
      continue;
    }
    let result = routeCache.get(routeKey);
    if (!result) {
      const originResult = geocodeCache.get(origin) || (await geocodeAddress(origin));
      geocodeCache.set(origin, originResult);
      const destinationResult =
        geocodeCache.get(destination) || (await geocodeAddress(destination));
      geocodeCache.set(destination, destinationResult);
      if (!originResult.success || !destinationResult.success) {
        const failure = !originResult.success ? originResult : destinationResult;
        result = {
          success: false,
          type: failure.type,
          request: failure.request,
          response: failure.response,
        };
      } else {
        result = await fetchRoute(
          originResult.lat,
          originResult.lng,
          destinationResult.lat,
          destinationResult.lng
        );
      }
      routeCache.set(routeKey, result);
    }
    geocodeState.processed += 1;

    if (result.success) {
      row["导航距离(km)"] = result.distanceKm;
      row["导航时间(min)"] = result.durationMin;
      points.value.push(
        { lat: result.origin.lat, lng: result.origin.lng, type: "origin" },
        { lat: result.destination.lat, lng: result.destination.lng, type: "destination" }
      );
      routeLine.value = result.line;
    } else {
      logs.value.push({
        address: routeKey,
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

const handleStart = () => {
  if (mode.value === "reverse") {
    startReverseGeocode();
  } else if (mode.value === "route") {
    if (provider.value === "custom") {
      startCustomRoute();
    } else {
      startRoute();
    }
  } else {
    if (provider.value === "custom") {
      startCustomGeocode();
    } else {
      startGeocode();
    }
  }
};

const geocodeAddress = async (address) => {
  const encoded = encodeURIComponent(address);
  if (provider.value === "custom") {
    const token = await fetchCustomToken();
    if (!token) {
      return {
        success: false,
        type: "auth_error",
        request: customTokenUrl.value || "getResAppDynamicToken",
        response: "无法获取自定义接口 Token",
      };
    }
    const url = customGeocodeUrl.value || "geographicSearch";
    try {
      const response = await fetch(url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: token,
        },
        body: JSON.stringify({
          address,
          language: "en",
          coordType: "wgs84",
        }),
      });
      const body = await response.json();
      if (!response.ok || body?.result?.status !== "OK") {
        return {
          success: false,
          type: "network_error",
          request: url,
          response: JSON.stringify(body),
        };
      }
      const location = body?.result?.geometry?.location;
      if (!location || location.lat == null || location.lng == null) {
        return {
          success: false,
          type: "no_result",
          request: url,
          response: JSON.stringify(body),
        };
      }
      return { success: true, lat: location.lat, lng: location.lng };
    } catch (error) {
      return {
        success: false,
        type: "network_error",
        request: url,
        response: String(error),
      };
    }
  }
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
      const [lng, lat] = body.features[0].center || [];
      if (!Number.isFinite(lat) || !Number.isFinite(lng)) {
        return {
          success: false,
          type: "no_result",
          request: url,
          response: JSON.stringify(body),
        };
      }
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
    const { lat, lng } = body.items[0].position || {};
    if (!Number.isFinite(lat) || !Number.isFinite(lng)) {
      return {
        success: false,
        type: "no_result",
        request: url,
        response: JSON.stringify(body),
      };
    }
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

const fetchCustomToken = async () => {
  if (customToken.value) {
    return customToken.value;
  }
  const url = customTokenUrl.value || "getResAppDynamicToken";
  try {
    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        appId: customAppId.value,
        credential: customCredential.value,
      }),
    });
    const body = await response.json();
    if (!response.ok || body?.status?.statusCode !== "SUCESS" || !body?.result) {
      return "";
    }
    customToken.value = body.result;
    return customToken.value;
  } catch (error) {
    return "";
  }
};

const reverseGeocode = async (lat, lng) => {
  if (provider.value === "mapbox") {
    const url = `https://api.mapbox.com/geocoding/v5/mapbox.places/${lng},${lat}.json?access_token=${providerApiKey.value}`;
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
      const feature = body.features[0];
      const { admin1, admin2, admin3 } = extractMapboxAdmin(feature);
      return {
        success: true,
        address: feature.place_name,
        admin1,
        admin2,
        admin3,
      };
    } catch (error) {
      return {
        success: false,
        type: "network_error",
        request: url,
        response: String(error),
      };
    }
  }

  const url = `https://revgeocode.search.hereapi.com/v1/revgeocode?at=${lat},${lng}&lang=zh-CN&apiKey=${providerApiKey.value}`;
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
    const address = body.items[0].address || {};
    return {
      success: true,
      address: body.items[0].title || "",
      admin1: address.state || address.province || "",
      admin2: address.city || address.county || "",
      admin3: address.district || address.subdistrict || address.county || "",
    };
  } catch (error) {
    return {
      success: false,
      type: "network_error",
      request: url,
      response: String(error),
    };
  }
};

const fetchRoute = async (originLat, originLng, destLat, destLng) => {
  if (provider.value === "mapbox") {
    const url = `https://api.mapbox.com/directions/v5/mapbox/driving/${originLng},${originLat};${destLng},${destLat}?geometries=geojson&overview=full&access_token=${providerApiKey.value}`;
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
      if (!body.routes || body.routes.length === 0) {
        return {
          success: false,
          type: "no_result",
          request: url,
          response: JSON.stringify(body),
        };
      }
      const route = body.routes[0];
      return {
        success: true,
        distanceKm: (route.distance / 1000).toFixed(2),
        durationMin: Math.round(route.duration / 60),
        line: route.geometry,
        origin: { lat: originLat, lng: originLng },
        destination: { lat: destLat, lng: destLng },
      };
    } catch (error) {
      return {
        success: false,
        type: "network_error",
        request: url,
        response: String(error),
      };
    }
  }

  const url = `https://router.hereapi.com/v8/routes?transportMode=car&origin=${originLat},${originLng}&destination=${destLat},${destLng}&return=summary,polyline&apiKey=${providerApiKey.value}`;
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
    if (!body.routes || body.routes.length === 0) {
      return {
        success: false,
        type: "no_result",
        request: url,
        response: JSON.stringify(body),
      };
    }
    const route = body.routes[0];
    const summary = route.sections?.[0]?.summary;
    const polyline = route.sections?.[0]?.polyline;
    const geometry = polyline ? decodeHerePolyline(polyline) : null;
    return {
      success: true,
      distanceKm: summary ? (summary.length / 1000).toFixed(2) : "",
      durationMin: summary ? Math.round(summary.duration / 60) : "",
      line: geometry,
      origin: { lat: originLat, lng: originLng },
      destination: { lat: destLat, lng: destLng },
    };
  } catch (error) {
    return {
      success: false,
      type: "network_error",
      request: url,
      response: String(error),
    };
  }
};

const extractMapboxAdmin = (feature) => {
  const context = feature.context || [];
  const place = context.find((item) => item.id?.startsWith("place"))?.text || "";
  const district = context.find((item) => item.id?.startsWith("district"))?.text || "";
  const region = context.find((item) => item.id?.startsWith("region"))?.text || "";
  const locality = context.find((item) => item.id?.startsWith("locality"))?.text || "";
  return {
    admin1: region || place || "",
    admin2: place || locality || "",
    admin3: district || locality || "",
  };
};

const decodeHerePolyline = (polyline) => {
  const decoder = new HerePolylineDecoder(polyline);
  const coordinates = [];
  while (decoder.hasNext()) {
    const { lat, lng } = decoder.next();
    coordinates.push([lng, lat]);
  }
  return {
    type: "LineString",
    coordinates,
  };
};

class HerePolylineDecoder {
  constructor(encoded) {
    this.encoded = encoded;
    this.index = 0;
    this.lat = 0;
    this.lng = 0;
    this.z = 0;
    this.precision = 5;
    this.thirdDim = 0;
    this.thirdDimPrecision = 0;
    this.headerDecoded = false;
  }

  hasNext() {
    if (!this.headerDecoded) {
      this.decodeHeader();
    }
    return this.index < this.encoded.length;
  }

  next() {
    if (!this.headerDecoded) {
      this.decodeHeader();
    }
    this.lat += this.decodeSigned();
    this.lng += this.decodeSigned();
    if (this.thirdDim) {
      this.z += this.decodeSigned();
    }
    return {
      lat: this.lat / Math.pow(10, this.precision),
      lng: this.lng / Math.pow(10, this.precision),
    };
  }

  decodeHeader() {
    const header = this.decodeUnsigned();
    this.precision = header & 15;
    this.thirdDim = (header >> 4) & 7;
    this.thirdDimPrecision = (header >> 7) & 15;
    this.headerDecoded = true;
  }

  decodeUnsigned() {
    let result = 0;
    let shift = 0;
    while (this.index < this.encoded.length) {
      const value = this.encoded.charCodeAt(this.index++) - 63;
      result |= (value & 31) << shift;
      if (value < 32) {
        return result;
      }
      shift += 5;
    }
    return result;
  }

  decodeSigned() {
    const result = this.decodeUnsigned();
    return result & 1 ? ~(result >> 1) : result >> 1;
  }
}

const downloadExcel = () => {
  const outputHeaders = getOutputHeaders();
  const data = [outputHeaders];
  rows.value.forEach((row) => {
    const rowData = headers.value.map((header) => row[header] ?? "");
    if (mode.value === "geocode") {
      rowData.push(row.纬度 ?? "", row.经度 ?? "");
    } else if (mode.value === "reverse") {
      rowData.push(
        row.解析地址 ?? "",
        row.一级行政区 ?? "",
        row.二级行政区 ?? "",
        row.三级行政区 ?? ""
      );
    } else {
      rowData.push(row["导航距离(km)"] ?? "", row["导航时间(min)"] ?? "");
    }
    data.push(rowData);
  });
  const worksheet = XLSX.utils.aoa_to_sheet(data);
  const workbook = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(workbook, worksheet, "Geocode");
  XLSX.writeFile(workbook, `geocode_${fileName.value || "result.xlsx"}`);
};

const getOutputHeaders = () => {
  if (mode.value === "reverse") {
    return [...headers.value, "解析地址", "一级行政区", "二级行政区", "三级行政区"];
  }
  if (mode.value === "route") {
    return [...headers.value, "导航距离(km)", "导航时间(min)"];
  }
  return [...headers.value, "纬度", "经度"];
};

const applyMapKey = () => {
  if (!mapApiKey.value) return;
  localStorage.setItem(storageKeys.mapboxMap, mapApiKey.value);
  initMap();
};

const initMap = () => {
  if (!mapContainer.value || !mapApiKey.value) return;
  mapboxgl.accessToken = mapApiKey.value;
  mapLoaded.value = false;
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
  mapInstance.on("load", () => {
    mapLoaded.value = true;
    refreshMarkers();
  });
};

const refreshMarkers = () => {
  if (!mapInstance) return;
  mapMarkers.forEach((marker) => marker.remove());
  mapMarkers = [];
  updateRouteLayer();
  if (!points.value.length) return;
  const bounds = new mapboxgl.LngLatBounds();
  points.value.forEach((point) => {
    const color =
      point.type === "origin" ? "#16a34a" : point.type === "destination" ? "#dc2626" : "#2563eb";
    const marker = new mapboxgl.Marker({ color })
      .setLngLat([point.lng, point.lat])
      .addTo(mapInstance);
    mapMarkers.push(marker);
    bounds.extend([point.lng, point.lat]);
  });
  if (routeLine.value?.coordinates?.length) {
    routeLine.value.coordinates.forEach((coord) => bounds.extend(coord));
  }
  if (!bounds.isEmpty()) {
    mapInstance.fitBounds(bounds, { padding: 80, maxZoom: 13 });
  }
};

const updateRouteLayer = () => {
  if (!mapInstance) return;
  const sourceId = "route-line";
  if (mapInstance.getLayer(sourceId)) {
    mapInstance.removeLayer(sourceId);
  }
  if (mapInstance.getSource(sourceId)) {
    mapInstance.removeSource(sourceId);
  }
  if (routeLine.value) {
    mapInstance.addSource(sourceId, {
      type: "geojson",
      data: {
        type: "Feature",
        geometry: routeLine.value,
      },
    });
    mapInstance.addLayer({
      id: sourceId,
      type: "line",
      source: sourceId,
      layout: {
        "line-join": "round",
        "line-cap": "round",
      },
      paint: {
        "line-color": "#0ea5e9",
        "line-width": 4,
      },
    });
  }
};

onMounted(() => {
  const savedMode = localStorage.getItem(storageKeys.mode);
  if (savedMode && modeOptions.some((item) => item.value === savedMode)) {
    mode.value = savedMode;
  }
  const savedProvider = localStorage.getItem(storageKeys.provider);
  if (savedProvider === "mapbox" || savedProvider === "here" || savedProvider === "custom") {
    provider.value = savedProvider;
  }
  if (provider.value === "custom") {
    const savedAppId = localStorage.getItem(storageKeys.customAppId);
    const savedCredential = localStorage.getItem(storageKeys.customCredential);
    const savedTokenUrl = localStorage.getItem(storageKeys.customTokenUrl);
    const savedGeocodeUrl = localStorage.getItem(storageKeys.customGeocodeUrl);
    const savedRouteUrl = localStorage.getItem(storageKeys.customRouteUrl);
    const savedWebSocketUrl = localStorage.getItem(storageKeys.customWebSocketUrl);
    if (savedAppId) {
      customAppId.value = savedAppId;
    }
    if (savedCredential) {
      customCredential.value = savedCredential;
    }
    if (savedTokenUrl) {
      customTokenUrl.value = savedTokenUrl;
    }
    if (savedGeocodeUrl) {
      customGeocodeUrl.value = savedGeocodeUrl;
    }
    if (savedRouteUrl) {
      customRouteUrl.value = savedRouteUrl;
    }
    if (savedWebSocketUrl) {
      customWebSocketUrl.value = savedWebSocketUrl;
    }
  } else {
    const savedProviderKey = localStorage.getItem(getProviderStorageKey(provider.value));
    if (savedProviderKey) {
      providerApiKey.value = savedProviderKey;
    }
  }
  const savedReverseMode = localStorage.getItem(storageKeys.reverseColumnMode);
  if (savedReverseMode === "single" || savedReverseMode === "separate") {
    reverseColumnMode.value = savedReverseMode;
  }
  const savedReverseColumn = localStorage.getItem(storageKeys.reverseColumnName);
  if (savedReverseColumn) {
    reverseColumnName.value = savedReverseColumn;
  }
  const savedDelimiterMode = localStorage.getItem(storageKeys.reverseDelimiterMode);
  if (savedDelimiterMode === "auto" || savedDelimiterMode === "custom") {
    reverseDelimiterMode.value = savedDelimiterMode;
  }
  const savedDelimiter = localStorage.getItem(storageKeys.reverseDelimiter);
  if (savedDelimiter) {
    reverseDelimiter.value = savedDelimiter;
  }
  const savedRouteInputMode = localStorage.getItem(storageKeys.routeInputMode);
  if (savedRouteInputMode === "address" || savedRouteInputMode === "coordinate") {
    routeInputMode.value = savedRouteInputMode;
  }
  const savedKey = localStorage.getItem(storageKeys.mapboxMap);
  if (savedKey) {
    mapApiKey.value = savedKey;
  }
  if (mapApiKey.value) {
    initMap();
  }
});

watch(provider, (value) => {
  localStorage.setItem(storageKeys.provider, value);
  if (value === "custom") {
    providerApiKey.value = "";
  } else {
    const savedKey = localStorage.getItem(getProviderStorageKey(value));
    providerApiKey.value = savedKey || "";
  }
});

watch(providerApiKey, (value) => {
  if (provider.value === "custom") {
    return;
  }
  const key = getProviderStorageKey(provider.value);
  if (value) {
    localStorage.setItem(key, value);
  } else {
    localStorage.removeItem(key);
  }
});

watch(customAppId, (value) => {
  customToken.value = "";
  if (value) {
    localStorage.setItem(storageKeys.customAppId, value);
  } else {
    localStorage.removeItem(storageKeys.customAppId);
  }
});

watch(customCredential, (value) => {
  customToken.value = "";
  if (value) {
    localStorage.setItem(storageKeys.customCredential, value);
  } else {
    localStorage.removeItem(storageKeys.customCredential);
  }
});

watch(customTokenUrl, (value) => {
  customToken.value = "";
  if (value) {
    localStorage.setItem(storageKeys.customTokenUrl, value);
  } else {
    localStorage.removeItem(storageKeys.customTokenUrl);
  }
});

watch(customGeocodeUrl, (value) => {
  if (value) {
    localStorage.setItem(storageKeys.customGeocodeUrl, value);
  } else {
    localStorage.removeItem(storageKeys.customGeocodeUrl);
  }
});

watch(customRouteUrl, (value) => {
  if (value) {
    localStorage.setItem(storageKeys.customRouteUrl, value);
  } else {
    localStorage.removeItem(storageKeys.customRouteUrl);
  }
});

watch(customWebSocketUrl, (value) => {
  if (value) {
    localStorage.setItem(storageKeys.customWebSocketUrl, value);
  } else {
    localStorage.removeItem(storageKeys.customWebSocketUrl);
  }
});

watch(columnName, (value) => {
  if (value) {
    localStorage.setItem(storageKeys.columnName, value);
  } else {
    localStorage.removeItem(storageKeys.columnName);
  }
});

watch(latColumnName, (value) => {
  if (value) {
    localStorage.setItem(storageKeys.latColumnName, value);
  } else {
    localStorage.removeItem(storageKeys.latColumnName);
  }
});

watch(lngColumnName, (value) => {
  if (value) {
    localStorage.setItem(storageKeys.lngColumnName, value);
  } else {
    localStorage.removeItem(storageKeys.lngColumnName);
  }
});

watch(reverseColumnMode, (value) => {
  if (value) {
    localStorage.setItem(storageKeys.reverseColumnMode, value);
  } else {
    localStorage.removeItem(storageKeys.reverseColumnMode);
  }
});

watch(reverseColumnName, (value) => {
  if (value) {
    localStorage.setItem(storageKeys.reverseColumnName, value);
  } else {
    localStorage.removeItem(storageKeys.reverseColumnName);
  }
});

watch(reverseDelimiterMode, (value) => {
  if (value) {
    localStorage.setItem(storageKeys.reverseDelimiterMode, value);
  } else {
    localStorage.removeItem(storageKeys.reverseDelimiterMode);
  }
});

watch(reverseDelimiter, (value) => {
  if (value) {
    localStorage.setItem(storageKeys.reverseDelimiter, value);
  } else {
    localStorage.removeItem(storageKeys.reverseDelimiter);
  }
});

watch(startColumnName, (value) => {
  if (value) {
    localStorage.setItem(storageKeys.startColumnName, value);
  } else {
    localStorage.removeItem(storageKeys.startColumnName);
  }
});

watch(endColumnName, (value) => {
  if (value) {
    localStorage.setItem(storageKeys.endColumnName, value);
  } else {
    localStorage.removeItem(storageKeys.endColumnName);
  }
});

watch(routeInputMode, (value) => {
  if (value) {
    localStorage.setItem(storageKeys.routeInputMode, value);
  } else {
    localStorage.removeItem(storageKeys.routeInputMode);
  }
});

watch(mode, (value) => {
  localStorage.setItem(storageKeys.mode, value);
  if (value === "reverse" && provider.value === "custom") {
    provider.value = "mapbox";
  }
  resetFileData();
  resetResults();
});
</script>
