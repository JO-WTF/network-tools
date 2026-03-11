<template>
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
</template>

<script setup>
defineProps({ logs: { type: Array, required: true } });
</script>
