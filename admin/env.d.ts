/// <reference types="vite/client" />

declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<object, object, any>
  export default component
}

/** 通用「键值对象」类型（职员端有同名全局类型，这里保持一致，页面代码可原样搬用） */
declare type Recordable<T = any> = Record<string, T>
