<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import SupportModeMultiSelect from './SupportModeMultiSelect.vue'

const props = defineProps<{
  data: Record<string, unknown>
}>()

const emit = defineEmits<{
  'update:data': [value: Record<string, unknown>]
}>()

const selectedProviderId = ref('')
const newProviderId = ref('')

const providers = computed<Record<string, Record<string, unknown>>>(() => {
  const value = props.data.providers
  return value && typeof value === 'object' && !Array.isArray(value)
    ? value as Record<string, Record<string, unknown>>
    : {}
})

const providerIds = computed(() => Object.keys(providers.value))
const selectedProvider = computed(() => providers.value[selectedProviderId.value] || null)

watch(
  providerIds,
  (ids) => {
    if (!ids.includes(selectedProviderId.value)) {
      selectedProviderId.value = ids[0] || ''
    }
  },
  { immediate: true },
)

function cloneData() {
  return JSON.parse(JSON.stringify(props.data || {})) as Record<string, unknown>
}

function emitProvider(providerId: string, nextProvider: Record<string, unknown>) {
  const next = cloneData()
  const nextProviders = {
    ...(next.providers && typeof next.providers === 'object' && !Array.isArray(next.providers)
      ? next.providers as Record<string, Record<string, unknown>>
      : {}),
    [providerId]: nextProvider,
  }
  next.providers = nextProviders
  emit('update:data', next)
}

function parseTextList(value: string) {
  return value
    .split(/[\n,]/)
    .map((item) => item.trim())
    .filter(Boolean)
}

function textList(value: unknown) {
  if (!Array.isArray(value)) return ''
  return value.map((item) => String(item)).join('\n')
}

function listValue(key: string) {
  const value = selectedProvider.value?.[key]
  if (!Array.isArray(value)) return []
  return value.map((item) => String(item || '').trim()).filter(Boolean)
}

function stringValue(key: string) {
  return String(selectedProvider.value?.[key] ?? '')
}

function booleanValue(key: string) {
  return selectedProvider.value?.[key] === true
}

function numberValue(key: string) {
  const value = selectedProvider.value?.[key]
  if (value === null || value === undefined || value === '') return ''
  return String(value)
}

function setField(key: string, value: unknown) {
  if (!selectedProviderId.value || !selectedProvider.value) return
  const provider = { ...selectedProvider.value }
  if (value === '' || value === null || value === undefined) {
    delete provider[key]
  } else {
    provider[key] = value
  }
  emitProvider(selectedProviderId.value, provider)
}

function setNumberField(key: string, raw: string) {
  const text = String(raw || '').trim()
  setField(key, text ? Number(text) : '')
}

function addProvider() {
  const id = newProviderId.value.trim()
  if (!id || providers.value[id]) return
  const next = cloneData()
  next.providers = {
    ...providers.value,
    [id]: {
      type: 'openai',
      model: '',
      supportmode: ['chat'],
    },
  }
  emit('update:data', next)
  selectedProviderId.value = id
  newProviderId.value = ''
}

function deleteProvider() {
  const id = selectedProviderId.value
  if (!id) return
  const next = cloneData()
  const nextProviders = { ...providers.value }
  delete nextProviders[id]
  next.providers = nextProviders
  emit('update:data', next)
  selectedProviderId.value = Object.keys(nextProviders)[0] || ''
}
</script>

