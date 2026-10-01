import { resolve } from 'path'
import { loadEnv } from 'vite'
import type { UserConfig, ConfigEnv } from 'vite'
import Vue from '@vitejs/plugin-vue'
import VueJsx from '@vitejs/plugin-vue-jsx'
import react from '@vitejs/plugin-react'
import progress from 'vite-plugin-progress'
import { ViteEjsPlugin } from 'vite-plugin-ejs'
import VueI18nPlugin from '@intlify/unplugin-vue-i18n/vite'
import { createSvgIconsPlugin } from 'vite-plugin-svg-icons'
import UnoCSS from 'unocss/vite'
import { visualizer } from 'rollup-plugin-visualizer'

// https://vitejs.dev/config/
const root = process.cwd()

function pathResolve(dir: string) {
  return resolve(root, '.', dir)
}

export default ({ command, mode }: ConfigEnv): UserConfig => {
  let env = {} as any
  const isBuild = command === 'build'
  if (!isBuild) {
    env = loadEnv(process.argv[3] === '--mode' ? process.argv[4] : process.argv[3], root)
  } else {
    env = loadEnv(mode, root)
  }
  return {
    base: env.VITE_BASE_PATH,
    plugins: [
      Vue({
        script: {
          // 开启defineModel
          defineModel: true
        }
      }),
      // 必须先让 React 处理 ledger-app；路径兼容 Windows 反斜杠
      react({
        include: [/[/\\]ledger-app[/\\].*\.[jt]sx$/],
        exclude: [/node_modules/],
        jsxRuntime: 'automatic',
        jsxImportSource: 'react'
      }),
      // Vue JSX：覆盖 src 下所有 Vue JSX / `<script lang="tsx">`，唯独排除记账 React
      VueJsx({
        include: [
          /[/\\]src[/\\].*\.[jt]sx$/,
          /\.vue\?[^\n]*lang\.[jt]sx/
        ],
        exclude: [/[/\\]ledger-app[/\\]/]
      }),
      // 仅对 ledger-app 启用 React JSX；其它文件留给 Vue JSX，避免登录页 [object Object]
      {
        name: 'fix-esbuild-jsx-for-react-ledger',
        config() {
          return {
            esbuild: {
              include: [/[/\\]ledger-app[/\\].*\.[jt]sx$/],
              jsx: 'automatic',
              jsxImportSource: 'react'
            }
          }
        }
      },
      // 构建后自检：禁止再出现「小体积 Vue JSX helper 被 mount 引用」
      {
        name: 'assert-ledger-uses-react-jsx',
        generateBundle(_opts, bundle) {
          const isVueJsxHelper = (code: string) =>
            code.length < 800 &&
            /delete \w+\.children/.test(code) &&
            /from\s*["'][^"']*vue-chunks/.test(code)

          const mountChunks = Object.entries(bundle).filter(
            ([fileName, chunk]) =>
              chunk.type === 'chunk' &&
              /assets\/mount-[^/]+\.js$/.test(fileName.replace(/\\/g, '/')) &&
              /mountLedgerApp/.test((chunk as any).code || '')
          )
          if (!mountChunks.length) {
            throw new Error('[ledger-jsx] mountLedgerApp chunk not found in bundle')
          }
          for (const [fileName, chunk] of mountChunks) {
            const imports: string[] = (chunk as any).imports || []
            for (const imp of imports) {
              const key = Object.keys(bundle).find(
                (k) => k === imp || k.endsWith('/' + imp) || k.replace(/\\/g, '/') === imp
              )
              if (!key) continue
              const imported = bundle[key]
              if (imported.type !== 'chunk') continue
              if (isVueJsxHelper(imported.code || '')) {
                throw new Error(
                  `[ledger-jsx] ${fileName} imports Vue JSX helper ${key}; React ledger would white-screen`
                )
              }
            }
          }
        }
      },
      // ServerUrlCopy 会拖慢启动，开发环境关掉
      // progress 保留轻量进度即可
      progress(),
      VueI18nPlugin({
        runtimeOnly: true,
        compositionOnly: true,
        include: [resolve(__dirname, 'src/locales/**')]
      }),
      createSvgIconsPlugin({
        iconDirs: [pathResolve('src/assets/svgs')],
        symbolId: 'icon-[dir]-[name]',
        svgoOptions: true
      }),
      // 去掉 PurgeIcons：扫描 @iconify/json 会显著拖慢启动
      ViteEjsPlugin({
        title: env.VITE_APP_DOCUMENT_TITLE || '薪火电商管理系统'
      }),
      UnoCSS()
    ],

    css: {
      preprocessorOptions: {
        less: {
          additionalData: '@import "./src/styles/variables.module.less";',
          javascriptEnabled: true
        }
      }
    },
    resolve: {
      extensions: ['.mjs', '.js', '.ts', '.jsx', '.tsx', '.json', '.less', '.css'],
      dedupe: ['react', 'react-dom'],
      alias: [
        {
          find: 'vue-i18n',
          replacement: 'vue-i18n/dist/vue-i18n.cjs.js'
        },
        {
          find: /\@\//,
          replacement: `${pathResolve('src')}/`
        }
      ]
    },
    esbuild: {
      pure: env.VITE_DROP_CONSOLE === 'true' ? ['console.log'] : undefined,
      drop: env.VITE_DROP_DEBUGGER === 'true' ? ['debugger'] : undefined
    },
    build: {
      target: 'es2015',
      outDir: env.VITE_OUT_DIR || 'dist',
      sourcemap: env.VITE_SOURCEMAP === 'true',
      // brotliSize: false,
      rollupOptions: {
        plugins: env.VITE_USE_BUNDLE_ANALYZER === 'true' ? [visualizer()] : undefined,
        // 拆包
        output: {
          manualChunks: {
            'vue-chunks': ['vue', 'vue-router', 'pinia', 'vue-i18n'],
            'element-plus': ['element-plus'],
            'wang-editor': ['@wangeditor/editor', '@wangeditor/editor-for-vue'],
            echarts: ['echarts', 'echarts-wordcloud']
          }
        }
      },
      cssCodeSplit: !(env.VITE_USE_CSS_SPLIT === 'false'),
      cssTarget: ['chrome31']
    },
    server: {
      port: 5173,
      proxy: {
        '/api': {
          target: process.env.VITE_API_PROXY_TARGET || 'http://127.0.0.1:8001',
          changeOrigin: true,
          configure: (proxy) => {
            proxy.on('error', (err, _req, res) => {
              const r = res as { writeHead?: Function; end?: Function; headersSent?: boolean }
              if (!r || typeof r.writeHead !== 'function' || r.headersSent) return
              r.writeHead(502, { 'Content-Type': 'application/json; charset=utf-8' })
              r.end(
                JSON.stringify({
                  detail:
                    '后端未启动或无法连接（请运行：python backend/manage.py runserver 8001）',
                  proxy_error: String((err as Error)?.message || err)
                })
              )
            })
          }
        },
        '/media': {
          target: process.env.VITE_API_PROXY_TARGET || 'http://127.0.0.1:8001',
          changeOrigin: true
        },
        '/ledger-api': {
          target: process.env.VITE_LEDGER_PROXY_TARGET || 'http://127.0.0.1:3001',
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/ledger-api/, '') || '/'
        }
      },
      hmr: {
        overlay: false
      },
      host: '0.0.0.0'
    },
    optimizeDeps: {
      include: [
        'vue',
        'vue-router',
        'vue-types',
        'element-plus',
        'element-plus/es',
        'element-plus/es/locale/lang/zh-cn',
        'element-plus/es/locale/lang/en',
        '@vueuse/core',
        'axios',
        'qs',
        'echarts',
        'dayjs',
        'lodash-es',
        'pinia',
        'pinia-plugin-persistedstate'
      ]
    }
  }
}
