<template>
  <template v-if="visible">
    <button
      class="agent-orb"
      :class="{ 'agent-orb-dragging': dragActive, 'agent-orb-open': panelOpen }"
      :style="orbStyle"
      type="button"
      aria-label="打开 Mira 主助手"
      @pointerdown="handlePointerDown"
      @keydown.enter.prevent="togglePanel"
      @keydown.space.prevent="togglePanel"
    >
      <span class="agent-orb-ring" />
      <span class="agent-logo">M</span>
      <span v-if="unread && !panelOpen" class="agent-unread" />
      <span class="agent-status-dot" />
    </button>

    <Transition name="agent-panel">
      <section
        v-if="panelOpen"
        class="agent-panel"
        :class="{ 'agent-panel-expanded': panelExpanded }"
        :style="panelStyle"
        aria-label="Mira 主助手聊天窗口"
      >
        <header
          class="agent-header"
          :class="{ 'agent-header-dragging': panelDragActive }"
          @pointerdown="handlePanelDragStart"
        >
          <div class="agent-identity">
            <div class="agent-header-logo">{{ currentAgent.initial }}</div>
            <div>
              <strong>{{ currentAgent.name }}</strong>
              <span>{{ currentAgent.subtitle }}</span>
            </div>
          </div>
          <div class="agent-header-actions">
            <button
              class="agent-icon-button"
              type="button"
              :aria-label="panelExpanded ? '退出全屏' : '展开全屏'"
              :title="panelExpanded ? '退出全屏' : '展开全屏'"
              @click="toggleExpanded"
            >
              {{ panelExpanded ? '↙' : '⛶' }}
            </button>
            <button class="agent-icon-button" type="button" aria-label="关闭助手" @click="closePanel">
              ×
            </button>
          </div>
        </header>

        <div ref="messageAreaRef" class="agent-messages">
          <article
            v-for="message in messages"
            :key="message.id"
            class="agent-message"
            :class="`agent-message-${message.role}`"
          >
            <span
              v-if="message.role === 'assistant'"
              class="agent-mini-avatar"
              :class="`agent-tone-${message.agentKey || 'main'}`"
            >
              {{ message.agentInitial || 'M' }}
            </span>
            <div class="agent-bubble">
              <div class="agent-message-meta">
                <span v-if="message.agentLabel" class="agent-message-agent">
                  {{ message.agentLabel }}
                </span>
                <time :datetime="message.createdAt" :title="formatFullTime(message.createdAt)">
                  {{ formatMessageTime(message.createdAt) }}
                </time>
              </div>
              <span class="agent-message-text" v-html="displayHtml(message.content)" />
              <div v-if="message.sources?.length" class="agent-sources">
                <span class="agent-source-label">知识来源</span>
                <span
                  v-for="source in message.sources"
                  :key="source.itemId"
                  class="agent-source"
                  :title="source.chapter"
                >
                  {{ source.itemId }} · {{ source.title }}
                </span>
              </div>
            </div>
          </article>

          <article v-if="loading" class="agent-message agent-message-assistant">
            <div class="agent-bubble agent-thinking">
              <span />
              <span />
              <span />
            </div>
          </article>
        </div>

        <div class="agent-composer">
          <div v-if="pendingAction" class="agent-pending-note">
            <span>待确认：{{ pendingAction.summary }}</span>
            <div class="agent-pending-actions">
              <button type="button" @click="sendMessage('确认执行', true)">确认执行</button>
              <button type="button" @click="discardPendingAction">放弃</button>
            </div>
          </div>
          <textarea
            v-model="draft"
            rows="2"
            maxlength="2000"
            placeholder="问我训练、课程或预约问题…"
            :disabled="loading"
            @keydown.enter.exact.prevent="sendMessage()"
          />
          <div class="agent-composer-actions">
            <button class="agent-clear" type="button" :disabled="loading" @click="clearChat">
              清空
            </button>
            <button class="agent-send" type="button" :disabled="loading || !draft.trim()" @click="sendMessage()">
              {{ loading ? '思考中' : '发送' }}
            </button>
          </div>
        </div>
      </section>
    </Transition>
  </template>
</template>

<script setup>
import {
  computed,
  nextTick,
  onBeforeUnmount,
  onMounted,
  reactive,
  ref,
  watch,
} from 'vue'
import { useRoute } from 'vue-router'
import { chatWithMainAgent } from '@/api/agent'
import { useUserStore } from '@/stores/user'

const BALL_SIZE = 62
const POSITION_KEY = 'multiagent_gym_assistant_position'
const PANEL_POSITION_KEY = 'multiagent_gym_assistant_panel_position'
const PANEL_MAX_WIDTH = 400
const PANEL_MAX_HEIGHT = 570

