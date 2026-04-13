import path from 'node:path'
import vue from '@vitejs/plugin-vue'
import { defineConfig, externalizeDepsPlugin } from 'electron-vite'
import UnoCSS from 'unocss/vite'
import AutoImport from 'unplugin-auto-import/vite'
import Components from 'unplugin-vue-components/vite'
import { NaiveUiResolver } from 'unplugin-vue-components/resolvers'

const projectRoot = __dirname
const sourceRoot = path.resolve(projectRoot, 'src')

export default defineConfig({
  main: {
    plugins: [externalizeDepsPlugin()],
    resolve: {
      alias: {
        '@': sourceRoot
      }
    },
    build: {
      outDir: 'out/main',
      rollupOptions: {
        input: {
          index: path.resolve(projectRoot, 'electron/main.ts')
        }
      }
    }
  },
  preload: {
    plugins: [externalizeDepsPlugin()],
    resolve: {
      alias: {
        '@': sourceRoot
      }
    },
    build: {
      outDir: 'out/preload',
      rollupOptions: {
        input: {
          index: path.resolve(projectRoot, 'electron/preload.ts')
        }
      }
    }
  },
  renderer: {
    root: projectRoot,
    resolve: {
      alias: {
        '@': sourceRoot
      }
    },
    build: {
      outDir: 'out/renderer',
      rollupOptions: {
        input: path.resolve(projectRoot, 'index.html')
      }
    },
    plugins: [
      vue(),
      UnoCSS(),
      AutoImport({
        imports: ['vue', 'vue-router', 'pinia'],
        dts: 'src/auto-imports.d.ts',
        vueTemplate: true,
        resolvers: [NaiveUiResolver()]
      }),
      Components({
        dirs: ['src/components', 'src/layouts', 'src/pages'],
        extensions: ['vue'],
        deep: true,
        dts: 'src/components.d.ts',
        resolvers: [NaiveUiResolver()]
      })
    ]
  }
})
