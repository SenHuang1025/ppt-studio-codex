import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { defineComponent, h, type Component } from 'vue'

type SlideModule = {
  default: Component
}

type SlideRouteEntry = {
  pageNumber: number
  loader: () => Promise<SlideModule>
}

const slideModules = import.meta.glob<SlideModule>('./slides/page-*.vue')

const slideEntries = Object.entries(slideModules)
  .map(([path, loader]) => {
    const match = path.match(/page-(\d+)\.vue$/)

    if (!match) {
      return null
    }

    return {
      pageNumber: Number(match[1]),
      loader
    } satisfies SlideRouteEntry
  })
  .filter((entry): entry is SlideRouteEntry => entry !== null)
  .sort((left, right) => left.pageNumber - right.pageNumber)

function createStateView(title: string, description: string) {
  return defineComponent({
    name: `${title.replace(/\s+/g, '')}View`,
    setup() {
      return () =>
        h(
          'main',
          {
            style: {
              minHeight: '100vh',
              display: 'grid',
              placeItems: 'center',
              padding: '48px',
              background:
                'radial-gradient(circle at top left, rgba(143, 191, 159, 0.18) 0%, rgba(143, 191, 159, 0) 40%), linear-gradient(180deg, rgba(251, 247, 238, 1) 0%, rgba(245, 236, 215, 1) 100%)',
              color: 'var(--slide-text)',
              fontFamily: 'var(--slide-font-body)'
            }
          },
          [
            h(
              'section',
              {
                style: {
                  width: 'min(560px, 100%)',
                  padding: '36px',
                  borderRadius: '24px',
                  border: '1px solid rgba(194, 186, 166, 0.76)',
                  background: 'rgba(255, 251, 243, 0.9)',
                  boxShadow: 'var(--slide-shadow)'
                }
              },
              [
                h(
                  'p',
                  {
                    style: {
                      margin: '0 0 12px',
                      color: 'var(--slide-text-secondary)',
                      fontSize: '13px',
                      letterSpacing: '0.18em',
                      textTransform: 'uppercase'
                    }
                  },
                  'Preview Sandbox'
                ),
                h(
                  'h1',
                  {
                    style: {
                      margin: '0 0 14px',
                      fontSize: '40px',
                      lineHeight: '1.1',
                      fontFamily: 'var(--slide-font-title)'
                    }
                  },
                  title
                ),
                h(
                  'p',
                  {
                    style: {
                      margin: 0,
                      fontSize: '18px',
                      lineHeight: '1.7',
                      color: 'var(--slide-text-secondary)'
                    }
                  },
                  description
                )
              ]
            )
          ]
        )
    }
  })
}

const emptySlidesView = createStateView(
  'No slides available',
  'Add page-*.vue files under src/slides to render slide routes in the preview sandbox.'
)
const missingSlideView = createStateView(
  'Slide not found',
  'The requested slide route does not currently have a matching page-*.vue file.'
)

const firstPageNumber = slideEntries[0]?.pageNumber ?? null

const routes: RouteRecordRaw[] = [
  firstPageNumber === null
    ? {
        path: '/',
        component: emptySlidesView
      }
    : {
        path: '/',
        redirect: `/slide/${firstPageNumber}`
      },
  ...slideEntries.map(({ pageNumber, loader }) => ({
    path: `/slide/${pageNumber}`,
    name: `slide-${pageNumber}`,
    component: loader
  })),
  {
    path: '/:pathMatch(.*)*',
    component: slideEntries.length > 0 ? missingSlideView : emptySlidesView
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior() {
    return {
      left: 0,
      top: 0
    }
  }
})

export default router
