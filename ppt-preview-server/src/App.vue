<script setup lang="ts">
import { onBeforeUnmount, onMounted } from 'vue'

type IframeScrollSnapshotElement = {
  left: number
  path: string
  top: number
}

type IframeScrollSnapshot = {
  elements: IframeScrollSnapshotElement[]
  window: {
    left: number
    top: number
  }
}

type HostMessageEnvelope = {
  id?: string
  payload?: unknown
  source?: string
  type?: string
}

const PREVIEW_IFRAME_MESSAGE_SOURCE = 'ppt-studio-preview-frame'
const PREVIEW_IFRAME_MESSAGE_TARGET = 'ppt-studio-host'

onMounted(() => {
  window.addEventListener('message', handleHostMessage)
})

onBeforeUnmount(() => {
  window.removeEventListener('message', handleHostMessage)
})

function handleHostMessage(event: MessageEvent<unknown>): void {
  const data = event.data as HostMessageEnvelope | null

  if (!data || data.source !== PREVIEW_IFRAME_MESSAGE_TARGET || typeof data.type !== 'string') {
    return
  }

  if (data.type === 'request-preview-scroll-snapshot' && typeof data.id === 'string') {
    window.parent.postMessage(
      {
        id: data.id,
        payload: collectScrollSnapshot(),
        source: PREVIEW_IFRAME_MESSAGE_SOURCE,
        type: 'preview-scroll-snapshot'
      },
      '*'
    )
    return
  }

  if (data.type === 'restore-preview-scroll-snapshot' && isIframeScrollSnapshot(data.payload)) {
    restoreScrollSnapshot(data.payload)
  }
}

function collectScrollSnapshot(): IframeScrollSnapshot {
  const scrollElements = Array.from(document.querySelectorAll<HTMLElement>('*'))
    .filter((element) => element.scrollTop !== 0 || element.scrollLeft !== 0)
    .map((element) => ({
      left: element.scrollLeft,
      path: buildElementPath(element),
      top: element.scrollTop
    }))

  return {
    elements: scrollElements,
    window: {
      left: window.scrollX,
      top: window.scrollY
    }
  }
}

function restoreScrollSnapshot(snapshot: IframeScrollSnapshot): void {
  window.requestAnimationFrame(() => {
    window.scrollTo({
      left: snapshot.window.left,
      top: snapshot.window.top
    })

    for (const item of snapshot.elements) {
      const target = resolveElementByPath(item.path)
      if (!(target instanceof HTMLElement)) {
        continue
      }

      target.scrollLeft = item.left
      target.scrollTop = item.top
    }
  })
}

function buildElementPath(element: HTMLElement): string {
  const segments: string[] = []
  let current: HTMLElement | null = element

  while (current && current !== document.body) {
    const parent: HTMLElement | null = current.parentElement
    if (!parent) {
      break
    }

    const tagName = current.tagName.toLowerCase()
    const siblings = Array.from(parent.children as HTMLCollectionOf<Element>).filter(
      (child: Element) => child.tagName.toLowerCase() === tagName
    )
    const index = siblings.indexOf(current)
    segments.unshift(`${tagName}:${index}`)
    current = parent
  }

  return segments.join('>')
}

function resolveElementByPath(path: string): Element | null {
  if (!path) {
    return null
  }

  let current: Element | null = document.body
  for (const segment of path.split('>')) {
    const [tagName, indexValue] = segment.split(':')
    const index = Number.parseInt(indexValue ?? '', 10)

    if (!current || !Number.isFinite(index)) {
      return null
    }

    const candidates: Element[] = Array.from(current.children as HTMLCollectionOf<Element>).filter(
      (child: Element) => child.tagName.toLowerCase() === tagName
    )
    current = candidates[index] ?? null
  }

  return current
}

function isIframeScrollSnapshot(value: unknown): value is IframeScrollSnapshot {
  if (!value || typeof value !== 'object') {
    return false
  }

  const candidate = value as Record<string, unknown>
  const windowSnapshot = candidate.window

  return Array.isArray(candidate.elements)
    && typeof windowSnapshot === 'object'
    && windowSnapshot !== null
    && typeof (windowSnapshot as Record<string, unknown>).left === 'number'
    && typeof (windowSnapshot as Record<string, unknown>).top === 'number'
}
</script>

<template>
  <RouterView />
</template>
