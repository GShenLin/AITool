<script setup lang="ts">
import { computed, inject, ref, watch } from 'vue'
import { type MessageEnvelope, type ResourceKind } from '../../api'
import { resolveDroppedPaths, resolvePastedImagePaths } from '../../composables/droppedPaths'
import { useGlobalState } from '../../composables/useGlobalState'
import { AgentBoardKey } from './context'
import NodeConfigSection from './NodeConfigSection.vue'
import NodeEditorInputSection from './NodeEditorInputSection.vue'
import { useNodeSideEditorPanel } from './useNodeSideEditorPanel'

const injected = inject(AgentBoardKey, null)
if (!injected) {
  throw new Error('AgentBoard context not found')
}
const ctx = injected

const {
  lastError,
  nodeEditorInputText,
  nodeEditorAttachments,
  nodeTriggerInputs,
  providers,
  availableTools,
} = useGlobalState()

const isUploadingFiles = ref(false)
const goalArmedByNode = ref<Record<string, boolean>>({})

const selectedNode = computed(() => {
  const id = String(ctx.selectedNodeId.value || '').trim()
  if (!id) return null
  return ctx.nodes.value.find((item) => item.id === id) || null
})

const {
  panelStyle,
  panelPlacement,
  horizontalResizeHandle,
  cornerResizeHandle,
  isResizingPanel,
  isDraggingPanel,
  startPanelResize,
  startPanelDrag,
} = useNodeSideEditorPanel(ctx, selectedNode)

const selectedConfig = computed(() => {
  const id = selectedNode.value?.id
  if (!id) return null
  return ctx.nodeConfigs.value[id] || null
})

const hasSelectedNode = computed(() => !!selectedNode.value)
const canSend = computed(() => hasSelectedNode.value)
const isNodeRunning = computed(() => (selectedNode.value ? ctx.isNodeRunning(selectedNode.value.id) : false))
const isStopRequested = computed(() => {
  const id = String(selectedNode.value?.id || '').trim()
  return !!(id && ctx.nodeConfigs.value[id]?._stop_requested)
})
const selectedGoalState = computed(() => {
  const state = selectedConfig.value?.goal_state
  return state && typeof state === 'object' ? state as Record<string, unknown> : null
})
const selectedGoalText = computed(() => String(selectedConfig.value?.goal || '').trim())
const hasPersistedGoal = computed(() => !!(selectedGoalText.value || selectedGoalState.value))
const isAgentNode = computed(() => selectedNode.value?.typeId === 'agent_node')
const goalEnabled = computed(() => isAgentNode.value || hasPersistedGoal.value)
const goalActive = computed(() => {
  const id = String(selectedNode.value?.id || '').trim()
  return goalEnabled.value && (!!(id && goalArmedByNode.value[id]) || hasPersistedGoal.value)
})
const goalTitle = computed(() => {
  const status = String(selectedGoalState.value?.status || '').trim()
  const reason = String(selectedGoalState.value?.reason || '').trim()
  if (selectedGoalText.value) {
    return reason ? `Goal ${status || 'set'}: ${reason}` : `Goal ${status || 'set'}`
  }
  if (!isAgentNode.value) return 'Goal mode is available on Agent nodes'
  return goalActive.value ? 'Disable goal mode' : 'Enable goal mode'
})

function resetEditorInput() {
  nodeEditorInputText.value = ''
  nodeEditorAttachments.value = []
}

function rememberEditorInput(nodeId: string | null | undefined) {
  const id = String(nodeId || '').trim()
  if (!id) return
  nodeTriggerInputs.value = {
    ...nodeTriggerInputs.value,
    [id]: String(nodeEditorInputText.value || ''),
  }
}

function loadEditorInput(nodeId: string | null | undefined) {
  const id = String(nodeId || '').trim()
  nodeEditorInputText.value = id ? String(nodeTriggerInputs.value[id] || '') : ''
  nodeEditorAttachments.value = []
}

function appendAttachment(path: string, name = '') {
  const safePath = String(path || '').trim()
  const safeName = String(name || '').trim() || safePath
  if (!safePath) return
  if (nodeEditorAttachments.value.some((item) => item.path === safePath)) return
  nodeEditorAttachments.value.push({ path: safePath, name: safeName })
}

function removeAttachment(index: number) {
  nodeEditorAttachments.value.splice(index, 1)
}

function clearAttachments() {
  nodeEditorAttachments.value = []
}

async function handleInputDrop(event: DragEvent) {
  event.preventDefault()
  isUploadingFiles.value = true
  try {
    const dropped = await resolveDroppedPaths(event, 'node-side-editor-input')
    for (const item of dropped) {
      appendAttachment(item.path, item.name)
    }
  } catch (e: any) {
    lastError.value = String(e?.message || e)
  } finally {
    isUploadingFiles.value = false
  }
}

