<script setup lang="ts">
// 教程+话术：新的「教程+话术」（职员端同名页面的内容）和旧的教程池 / 话术池 / SKU 快捷话术合在一个入口，用标签切换。
// 旧的三个暂时保留（商品编辑、机器人还在用），确认新的没问题后再删除。
import { ref } from 'vue'
import { ElAlert, ElTabPane, ElTabs } from 'element-plus'
import ContentWrap from '@/components/ContentWrap.vue'
import KnowledgeManager from './KnowledgeManager.vue'
import TutorialPoolPage from './TutorialPoolPage.vue'
import PhrasePoolPage from './PhrasePoolPage.vue'
import QuickPhrasePage from './QuickPhrasePage.vue'

defineOptions({ name: 'ManageKnowledge' })

const props = defineProps<{ tab?: string }>()
const active = ref(props.tab || 'knowledge')
</script>

<template>
  <ContentWrap title="教程+话术">
    <ElTabs v-model="active">
      <ElTabPane label="教程+话术（问答 / 教程 / 快捷语）" name="knowledge" lazy>
        <KnowledgeManager v-if="active === 'knowledge'" />
      </ElTabPane>
      <ElTabPane label="教程池（旧）" name="tutorial-pool" lazy>
        <ElAlert type="info" :closable="false" show-icon class="old-tip" title="旧数据：商品编辑和机器人还在用，确认新的「教程+话术」没问题后再删除。" />
        <TutorialPoolPage v-if="active === 'tutorial-pool'" />
      </ElTabPane>
      <ElTabPane label="话术池（旧）" name="phrase-pool" lazy>
        <ElAlert type="info" :closable="false" show-icon class="old-tip" title="旧数据：商品编辑时从这里选话术。" />
        <PhrasePoolPage v-if="active === 'phrase-pool'" />
      </ElTabPane>
      <ElTabPane label="SKU 快捷话术（旧）" name="quick-phrases" lazy>
        <ElAlert type="info" :closable="false" show-icon class="old-tip" title="旧数据：「业务+价格」详情里「复制话术」按钮复制的是这里的话术。" />
        <QuickPhrasePage v-if="active === 'quick-phrases'" />
      </ElTabPane>
    </ElTabs>
  </ContentWrap>
</template>

<style scoped>
.old-tip {
  margin-bottom: 12px;
}
</style>
