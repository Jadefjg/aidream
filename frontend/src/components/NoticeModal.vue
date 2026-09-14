<template>
  <div v-if="open" class="modal-mask" @click.self="$emit('close')">
    <div class="modal">
      <div class="card-title">
        <h5>系统公告</h5>
        <button class="icon-btn" @click="$emit('close')">×</button>
      </div>
      <p>欢迎大家使用ThinkAi Token聚合平台，统一接口、多渠道调度、模型持续更新</p>
      <p>GPT官方价格1/17，Claude官方价格1/3</p>
      <p>Image2生图模型1、2、4k分别为，6分、8分、1毛</p>
      <p>进群领新人测试额度/使用Claude满血渠道/开票：418671514</p>
      <div class="notice-actions">
        <button class="ghost-btn" @click="today">今日关闭</button>
        <button class="ghost-btn" @click="$emit('close')">关闭公告</button>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({ open: Boolean });
const emit = defineEmits(["close"]);
function today() {
  sessionStorage.setItem("notice_closed", "1");
  emit("close");
}
</script>
