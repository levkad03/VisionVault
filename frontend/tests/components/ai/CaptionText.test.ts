import CaptionText from '@/components/ai/CaptionText.vue';
import type { Caption } from '@/types/image';
import { mount } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';

function makeCaption(overrides: Partial<Caption> = {}): Caption {
  return {
    id: 'cap-1',
    text: 'a dog sitting on a couch',
    model: 'Salesforce/blip-image-captioning-base',
    ...overrides,
  };
}

describe('CaptionText', () => {
  it('shows a placeholder when there is no caption', () => {
    const wrapper = mount(CaptionText, { props: { caption: null } });
    expect(wrapper.text()).toBe('No caption generated');
  });

  it('renders the caption text', () => {
    const wrapper = mount(CaptionText, { props: { caption: makeCaption() } });

    expect(wrapper.text()).toBe('a dog sitting on a couch');
    expect(wrapper.text()).not.toContain('No caption generated');
  });

  it('replaces the placeholder once a caption arrives', async () => {
    const wrapper = mount(CaptionText, { props: { caption: null } });

    await wrapper.setProps({ caption: makeCaption({ text: 'a red car' }) });

    expect(wrapper.text()).toBe('a red car');
  });
});
