<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { getNodeTemplate, listProviders, listTools, type ProviderInfo } from '../api'
import { getSchemaFieldOptions } from '../composables/nodeSchemaFields'
import {
  getSettingsSection,
  listSettingsSections,
  updateSettingsSection,
  type SettingsDocument,
  type SettingsSectionInfo,
} from '../settingsApi'
import CompanionSettingsForm from './settings/CompanionSettingsForm.vue'
import type { CompanionCapabilityOption } from './settings/CompanionCapabilitySelect.vue'
import DefaultSettingsForm from './settings/DefaultSettingsForm.vue'
import ModuleProviderSettingsForm from './settings/ModuleProviderSettingsForm.vue'

const props = withDefaults(defineProps<{
  backLabel?: string
}>(), {
  backLabel: 'Board',
})

const emit = defineEmits<{
  back: []
  providersUpdated: []
}>()

const sections = ref<SettingsSectionInfo[]>([])
const activeSection = ref('module-provider')
const loadedDocument = ref<SettingsDocument | null>(null)
const editorContent = ref('')
const advancedMode = ref(false)
const loading = ref(false)
const saving = ref(false)
const error = ref('')
const status = ref('')
const providers = ref<ProviderInfo[]>([])
const availableTools = ref<string[]>([])
const companionCapabilityOptions = ref<Record<string, CompanionCapabilityOption[]>>({})

const currentSection = computed(() => {
  return sections.value.find((item) => item.id === activeSection.value) || null
})

const activeLabel = computed(() => {
  if (activeSection.value === 'module-provider') return 'moduleProvider'
  if (activeSection.value === 'defaults') return 'Default settings'
  if (activeSection.value === 'companion') return 'Companion'
  return currentSection.value?.label || activeSection.value
})

const dirty = computed(() => editorContent.value !== String(loadedDocument.value?.content || ''))

const formData = computed<Record<string, unknown> | null>(() => {
  try {
    const parsed = JSON.parse(editorContent.value || '{}')
    return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? parsed as Record<string, unknown> : null
  } catch {
    return null
  }
})

function labelFor(section: SettingsSectionInfo) {
  if (section.id === 'module-provider') return 'moduleProvider'
  if (section.id === 'defaults') return 'Default settings'
  if (section.id === 'companion') return 'Companion'
  return section.label
}

function replaceData(data: Record<string, unknown>) {
  editorContent.value = `${JSON.stringify(data, null, 2)}\n`
  status.value = ''
  error.value = ''
}

async function loadCatalog() {
  const [nextProviders, nextTools] = await Promise.all([
    listProviders(),
    listTools(),
  ])
  providers.value = nextProviders
  availableTools.value = nextTools
}

async function loadCatalogForForms() {
  try {
    await loadCatalog()
    await loadCompanionCapabilityOptions()
  } catch (e: any) {
    error.value = String(e?.message || e)
  }
}

async function loadCompanionCapabilityOptions() {
  const template = await getNodeTemplate('agent_node')
  const schema = template.schema || {}
  companionCapabilityOptions.value = {
    tools: getSchemaFieldOptions(schema, 'tools'),
    mcp_servers: getSchemaFieldOptions(schema, 'mcp_servers'),
    skills: getSchemaFieldOptions(schema, 'skills'),
    plugins: getSchemaFieldOptions(schema, 'plugins'),
  }
}

async function loadSections() {
  sections.value = await listSettingsSections()
  if (!sections.value.some((item) => item.id === activeSection.value)) {
    activeSection.value = sections.value[0]?.id || 'module-provider'
  }
}

async function loadSection(sectionId = activeSection.value) {
  loading.value = true
  error.value = ''
  status.value = ''
  try {
    activeSection.value = sectionId
    const document = await getSettingsSection(sectionId)
    loadedDocument.value = document
    editorContent.value = document.content
    advancedMode.value = false
  } catch (e: any) {
    error.value = String(e?.message || e)
  } finally {
    loading.value = false
  }
}

async function selectSection(sectionId: string) {
  if (sectionId === activeSection.value) return
  await loadSection(sectionId)
}

function formatJson() {
  error.value = ''
  status.value = ''
  try {
    const parsed = JSON.parse(editorContent.value)
    editorContent.value = `${JSON.stringify(parsed, null, 2)}\n`
  } catch (e: any) {
    error.value = String(e?.message || e)
  }
}

async function saveSection() {
  if (saving.value) return
  saving.value = true
  error.value = ''
  status.value = ''
  try {
    const document = await updateSettingsSection(activeSection.value, editorContent.value)
    loadedDocument.value = document
    editorContent.value = document.content
    status.value = 'Saved'
    if (activeSection.value === 'module-provider') {
      emit('providersUpdated')
      await loadCatalogForForms()
    } else if (activeSection.value === 'defaults') {
      await loadCompanionCapabilityOptions()
    }
  } catch (e: any) {
    error.value = String(e?.message || e)
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  try {
    await loadSections()
    await loadSection(activeSection.value)
    await loadCatalogForForms()
  } catch (e: any) {
    error.value = String(e?.message || e)
  }
})
</script>

