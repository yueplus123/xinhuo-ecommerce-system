<script setup lang="ts">
import { LoginForm } from './components'
import { useDesign } from '@/hooks/web/useDesign'
import { ElScrollbar } from 'element-plus'

const { getPrefixCls } = useDesign()

const prefixCls = getPrefixCls('login')
</script>

<template>
  <div
    :class="prefixCls"
    class="h-[100%] relative lt-xl:bg-[var(--login-bg-color)] lt-sm:px-10px lt-xl:px-10px lt-md:px-10px"
  >
    <ElScrollbar class="h-full">
      <div class="relative flex mx-auto min-h-100vh">
        <div
          :class="`${prefixCls}__left flex-1 bg-gray-500 bg-opacity-20 relative p-30px lt-xl:hidden`"
        >
          <div class="flex items-center justify-center mb-8px">
            <span class="login-brand">薪火电商</span>
          </div>
          <div class="flex justify-center items-center h-[calc(100%-60px)]">
            <Transition appear enter-active-class="animate__animated animate__bounceInLeft">
              <img
                src="@/assets/svgs/login-box-bg.svg"
                alt=""
                class="w-[350px]"
              />
            </Transition>
          </div>
        </div>
        <div class="flex-1 p-30px lt-sm:p-10px dark:bg-[var(--login-bg-color)] relative">
          <div class="flex items-center at-2xl:hidden at-xl:hidden mb-20px">
            <span class="login-brand">薪火电商</span>
          </div>
          <Transition appear enter-active-class="animate__animated animate__bounceInRight">
            <div
              class="h-full flex items-center m-auto w-[100%] at-2xl:max-w-500px at-xl:max-w-500px at-md:max-w-500px at-lg:max-w-500px"
            >
              <LoginForm class="p-20px h-auto m-auto lt-xl:rounded-3xl lt-xl:light:bg-white" />
            </div>
          </Transition>
        </div>
      </div>
    </ElScrollbar>
  </div>
</template>

<style lang="less" scoped>
@prefix-cls: ~'@{adminNamespace}-login';

.@{prefix-cls} {
  overflow: auto;

  &__left {
    &::before {
      position: absolute;
      top: 0;
      left: 0;
      z-index: -1;
      width: 100%;
      height: 100%;
      background-image: url('@/assets/svgs/login-bg.svg');
      background-position: center;
      background-repeat: no-repeat;
      content: '';
    }
  }
}

.login-brand {
  display: block;
  width: 100%;
  text-align: center;
  font-size: 28px;
  font-weight: 700;
  letter-spacing: 0.18em;
  color: #059669;
  line-height: 1.2;
}
</style>
