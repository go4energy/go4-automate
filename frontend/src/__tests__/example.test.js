import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { h } from 'vue'

// Simple component for testing
const HelloWorld = {
  props: ['msg'],
  setup(props) {
    return () => h('div', { class: 'greeting' }, props.msg)
  }
}

describe('Vitest Setup', () => {
  it('should work', () => {
    expect(1 + 1).toBe(2)
  })

  it('should mount a Vue component', () => {
    const wrapper = mount(HelloWorld, {
      props: { msg: 'Hello Vitest' }
    })
    expect(wrapper.text()).toContain('Hello Vitest')
  })
})