const route = useRoute()
const userStore = useUserStore()
const panelOpen = ref(false)
const panelExpanded = ref(false)
const unread = ref(false)
const loading = ref(false)
const draft = ref('')
const dragActive = ref(false)
const panelDragActive = ref(false)
const activeAgent = ref('main')
const pendingActionToken = ref('')
const pendingAction = ref(null)
const messageAreaRef = ref(null)
const viewport = reactive({ width: window.innerWidth, height: window.innerHeight })
const position = reactive(readPosition())
const panelPosition = reactive(readPanelPosition())
let messageId = 1
const messages = ref([welcomeMessage()])

let dragState = null
let panelDragState = null
let conversationOwner = currentIdentity()

const AGENT_META = {
  main: {
    name: 'Mira',
    subtitle: '健身房智能助手',
    label: '主助手 Mira',
    initial: 'M',
  },
  appointment: {
    name: 'Vera',
    subtitle: '预约助手 · 预约、取消与改约',
    label: '预约助手 Vera',
    initial: 'V',
  },
  course: {
    name: 'Nova',
    subtitle: '课程推荐助手 · 实时课程分析',
    label: '课程助手 Nova',
    initial: 'N',
  },
  operations: {
    name: 'Atlas',
    subtitle: '运营助手 · 管理员专属分析',
    label: '运营助手 Atlas',
    initial: 'A',
  },
}
const wordSegmenter =
  typeof Intl !== 'undefined' && Intl.Segmenter
    ? new Intl.Segmenter('zh-CN', { granularity: 'word' })
    : null

const visible = computed(
  () => Boolean(userStore.token) && route.path !== '/login',
)
const currentAgent = computed(() => AGENT_META[activeAgent.value] || AGENT_META.main)

const orbStyle = computed(() => ({
  left: `${position.x}px`,
  top: `${position.y}px`,
}))

const panelStyle = computed(() => {
  if (panelExpanded.value) return {}
  const panelWidth = Math.min(PANEL_MAX_WIDTH, viewport.width - 24)
  const panelHeight = Math.min(PANEL_MAX_HEIGHT, viewport.height - 32)
  return {
    left: `${panelPosition.x}px`,
    top: `${panelPosition.y}px`,
    width: `${panelWidth}px`,
    maxHeight: `${panelHeight}px`,
  }
})

function welcomeMessage() {
  return {
    id: messageId++,
    role: 'assistant',
    content:
      '你好，我是 Mira。健身知识问题我会优先查询项目知识库；课程、预约和统计数据会通过实时工具查询。当前我只提供查询和指导，不会直接修改预约。',
    sources: [],
    createdAt: new Date().toISOString(),
    agentInitial: 'M',
    agentKey: 'main',
  }
}

function currentIdentity() {
  return [userStore.userId, userStore.username, userStore.role].join('|')
}

function createTimestamp() {
  return new Date().toISOString()
}

function formatMessageTime(value) {
  const date = value ? new Date(value) : new Date()
  if (Number.isNaN(date.getTime())) return ''
  const pad = (number) => String(number).padStart(2, '0')
  return `${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`
}

function formatFullTime(value) {
  const date = value ? new Date(value) : new Date()
  return Number.isNaN(date.getTime()) ? '' : date.toLocaleString('zh-CN')
}

function clampPosition(x, y) {
  return {
    x: Math.max(12, Math.min(x, window.innerWidth - BALL_SIZE - 12)),
    y: Math.max(12, Math.min(y, window.innerHeight - BALL_SIZE - 12)),
  }
}

function readPosition() {
  const fallback = clampPosition(
    window.innerWidth - BALL_SIZE - 24,
    window.innerHeight - BALL_SIZE - 28,
  )
  try {
    const stored = JSON.parse(localStorage.getItem(POSITION_KEY) || 'null')
    if (Number.isFinite(stored?.x) && Number.isFinite(stored?.y)) {
      return clampPosition(stored.x, stored.y)
    }
  } catch {
    // Use the default position when stored data is invalid.
  }
  return fallback
}

function clampPanelPosition(x, y) {
  const panelWidth = Math.min(PANEL_MAX_WIDTH, window.innerWidth - 24)
  const panelHeight = Math.min(PANEL_MAX_HEIGHT, window.innerHeight - 32)
  return {
    x: Math.max(12, Math.min(x, window.innerWidth - panelWidth - 12)),
    y: Math.max(12, Math.min(y, window.innerHeight - panelHeight - 12)),
  }
}

