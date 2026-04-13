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
                <component :is="Component" />
              </MainLayout>
            </RouterView>
          </NMessageProvider>
        </NNotificationProvider>
      </NDialogProvider>
    </NLoadingBarProvider>
  </NConfigProvider>
</template>
