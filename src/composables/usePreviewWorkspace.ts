import { computed, watch, type Ref } from 'vue'
import type { RouteLocationNormalizedLoaded, Router } from 'vue-router'
import type { useWorkspaceStore, WorkspaceMode } from '@/stores/workspaceStore'
import type { PreviewPageItem, RealtimePageGenerationState } from '@/types/preview'
import type { Outline, OutlinePage, ProjectPage } from '@/types/project'
import {
  clampPreviewPageNumber,
  normalizePreviewText,
  parsePreviewPageQuery,
  resolvePreviewPageStatus,
  resolvePreviewPageTitle
} from '@/utils/preview'

type WorkspaceStore = ReturnType<typeof useWorkspaceStore>

interface UsePreviewWorkspaceOptions {
  mode: Ref<WorkspaceMode>
  pageGenerationStates: Ref<Record<number, RealtimePageGenerationState>>
  projectId: Ref<string>
  resolvedOutline: Ref<Outline | null>
  route: RouteLocationNormalizedLoaded
  router: Router
  workspaceStore: WorkspaceStore
}

export function usePreviewWorkspace(options: UsePreviewWorkspaceOptions) {
  const previewThemeError = computed<string | null>(() =>
    options.workspaceStore.previewThemeSyncError || options.workspaceStore.themePresetsError
  )
  const generatedPageMap = computed<Map<number, ProjectPage>>(() =>
    new Map(options.workspaceStore.projectPages.map((page) => [page.page_number, page]))
  )
  const totalPreviewPages = computed<number>(() => {
    const outlineTotal = options.resolvedOutline.value?.total_pages ?? 0
    const projectTotal = options.workspaceStore.project?.total_pages ?? 0
    const highestGeneratedPageNumber =
      options.workspaceStore.projectPages[options.workspaceStore.projectPages.length - 1]?.page_number ?? 0
    const realtimePageNumbers = Object.keys(options.pageGenerationStates.value)
      .map((pageNumber) => Number(pageNumber))
      .filter((pageNumber) => Number.isFinite(pageNumber) && pageNumber > 0)
    const highestRealtimePageNumber = realtimePageNumbers.length > 0 ? Math.max(...realtimePageNumbers) : 0

    return Math.max(outlineTotal, projectTotal, highestGeneratedPageNumber, highestRealtimePageNumber)
  })
  const currentRouteQueryPage = computed<number | null>(() => parsePreviewPageQuery(options.route.query.page))
  const previewRouteQuery = computed<Record<string, string>>(() => ({
    page: String(clampPreviewPageNumber(options.workspaceStore.currentPreviewPage, totalPreviewPages.value))
  }))
  const previewPageItems = computed<PreviewPageItem[]>(() => {
    if (totalPreviewPages.value <= 0) {
      return []
    }

    const outlinePageMap = new Map<number, OutlinePage>(
      (options.resolvedOutline.value?.pages ?? []).map((page) => [page.page_number, page])
    )

    return Array.from({ length: totalPreviewPages.value }, (_, index) => {
      const pageNumber = index + 1
      const outlinePage = outlinePageMap.get(pageNumber) ?? null
      const generatedPage = generatedPageMap.value.get(pageNumber) ?? null
      const realtimeState = options.pageGenerationStates.value[pageNumber]

      return {
        chatMessageCount: generatedPage?.chat_message_count ?? 0,
        contentBrief: normalizePreviewText(outlinePage?.content_brief),
        generatedPage,
        hasGeneratedCode: Boolean(generatedPage?.vue_code?.trim()),
        layout: normalizePreviewText(outlinePage?.layout),
        outlinePage,
        pageNumber,
        pageType: normalizePreviewText(generatedPage?.page_type) || normalizePreviewText(outlinePage?.type),
        status: resolvePreviewPageStatus({
          generatedPage,
          projectStatus: options.workspaceStore.project?.status,
          realtimeState: realtimeState ?? null
        }),
        thumbnailSignature: buildThumbnailSignature(generatedPage),
        title: resolvePreviewPageTitle({
          generatedPage,
          outlinePageTitle: outlinePage?.title,
          pageNumber,
          realtimeTitle: realtimeState?.title ?? null
        }),
        updatedAt: generatedPage?.updated_at ?? null,
        version: generatedPage?.version ?? null
      }
    })
  })
  const currentPageItem = computed<PreviewPageItem | null>(() =>
    previewPageItems.value.find((item) => item.pageNumber === options.workspaceStore.currentPreviewPage)
      ?? previewPageItems.value[0]
      ?? null
  )
  const canGoPrevious = computed<boolean>(() => options.workspaceStore.currentPreviewPage > 1)
  const canGoNext = computed<boolean>(() =>
    totalPreviewPages.value > 0 && options.workspaceStore.currentPreviewPage < totalPreviewPages.value
  )

  watch(
    [() => options.route.name, () => options.route.params.id, currentRouteQueryPage, totalPreviewPages],
    ([routeName, routeProjectId, routePageNumber, pageCount]) => {
      if (!isActivePreviewRoute(routeName, routeProjectId)) {
        return
      }

      const normalizedPageNumber = clampPreviewPageNumber(
        routePageNumber ?? options.workspaceStore.currentPreviewPage,
        pageCount
      )

      if (normalizedPageNumber !== options.workspaceStore.currentPreviewPage) {
        options.workspaceStore.setPreviewPage(normalizedPageNumber)
      }

      void syncPreviewRouteQuery(normalizedPageNumber)
    },
    { immediate: true }
  )

  watch(
    [() => options.workspaceStore.currentPreviewPage, totalPreviewPages, () => options.route.name, () => options.route.params.id],
    ([currentPageNumber, pageCount, routeName, routeProjectId]) => {
      if (!isActivePreviewRoute(routeName, routeProjectId)) {
        return
      }

      const normalizedPageNumber = clampPreviewPageNumber(currentPageNumber, pageCount)

      if (normalizedPageNumber !== currentPageNumber) {
        options.workspaceStore.setPreviewPage(normalizedPageNumber)
        return
      }

      void syncPreviewRouteQuery(normalizedPageNumber)
    },
    { immediate: true }
  )

  function selectPage(pageNumber: number): void {
    setPreviewPage(pageNumber)
  }

  function goToPreviousPage(): void {
    if (!canGoPrevious.value) {
      return
    }

    setPreviewPage(options.workspaceStore.currentPreviewPage - 1)
  }

  function goToNextPage(): void {
    if (!canGoNext.value) {
      return
    }

    setPreviewPage(options.workspaceStore.currentPreviewPage + 1)
  }

  function setPreviewPage(pageNumber: number): void {
    const normalizedPageNumber = clampPreviewPageNumber(pageNumber, totalPreviewPages.value)

    if (normalizedPageNumber !== options.workspaceStore.currentPreviewPage) {
      options.workspaceStore.setPreviewPage(normalizedPageNumber)
    }

    void syncPreviewRouteQuery(normalizedPageNumber)
  }

  function isActivePreviewRoute(routeName: unknown, routeProjectId: unknown): boolean {
    return routeName === 'project-preview'
      && String(routeProjectId ?? '') === options.projectId.value
      && options.mode.value === 'preview'
  }

  async function syncPreviewRouteQuery(pageNumber: number): Promise<void> {
    if (!isActivePreviewRoute(options.route.name, options.route.params.id)) {
      return
    }

    const normalizedPageNumber = String(clampPreviewPageNumber(pageNumber, totalPreviewPages.value))
    const currentQueryPage = Array.isArray(options.route.query.page)
      ? options.route.query.page[0]
      : options.route.query.page

    if (currentQueryPage === normalizedPageNumber) {
      return
    }

    await options.router.replace({
      name: 'project-preview',
      params: {
        id: options.projectId.value
      },
      query: {
        ...options.route.query,
        page: normalizedPageNumber
      }
    }).catch(() => undefined)
  }

  return {
    canGoNext,
    canGoPrevious,
    currentPageItem,
    previewPageItems,
    previewRouteQuery,
    previewThemeError,
    selectPage,
    goToNextPage,
    goToPreviousPage,
    totalPreviewPages
  }
}

function buildThumbnailSignature(generatedPage: ProjectPage | null): string | null {
  if (!generatedPage) {
    return null
  }

  return [
    generatedPage.version,
    generatedPage.thumbnail_updated_at || generatedPage.updated_at
  ].join(':')
}
