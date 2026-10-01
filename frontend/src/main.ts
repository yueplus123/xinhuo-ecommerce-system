import './styles/xinhuo-legacy.css'
import 'vue/jsx'

// 寮曞叆windi css
import '@/plugins/unocss'

// 瀵煎叆鍏ㄥ眬鐨剆vg鍥炬爣
import '@/plugins/svgIcon'

// 鍒濆鍖栧璇█
import { setupI18n } from '@/plugins/vueI18n'

// 寮曞叆鐘舵€佺鐞?
import { setupStore } from '@/store'

// 鍏ㄥ眬缁勪欢
import { setupGlobCom } from '@/components'

// 寮曞叆element-plus
import { setupElementPlus } from '@/plugins/elementPlus'

// 寮曞叆鍏ㄥ眬鏍峰紡
import '@/styles/index.less'

// 寮曞叆鍔ㄧ敾
import '@/plugins/animate.css'

// 璺敱
import { setupRouter } from './router'

// 鏉冮檺
import { setupPermission } from './directives'

import { createApp } from 'vue'

import App from './App.vue'

import './permission'

// 鍒涘缓瀹炰緥
const setupAll = async () => {
  const app = createApp(App)

  await setupI18n(app)

  setupStore(app)

  setupGlobCom(app)

  setupElementPlus(app)

  setupRouter(app)

  setupPermission(app)

  app.mount('#app')
}

setupAll()