function readPanelPosition() {
  const panelHeight = Math.min(PANEL_MAX_HEIGHT, window.innerHeight - 32)
  const fallback = clampPanelPosition(
    24,
    window.innerHeight - panelHeight - 16,
  )
  try {
    const stored = JSON.parse(localStorage.getItem(PANEL_POSITION_KEY) || 'null')
    if (Number.isFinite(stored?.x) && Number.isFinite(stored?.y)) {
      return clampPanelPosition(stored.x, stored.y)
    }
  } catch {
    // Use the default left-side position when stored data is invalid.
  }
  return fallback
}

function handlePointerDown(event) {
  if (event.button !== 0) return
  event.preventDefault()
  dragState = {
    pointerId: event.pointerId,
    startX: event.clientX,
    startY: event.clientY,
    originX: position.x,
    originY: position.y,
    moved: false,
  }
  dragActive.value = true
}

function handlePointerMove(event) {
  if (!dragState || dragState.pointerId !== event.pointerId) return
  const deltaX = event.clientX - dragState.startX
  const deltaY = event.clientY - dragState.startY
  if (Math.abs(deltaX) + Math.abs(deltaY) > 5) {
    dragState.moved = true
  }
  if (!dragState.moved) return
  const next = clampPosition(
    dragState.originX + deltaX,
    dragState.originY + deltaY,
  )
  position.x = next.x
  position.y = next.y
}

function handlePointerUp(event) {
  if (!dragState || dragState.pointerId !== event.pointerId) return
  const wasMoved = dragState.moved
  dragState = null
  dragActive.value = false
  localStorage.setItem(POSITION_KEY, JSON.stringify(position))
  if (!wasMoved) {
    togglePanel()
  }
}

function handlePointerCancel() {
  dragState = null
  dragActive.value = false
  panelDragState = null
  panelDragActive.value = false
}

function handlePanelDragStart(event) {
  if (
    panelExpanded.value ||
    event.button !== 0 ||
    (event.target instanceof Element && event.target.closest('button'))
  ) {
    return
  }
  event.preventDefault()
  panelDragState = {
    pointerId: event.pointerId,
    startX: event.clientX,
    startY: event.clientY,
    originX: panelPosition.x,
    originY: panelPosition.y,
  }
  panelDragActive.value = true
}

function handlePanelPointerMove(event) {
  if (!panelDragState || panelDragState.pointerId !== event.pointerId) return
  const next = clampPanelPosition(
    panelDragState.originX + event.clientX - panelDragState.startX,
    panelDragState.originY + event.clientY - panelDragState.startY,
  )
  panelPosition.x = next.x
  panelPosition.y = next.y
}

function handlePanelPointerUp(event) {
  if (!panelDragState || panelDragState.pointerId !== event.pointerId) return
  panelDragState = null
  panelDragActive.value = false
  localStorage.setItem(
    PANEL_POSITION_KEY,
    JSON.stringify({ x: panelPosition.x, y: panelPosition.y }),
  )
}

function handleResize() {
  viewport.width = window.innerWidth
  viewport.height = window.innerHeight
  const next = clampPosition(position.x, position.y)
  position.x = next.x
  position.y = next.y
  const nextPanel = clampPanelPosition(panelPosition.x, panelPosition.y)
  panelPosition.x = nextPanel.x
  panelPosition.y = nextPanel.y
}

function togglePanel() {
  panelOpen.value = !panelOpen.value
  unread.value = false
  scrollToBottom()
}

function toggleExpanded() {
  panelExpanded.value = !panelExpanded.value
  scrollToBottom()
}

function closePanel() {
  panelOpen.value = false
  panelExpanded.value = false
}