<template>
  <div class="provider-settings">
    <aside class="provider-list">
      <button
        v-for="providerId in providerIds"
        :key="providerId"
        type="button"
        class="provider-item"
        :class="{ active: selectedProviderId === providerId }"
        @click="selectedProviderId = providerId"
      >
        <span>{{ providerId }}</span>
        <small>{{ providers[providerId]?.model || providers[providerId]?.type || '' }}</small>
      </button>
      <div class="provider-add">
        <input v-model="newProviderId" placeholder="New provider id" @keydown.enter.prevent="addProvider" />
        <button type="button" @click="addProvider">Add</button>
      </div>
    </aside>

    <section v-if="selectedProvider" class="provider-form">
      <div class="form-head">
        <div>
          <h2>{{ selectedProviderId }}</h2>
          <span>Provider fields</span>
        </div>
        <button type="button" class="danger" @click="deleteProvider">Delete</button>
      </div>

      <div class="form-grid">
        <label>
          <span>Type</span>
          <select :value="stringValue('type')" @change="setField('type', ($event.target as HTMLSelectElement).value)">
            <option value="">Unset</option>
            <option value="openai">openai</option>
            <option value="doubao">doubao</option>
            <option value="gemini">gemini</option>
            <option value="zhipu">zhipu</option>
            <option value="hyper3d">hyper3d</option>
          </select>
        </label>
        <label>
          <span>Model</span>
          <input :value="stringValue('model')" @input="setField('model', ($event.target as HTMLInputElement).value)" />
        </label>
        <label>
          <span>Base URL</span>
          <input :value="stringValue('baseUrl')" @input="setField('baseUrl', ($event.target as HTMLInputElement).value)" />
        </label>
        <label>
          <span>API Key</span>
          <input :value="stringValue('apiKey')" type="password" autocomplete="off" @input="setField('apiKey', ($event.target as HTMLInputElement).value)" />
        </label>
        <label>
          <span>Timeout Ms</span>
          <input :value="numberValue('timeoutMs')" type="number" min="1" @input="setNumberField('timeoutMs', ($event.target as HTMLInputElement).value)" />
        </label>
        <label>
          <span>Max Tokens</span>
          <input :value="numberValue('maxTokens')" type="number" min="1" @input="setNumberField('maxTokens', ($event.target as HTMLInputElement).value)" />
        </label>
        <label>
          <span>Reasoning Effort</span>
          <select :value="stringValue('reasoningEffort')" @change="setField('reasoningEffort', ($event.target as HTMLSelectElement).value)">
            <option value="">Unset</option>
            <option value="minimal">minimal</option>
            <option value="low">low</option>
            <option value="medium">medium</option>
            <option value="high">high</option>
            <option value="xhigh">xhigh</option>
            <option value="max">max</option>
            <option value="auto">auto</option>
          </select>
        </label>
        <label>
          <span>Continuation Mode</span>
          <select :value="stringValue('responsesContinuationMode')" @change="setField('responsesContinuationMode', ($event.target as HTMLSelectElement).value)">
            <option value="">Unset</option>
            <option value="previous_response_id">previous_response_id</option>
            <option value="explicit_context">explicit_context</option>
          </select>
        </label>
      </div>

      <div class="switch-grid">
        <label class="switch-field"><span>Responses API</span><input type="checkbox" :checked="booleanValue('responsesApi')" @change="setField('responsesApi', ($event.target as HTMLInputElement).checked)" /></label>
        <label class="switch-field"><span>Replay reasoning items</span><input type="checkbox" :checked="booleanValue('responsesReplayReasoningItems')" @change="setField('responsesReplayReasoningItems', ($event.target as HTMLInputElement).checked)" /></label>
        <label class="switch-field"><span>Tool context compaction</span><input type="checkbox" :checked="booleanValue('toolContextCompactionEnabled')" @change="setField('toolContextCompactionEnabled', ($event.target as HTMLInputElement).checked)" /></label>
        <label class="switch-field"><span>Item-level streaming</span><input type="checkbox" :checked="booleanValue('responsesItemLevelStreaming')" @change="setField('responsesItemLevelStreaming', ($event.target as HTMLInputElement).checked)" /></label>
      </div>

      <div class="form-grid">
        <label class="dropdown-field">
          <span>Support Modes</span>
          <SupportModeMultiSelect
            :selected-values="listValue('supportmode')"
            @update:selected-values="setField('supportmode', $event)"
          />
        </label>
        <label>
          <span>Web Search Sources</span>
          <textarea :value="textList(selectedProvider.webSearchSources)" @input="setField('webSearchSources', parseTextList(($event.target as HTMLTextAreaElement).value))"></textarea>
        </label>
        <label>
          <span>Web Search Max Keyword</span>
          <input :value="numberValue('webSearchMaxKeyword')" type="number" min="1" @input="setNumberField('webSearchMaxKeyword', ($event.target as HTMLInputElement).value)" />
        </label>
        <label>
          <span>Web Search Limit</span>
          <input :value="numberValue('webSearchLimit')" type="number" min="1" @input="setNumberField('webSearchLimit', ($event.target as HTMLInputElement).value)" />
        </label>
        <label>
          <span>Compaction Every Tool Calls</span>
          <input :value="numberValue('toolContextCompactionEveryToolCalls')" type="number" min="1" @input="setNumberField('toolContextCompactionEveryToolCalls', ($event.target as HTMLInputElement).value)" />
        </label>
        <label>
          <span>Tool Result Max Chars</span>
          <input :value="numberValue('toolResultSubmissionMaxChars')" type="number" min="1" @input="setNumberField('toolResultSubmissionMaxChars', ($event.target as HTMLInputElement).value)" />
        </label>
      </div>
    </section>
  </div>
</template>

<style scoped>
.provider-settings {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: 260px minmax(0, 1fr);
  gap: 12px;
}

.provider-list,
.provider-form {
  min-height: 0;
  overflow: auto;
}

.provider-list {
  display: flex;
  flex-direction: column;
  gap: 7px;
  padding-right: 10px;
  border-right: 1px solid rgba(148, 163, 184, 0.16);
}

.provider-item {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
  width: 100%;
  text-align: left;
}

.provider-item.active {
  border-color: rgba(56, 189, 248, 0.66);
  background: rgba(14, 165, 233, 0.18);
}

.provider-item small,
.form-head span {
  color: rgba(148, 163, 184, 0.9);
  font-size: 11px;
}

.provider-add {
  display: flex;
  gap: 6px;
  margin-top: 4px;
}

.provider-add input {
  min-width: 0;
  flex: 1;
}

.provider-form {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding-right: 4px;
}

.form-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.form-head h2 {
  margin: 0;
  font-size: 17px;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(220px, 1fr));
  gap: 12px;
}

.switch-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(220px, 1fr));
  gap: 8px 12px;
}

label {
  display: flex;
  flex-direction: column;
  gap: 5px;
  color: rgba(226, 232, 240, 0.94);
  font-size: 12px;
}

.switch-field {
  flex-direction: row;
  align-items: center;
  justify-content: flex-start;
  gap: 8px;
  min-height: 32px;
}

.switch-field input {
  width: 14px;
  height: 14px;
  margin: 0;
  accent-color: #38bdf8;
}

.dropdown-field {
  position: relative;
}

input,
select,
textarea {
  width: 100%;
  border: 1px solid rgba(148, 163, 184, 0.24);
  border-radius: 8px;
  padding: 8px 9px;
  color: rgba(226, 232, 240, 0.96);
  background: rgba(2, 6, 23, 0.5);
  font: inherit;
}

textarea {
  min-height: 76px;
  resize: vertical;
}

button.danger {
  border-color: rgba(248, 113, 113, 0.35);
  color: rgba(254, 202, 202, 0.95);
}

@media (max-width: 1120px) {
  .form-grid,
  .switch-grid {
    grid-template-columns: 1fr;
  }

  .provider-settings {
    grid-template-columns: minmax(132px, 38vw) minmax(0, 1fr);
  }

  .provider-list {
    padding-right: 8px;
  }

  .provider-add {
    flex-direction: column;
  }
}
</style>
