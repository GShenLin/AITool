<script setup lang="ts">
import { computed } from 'vue'
import type { ProviderInfo } from '../../api'
import CompanionCapabilitySelect, { type CompanionCapabilityOption } from './CompanionCapabilitySelect.vue'

const props = defineProps<{
  data: Record<string, unknown>
  providers: ProviderInfo[]
  availableTools: string[]
  capabilityOptions: Record<string, CompanionCapabilityOption[]>
}>()

const emit = defineEmits<{
  'update:data': [value: Record<string, unknown>]
}>()

const modeOptions = ['chat', 'imagechat', 'vision_understand']
const switchOptions = ['disabled', 'enabled']
const reasoningEffortOptions = ['', 'minimal', 'low', 'medium', 'high', 'xhigh', 'max', 'auto']

const providerOptions = computed(() =>
  props.providers
    .filter((provider) => provider.supportmode.includes('chat') || provider.supportmode.includes('imagechat'))
    .map((provider) => String(provider.id || '').trim())
    .filter(Boolean)
    .sort((a, b) => a.localeCompare(b)),
)
const fallbackToolOptions = computed(() => props.availableTools.map((value) => ({ value, label: value })))

function cloneData() {
  return JSON.parse(JSON.stringify(props.data || {})) as Record<string, unknown>
}

function stringValue(key: string) {
  return String(props.data[key] ?? '')
}

function listValue(key: string) {
  const value = props.data[key]
  if (!Array.isArray(value)) return []
  return value.map((item) => String(item || '').trim()).filter(Boolean)
}

function capabilityOptions(key: string) {
  const options = props.capabilityOptions[key] || []
  if (key === 'tools' && options.length === 0) return fallbackToolOptions.value
  return options
}

function setField(key: string, value: unknown) {
  const next = cloneData()
  if (value === '' || value === null || value === undefined) {
    delete next[key]
  } else {
    next[key] = value
  }
  emit('update:data', next)
}

function setListField(key: string, values: string[]) {
  setField(key, values.map((item) => String(item || '').trim()).filter(Boolean))
}
</script>

<template>
  <div class="companion-form">
    <section class="settings-group">
      <h2>Model</h2>
      <div class="form-grid">
        <label>
          <span>Provider</span>
          <select :value="stringValue('provider_id')" @change="setField('provider_id', ($event.target as HTMLSelectElement).value)">
            <option value="">Unset</option>
            <option v-for="providerId in providerOptions" :key="providerId" :value="providerId">{{ providerId }}</option>
          </select>
        </label>
        <label>
          <span>Mode</span>
          <select :value="stringValue('mode') || 'chat'" @change="setField('mode', ($event.target as HTMLSelectElement).value)">
            <option v-for="mode in modeOptions" :key="mode" :value="mode">{{ mode }}</option>
          </select>
        </label>
        <label>
          <span>Web Search</span>
          <select :value="stringValue('web_search') || 'disabled'" @change="setField('web_search', ($event.target as HTMLSelectElement).value)">
            <option v-for="option in switchOptions" :key="option" :value="option">{{ option }}</option>
          </select>
        </label>
        <label>
          <span>Thinking</span>
          <select :value="stringValue('thinking') || 'disabled'" @change="setField('thinking', ($event.target as HTMLSelectElement).value)">
            <option v-for="option in switchOptions" :key="option" :value="option">{{ option }}</option>
          </select>
        </label>
        <label>
          <span>Reasoning Effort</span>
          <select :value="stringValue('reasoning_effort')" @change="setField('reasoning_effort', ($event.target as HTMLSelectElement).value)">
            <option v-for="option in reasoningEffortOptions" :key="option || 'unset'" :value="option">{{ option || 'Unset' }}</option>
          </select>
        </label>
        <label>
          <span>Working Path</span>
          <input :value="stringValue('working_path')" @input="setField('working_path', ($event.target as HTMLInputElement).value)" />
        </label>
      </div>
      <label class="wide-field">
        <span>System Prompt</span>
        <textarea :value="stringValue('system_prompt')" rows="5" @input="setField('system_prompt', ($event.target as HTMLTextAreaElement).value)"></textarea>
      </label>
    </section>

    <section class="settings-group">
      <h2>Capabilities</h2>
      <div class="capability-grid">
        <CompanionCapabilitySelect
          title="Tools"
          :values="listValue('tools')"
          :options="capabilityOptions('tools')"
          empty-text="No tools found."
          add-placeholder="Tool id"
          @update:values="setListField('tools', $event)"
        />
        <CompanionCapabilitySelect
          title="MCP Servers"
          :values="listValue('mcp_servers')"
          :options="capabilityOptions('mcp_servers')"
          empty-text="No MCP servers found."
          add-placeholder="MCP server id"
          @update:values="setListField('mcp_servers', $event)"
        />
        <CompanionCapabilitySelect
          title="Skills"
          :values="listValue('skills')"
          :options="capabilityOptions('skills')"
          empty-text="No skills found."
          add-placeholder="Skill id"
          @update:values="setListField('skills', $event)"
        />
        <CompanionCapabilitySelect
          title="Plugins"
          :values="listValue('plugins')"
          :options="capabilityOptions('plugins')"
          empty-text="No plugins found."
          add-placeholder="Plugin id"
          @update:values="setListField('plugins', $event)"
        />
      </div>
    </section>
  </div>
</template>

<style scoped>
.companion-form {
  flex: 1;
  min-height: 0;
  overflow: auto;
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding-right: 4px;
}

.settings-group {
  border: 1px solid rgba(148, 163, 184, 0.18);
  border-radius: 8px;
  padding: 12px;
  background: rgba(15, 23, 42, 0.28);
}

.settings-group h2 {
  margin: 0 0 10px;
  font-size: 15px;
}

.form-grid,
.capability-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(220px, 1fr));
  gap: 12px;
}

label {
  display: flex;
  flex-direction: column;
  gap: 5px;
  color: rgba(226, 232, 240, 0.94);
  font-size: 12px;
}

.wide-field {
  margin-top: 12px;
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
  resize: vertical;
  min-height: 98px;
}

@media (max-width: 1120px) {
  .form-grid,
  .capability-grid {
    grid-template-columns: 1fr;
  }
}
</style>
