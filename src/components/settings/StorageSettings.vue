<script setup lang="ts">
import { NButton, NForm, NFormItem, NInput } from 'naive-ui'

defineProps<{
  storagePath: string
}>()
</script>

<template>
  <div class="space-y-5">
    <div>
      <p class="mono-meta mb-2 text-[color:var(--app-text-tertiary)]">存储路径</p>
      <h2 class="m-0 text-2xl font-semibold">本地项目目录</h2>
      <p class="mt-3 text-sm leading-7 text-[color:var(--app-text-secondary)]">
        当前阶段先展示 Python Sidecar 使用的项目存储根目录，避免在 Phase 1 提前引入目录迁移、数据搬运和权限处理。
      </p>
    </div>

    <NForm label-placement="top">
      <NFormItem label="项目存储路径">
        <NInput :value="storagePath" readonly />
      </NFormItem>
    </NForm>

    <div class="flex flex-wrap items-start justify-between gap-3 rounded-[var(--radius-xl)] border border-[color:var(--app-border-subtle)] bg-[color:var(--surface-editor)] p-4">
      <div class="text-sm leading-7 text-[color:var(--app-text-secondary)]">
        路径展示已经接通真实后端配置。目录选择与迁移策略会放在后续阶段实现，本次不写入数据库也不变更现有 SQLite 方案。
      </div>
      <NButton secondary strong disabled>选择目录（后续）</NButton>
    </div>
  </div>
</template>
