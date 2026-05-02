<script setup>
/**
 * CodeMirror 6 Wrapper for HTML editing.
 *
 * Light/Dark theme follows the layout-store; HTML language support with
 * syntax highlighting + tag autocomplete.
 */
import { onMounted, onBeforeUnmount, ref, watch } from 'vue'
import { EditorView, basicSetup } from 'codemirror'
import { EditorState, Compartment } from '@codemirror/state'
import { html } from '@codemirror/lang-html'
import { oneDark } from '@codemirror/theme-one-dark'
import { useLayoutStore } from '@/stores/layout'

const props = defineProps({
  modelValue: { type: String, default: '' },
  minHeight: { type: Number, default: 500 },
})
const emit = defineEmits(['update:modelValue'])

const layout = useLayoutStore()
const container = ref(null)
let view = null
const themeCompartment = new Compartment()

function buildExtensions() {
  return [
    basicSetup,
    html({ matchClosingTags: true, autoCloseTags: true }),
    themeCompartment.of(layout.darkMode ? oneDark : []),
    EditorView.lineWrapping,
    EditorView.updateListener.of((u) => {
      if (u.docChanged) {
        emit('update:modelValue', u.state.doc.toString())
      }
    }),
    EditorView.theme({
      '&': {
        minHeight: `${props.minHeight}px`,
        fontSize: '13px',
      },
      '.cm-scroller': {
        fontFamily: '"SF Mono", Monaco, Menlo, Consolas, monospace',
      },
    }),
  ]
}

function createView() {
  if (!container.value) return
  view = new EditorView({
    state: EditorState.create({
      doc: props.modelValue,
      extensions: buildExtensions(),
    }),
    parent: container.value,
  })
}

onMounted(createView)

onBeforeUnmount(() => {
  if (view) {
    view.destroy()
    view = null
  }
})

// Sync external modelValue → editor only if it changed externally (not from editor itself)
watch(
  () => props.modelValue,
  (next) => {
    if (!view) return
    const current = view.state.doc.toString()
    if (next !== current) {
      view.dispatch({
        changes: { from: 0, to: current.length, insert: next || '' },
      })
    }
  },
)

// React to dark-mode changes
watch(
  () => layout.darkMode,
  (dark) => {
    if (view) {
      view.dispatch({
        effects: themeCompartment.reconfigure(dark ? oneDark : []),
      })
    }
  },
)
</script>

<template>
  <div
    ref="container"
    class="rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden"
    :style="{ minHeight: `${minHeight}px` }"
  />
</template>
