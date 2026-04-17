<script setup lang="ts">
import {
  NConfigProvider,
  NDialogProvider,
  NGlobalStyle,
  NLoadingBarProvider,
  NMessageProvider,
  NNotificationProvider,
  lightTheme
} from 'naive-ui'
import { RouterView } from 'vue-router'
import ErrorBoundary from '@/components/common/ErrorBoundary.vue'
import MainLayout from '@/layouts/MainLayout.vue'
import { naiveThemeOverrides } from '@/utils/naive-theme'
</script>

<template>
  <NConfigProvider :theme="lightTheme" :theme-overrides="naiveThemeOverrides">
    <NLoadingBarProvider>
      <NDialogProvider>
        <NNotificationProvider>
          <NMessageProvider>
            <NGlobalStyle />
            <RouterView v-slot="{ Component }">
              <MainLayout>
                <ErrorBoundary title="页面渲染失败" description="当前页面渲染异常，请重试或切换到其他页面后返回。">
                  <component :is="Component" />
                </ErrorBoundary>
              </MainLayout>
            </RouterView>
          </NMessageProvider>
        </NNotificationProvider>
      </NDialogProvider>
    </NLoadingBarProvider>
  </NConfigProvider>
</template>