async function handleInputPaste(event: ClipboardEvent) {
  const hasImage = Array.from(event.clipboardData?.items || []).some(
    (item) => item.kind === 'file' && item.type.toLowerCase().startsWith('image/'),
  )
  if (!hasImage) return

  event.preventDefault()
  isUploadingFiles.value = true
  try {
    const pasted = await resolvePastedImagePaths(event, 'node-side-editor-paste')
    for (const item of pasted) {
      appendAttachment(item.path, item.name)
    }
  } catch (e: any) {
    lastError.value = String(e?.message || e)
  } finally {
    isUploadingFiles.value = false
  }
}

function guessResourceKind(path: string): ResourceKind | 'file' {
  const lower = String(path || '').toLowerCase()
  if (/\.(png|jpg|jpeg|webp|gif|bmp|svg)$/.test(lower)) return 'image'
  if (/\.(mp4|mov|mkv|webm|avi|flv|m4v)$/.test(lower)) return 'video'
  if (/\.(mp3|wav|ogg|flac|m4a)$/.test(lower)) return 'audio'
  if (/\.(pdf|doc|docx|ppt|pptx|xls|xlsx|txt|md)$/.test(lower)) return 'doc'
  return 'file'
}

function composePayload(): string | MessageEnvelope {
  const text = nodeEditorInputText.value.trim()
  if (!nodeEditorAttachments.value.length) {
    if (text) return text
    return { role: 'user', parts: [] }
  }
  const parts: MessageEnvelope['parts'] = []
  if (text) {
    parts.push({ type: 'text', text })
  }
  for (const file of nodeEditorAttachments.value) {
    const uri = String(file.path || '').trim()
    if (!uri) continue
    parts.push({
      type: 'resource',
      resource: {
        uri,
        name: String(file.name || ''),
        kind: guessResourceKind(uri),
        source: 'node_editor',
      },
    })
  }
  return { role: 'user', parts }
}

function payloadGoalText(payload: string | MessageEnvelope) {
  if (typeof payload === 'string') return payload.trim()
  const parts = Array.isArray(payload?.parts) ? payload.parts : []
  const texts: string[] = []
  for (const part of parts) {
    if (!part || typeof part !== 'object') continue
    if (part.type === 'text') {
      const text = String((part as any).text || '').trim()
      if (text) texts.push(text)
    } else if (part.type === 'resource') {
      const resource = (part as any).resource
      const uri = String(resource?.uri || '').trim()
      if (uri) texts.push(`[${String(resource?.kind || 'file')}] ${uri}`)
    } else if (part.type === 'structured') {
      texts.push(JSON.stringify((part as any).data))
    }
  }
  return texts.join('\n').trim()
}

async function persistGoalForSend(nodeId: string, payload: string | MessageEnvelope) {
  if (!goalActive.value || !isAgentNode.value) return
  const objective = payloadGoalText(payload)
  if (!objective) {
    throw new Error('Goal mode requires non-empty input.')
  }
  await ctx.setNodeFields(nodeId, {
    goal: objective,
    goal_state: {
      status: 'active',
      reason: 'Goal started from node input.',
      turn_count: 0,
      updated_at: new Date().toISOString(),
    },
  })
}

async function toggleGoal() {
  const nodeId = selectedNode.value?.id
  if (!nodeId) return
  if (!goalEnabled.value) return
  lastError.value = null
  try {
    if (goalActive.value) {
      goalArmedByNode.value = { ...goalArmedByNode.value, [nodeId]: false }
      await ctx.clearNodeFields(nodeId, ['goal', 'goal_state'])
    } else {
      goalArmedByNode.value = { ...goalArmedByNode.value, [nodeId]: true }
    }
  } catch (e: any) {
    lastError.value = String(e?.message || e)
  }
}

async function sendMessage() {
  const nodeId = selectedNode.value?.id
  if (!nodeId || !canSend.value) return
  const payload = composePayload()
  lastError.value = null
  try {
    await persistGoalForSend(nodeId, payload)
    await ctx.sendNodeMessage(nodeId, payload)
    if (String(ctx.selectedNodeId.value || '') === nodeId) {
      resetEditorInput()
    }
    nodeTriggerInputs.value = { ...nodeTriggerInputs.value, [nodeId]: '' }
  } catch (e: any) {
    lastError.value = String(e?.message || e)
  }
}

function showEditorError(message: string) {
  lastError.value = String(message || '').trim() || null
}

watch(
  () => ctx.selectedNodeId.value,
  async (nodeId, prevNodeId) => {
    if (String(nodeId || '') === String(prevNodeId || '')) return
    rememberEditorInput(prevNodeId)
    loadEditorInput(nodeId)
  },
  { immediate: true },
)

