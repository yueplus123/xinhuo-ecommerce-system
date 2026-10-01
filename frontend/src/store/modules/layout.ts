import { defineStore } from 'pinia'

export const useLayoutStore = defineStore('layout', {
  state: () => ({
    dataScreenImmersive: false
  }),
  actions: {
    setDataScreenImmersive(v: boolean) {
      this.dataScreenImmersive = !!v
    },
    exitDataScreenImmersive() {
      this.dataScreenImmersive = false
    }
  }
})