<template>
  <section class="settings-page">
    <header class="settings-head">
      <div class="settings-title-wrap">
        <h1>Settings</h1>
        <div class="settings-path">{{ loadedDocument?.path || currentSection?.path || '' }}</div>
      </div>
      <div class="settings-head-actions">
        <button type="button" class="settings-btn" @click="emit('back')">{{ props.backLabel }}</button>
      </div>
    </header>

    <div class="settings-body">
      <nav class="settings-tabs" aria-label="Settings sections">
        <button
          v-for="section in sections"
          :key="section.id"
          type="button"
          class="settings-tab"
          :class="{ active: activeSection === section.id }"
          @click="selectSection(section.id)"
        >
          {{ labelFor(section) }}
        </button>
      </nav>

      <main class="settings-editor">
        <div class="editor-toolbar">
          <div class="editor-title">
            <span>{{ activeLabel }}</span>
            <span v-if="dirty" class="editor-state">Unsaved</span>
            <span v-else-if="status" class="editor-state saved">{{ status }}</span>
          </div>
          <div class="editor-actions">
            <button type="button" class="settings-btn" :disabled="loading || saving" @click="loadSection()">Reload</button>
            <button type="button" class="settings-btn" :disabled="loading || saving" @click="advancedMode = !advancedMode">
              {{ advancedMode ? 'Form' : 'Advanced JSON' }}
            </button>
            <button v-if="advancedMode" type="button" class="settings-btn" :disabled="loading || saving" @click="formatJson">Format</button>
            <button type="button" class="settings-btn primary" :disabled="loading || saving || !dirty" @click="saveSection">
              {{ saving ? 'Saving...' : 'Save' }}
            </button>
          </div>
        </div>

        <textarea
          v-if="advancedMode"
          v-model="editorContent"
          class="json-editor"
          spellcheck="false"
          :disabled="loading || saving"
          :aria-label="`${activeLabel} JSON`"
        ></textarea>

        <template v-else>
          <ModuleProviderSettingsForm
            v-if="activeSection === 'module-provider' && formData"
            :data="formData"
            @update:data="replaceData"
          />
          <DefaultSettingsForm
            v-else-if="activeSection === 'defaults' && formData"
            :data="formData"
            @update:data="replaceData"
          />
          <CompanionSettingsForm
            v-else-if="activeSection === 'companion' && formData"
            :data="formData"
            :providers="providers"
            :available-tools="availableTools"
            :capability-options="companionCapabilityOptions"
            @update:data="replaceData"
          />
          <div v-else class="settings-error">Invalid JSON. Switch to Advanced JSON to fix it.</div>
        </template>

        <div v-if="error" class="settings-error">{{ error }}</div>
      </main>
    </div>
  </section>
</template>

<style scoped>
.settings-page {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  padding: 14px;
  gap: 12px;
}

.settings-head {
  flex: 0 0 auto;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.settings-title-wrap {
  min-width: 0;
}

.settings-title-wrap h1 {
  margin: 0;
  font-size: 20px;
  line-height: 1.2;
}

.settings-path {
  margin-top: 6px;
  color: rgba(148, 163, 184, 0.9);
  font-family: Consolas, 'Cascadia Mono', monospace;
  font-size: 12px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: min(880px, 70vw);
}

.settings-head-actions,
.editor-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.settings-body {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: 180px minmax(0, 1fr);
  gap: 12px;
}

.settings-tabs {
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 10px;
  border-right: 1px solid rgba(148, 163, 184, 0.18);
}

.settings-tab {
  width: 100%;
  min-height: 34px;
  text-align: left;
  border-color: rgba(148, 163, 184, 0.2);
  background: rgba(15, 23, 42, 0.52);
}

.settings-tab.active {
  border-color: rgba(56, 189, 248, 0.65);
  background: rgba(14, 165, 233, 0.18);
  color: rgba(224, 242, 254, 0.98);
}

.settings-editor {
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.editor-toolbar {
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.editor-title {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
  font-size: 14px;
  font-weight: 700;
}

.editor-state {
  border: 1px solid rgba(251, 191, 36, 0.4);
  border-radius: 999px;
  padding: 2px 8px;
  color: rgba(254, 240, 138, 0.98);
  font-size: 11px;
  font-weight: 500;
}

.editor-state.saved {
  border-color: rgba(34, 197, 94, 0.4);
  color: rgba(187, 247, 208, 0.98);
}

.json-editor {
  flex: 1;
  min-height: 0;
  width: 100%;
  resize: none;
  border: 1px solid rgba(148, 163, 184, 0.24);
  border-radius: 8px;
  padding: 14px;
  color: rgba(226, 232, 240, 0.96);
  background: rgba(2, 6, 23, 0.72);
  font: 12px/1.55 Consolas, 'Cascadia Mono', monospace;
  tab-size: 2;
}

.settings-btn {
  min-height: 32px;
  padding: 6px 10px;
  font-size: 12px;
}

.settings-btn.primary {
  border-color: rgba(56, 189, 248, 0.45);
  color: rgba(186, 230, 253, 0.98);
}

.settings-btn:disabled {
  cursor: not-allowed;
  opacity: 0.45;
}

.settings-error {
  flex: 0 0 auto;
  border: 1px solid rgba(248, 113, 113, 0.5);
  border-radius: 8px;
  padding: 9px 11px;
  color: rgba(254, 226, 226, 0.95);
  background: rgba(127, 29, 29, 0.32);
  font-size: 12px;
}

@media (max-width: 960px) {
  .settings-body {
    grid-template-columns: 1fr;
  }

  .settings-tabs {
    flex-direction: row;
    overflow-x: auto;
    border-right: 0;
    border-bottom: 1px solid rgba(148, 163, 184, 0.18);
  }

  .settings-tab {
    width: auto;
    white-space: nowrap;
  }

  .editor-toolbar,
  .settings-head {
    align-items: stretch;
    flex-direction: column;
  }

  .editor-actions {
    flex-wrap: wrap;
  }
}
</style>