</script>

<template>
  <aside
    v-if="selectedNode"
    class="node-side-editor"
    :class="{ resizing: isResizingPanel, dragging: isDraggingPanel }"
    :style="panelStyle"
    @pointerdown.stop
    @click.stop
    @dragover.prevent
  >
    <div class="editor-head" @pointerdown="startPanelDrag">
      <div class="editor-title-wrap">
        <div class="editor-title">{{ selectedNode.name }}</div>
        <div class="editor-sub">{{ selectedNode.typeId }} / {{ selectedNode.id }}</div>
      </div>
      <button v-if="isNodeRunning" type="button" class="head-btn danger" @click="ctx.stopNodeWork(selectedNode.id).catch(() => null)">
        {{ isStopRequested ? 'Stopping' : 'Stop' }}
      </button>
    </div>

    <NodeEditorInputSection
      v-model:input-text="nodeEditorInputText"
      :attachments="nodeEditorAttachments"
      :can-send="canSend"
      :is-uploading-files="isUploadingFiles"
      :goal-active="goalActive"
      :goal-enabled="goalEnabled"
      :goal-title="goalTitle"
      @drop-input="handleInputDrop"
      @paste-input="handleInputPaste"
      @remove-attachment="removeAttachment"
      @clear-attachments="clearAttachments"
      @toggle-goal="toggleGoal"
      @send="sendMessage"
    />

    <NodeConfigSection
      :node="selectedNode"
      :config="selectedConfig"
      :providers="providers"
      :available-tools="availableTools"
      @error="showEditorError"
    />

    <div
      class="resize-handle resize-handle-x"
      :class="panelPlacement === 'right' ? 'resize-handle-right' : 'resize-handle-left'"
      @pointerdown="startPanelResize(horizontalResizeHandle, $event)"
    ></div>
    <div class="resize-handle resize-handle-bottom" @pointerdown="startPanelResize('bottom', $event)"></div>
    <div
      class="resize-handle resize-handle-corner"
      :class="panelPlacement === 'right' ? 'resize-handle-bottom-right' : 'resize-handle-bottom-left'"
      @pointerdown="startPanelResize(cornerResizeHandle, $event)"
    ></div>
  </aside>
</template>

<style scoped>
.node-side-editor {
  position: absolute;
  z-index: 100;
  box-sizing: border-box;
  pointer-events: auto;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 16px;
  border-radius: 16px;
  border: 1px solid rgba(148, 163, 184, 0.24);
  background: rgba(2, 6, 23, 0.96);
  box-shadow: 0 18px 40px rgba(15, 23, 42, 0.34);
  backdrop-filter: blur(14px);
  isolation: isolate;
}

.node-side-editor.resizing,
.node-side-editor.dragging {
  transition: none;
}

.editor-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  cursor: move;
  user-select: none;
}

.editor-head,
.section-divider {
  flex: 0 0 auto;
}

.editor-title-wrap {
  display: flex;
  flex-direction: column;
}

.editor-title {
  font-size: 16px;
  font-weight: 700;
  color: #f8fafc;
}

.editor-sub {
  font-size: 12px;
  color: rgba(148, 163, 184, 0.84);
}

.head-btn {
  border: 1px solid rgba(148, 163, 184, 0.22);
  border-radius: 10px;
  background: rgba(15, 23, 42, 0.9);
  color: #f8fafc;
  padding: 8px 12px;
  cursor: pointer;
  position: relative;
  z-index: 2;
}

.head-btn {
  padding: 6px 10px;
  font-size: 12px;
}

.head-btn.danger {
  background: rgba(239, 68, 68, 0.2);
  border-color: rgba(248, 113, 113, 0.35);
}

.resize-handle {
  position: absolute;
  z-index: 20;
  pointer-events: auto;
}

.resize-handle::after {
  content: '';
  position: absolute;
  inset: 0;
  background: transparent;
  transition: background 0.12s ease;
}

.resize-handle:hover::after,
.resize-handle:active::after {
  background: rgba(125, 211, 252, 0.16);
}

.resize-handle-x {
  top: 10px;
  bottom: 18px;
  width: 8px;
  cursor: ew-resize;
}

.resize-handle-right {
  right: 0;
}

.resize-handle-left {
  left: 0;
}

.resize-handle-bottom {
  left: 18px;
  right: 18px;
  bottom: 0;
  height: 8px;
  cursor: ns-resize;
}

.resize-handle-corner {
  bottom: 0;
  width: 18px;
  height: 18px;
  cursor: nwse-resize;
}

.resize-handle-bottom-right {
  right: 0;
}

.resize-handle-bottom-left {
  left: 0;
  cursor: nesw-resize;
}
</style>