function displayText(content) {
  return String(content || '')
    .replace(/\r\n/g, '\n')
    .replace(/\*\*([^*]+)\*\*/g, '$1')
    .replace(/`([^`]+)`/g, '$1')
    .replace(/^#{1,6}\s+/gm, '')
    .replace(/\n{3,}/g, '\n\n')
    .trim()
}

function textSegments(content) {
  const text = displayText(content)
  if (!text) return []
  if (!wordSegmenter) return [{ text, breakAfter: false }]
  return Array.from(wordSegmenter.segment(text), (item) => ({
    text: item.segment,
    breakAfter:
      item.isWordLike ||
      /[\s，。！？；：、,.!?;:]$/.test(item.segment),
  }))
}

function displayHtml(content) {
  return textSegments(content)
    .map(
      (segment) =>
        escapeHtml(segment.text) + (segment.breakAfter ? '<wbr>' : ''),
    )
    .join('')
}

function escapeHtml(value) {
  return String(value).replace(
    /[&<>"']/g,
    (character) =>
      ({
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#39;',
      })[character],
  )
}

function scrollToBottom() {
  nextTick(() => {
    const area = messageAreaRef.value
    if (area) area.scrollTop = area.scrollHeight
  })
}

function clearChat() {
  resetConversation(true)
}

function resetConversation(keepPanelOpen = false) {
  messages.value = [welcomeMessage()]
  draft.value = ''
  activeAgent.value = 'main'
  pendingActionToken.value = ''
  pendingAction.value = null
  unread.value = false
  loading.value = false
  if (!keepPanelOpen) {
    panelOpen.value = false
    panelExpanded.value = false
  }
}

async function sendMessage(overrideText = null, forceConfirmation = false) {
  const content = (
    typeof overrideText === 'string' ? overrideText : draft.value
  ).trim()
  if (!content || loading.value) return
  const requestOwner = currentIdentity()

  const history = messages.value.map(({ role, content: text }) => ({
    role,
    content: text,
  }))
  messages.value.push({
    id: messageId++,
    role: 'user',
    content,
    sources: [],
    createdAt: createTimestamp(),
  })
  draft.value = ''
  loading.value = true
  scrollToBottom()

  try {
    const result = await chatWithMainAgent({
      message: content,
      history,
      activeAgent: activeAgent.value,
      pendingActionToken: pendingActionToken.value || null,
      confirmationApproved:
        Boolean(pendingActionToken.value) &&
        (forceConfirmation || isConfirmationPhrase(content)),
    })
    if (currentIdentity() !== requestOwner) return
    activeAgent.value = result?.activeAgent || 'main'
    pendingAction.value = result?.pendingAction || null
    pendingActionToken.value = result?.pendingAction?.token || ''
    messages.value.push({
      id: messageId++,
      role: 'assistant',
      content: result?.reply || '我暂时没有得到有效回答。',
      sources: result?.sources || [],
      agentLabel: currentAgent.value.label,
      agentInitial: currentAgent.value.initial,
      agentKey: activeAgent.value,
      createdAt: createTimestamp(),
    })
    if (!panelOpen.value) unread.value = true
  } catch (error) {
    if (currentIdentity() !== requestOwner) return
    messages.value.push({
      id: messageId++,
      role: 'assistant',
      content: error?.message || '主助手暂时不可用，请稍后重试。',
      sources: [],
      agentInitial: currentAgent.value.initial,
      agentKey: activeAgent.value,
      createdAt: createTimestamp(),
    })
  } finally {
    if (currentIdentity() === requestOwner) {
      loading.value = false
      scrollToBottom()
    }
  }
}

function discardPendingAction() {
  pendingAction.value = null
  pendingActionToken.value = ''
  messages.value.push({
    id: messageId++,
    role: 'assistant',
    content: '已放弃这次待确认操作，数据库没有发生修改。',
    sources: [],
    agentLabel: currentAgent.value.label,
    agentInitial: currentAgent.value.initial,
    agentKey: activeAgent.value,
    createdAt: createTimestamp(),
  })
  scrollToBottom()
}

function isConfirmationPhrase(content) {
  return /^(确认|确认执行|确认预约|确认取消|确认改约|好的[，, ]*确认|是)$/.test(
    content.trim(),
  )
}

function handleKeydown(event) {
  if (event.key === 'Escape' && panelOpen.value) {
    if (panelExpanded.value) {
      panelExpanded.value = false
    } else {
      closePanel()
    }
  }
}

watch(
  () => currentIdentity(),
  (identity) => {
    if (identity === conversationOwner) return
    conversationOwner = identity
    resetConversation()
  },
  { flush: 'sync' },
)

onMounted(() => {
  window.addEventListener('resize', handleResize)
  window.addEventListener('pointermove', handlePointerMove)
  window.addEventListener('pointerup', handlePointerUp)
  window.addEventListener('pointermove', handlePanelPointerMove)
  window.addEventListener('pointerup', handlePanelPointerUp)
  window.addEventListener('pointercancel', handlePointerCancel)
  window.addEventListener('blur', handlePointerCancel)
  window.addEventListener('keydown', handleKeydown)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  window.removeEventListener('pointermove', handlePointerMove)
  window.removeEventListener('pointerup', handlePointerUp)
  window.removeEventListener('pointermove', handlePanelPointerMove)
  window.removeEventListener('pointerup', handlePanelPointerUp)
  window.removeEventListener('pointercancel', handlePointerCancel)
  window.removeEventListener('blur', handlePointerCancel)
  window.removeEventListener('keydown', handleKeydown)
})
</script>
