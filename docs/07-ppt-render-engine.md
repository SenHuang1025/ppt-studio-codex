# PPT 渲染引擎方案

## 核心挑战
Agent 生成的是 Vue3 SFC 源代码字符串，需要在前端实时编译并渲染为可交互的页面。

## 方案选择：iframe + 本地 Vite Dev Server

### 原理

```text
Agent 生成 Vue SFC 代码
    ↓
Python 后端写入文件 pages/page-{n}.vue
    ↓
本地 Vite Dev Server 监听文件变更 (HMR)
    ↓
前端 iframe 加载 http://localhost:18921/slide/{n}
    ↓
文件更新时 Vite HMR 自动热刷新 iframe 内容
```

### 架构

```text
python-backend/
    写入 → ppt-preview-server/src/slides/page-{n}.vue

ppt-preview-server/          # 独立的 Vite 项目（预览沙箱）
├── src/
│   ├── main.ts
│   ├── App.vue
│   ├── router.ts            # /slide/1, /slide/2, ...
│   ├── slides/
│   │   ├── page-1.vue
│   │   ├── page-2.vue
│   │   └── ...
│   ├── theme/
│   │   └── variables.css
│   └── components/
│       ├── CountUp.vue
│       ├── AnimatedChart.vue
│       └── ...
├── package.json              # 预装 echarts, gsap, @vueuse/motion
└── vite.config.ts
```

### 预览 Vite 项目配置

```ts
// ppt-preview-server/vite.config.ts
import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 18921,
    strictPort: true,
    host: "127.0.0.1",
  },
});
```

### 预览路由

```ts
// ppt-preview-server/src/router.ts
import { createRouter, createWebHistory } from "vue-router";

const slideModules = import.meta.glob("./slides/page-*.vue");

const routes = Object.entries(slideModules).map(([path, component]) => {
  const pageNumber = path.match(/page-(\d+)\.vue/)?.[1];
  return {
    path: `/slide/${pageNumber}`,
    component,
  };
});

export default createRouter({
  history: createWebHistory(),
  routes,
});
```

### 前端 iframe 集成

```vue
<!-- src/components/preview/SlideRenderer.vue -->
<template>
  <div class="slide-renderer" ref="containerRef">
    <iframe
      ref="iframeRef"
      :src="`http://127.0.0.1:18921/slide/${pageNumber}`"
      sandbox="allow-scripts allow-same-origin"
      :style="iframeStyle"
      @load="onIframeLoad"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useElementSize } from "@vueuse/core";

const props = defineProps<{
  pageNumber: number;
}>();

const containerRef = ref<HTMLElement>();
const iframeRef = ref<HTMLIFrameElement>();
const { width: containerWidth, height: containerHeight } = useElementSize(containerRef);

const SLIDE_WIDTH = 1920;
const SLIDE_HEIGHT = 1080;

const iframeStyle = computed(() => {
  const scaleX = containerWidth.value / SLIDE_WIDTH;
  const scaleY = containerHeight.value / SLIDE_HEIGHT;
  const scale = Math.min(scaleX, scaleY);

  return {
    width: `${SLIDE_WIDTH}px`,
    height: `${SLIDE_HEIGHT}px`,
    transform: `scale(${scale})`,
    transformOrigin: "top left",
  };
});

watch(() => props.pageNumber, () => {
  if (iframeRef.value) {
    iframeRef.value.src = `http://127.0.0.1:18921/slide/${props.pageNumber}`;
  }
});
</script>
```

### 主题注入

```css
/* ppt-preview-server/src/theme/variables.css */
/* Python 后端在切换主题时重写此文件，触发 HMR */
:root {
  --slide-primary: #1a73e8;
  --slide-secondary: #4285f4;
  --slide-accent: #ea4335;
  --slide-bg: #ffffff;
  --slide-text: #202124;
  --slide-text-secondary: #5f6368;
  --slide-font-title: "Inter", sans-serif;
  --slide-font-body: "Inter", sans-serif;
}
```

### 缩略图生成

```python
# python-backend/app/services/thumbnail_service.py
# 使用 Playwright 截图生成缩略图

from playwright.async_api import async_playwright


async def generate_thumbnail(page_number: int, project_id: str) -> str:
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1920, "height": 1080})
        await page.goto(f"http://127.0.0.1:18921/slide/{page_number}")
        await page.wait_for_load_state("networkidle")

        thumbnail_path = f"projects/{project_id}/thumbnails/page-{page_number}.png"
        await page.screenshot(path=thumbnail_path)
        await browser.close()

        return thumbnail_path
```

### Agent 生成代码时可用的组件和库

Agent 生成页面代码时，以下库和组件可直接 import 使用：

预装 npm 包：
- `vue`（Composition API）
- `echarts` + `vue-echarts`
- `gsap`
- `@vueuse/motion`
- `@vueuse/core`

预装自定义组件（在 `components/` 目录下）：
- `CountUp`：数字滚动动画
- `AnimatedChart`：封装的动画图表
- `ProgressBar`：进度条
- `IconCard`：图标卡片
- `DataTable`：数据表格
- `TimelineItem`：时间线节点
- `QuoteBlock`：引用块

CSS 变量（通过 `theme/variables.css` 全局注入）：
- `--slide-primary`
- `--slide-secondary`
- `--slide-accent`
- `--slide-bg`
- `--slide-text`
- `--slide-text-secondary`

每个 slide 组件的根元素应该是：

```html
<div class="slide" style="width: 1920px; height: 1080px; overflow: hidden;">
```
